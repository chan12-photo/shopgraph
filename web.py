"""ShopGraph의 로컬 HTTP API.

Python 표준 라이브러리의 ThreadingHTTPServer만 사용한다. 연결은 동시에 받고 그래프 처리는 서버당
잠금 하나로 한 번에 하나씩 한다. 계산·상태 변경은 ShopGraph 공개 메서드와 search.py 공개 함수가
맡고, 이 모듈은 JSON 변환과 요청 검증만 담당한다.
"""

import json
import logging
import mimetypes
import re
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import SplitResult, parse_qs, unquote, urlsplit

from graph import AGE_BANDS, GENDER_LABELS, GENDERS, GROUP_IDS, GROUP_IDS_BY_GENDER, GROUP_LABELS, K_DEFAULT, K_MAX, ShopGraph
from search import customers_of, group_popular, products_of, recommend
from view import recommendation_scope_label, recommendation_view

_LOGGER = logging.getLogger(__name__)
_DIST_ROOT = Path(__file__).resolve().parent / "frontend" / "dist"
_JSON_TYPE = "application/json; charset=utf-8"
_INT_QUERY = re.compile(r"[0-9]+\Z")
_NOT_FOUND = object()
_MAX_BODY_BYTES = 64 * 1024
_MAX_DIGITS = 9
_MAX_JSON_DEPTH = 64
_DEEP_JSON = "요청 JSON: 너무 깊게 중첩되어 있습니다"
_TRANSPORT_ERRORS = {
    400: "요청 형식이 올바르지 않습니다",
    414: "요청 주소가 너무 깁니다",
    431: "요청 헤더가 너무 크거나 많습니다",
    505: "지원하지 않는 HTTP 버전입니다",
}


class _RequestError(ValueError):
    """요청 본문 자체의 HTTP 상태와 응답 헤더를 보존하는 입력 오류."""

    def __init__(self, status: int, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.headers = headers


class _ResponseBuildError(Exception):
    """응답 생성·직렬화 실패. ValueError여도 입력 오류 400으로 바뀌지 않게 감싼다."""


def _json_bytes(payload: dict) -> bytes:
    """JSON 응답 객체를 UTF-8 바이트로 직렬화한다."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _error_bytes(message: str) -> bytes:
    """오류 응답 본문을 어떤 문구에서도 실패하지 않게 직렬화한다.

    인자:
        message: 오류 문구. 짝 없는 서로게이트가 섞여 있어도 된다.

    반환:
        ``{"error": message}`` JSON 바이트. 서로게이트는 JSON 이스케이프 ``\\ud800`` 형태가 된다.

    예외:
        없음.
    """
    text = json.dumps({"error": message}, ensure_ascii=False, separators=(",", ":"))
    return text.encode("utf-8", "backslashreplace")


def _built_response(build: Callable[[], dict]) -> bytes:
    """응답 객체를 만들고 직렬화한다.

    인자:
        build: 응답 객체를 돌려주는 함수.

    반환:
        JSON 응답 바이트.

    예외:
        _ResponseBuildError: 생성·직렬화 중 어떤 예외든 났을 때.
    """
    try:
        return _json_bytes(build())
    except Exception as error:
        raise _ResponseBuildError("응답을 만들 수 없습니다") from error


def _split_url(raw_path: str) -> SplitResult:
    """요청 대상을 나눈다.

    인자:
        raw_path: 요청 줄의 경로 원문.

    반환:
        urlsplit 결과.

    예외:
        _RequestError: URL 형식이 잘못돼 나눌 수 없을 때 (400).
    """
    try:
        return urlsplit(raw_path)
    except ValueError:
        raise _RequestError(400, "요청 경로가 올바르지 않습니다") from None


def _trimmed(value: object) -> object:
    """문자열이면 앞뒤 공백을 지우고, 아니면 graph.py 검증에 그대로 넘긴다."""
    return value.strip() if isinstance(value, str) else value


def _web_product(product: dict) -> dict:
    """Product 응답의 stock 키를 색상 이름순으로 구성한다 (UI0 3.1)."""
    return {**product, "stock": dict(sorted(product["stock"].items()))}


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
    product = _web_product(g.get_product(product_id))
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
    if len(raw) > _MAX_DIGITS:
        raise ValueError(f"요청 쿼리: k가 너무 깁니다 ({_MAX_DIGITS}자리 이하)")
    return int(raw)


def _valid_host(handler: BaseHTTPRequestHandler) -> bool:
    """Host 헤더가 정확히 하나이고 로컬 서버의 실제 주소인지 확인한다."""
    hosts = handler.headers.get_all("Host", [])
    if len(hosts) != 1:
        return False
    host = hosts[0]
    expected = f"127.0.0.1:{handler.server.server_address[1]}"
    return host == expected


def _valid_origin(handler: BaseHTTPRequestHandler) -> bool:
    """Origin이 없거나, 하나이고 ``http://127.0.0.1:<실제 포트>``와 정확히 같은지 확인한다."""
    origins = handler.headers.get_all("Origin", [])
    if len(origins) > 1:
        return False
    origin = origins[0] if origins else None
    if origin is None:
        return True
    return origin == f"http://127.0.0.1:{handler.server.server_address[1]}"


def _decoded_parts(raw_path: str) -> list[str]:
    """URL 경로를 퍼센트 디코드한 조각 목록으로 만든다."""
    return [unquote(part) for part in _split_url(raw_path).path.split("/") if part]


def _static_file(path: str) -> Path | None:
    """정적 경로를 frontend/dist 안의 실제 파일로 바꾼다.

    인자:
        path: URL 경로. ``/``는 index.html을 뜻한다.

    반환:
        dist 안에 있는 파일 경로. 없거나 dist 밖이거나 NUL이 든 경로면 None.

    예외:
        없음.
    """
    relative = "index.html" if path == "/" else unquote(path.lstrip("/"))
    if "\0" in relative:
        return None
    root = _DIST_ROOT.resolve()
    try:
        candidate = (root / relative).resolve()
        return candidate if root in candidate.parents and candidate.is_file() else None
    except OSError:
        return None


def _allowed_methods(raw_path: str) -> tuple[str, ...]:
    """경로에 정의된 메서드 목록을 결정적 순서로 돌려준다."""
    path = _split_url(raw_path).path
    parts = _decoded_parts(raw_path)
    if path == "/":
        return ("GET",)
    if not path.startswith("/api/"):
        return ("GET",) if _static_file(path) is not None else ()
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


def _reject_json_constant(value: str) -> None:
    """json.loads의 parse_constant 훅. NaN·Infinity를 거절한다.

    인자:
        value: ``NaN``, ``Infinity`` 또는 ``-Infinity``.

    반환:
        없음 (항상 예외).

    예외:
        ValueError: 항상.
    """
    raise ValueError(f"요청 JSON: 허용하지 않는 숫자입니다 (입력: {value})")


def _parse_json_int(text: str) -> int:
    """json.loads의 parse_int 훅. Python 자릿수 제한의 영어 오류를 한국어로 바꾼다.

    인자:
        text: JSON 정수 표기 원문.

    반환:
        변환한 정수.

    예외:
        ValueError: int()의 자릿수 제한을 넘을 때.
    """
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"요청 JSON: 숫자가 너무 깁니다 ({_MAX_DIGITS}자리 이하)") from None


def _too_deep(text: str) -> bool:
    """JSON 문자열 밖의 괄호 깊이가 한도를 넘는지 확인한다.

    Python 버전마다 해독기의 재귀 한도가 달라 결과가 갈리므로 해독 전에 같은 기준으로 자른다.

    인자:
        text: 해독 전 JSON 문자열. 문법이 틀려도 된다.

    반환:
        깊이가 _MAX_JSON_DEPTH를 넘으면 True.

    예외:
        없음.
    """
    depth = 0
    in_string = escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > _MAX_JSON_DEPTH:
                return True
        elif char in "]}":
            depth -= 1
    return False


def _require_utf8_text(value: object) -> None:
    """해독한 JSON의 모든 문자열 키·값이 UTF-8로 표현 가능한지 확인한다.

    인자:
        value: 해독한 JSON 값. 깊이는 _too_deep으로 이미 제한돼 있다.

    반환:
        없음.

    예외:
        _RequestError: 짝 없는 서로게이트가 있을 때 (400).
    """
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise _RequestError(400, "요청 JSON: 표현할 수 없는 문자가 있습니다") from None
    elif isinstance(value, dict):
        for key, item in value.items():
            _require_utf8_text(key)
            _require_utf8_text(item)
    elif isinstance(value, list):
        for item in value:
            _require_utf8_text(item)


def _decode_json_object(raw: bytes) -> dict:
    """요청 본문 바이트를 JSON 객체로 해독한다.

    인자:
        raw: 요청 본문.

    반환:
        모든 문자열이 UTF-8로 표현 가능한 JSON 객체.

    예외:
        _RequestError: UTF-8·JSON 해독에 실패하거나 객체가 아닐 때 (400).
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise _RequestError(400, "요청 JSON: UTF-8로 해독할 수 없습니다") from None
    if _too_deep(text):
        raise _RequestError(400, _DEEP_JSON)
    try:
        payload = json.loads(text, object_pairs_hook=_json_pairs, parse_constant=_reject_json_constant,
                             parse_int=_parse_json_int)
    except RecursionError:
        raise _RequestError(400, _DEEP_JSON) from None
    except json.JSONDecodeError as error:
        raise _RequestError(
            400, f"요청 JSON: 형식이 올바르지 않습니다 (줄 {error.lineno}, 칸 {error.colno})") from None
    except ValueError as error:
        raise _RequestError(400, str(error)) from None
    if not isinstance(payload, dict):
        raise _RequestError(400, "요청 JSON은 객체여야 합니다")
    _require_utf8_text(payload)
    return payload


def _content_length(handler: BaseHTTPRequestHandler) -> int:
    """본문 길이 헤더를 읽는다.

    인자:
        handler: 헤더를 읽은 요청 핸들러.

    반환:
        0 이상 _MAX_BODY_BYTES 이하의 본문 길이.

    예외:
        _RequestError: Transfer-Encoding이 있거나 Content-Length가 없거나, 하나의 ASCII 십진수가
            아닐 때 (400). 길이가 한도를 넘을 때 (413).
    """
    if handler.headers.get_all("Transfer-Encoding"):
        raise _RequestError(400, "Transfer-Encoding 요청은 지원하지 않습니다")
    values = handler.headers.get_all("Content-Length", [])
    if not values:
        raise _RequestError(400, "요청 본문 길이가 필요합니다")
    if len(values) != 1 or _INT_QUERY.fullmatch(values[0]) is None:
        raise _RequestError(400, "요청 본문 길이가 올바르지 않습니다")
    try:
        length = int(values[0])
    except ValueError:
        length = _MAX_BODY_BYTES + 1  # int()의 자릿수 제한을 넘는 값도 한도 초과다
    if length > _MAX_BODY_BYTES:
        raise _RequestError(413, "요청 본문이 너무 큽니다 (64KiB 이하)")
    return length


def _read_json_object(handler: BaseHTTPRequestHandler) -> dict:
    """Content-Length만큼 JSON 객체를 읽고 전송 형식 오류를 400/413/415로 바꾼다."""
    content_type = handler.headers.get("Content-Type", "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise _RequestError(415, "요청 본문은 application/json이어야 합니다")
    length = _content_length(handler)
    try:
        handler.connection.settimeout(2.0)
        raw = handler.rfile.read(length)
    except TimeoutError:
        raise _RequestError(400, "요청 본문을 읽을 수 없습니다") from None
    if len(raw) != length:
        raise _RequestError(400, "요청 본문 길이가 올바르지 않습니다")
    return _decode_json_object(raw)


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
    if len(str(abs(value))) > _MAX_DIGITS:
        raise ValueError(f"요청 JSON: {label}은 {_MAX_DIGITS}자리 이하 정수여야 합니다 (입력: {value})")
    return value


def _customer_created(g: ShopGraph, customer_id: str) -> dict:
    """고객 등록 응답 객체를 만든다."""
    customer = g.get_customer(customer_id)
    group_id = g.group_of(customer_id)
    return {"customer": customer, "group": _group(g, group_id)}


def _purchase_created(g: ShopGraph, purchase_id: str, customer_id: str, product_id: str) -> dict:
    """구매 등록 응답 객체를 만든다."""
    return {"purchase_id": purchase_id, "customer_id": customer_id, "product_id": product_id,
            "edge": g.edge(customer_id, product_id), "weight": g.weight(customer_id, product_id)}


def _stock_updated(g: ShopGraph, product_id: str) -> dict:
    """재고 교체 응답 객체를 만든다."""
    product = _web_product(g.get_product(product_id))
    sold_out = g.is_sold_out(product_id)
    available = g.available_colors(product_id)
    return {"product": product, "sold_out": sold_out, "available_colors": available,
            "status_label": "품절" if sold_out else "판매 중"}


def _route_post(g: ShopGraph, raw_path: str, payload: dict) -> tuple[int, Callable[[], dict]] | object:
    """POST 변경 경로를 ShopGraph 공개 메서드 호출로 변환한다.

    인자:
        g: 바꿀 ShopGraph. 호출자가 잠금을 잡고 있어야 한다.
        raw_path: 요청 경로.
        payload: 해독한 JSON 객체.

    반환:
        (상태, 변경 뒤 응답 객체를 만드는 함수). 없는 경로면 _NOT_FOUND.

    예외:
        ValueError: 변경 전 검증 또는 변경 메서드의 검증에 실패했을 때. 이때 g는 바뀌지 않는다.
    """
    parsed = _split_url(raw_path)
    if parsed.query:
        raise ValueError("요청 쿼리: 이 경로에는 쿼리를 사용할 수 없습니다")
    parts = _decoded_parts(raw_path)
    if parts == ["api", "customers"]:
        _require_keys(payload, {"name", "gender", "age"})
        age = _json_int(payload["age"], "나이")
        customer_id = g.add_customer(payload["name"], payload["gender"], age)
        return 201, lambda: _customer_created(g, customer_id)
    if parts == ["api", "purchases"]:
        _require_keys(payload, {"customer_id", "product_id", "color", "qty", "date"})
        qty = _json_int(payload["qty"], "수량")
        customer_id = _trimmed(payload["customer_id"])
        product_id = _trimmed(payload["product_id"])
        purchase_id = g.add_purchase(customer_id, product_id, payload["color"], qty,
                                     _trimmed(payload["date"]))
        return 201, lambda: _purchase_created(g, purchase_id, customer_id, product_id)
    return _NOT_FOUND


def _route_put(g: ShopGraph, raw_path: str, payload: dict) -> tuple[int, Callable[[], dict]] | object:
    """PUT 재고 경로를 ShopGraph 공개 메서드 호출로 변환한다.

    인자:
        g: 바꿀 ShopGraph. 호출자가 잠금을 잡고 있어야 한다.
        raw_path: 요청 경로.
        payload: 해독한 JSON 객체.

    반환:
        (상태, 변경 뒤 응답 객체를 만드는 함수). 없는 경로면 _NOT_FOUND.

    예외:
        ValueError: 변경 전 검증 또는 변경 메서드의 검증에 실패했을 때. 이때 g는 바뀌지 않는다.
    """
    parsed = _split_url(raw_path)
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
    product_id = parts[2].strip()
    g.update_product(product_id, stock=checked_stock)
    return 200, lambda: _stock_updated(g, product_id)


def _route_get(g: ShopGraph, raw_path: str) -> dict | object:
    """GET API 경로 하나를 공개 함수 호출 결과로 변환한다."""
    parsed = _split_url(raw_path)
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
        return _customer(g, parts[2].strip())
    if len(parts) == 4 and parts[:2] == ["api", "customers"] and parts[3] == "recommendations":
        k = _query_k(parsed.query, K_DEFAULT)
        if k is None:
            k = K_DEFAULT
        return _recommendations(g, parts[2].strip(), k)
    if len(parts) == 3 and parts[:2] == ["api", "products"]:
        _query_k(parsed.query, None, allow_k=False)
        return _product(g, parts[2].strip())
    if len(parts) == 4 and parts[:2] == ["api", "groups"] and parts[3] == "popular":
        k = _query_k(parsed.query, None)
        return _popular(g, parts[2].strip(), k)
    return _NOT_FOUND


def _known_path(raw_path: str) -> bool:
    """UI1 읽기 경로와 UI2 예약 변경 경로인지 판정한다."""
    return bool(_allowed_methods(raw_path))


def _checked_url(raw_path: str, method: str) -> SplitResult:
    """경로에 정의된 메서드인지 확인한다.

    인자:
        raw_path: 요청 경로.
        method: HTTP 메서드.

    반환:
        urlsplit 결과.

    예외:
        _RequestError: URL이 잘못됐거나(400), 없는 경로이거나(404), 메서드가 다를 때(405).
    """
    parsed = _split_url(raw_path)
    allowed = _allowed_methods(raw_path)
    if method in allowed:
        return parsed
    if not allowed:
        raise _RequestError(404, "없는 경로입니다")
    raise _RequestError(405, "지원하지 않는 메서드입니다", {"Allow": ", ".join(allowed)})


def _static_response(path: str) -> tuple[int, bytes, str]:
    """frontend/dist 안의 정적 파일 응답을 만든다.

    인자:
        path: URL 경로.

    반환:
        (상태, 파일 바이트, 내용 형식).

    예외:
        _RequestError: 루트인데 dist가 없을 때(503), 파일이 없을 때(404).
    """
    candidate = _static_file(path)
    if candidate is None:
        if path == "/" and not _DIST_ROOT.is_dir():
            raise _RequestError(503, "웹 빌드 결과가 없습니다")
        raise _RequestError(404, "없는 경로입니다")
    content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    return 200, candidate.read_bytes(), content_type


class _RequestHandler(BaseHTTPRequestHandler):
    """요청 읽기·전송 검증은 동시에, 그래프 처리는 서버 잠금 안에서 하는 API 핸들러."""

    server_version = "ShopGraphHTTP/1.0"
    protocol_version = "HTTP/1.0"
    timeout = 2

    def log_message(self, format: str, *args: object) -> None:
        """기본 stderr 로그 대신 표준 logging으로 보낸다."""
        _LOGGER.info("%s - %s", self.address_string(), format % args)

    def send_error(self, code: int, message: str | None = None,
                   explain: str | None = None) -> None:
        """기본 HTML 오류 대신 계약 JSON으로 응답한다. 501은 정의하지 않은 메서드다."""
        if code == 501:
            self._dispatch(self.command)
            return
        if self.request_version == "HTTP/0.9":
            self.request_version = self.protocol_version  # 잘못된 요청 줄에도 상태 줄을 보낸다
        text = _TRANSPORT_ERRORS.get(code, "요청을 처리할 수 없습니다")
        self._send_bytes(code, _error_bytes(text), _JSON_TYPE)

    def do_GET(self) -> None:
        """GET 요청을 API 또는 안전한 dist 정적 파일로 처리한다."""
        self._dispatch("GET")

    def do_POST(self) -> None:
        """POST 변경 API를 처리한다."""
        self._dispatch("POST")

    def do_PUT(self) -> None:
        """PUT 변경 API를 처리한다."""
        self._dispatch("PUT")

    def _dispatch(self, method: str) -> None:
        """공통 Host·Origin·경로·예외 처리를 수행하고 응답을 한 번 보낸다.

        ValueError는 변경 메서드가 끝나기 전 단계에서만 400이 된다. 변경 뒤 응답 생성 실패는
        _ResponseBuildError로 감싸여 불확실성 500이 된다.
        """
        mutation = False
        content_type = _JSON_TYPE
        extra_headers = None
        try:
            if not _valid_host(self) or not _valid_origin(self):
                raise _RequestError(403, "허용하지 않는 Host 또는 Origin입니다")
            parsed = _checked_url(self.path, method)
            if method in ("POST", "PUT"):
                payload = _read_json_object(self)
                mutation = True
                status, body = self._change(method, payload)
            elif parsed.path.startswith("/api/"):
                status, body = 200, self._read_api()
            else:
                status, body, content_type = _static_response(parsed.path)
        except _RequestError as error:
            status, body, extra_headers = error.status, _error_bytes(str(error)), error.headers
        except ValueError as error:
            status, body = 400, _error_bytes(str(error))
        except Exception:
            _LOGGER.exception("웹 요청 처리 중 예외")
            message = ("변경이 반영됐을 수 있습니다. 다시 조회해 확인하세요"
                       if mutation else "서버 처리 중 오류가 발생했습니다")
            status, body = 500, _error_bytes(message)
        self._send_bytes(status, body, content_type, extra_headers)

    def _read_api(self) -> bytes:
        """잠금 안에서 GET API를 조회하고 응답 본문을 만든다."""
        with self.server.graph_lock:
            payload = _route_get(self.server.graph, self.path)
            if payload is _NOT_FOUND:
                raise _RequestError(404, "없는 경로입니다")
            return _built_response(lambda: payload)

    def _change(self, method: str, payload: dict) -> tuple[int, bytes]:
        """잠금 안에서 변경 메서드를 부르고 응답 본문을 만든다."""
        route = _route_post if method == "POST" else _route_put
        with self.server.graph_lock:
            result = route(self.server.graph, self.path, payload)
            if result is _NOT_FOUND:
                raise _RequestError(404, "없는 경로입니다")
            status, build = result
            return status, _built_response(build)

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


class _ShopGraphHTTPServer(ThreadingHTTPServer):
    """그래프 하나와 그 처리 잠금을 보관하는 동시 수신 HTTP 서버."""

    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 32


def create_server(g: ShopGraph, port: int = 8000) -> HTTPServer:
    """127.0.0.1에 ShopGraph API 서버를 만든다.

    인자:
        g: 요청 동안 유지할 ShopGraph 객체.
        port: 바인드할 포트. 0이면 운영체제가 빈 포트를 정한다.

    반환:
        아직 serve_forever를 시작하지 않은 HTTPServer. 연결은 동시에 받고 그래프 처리는 잠금으로 하나씩 한다.

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
    server.graph_lock = threading.Lock()
    return server
