"""ShopGraph의 읽기 전용 로컬 HTTP API.

Python 표준 라이브러리의 HTTPServer만 사용한다. 계산·상태 변경은 ShopGraph 공개 메서드와
search.py 공개 함수가 맡고, 이 모듈은 JSON 변환과 요청 검증만 담당한다.
"""

import json
import logging
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from graph import AGE_BANDS, GENDER_LABELS, GENDERS, GROUP_IDS, GROUP_IDS_BY_GENDER, GROUP_LABELS, K_DEFAULT, K_MAX, ShopGraph
from search import customers_of, group_popular, products_of, recommend
from view import recommendation_scope_label, recommendation_view

_LOGGER = logging.getLogger(__name__)
_DIST_ROOT = Path(__file__).resolve().parent / "frontend" / "dist"
_JSON_TYPE = "application/json; charset=utf-8"
_INT_QUERY = re.compile(r"[0-9]+\Z")
_NOT_FOUND = object()
_MAX_BODY_BYTES = 64 * 1024


class _RequestError(ValueError):
    """요청 본문 자체의 HTTP 상태를 보존하는 입력 오류."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def _json_bytes(payload: dict) -> bytes:
    """JSON 응답 객체를 UTF-8 바이트로 직렬화한다."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _group(g: ShopGraph, group_id: str) -> dict[str, str]:
    """그룹 ID를 공개 표시 객체로 바꾼다."""
    g.members(group_id)
    return {"id": group_id, "label": GROUP_LABELS[group_id]}


def _customer(g: ShopGraph, customer_id: str) -> dict:
    """고객 상세·소속 그룹·S1을 API 객체로 만든다."""
    customer = g.get_customer(customer_id)
    group_id = g.group_of(customer_id)
    return {"customer": customer, "group": _group(g, group_id), "purchases": products_of(g, customer_id)}


def _product(g: ShopGraph, product_id: str) -> dict:
    """상품 상세·S2·재고 상태를 API 객체로 만든다."""
    product = g.get_product(product_id)
    sold_out = g.is_sold_out(product_id)
    return {
        "product": product,
        "buyers": customers_of(g, product_id),
        "sold_out": sold_out,
        "available_colors": g.available_colors(product_id),
        "status_label": "품절" if sold_out else "판매 중",
    }


def _graph(g: ShopGraph) -> dict:
    """그룹·고객·상품 노드와 membership/purchase 간선을 결정적 순서로 만든다."""
    customer_ids = g.customer_ids()
    product_ids = g.product_ids()
    product_set = set(product_ids)
    nodes = []
    for group_id in GROUP_IDS:
        nodes.append({"id": group_id, "kind": "group", "label": GROUP_LABELS[group_id],
                      "neighbor_ids": g.neighbors(group_id)})
    for customer_id in customer_ids:
        nodes.append({"id": customer_id, "kind": "customer", "label": g.get_customer(customer_id)["name"],
                      "neighbor_ids": g.neighbors(customer_id)})
    for product_id in product_ids:
        nodes.append({"id": product_id, "kind": "product", "label": g.get_product(product_id)["name"],
                      "neighbor_ids": g.neighbors(product_id)})

    edges = []
    for group_id in GROUP_IDS:
        edges.extend({"kind": "membership", "source": group_id, "target": customer_id, "weight": None}
                     for customer_id in g.members(group_id))
    for customer_id in customer_ids:
        for product_id in g.neighbors(customer_id):
            if product_id not in product_set:
                continue
            aggregate = g.edge(customer_id, product_id)
            if aggregate is None:
                continue
            edges.append({"kind": "purchase", "source": customer_id, "target": product_id,
                          "weight": g.weight(customer_id, product_id), **aggregate})
    return {"nodes": nodes, "edges": edges}


def _groups(g: ShopGraph) -> dict:
    """성별·연령대 그룹 트리를 공개 상수 순서로 만든다."""
    branches = []
    for gender, _ in GENDERS:
        group_rows = []
        group_ids = GROUP_IDS_BY_GENDER[gender]
        for index, group_id in enumerate(group_ids):
            member_rows = [g.get_customer(customer_id) for customer_id in g.members(group_id)]
            group_rows.append({"id": group_id, "label": GROUP_LABELS[group_id],
                               "band_label": AGE_BANDS[index][1], "count": len(member_rows),
                               "members": member_rows})
        branches.append({"gender": gender, "label": GENDER_LABELS[gender],
                         "count": sum(row["count"] for row in group_rows), "groups": group_rows})
    return {"total_customers": len(g.customer_ids()), "branches": branches}


def _popular(g: ShopGraph, group_id: str, k: int | None) -> dict:
    """S4 반환값에 상품 이름과 판매 상태를 덧붙인다."""
    items = []
    for item in group_popular(g, group_id, k):
        product_id = item["product_id"]
        sold_out = item["sold_out"]
        items.append({**item, "product_name": g.get_product(product_id)["name"],
                      "status_label": "품절" if sold_out else "판매 중"})
    return {"group": _group(g, group_id), "k": k, "items": items}


def _recommendations(g: ShopGraph, customer_id: str, k: int) -> dict:
    """추천 결과와 view.py가 만든 표시 줄 구조를 하나의 JSON 객체로 만든다."""
    result = recommend(g, customer_id, k)
    view = recommendation_view(g, customer_id, result, k)
    items = []
    for item, lines in zip(result, view["items"]):
        product_id = item["product_id"]
        items.append({**item, "product_name": g.get_product(product_id)["name"],
                      "scope_label": recommendation_scope_label(g, customer_id, item["scope"]),
                      "display_lines": list(lines)})
    lines = [view["header"]]
    lines.extend(line for item_lines in view["items"] for line in item_lines)
    lines.extend(view["notices"])
    return {"customer_id": customer_id, "k": k, "items": items,
            "header_line": view["header"], "notice_lines": list(view["notices"]), "lines": lines}


def _integrity(g: ShopGraph) -> dict:
    """무결성 위반 목록과 화면용 줄을 만든다."""
    violations = g.check_integrity()
    if violations:
        lines = [f"[무결성 검사] 위반 {len(violations)}건", *[f"  - {problem}" for problem in violations]]
    else:
        lines = ["[무결성 검사] 위반 없음: 원본과 그래프가 일치함을 확인"]
    return {"violations": violations, "violation_count": len(violations), "lines": lines}


def _query_k(query: str, default: int | None, *, allow_k: bool = True) -> int | None:
    """허용된 경로에서 중복 없는 k 하나를 읽고 숫자 형식만 확인한다."""
    params = parse_qs(query, keep_blank_values=True)
    if not allow_k and params:
        raise ValueError("요청 쿼리: 이 경로에는 쿼리를 사용할 수 없습니다")
    if any(key != "k" for key in params) or len(params.get("k", [])) > 1:
        raise ValueError("요청 쿼리: k는 한 번만 지정할 수 있습니다")
    if "k" not in params:
        return default
    raw = params["k"][0]
    if not raw or _INT_QUERY.fullmatch(raw) is None:
        raise ValueError(f"요청 쿼리: k는 정수여야 합니다 (입력: {raw})")
    return int(raw)


def _valid_host(handler: BaseHTTPRequestHandler) -> bool:
    """Host 헤더가 로컬 서버의 실제 주소인지 확인한다."""
    host = handler.headers.get("Host", "")
    expected = f"127.0.0.1:{handler.server.server_address[1]}"
    return host == expected


def _valid_origin(handler: BaseHTTPRequestHandler) -> bool:
    """Origin이 있으면 현재 로컬 출처와 같은지 확인한다."""
    origin = handler.headers.get("Origin")
    if origin is None:
        return True
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError:
        return False
    return (parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
            and port == handler.server.server_address[1] and parsed.path in ("", "/")
            and not parsed.query and not parsed.fragment)


def _decoded_parts(raw_path: str) -> list[str]:
    """URL 경로를 퍼센트 디코드한 조각 목록으로 만든다."""
    return [unquote(part) for part in urlsplit(raw_path).path.split("/") if part]


def _allowed_methods(raw_path: str) -> tuple[str, ...]:
    """경로에 정의된 메서드 목록을 결정적 순서로 돌려준다."""
    path = urlsplit(raw_path).path
    parts = _decoded_parts(raw_path)
    if path == "/":
        return ("GET",)
    if not path.startswith("/api/"):
        return ("GET",)
    if parts in (["api", "meta"], ["api", "graph"], ["api", "groups"],
                 ["api", "stats"], ["api", "integrity"]):
        return ("GET",)
    if parts == ["api", "customers"]:
        return ("POST",)
    if parts == ["api", "purchases"]:
        return ("POST",)
    if len(parts) == 3 and parts[:2] == ["api", "customers"] and parts[2] != "recommendations":
        return ("GET",)
    if len(parts) == 4 and parts[:2] == ["api", "customers"] and parts[3] == "recommendations":
        return ("GET",)
    if len(parts) == 3 and parts[:2] == ["api", "products"]:
        return ("GET",)
    if len(parts) == 4 and parts[:2] == ["api", "products"] and parts[3] == "stock":
        return ("PUT",)
    if len(parts) == 4 and parts[:2] == ["api", "groups"] and parts[3] == "popular":
        return ("GET",)
    return ()


def _json_pairs(pairs: list[tuple[object, object]]) -> dict:
    """JSON 객체의 중복 키를 거부하면서 딕셔너리로 만든다."""
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"요청 JSON: 중복 키입니다 (입력: {key})")
        result[key] = value
    return result


def _read_json_object(handler: BaseHTTPRequestHandler) -> dict:
    """Content-Length만큼 JSON 객체를 읽고 전송 형식 오류를 400/413/415로 바꾼다."""
    content_type = handler.headers.get("Content-Type", "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise _RequestError(415, "요청 본문은 application/json이어야 합니다")
    raw_length = handler.headers.get("Content-Length")
    if raw_length is None:
        raise _RequestError(400, "요청 본문 길이가 필요합니다")
    try:
        length = int(raw_length)
    except ValueError:
        raise _RequestError(400, "요청 본문 길이가 올바르지 않습니다") from None
    if length < 0:
        raise _RequestError(400, "요청 본문 길이가 올바르지 않습니다")
    if length > _MAX_BODY_BYTES:
        raise _RequestError(413, "요청 본문이 너무 큽니다 (64KiB 이하)")
    try:
        handler.connection.settimeout(2.0)
        raw = handler.rfile.read(length)
    except TimeoutError:
        raise _RequestError(400, "요청 본문을 읽을 수 없습니다") from None
    if len(raw) != length:
        raise _RequestError(400, "요청 본문 길이가 올바르지 않습니다")
    try:
        text = raw.decode("utf-8")
        payload = json.loads(text, object_pairs_hook=_json_pairs,
                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError(
                                 f"요청 JSON: 허용하지 않는 숫자입니다 (입력: {value})")))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        if str(error).startswith("요청 JSON:"):
            raise _RequestError(400, str(error)) from None
        raise _RequestError(400, f"요청 JSON이 올바르지 않습니다: {error}") from None
    if not isinstance(payload, dict):
        raise _RequestError(400, "요청 JSON은 객체여야 합니다")
    return payload


def _require_keys(payload: dict, required: set[str]) -> None:
    """변경 API 본문이 필수 키를 정확히 한 번씩 갖는지 확인한다."""
    missing = sorted(required - set(payload))
    unknown = sorted(set(payload) - required)
    if missing:
        raise ValueError(f"요청 JSON: 필수 키가 없습니다 (입력: {', '.join(missing)})")
    if unknown:
        raise ValueError(f"요청 JSON: 알 수 없는 키입니다 (입력: {', '.join(unknown)})")


def _json_int(value: object, label: str) -> int:
    """JSON 정수 형식과 9자리 전송 제한만 확인하고 범위는 graph.py에 맡긴다."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"요청 JSON: {label}은 JSON 정수여야 합니다 (입력: {value!r})")
    if len(str(abs(value))) > 9:
        raise ValueError(f"요청 JSON: {label}은 9자리 이하 정수여야 합니다 (입력: {value})")
    return value


def _route_post(g: ShopGraph, raw_path: str, payload: dict) -> tuple[int, dict] | object:
    """POST 변경 경로를 ShopGraph 공개 메서드 호출로 변환한다."""
    parsed = urlsplit(raw_path)
    if parsed.query:
        raise ValueError("요청 쿼리: 이 경로에는 쿼리를 사용할 수 없습니다")
    parts = _decoded_parts(raw_path)
    if parts == ["api", "customers"]:
        _require_keys(payload, {"name", "gender", "age"})
        age = _json_int(payload["age"], "나이")
        customer_id = g.add_customer(payload["name"], payload["gender"], age)
        customer = g.get_customer(customer_id)
        group_id = g.group_of(customer_id)
        return 201, {"customer": customer, "group": _group(g, group_id)}
    if parts == ["api", "purchases"]:
        _require_keys(payload, {"customer_id", "product_id", "color", "qty", "date"})
        qty = _json_int(payload["qty"], "수량")
        purchase_id = g.add_purchase(payload["customer_id"], payload["product_id"],
                                     payload["color"], qty, payload["date"])
        edge = g.edge(payload["customer_id"], payload["product_id"])
        return 201, {"purchase_id": purchase_id, "customer_id": payload["customer_id"],
                     "product_id": payload["product_id"], "edge": edge,
                     "weight": g.weight(payload["customer_id"], payload["product_id"])}
    return _NOT_FOUND


def _route_put(g: ShopGraph, raw_path: str, payload: dict) -> tuple[int, dict] | object:
    """PUT 재고 경로를 ShopGraph 공개 메서드 호출로 변환한다."""
    parsed = urlsplit(raw_path)
    if parsed.query:
        raise ValueError("요청 쿼리: 이 경로에는 쿼리를 사용할 수 없습니다")
    parts = _decoded_parts(raw_path)
    if len(parts) != 4 or parts[:2] != ["api", "products"] or parts[3] != "stock":
        return _NOT_FOUND
    _require_keys(payload, {"stock"})
    stock = payload["stock"]
    if not isinstance(stock, dict):
        raise ValueError("요청 JSON: stock은 객체여야 합니다")
    checked_stock: dict[object, int] = {}
    for color, count in stock.items():
        if not isinstance(color, str):
            raise ValueError(f"요청 JSON: 재고 색상 키는 문자열이어야 합니다 (입력: {color!r})")
        checked_stock[color] = _json_int(count, f"재고({color})")
    product_id = parts[2]
    g.update_product(product_id, stock=checked_stock)
    product = g.get_product(product_id)
    sold_out = g.is_sold_out(product_id)
    available = g.available_colors(product_id)
    return 200, {"product": product, "sold_out": sold_out,
                 "available_colors": available,
                 "status_label": "품절" if sold_out else "판매 중"}


def _route_get(g: ShopGraph, raw_path: str) -> dict | object:
    """GET API 경로 하나를 공개 함수 호출 결과로 변환한다."""
    parsed = urlsplit(raw_path)
    parts = _decoded_parts(raw_path)
    if parts == ["api", "meta"]:
        _query_k(parsed.query, None, allow_k=False)
        return {"genders": [{"value": gender, "label": GENDER_LABELS[gender]} for gender, _ in GENDERS],
                "k_default": K_DEFAULT, "k_max": K_MAX}
    if parts == ["api", "graph"]:
        _query_k(parsed.query, None, allow_k=False)
        return _graph(g)
    if parts == ["api", "groups"]:
        _query_k(parsed.query, None, allow_k=False)
        return _groups(g)
    if parts == ["api", "stats"]:
        _query_k(parsed.query, None, allow_k=False)
        return {"stats": g.stats()}
    if parts == ["api", "integrity"]:
        _query_k(parsed.query, None, allow_k=False)
        return _integrity(g)
    if len(parts) == 3 and parts[:2] == ["api", "customers"] and parts[2] != "recommendations":
        _query_k(parsed.query, None, allow_k=False)
        return _customer(g, parts[2])
    if len(parts) == 4 and parts[:2] == ["api", "customers"] and parts[3] == "recommendations":
        k = _query_k(parsed.query, K_DEFAULT)
        if k is None:
            k = K_DEFAULT
        return _recommendations(g, parts[2], k)
    if len(parts) == 3 and parts[:2] == ["api", "products"]:
        _query_k(parsed.query, None, allow_k=False)
        return _product(g, parts[2])
    if len(parts) == 4 and parts[:2] == ["api", "groups"] and parts[3] == "popular":
        k = _query_k(parsed.query, None)
        return _popular(g, parts[2], k)
    return _NOT_FOUND


def _known_path(raw_path: str) -> bool:
    """UI1 읽기 경로와 UI2 예약 변경 경로인지 판정한다."""
    return bool(_allowed_methods(raw_path))


class _RequestHandler(BaseHTTPRequestHandler):
    """HTTP 요청을 한 번에 하나씩 처리하는 API 핸들러."""

    server_version = "ShopGraphHTTP/1.0"
    protocol_version = "HTTP/1.0"
    timeout = 2

    def log_message(self, format: str, *args: object) -> None:
        """기본 stderr 로그 대신 표준 logging으로 보낸다."""
        _LOGGER.info("%s - %s", self.address_string(), format % args)

    def send_error(self, code: int, message: str | None = None,
                   explain: str | None = None) -> None:
        """정의하지 않은 HTTP 메서드도 HTML 501 대신 계약 JSON으로 응답한다."""
        if code == 501:
            if not _valid_host(self) or not _valid_origin(self):
                self._send_json(403, {"error": "허용하지 않는 Host 또는 Origin입니다"})
            elif (allowed := _allowed_methods(getattr(self, "path", ""))):
                self._send_json(405, {"error": "지원하지 않는 메서드입니다"},
                                 {"Allow": ", ".join(allowed)})
            else:
                self._send_json(404, {"error": "없는 경로입니다"})
            return
        super().send_error(code, message, explain)

    def do_GET(self) -> None:
        """GET 요청을 API 또는 안전한 dist 정적 파일로 처리한다."""
        self._dispatch("GET")

    def do_POST(self) -> None:
        """UI2 변경 API 전까지 POST는 허용 메서드 오류로 응답한다."""
        self._dispatch("POST")

    def do_PUT(self) -> None:
        """PUT 변경 API를 처리한다."""
        self._dispatch("PUT")

    def _dispatch(self, method: str) -> None:
        """공통 Host·Origin·경로·예외 처리를 수행한다."""
        if not _valid_host(self) or not _valid_origin(self):
            self._send_json(403, {"error": "허용하지 않는 Host 또는 Origin입니다"})
            return
        parsed = urlsplit(self.path)
        mutation = False
        try:
            allowed = _allowed_methods(self.path)
            if method not in allowed:
                if not allowed:
                    self._send_json(404, {"error": "없는 경로입니다"})
                else:
                    self._send_json(405, {"error": "지원하지 않는 메서드입니다"},
                                     {"Allow": ", ".join(allowed)})
                return
            if method == "POST":
                payload = _read_json_object(self)
                mutation = True
                result = _route_post(self.server.graph, self.path, payload)
                if result is _NOT_FOUND:
                    self._send_json(404, {"error": "없는 경로입니다"})
                    return
                status, response = result
                self._send_json(status, response)
                return
            if method == "PUT":
                payload = _read_json_object(self)
                mutation = True
                result = _route_put(self.server.graph, self.path, payload)
                if result is _NOT_FOUND:
                    self._send_json(404, {"error": "없는 경로입니다"})
                    return
                status, response = result
                self._send_json(status, response)
                return
            if parsed.path == "/":
                self._serve_static(parsed.path, missing_status=503)
                return
            if not parsed.path.startswith("/api/"):
                self._serve_static(parsed.path, missing_status=404)
                return
            payload = _route_get(self.server.graph, self.path)
            if payload is _NOT_FOUND:
                self._send_json(404, {"error": "없는 경로입니다"})
                return
            self._send_json(200, payload)
        except _RequestError as error:
            self._send_json(error.status, {"error": str(error)})
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
        except Exception:
            _LOGGER.exception("웹 요청 처리 중 예외")
            message = ("변경이 반영됐을 수 있습니다. 다시 조회해 확인하세요"
                       if mutation else "서버 처리 중 오류가 발생했습니다")
            self._send_json(500, {"error": message})

    def _serve_static(self, path: str, *, missing_status: int) -> None:
        """frontend/dist 안의 정적 파일만 제공한다 (루트만 dist 없음 503)."""
        if not _DIST_ROOT.is_dir():
            if missing_status == 503:
                self._send_json(503, {"error": "웹 빌드 결과가 없습니다"})
            else:
                self._send_json(404, {"error": "없는 경로입니다"})
            return
        relative = "index.html" if path == "/" else unquote(path.lstrip("/"))
        candidate = (_DIST_ROOT / relative).resolve()
        if _DIST_ROOT.resolve() not in candidate.parents and candidate != _DIST_ROOT.resolve():
            self._send_json(404, {"error": "없는 경로입니다"})
            return
        if not candidate.is_file():
            self._send_json(404, {"error": "없는 경로입니다"})
            return
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self._send_bytes(200, body, content_type)

    def _send_json(self, status: int, payload: dict, extra_headers: dict[str, str] | None = None) -> None:
        """JSON 응답을 공통 헤더와 함께 보낸다."""
        self._send_bytes(status, _json_bytes(payload), _JSON_TYPE, extra_headers)

    def _send_bytes(self, status: int, body: bytes, content_type: str,
                    extra_headers: dict[str, str] | None = None) -> None:
        """바이트 응답을 쓰고 연결을 닫는다."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        self.close_connection = True


class _ShopGraphHTTPServer(HTTPServer):
    """그래프 하나를 보관하는 순차 처리 HTTPServer."""

    allow_reuse_address = True


def create_server(g: ShopGraph, port: int = 8000) -> HTTPServer:
    """127.0.0.1에 ShopGraph 읽기 API 서버를 만든다.

    인자:
        g: 요청 동안 유지할 ShopGraph 객체.
        port: 바인드할 포트. 0이면 운영체제가 빈 포트를 정한다.

    반환:
        아직 serve_forever를 시작하지 않은 순차 처리 HTTPServer.

    예외:
        OSError: 포트를 열 수 없을 때.
        TypeError: g가 ShopGraph가 아니거나 port 형식이 잘못될 때.
    """
    if not isinstance(g, ShopGraph):
        raise TypeError("g는 ShopGraph여야 합니다")
    if not isinstance(port, int) or isinstance(port, bool):
        raise TypeError("port는 정수여야 합니다")
    server = _ShopGraphHTTPServer(("127.0.0.1", port), _RequestHandler)
    server.graph = g
    return server
