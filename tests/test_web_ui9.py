"""UI9 외부 버그 검토 반영: 실제 HTTP로 웹 서버 계약 보완을 확인한다.

기대값은 찬일 11/07 판정(D-A·D-B), docs/verification/ui0_design.md 3절,
docs/verification/bug_review_1107.md의 재현 입력에서 가져온다.
"""

import json
import socket
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from pathlib import Path
from unittest import mock

import main
import web
from tests.fixtures import make_graph
from tests.helpers import snapshot
from tests.test_web import _ServerHarness
from view import recommendation_scope_label

_UNCERTAIN = "변경이 반영됐을 수 있습니다. 다시 조회해 확인하세요"
_BAD_TEXT = "요청 JSON: 표현할 수 없는 문자가 있습니다"
_DEEP = "요청 JSON: 너무 깊게 중첩되어 있습니다"
_FORBIDDEN = "허용하지 않는 Host 또는 Origin입니다"
_BAD_LENGTH = "요청 본문 길이가 올바르지 않습니다"
_MISSING = "없는 경로입니다"


def _customer_body(**changes: object) -> bytes:
    """정상 고객 등록 본문에 changes를 덮어쓴 ASCII JSON 바이트를 만든다.

    인자: changes는 바꿀 키와 값. 반환: 본문 바이트. 예외: 없음.
    """
    return json.dumps({"name": "새 고객", "gender": "여", "age": 22, **changes}).encode("ascii")


def _purchase_body(**changes: object) -> bytes:
    """정상 구매 등록 본문에 changes를 덮어쓴 ASCII JSON 바이트를 만든다.

    인자: changes는 바꿀 키와 값. 반환: 본문 바이트. 예외: 없음.
    """
    record = {"customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": 2,
              "date": "2026-10-03"}
    return json.dumps({**record, **changes}).encode("ascii")


class _WireCase(unittest.TestCase):
    """실제 서버를 켜고 요청 바이트를 그대로 보내는 공통 도구."""

    def setUp(self) -> None:
        self.harness = _ServerHarness()
        self.address = self.harness.server.server_address
        self.host = f"127.0.0.1:{self.address[1]}"

    def tearDown(self) -> None:
        self.harness.close()

    def wire(self, request: bytes) -> tuple[int, dict[str, str], bytes]:
        """요청 바이트를 소켓으로 보내고 상태·헤더·본문을 돌려준다.

        인자: request는 요청 전체 바이트. 반환: (상태, 소문자 헤더 사전, 본문).
        예외: OSError는 전송 실패, ValueError는 HTTP 상태 줄이 없을 때.
        """
        chunks = []
        with socket.create_connection(self.address, timeout=5) as connection:
            connection.sendall(request)
            try:
                while chunk := connection.recv(65536):
                    chunks.append(chunk)
            except ConnectionResetError:
                # 읽지 않은 본문을 남기고 거절하면 응답 뒤에 RST가 올 수 있다
                self.assertTrue(chunks, "응답을 받기 전에 연결이 끊김")
        head, _, body = b"".join(chunks).partition(b"\r\n\r\n")
        lines = head.decode("iso-8859-1").split("\r\n")
        headers = {}
        for line in lines[1:]:
            key, _, value = line.partition(":")
            headers[key.lower()] = value.strip()
        return int(lines[0].split()[1]), headers, body

    def message(self, method: str, path: str, body: bytes = b"",
                headers: tuple[tuple[str, str], ...] = (), *, host: bool = True,
                length: bool = True) -> bytes:
        """HTTP/1.1 요청 바이트를 조립한다.

        인자: 메서드·경로·본문·추가 헤더, Host와 자동 Content-Length를 넣을지 여부.
        반환: 요청 전체 바이트. 예외: UnicodeEncodeError는 헤더가 latin-1이 아닐 때.
        """
        lines = [f"{method} {path} HTTP/1.1"]
        if host:
            lines.append(f"Host: {self.host}")
        lines.extend(f"{key}: {value}" for key, value in headers)
        if method in ("POST", "PUT"):
            lines.append("Content-Type: application/json")
            if length:
                lines.append(f"Content-Length: {len(body)}")
        return "\r\n".join(lines).encode("iso-8859-1") + b"\r\n\r\n" + body

    def send(self, method: str, path: str, body: bytes = b"",
             headers: tuple[tuple[str, str], ...] = (), **options: bool) -> tuple[int, dict]:
        """요청을 보내고 상태와 JSON 본문을 돌려준다.

        인자: message와 같다. 반환: (상태, JSON 객체). 예외: json.JSONDecodeError는 본문이 JSON이 아닐 때.
        """
        status, _, raw = self.wire(self.message(method, path, body, headers, **options))
        return status, json.loads(raw.decode("utf-8"))

    def assert_rejected(self, expected: tuple[int, dict], method: str, path: str, body: bytes = b"",
                        headers: tuple[tuple[str, str], ...] = (), **options: bool) -> None:
        """요청이 기대 상태·본문으로 거절되고 전체 상태가 그대로인지 확인한다.

        인자: expected는 (상태, JSON), 나머지는 message와 같다. 반환: 없음.
        예외: AssertionError는 응답이 다르거나 상태가 바뀌었을 때.
        """
        before = snapshot(self.harness.graph)
        self.assertEqual(self.send(method, path, body, headers, **options), expected)
        self.assertEqual(snapshot(self.harness.graph), before)

    def assert_session_usable(self) -> None:
        """거절 뒤 그래프·그룹·통계 조회가 200이고 무결성 위반이 없는지 확인한다.

        인자: 없음. 반환: 없음. 예외: AssertionError는 조회 실패나 위반이 있을 때.
        """
        for path in ("/api/graph", "/api/groups", "/api/stats"):
            self.assertEqual(self.send("GET", path)[0], 200, msg=path)
        self.assertEqual(self.harness.graph.check_integrity(), [])


class TestUI9Surrogate(_WireCase):
    """#1 UTF-8로 표현할 수 없는 문자열과 변경 뒤 응답 실패."""

    def test_surrogate_customer_name_rejected_before_change(self) -> None:
        """이름의 짝 없는 서로게이트는 400이고 ID를 쓰지 않으며 세션을 훼손하지 않는다."""
        self.assert_rejected((400, {"error": _BAD_TEXT}), "POST", "/api/customers",
                             _customer_body(name="\ud800"))
        self.assert_session_usable()
        status, body = self.send("POST", "/api/customers", _customer_body())
        self.assertEqual((status, body["customer"]["id"]), (201, "C07"))
        self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_surrogate_stock_key_rejected_before_change(self) -> None:
        """기존 색상에 서로게이트 색상 키를 더한 재고는 400이고 P01이 그대로 조회된다."""
        stock = {**self.harness.graph.get_product("P01")["stock"], "\ud800": 1}
        self.assert_rejected((400, {"error": _BAD_TEXT}), "PUT", "/api/products/P01/stock",
                             json.dumps({"stock": stock}).encode("ascii"))
        self.assertEqual(self.send("GET", "/api/products/P01")[0], 200)
        self.assert_session_usable()

    def test_surrogate_anywhere_in_body_gets_json_400(self) -> None:
        """구매 값·모르는 키·중첩 배열의 서로게이트도 변경 전에 JSON 400이다."""
        cases = [
            ("/api/purchases", _purchase_body(color="\udfff")),
            ("/api/customers", _customer_body(**{"\ud800": 0})),
            ("/api/customers", _customer_body(extra=[{"a": ["\ud800"]}])),
        ]
        for path, raw in cases:
            with self.subTest(path=path, raw=raw):
                self.assert_rejected((400, {"error": _BAD_TEXT}), "POST", path, raw)
        self.assert_session_usable()

    def test_duplicate_surrogate_key_error_body_is_serialized(self) -> None:
        """오류 문구가 서로게이트를 그대로 담아도 오류 본문은 JSON으로 직렬화된다."""
        raw = b'{"\\ud800":1,"\\ud800":2}'
        self.assert_rejected((400, {"error": "요청 JSON: 중복 키입니다 (입력: \ud800)"}),
                             "POST", "/api/customers", raw)

    def test_encoding_failure_after_change_is_uncertain_500(self) -> None:
        """변경 뒤 직렬화의 UnicodeError는 400이 아니라 불확실성 500이고 변경은 남는다."""
        failure = UnicodeEncodeError("utf-8", "x", 0, 1, "고장 주입")
        with (mock.patch.object(web, "_json_bytes", side_effect=failure),
              self.assertLogs("web", level="ERROR")):
            result = self.send("POST", "/api/customers", _customer_body())
        self.assertEqual(result, (500, {"error": _UNCERTAIN}))
        self.assertEqual(self.harness.graph.get_customer("C07")["name"], "새 고객")
        self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_value_error_after_change_is_uncertain_500(self) -> None:
        """세 변경 경로 모두 변경 메서드가 끝난 뒤의 ValueError를 500으로 보낸다."""
        cases = [
            ("group_of", "POST", "/api/customers", _customer_body()),
            ("edge", "POST", "/api/purchases", _purchase_body()),
            ("is_sold_out", "PUT", "/api/products/P03/stock", b'{"stock":{"\\uc544\\uc774\\ubcf4\\ub9ac":7,'
                                                              b'"\\ub124\\uc774\\ube44":1}}'),
        ]
        for name, method, path, raw in cases:
            with self.subTest(name=name):
                before = snapshot(self.harness.graph)
                with (mock.patch.object(self.harness.graph, name, side_effect=ValueError("고장 주입")),
                      self.assertLogs("web", level="ERROR")):
                    result = self.send(method, path, raw)
                self.assertEqual(result, (500, {"error": _UNCERTAIN}))
                self.assertNotEqual(snapshot(self.harness.graph), before)
                self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_business_value_error_stays_400(self) -> None:
        """변경 메서드가 검증에서 거절한 업무 오류는 그대로 400이고 상태가 불변이다."""
        self.assert_rejected((400, {"error": "나이: 10~99이어야 합니다 (입력: 5)"}),
                             "POST", "/api/customers", _customer_body(age=5))

    def test_read_serialization_failure_is_500_not_400(self) -> None:
        """조회 응답 직렬화 실패는 입력 오류가 아니므로 JSON 500이다."""
        self.harness.graph.add_customer("\ud800", "여", 22)
        with self.assertLogs("web", level="ERROR"):
            result = self.send("GET", "/api/graph")
        self.assertEqual(result, (500, {"error": "서버 처리 중 오류가 발생했습니다"}))


class TestUI9Concurrency(_WireCase):
    """#6 D-A: 연결은 동시에 받고 그래프 처리는 잠금 안에서 한 번에 하나만 한다."""

    def test_idle_connections_do_not_delay_get(self) -> None:
        """무전송 연결 5개가 열려 있어도 GET /api/stats는 0.5초 안에 200이다."""
        idle = [socket.create_connection(self.address, timeout=3) for _ in range(5)]
        try:
            started = time.monotonic()
            status, _ = self.send("GET", "/api/stats")
            elapsed = time.monotonic() - started
        finally:
            for connection in idle:
                connection.close()
        self.assertEqual(status, 200)
        self.assertLess(elapsed, 0.5)

    def test_partial_header_does_not_delay_get(self) -> None:
        """헤더를 보내다 멈춘 연결이 있어도 GET /api/stats는 0.5초 안에 200이다."""
        with socket.create_connection(self.address, timeout=3) as slow:
            slow.sendall(b"GET /api/stats HTTP/1.1\r\nX: ")
            started = time.monotonic()
            status, _ = self.send("GET", "/api/stats")
            elapsed = time.monotonic() - started
        self.assertEqual(status, 200)
        self.assertLess(elapsed, 0.5)

    def test_unfinished_body_does_not_hold_graph_lock(self) -> None:
        """본문을 보내다 멈춘 POST가 있어도 잠금이 비어 있고 다른 GET이 바로 처리된다."""
        with socket.create_connection(self.address, timeout=3) as slow:
            slow.sendall(self.message("POST", "/api/customers", b"", (("Content-Length", "100"),),
                                      length=False))
            started = time.monotonic()
            status, _ = self.send("GET", "/api/stats")
            elapsed = time.monotonic() - started
        self.assertEqual(status, 200)
        self.assertLess(elapsed, 0.5)

    def test_concurrent_posts_get_unique_ids(self) -> None:
        """동시에 보낸 고객 등록 10건은 ID가 겹치지 않고 무결성 위반이 없다."""
        barrier = threading.Barrier(10)

        def post(number: int) -> tuple[int, dict]:
            """모든 스레드가 모인 뒤 고객 하나를 등록한다."""
            barrier.wait(timeout=5)
            return self.send("POST", "/api/customers", _customer_body(name=f"동시{number}"))

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(post, range(10)))
        self.assertEqual([status for status, _ in results], [201] * 10)
        ids = sorted(body["customer"]["id"] for _, body in results)
        self.assertEqual(ids, [f"C{number:02}" for number in range(7, 17)])
        self.assertEqual(self.harness.graph.stats()["customers"], 16)
        self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_graph_requests_wait_for_lock_but_transport_does_not(self) -> None:
        """잠금이 잡혀 있으면 그래프 요청만 기다리고 없는 경로 응답은 바로 나온다."""
        lock = self.harness.server.graph_lock
        results = []
        lock.acquire()
        try:
            waiter = threading.Thread(target=lambda: results.append(self.send("GET", "/api/stats")))
            waiter.start()
            time.sleep(0.2)
            self.assertEqual(results, [])
            self.assertEqual(self.send("GET", "/not-there.js")[0], 404)
        finally:
            lock.release()
        waiter.join(timeout=3)
        self.assertEqual(results[0][0], 200)

    def test_response_built_inside_lock_and_sent_outside(self) -> None:
        """응답 본문은 잠금 안에서 만들고 소켓 쓰기는 잠금 밖에서 한다."""
        lock = self.harness.server.graph_lock
        built, sent = [], []
        real_bytes = web._json_bytes
        real_send = web._RequestHandler._send_bytes

        def spy_bytes(payload: dict) -> bytes:
            """직렬화 시점의 잠금 상태를 기록한다."""
            built.append(lock.locked())
            return real_bytes(payload)

        def spy_send(handler: web._RequestHandler, *args: object) -> None:
            """소켓 쓰기 시점의 잠금 상태를 기록한다."""
            sent.append(lock.locked())
            real_send(handler, *args)

        with (mock.patch.object(web, "_json_bytes", spy_bytes),
              mock.patch.object(web._RequestHandler, "_send_bytes", spy_send)):
            self.assertEqual(self.send("GET", "/api/stats")[0], 200)
            self.assertEqual(self.send("POST", "/api/customers", _customer_body())[0], 201)
        self.assertEqual((built, sent), ([True, True], [False, False]))


class TestUI9Transport(_WireCase):
    """#7·#8·#9 HTTP 메시지 길이·Host·Origin·URL·기본 오류 응답."""

    def test_content_length_must_be_single_ascii_decimal(self) -> None:
        """+N·공백 뒤 문자·두 개인 길이는 400이고 고객이 등록되지 않는다."""
        raw = _customer_body()
        size = str(len(raw))
        cases = [
            (("Content-Length", "+" + size),),
            (("Content-Length", "-1"),),
            (("Content-Length", size + "x"),),
            (("Content-Length", "²"),),
            (("Content-Length", size), ("Content-Length", "0")),
            (("Content-Length", size), ("Content-Length", size)),
        ]
        for headers in cases:
            with self.subTest(headers=headers):
                self.assert_rejected((400, {"error": _BAD_LENGTH}), "POST", "/api/customers", raw,
                                     headers, length=False)

    def test_transfer_encoding_is_rejected_before_change(self) -> None:
        """Transfer-Encoding이 있으면 Content-Length가 맞아도 변경 전에 400이다."""
        self.assert_rejected((400, {"error": "Transfer-Encoding 요청은 지원하지 않습니다"}),
                             "POST", "/api/customers", _customer_body(),
                             (("Transfer-Encoding", "chunked"),))

    def test_huge_content_length_is_413_without_runtime_text(self) -> None:
        """int 자릿수 제한을 넘는 길이도 영어 오류 없이 413이다."""
        self.assert_rejected((413, {"error": "요청 본문이 너무 큽니다 (64KiB 이하)"}),
                             "POST", "/api/customers", b"", (("Content-Length", "9" * 5000),), length=False)

    def test_host_must_be_exactly_one(self) -> None:
        """Host가 없거나 둘이면 첫 값이 맞아도 403이다."""
        self.assert_rejected((403, {"error": _FORBIDDEN}), "GET", "/api/stats", b"",
                             (("Host", "bad.example"),))
        self.assert_rejected((403, {"error": _FORBIDDEN}), "GET", "/api/stats", b"",
                             (("Host", self.host), ("Host", self.host)), host=False)
        self.assert_rejected((403, {"error": _FORBIDDEN}), "GET", "/api/stats", host=False)

    def test_origin_must_be_at_most_one_exact_local_origin(self) -> None:
        """Origin은 최대 하나이고 사용자 정보·경로·다른 스킴이 섞이면 403이다."""
        origin = f"http://{self.host}"
        cases = [
            (("Origin", origin), ("Origin", "http://evil.test")),
            (("Origin", origin), ("Origin", origin)),
            (("Origin", f"http://evil@{self.host}"),),
            (("Origin", f"http://user:pw@{self.host}"),),
            (("Origin", f"{origin}/"),),
            (("Origin", f"{origin}/path"),),
            (("Origin", f"{origin}?x=1"),),
            (("Origin", f"https://{self.host}"),),
            (("Origin", "http://127.0.0.1"),),
        ]
        for headers in cases:
            with self.subTest(headers=headers):
                self.assert_rejected((403, {"error": _FORBIDDEN}), "GET", "/api/stats", b"", headers)
        self.assertEqual(self.send("GET", "/api/stats", b"", (("Origin", origin),))[0], 200)

    def test_invalid_url_gets_json_400(self) -> None:
        """urlsplit이 거절하는 URL은 GET·미지원 메서드 모두 JSON 400이다."""
        for method in ("GET", "POST", "DELETE"):
            with self.subTest(method=method):
                self.assert_rejected((400, {"error": "요청 경로가 올바르지 않습니다"}),
                                     method, "http://[/api/stats")
        self.assertEqual(self.send("GET", "/api/stats")[0], 200)

    def _assert_transport_error(self, request: bytes, status: int, message: str) -> None:
        """BaseHTTPRequestHandler가 낸 오류가 계약 JSON 형식인지 확인한다.

        인자: 요청 바이트, 기대 상태·문구. 반환: 없음. 예외: AssertionError는 형식이 다를 때.
        """
        before = snapshot(self.harness.graph)
        actual, headers, raw = self.wire(request)
        self.assertEqual((actual, json.loads(raw.decode("utf-8"))), (status, {"error": message}))
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(snapshot(self.harness.graph), before)

    def test_url_too_long_is_json_414(self) -> None:
        """요청 줄이 65,536바이트를 넘으면 HTML이 아니라 JSON 414이다."""
        self._assert_transport_error(self.message("GET", "/api/" + "x" * 65536), 414,
                                     "요청 주소가 너무 깁니다")

    def test_too_many_or_long_headers_are_json_431(self) -> None:
        """헤더 110개와 65,536바이트 넘는 헤더 줄은 JSON 431이다."""
        many = tuple((f"X-{number}", "a") for number in range(110))
        self._assert_transport_error(self.message("GET", "/api/stats", b"", many), 431,
                                     "요청 헤더가 너무 크거나 많습니다")
        self._assert_transport_error(self.message("GET", "/api/stats", b"", (("X-Long", "a" * 70000),)),
                                     431, "요청 헤더가 너무 크거나 많습니다")

    def test_bad_request_line_and_version_are_json(self) -> None:
        """요청 줄 형식·HTTP 버전 오류도 상태 줄과 JSON 본문을 받는다."""
        self._assert_transport_error(b"NONSENSE\r\n\r\n", 400, "요청 형식이 올바르지 않습니다")
        self._assert_transport_error(b"GET / HTTP/abc\r\n\r\n", 400, "요청 형식이 올바르지 않습니다")
        self._assert_transport_error(b"GET / HTTP/3.0\r\n\r\n", 505, "지원하지 않는 HTTP 버전입니다")


class TestUI9JsonDecoding(_WireCase):
    """#10·#19 JSON 해독 경계."""

    def test_deep_json_is_400_on_every_version(self) -> None:
        """깊이 2,000 입력은 필수 키가 있든 없든 같은 한국어 400이고 서버는 계속 돈다."""
        deep = b"[" * 2000 + b"0" + b"]" * 2000
        for raw in (b'{"age":' + deep + b"}", b'{"name":"x","gender":"x","age":' + deep + b"}", b"[" * 2000):
            with self.subTest(size=len(raw)):
                self.assert_rejected((400, {"error": _DEEP}), "POST", "/api/customers", raw)
        self.assert_session_usable()

    def test_decoder_recursion_error_is_400(self) -> None:
        """해독기가 RecursionError를 내면 서버 고장이 아니라 입력 오류 400이다."""
        before = snapshot(self.harness.graph)
        with mock.patch.object(web.json, "loads", side_effect=RecursionError("고장 주입")):
            status, _, raw = self.wire(self.message("POST", "/api/customers", _customer_body()))
        self.assertEqual((status, json.loads(raw.decode("utf-8"))), (400, {"error": _DEEP}))
        self.assertEqual(snapshot(self.harness.graph), before)

    def test_depth_limit_counts_only_real_nesting(self) -> None:
        """깊이 제한은 64에서 갈리고 문자열 안의 괄호는 세지 않는다."""
        allowed = b'{"x":' + b"[" * 63 + b"]" * 63 + b"}"
        self.assert_rejected((400, {"error": "요청 JSON: 필수 키가 없습니다 (입력: age, gender, name)"}),
                             "POST", "/api/customers", allowed)
        refused = b'{"x":' + b"[" * 64 + b"]" * 64 + b"}"
        self.assert_rejected((400, {"error": _DEEP}), "POST", "/api/customers", refused)
        before = snapshot(self.harness.graph)
        status, body = self.send("POST", "/api/customers", _customer_body(name='\\"' + "[" * 100))
        self.assertEqual(status, 400)
        self.assertNotEqual(body["error"], _DEEP)
        self.assertEqual(snapshot(self.harness.graph), before)

    def test_integer_over_python_limit_is_korean_400(self) -> None:
        """5,000자리 JSON 정수는 Python 영어 문구 없이 9자리 안내로 거절한다."""
        raw = b'{"age":' + b"9" * 5000 + b"}"
        self.assert_rejected((400, {"error": "요청 JSON: 숫자가 너무 깁니다 (9자리 이하)"}),
                             "POST", "/api/customers", raw)

    def test_invalid_utf8_is_korean_400(self) -> None:
        """잘못된 UTF-8 본문은 코덱 영어 문구 없이 400이다."""
        self.assert_rejected((400, {"error": "요청 JSON: UTF-8로 해독할 수 없습니다"}),
                             "POST", "/api/customers", b"\xff")

    def test_decode_error_reports_line_and_column(self) -> None:
        """둘째 줄의 문법 오류는 줄·칸을 한국어 형식으로 알린다."""
        self.assert_rejected((400, {"error": "요청 JSON: 형식이 올바르지 않습니다 (줄 2, 칸 3)"}),
                             "POST", "/api/customers", b'{\n  x}')


class TestUI9Paths(_WireCase):
    """#11·#16·#17·#19 경로·입력 정리·응답 순서."""

    def test_purchase_ids_and_date_are_trimmed(self) -> None:
        """구매의 고객·상품 ID·날짜 앞뒤 공백은 지우고 응답도 정리된 ID를 쓴다."""
        status, body = self.send("POST", "/api/purchases", _purchase_body(
            customer_id=" C01 ", product_id="\tP03 ", date=" 2026-10-03\n"))
        self.assertEqual(status, 201)
        self.assertEqual(body, {
            "purchase_id": "T014", "customer_id": "C01", "product_id": "P03",
            "edge": {"colors": ["네이비"], "count": 1, "total_qty": 2, "last_date": "2026-10-03"},
            "weight": 1,
        })
        self.assertEqual(self.harness.graph.get_purchase("T014"), {
            "id": "T014", "customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": 2,
            "date": "2026-10-03",
        })
        self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_each_purchase_field_is_trimmed_alone(self) -> None:
        """고객 ID·상품 ID·날짜 각각에만 공백이 있어도 등록된다."""
        for number, field in enumerate(("customer_id", "product_id", "date"), start=14):
            value = json.loads(_purchase_body())[field]
            with self.subTest(field=field):
                status, body = self.send("POST", "/api/purchases", _purchase_body(**{field: f" {value} "}))
                self.assertEqual((status, body["purchase_id"]), (201, f"T{number:03}"))
        self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_non_string_ids_still_fail_in_graph(self) -> None:
        """문자열이 아닌 ID는 공백 정리를 건너뛰고 기존 검증으로 400이다."""
        before = snapshot(self.harness.graph)
        status, body = self.send("POST", "/api/purchases", _purchase_body(customer_id=1))
        self.assertEqual(status, 400)
        self.assertIn("error", body)
        self.assertEqual(snapshot(self.harness.graph), before)

    def test_path_ids_are_trimmed(self) -> None:
        """경로의 고객·상품·그룹 ID도 앞뒤 공백을 지우고 처리한다."""
        status, body = self.send("GET", "/api/customers/%20C01%20")
        self.assertEqual((status, body["customer"]["id"]), (200, "C01"))
        status, body = self.send("GET", "/api/customers/%20C01%20/recommendations?k=1")
        self.assertEqual((status, body["customer_id"]), (200, "C01"))
        status, body = self.send("GET", "/api/products/%20P01%20")
        self.assertEqual((status, body["product"]["id"]), (200, "P01"))
        status, body = self.send("GET", "/api/groups/%20G-F-20%20/popular")
        self.assertEqual((status, body["group"]["id"]), (200, "G-F-20"))
        raw = json.dumps({"stock": {"아이보리": 3, "네이비": 1}}).encode("ascii")
        status, body = self.send("PUT", "/api/products/%20P03%20/stock", raw)
        self.assertEqual((status, body["product"]["stock"]), (200, {"아이보리": 3, "네이비": 1}))
        self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_missing_static_path_is_404_for_every_method(self) -> None:
        """없는 정적 경로는 메서드와 관계없이 404이고, 있는 파일의 메서드 오류는 405로 남는다."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "app.js").write_bytes(b"ok")
            with mock.patch.object(web, "_DIST_ROOT", root):
                for method in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"):
                    with self.subTest(method=method):
                        self.assert_rejected((404, {"error": _MISSING}), method, "/not-there.js")
                self.assertEqual(self.wire(self.message("HEAD", "/not-there.js"))[0], 404)
                status, headers, raw = self.wire(self.message("DELETE", "/app.js"))
                self.assertEqual((status, headers["allow"]), (405, "GET"))
                self.assertEqual(json.loads(raw.decode("utf-8")), {"error": "지원하지 않는 메서드입니다"})
                status, _, raw = self.wire(self.message("GET", "/app.js"))
                self.assertEqual((status, raw), (200, b"ok"))

    def test_static_rules_without_dist(self) -> None:
        """dist가 없으면 다른 정적 경로는 메서드와 관계없이 404다."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(web, "_DIST_ROOT", Path(temp_dir) / "none"):
                self.assert_rejected((404, {"error": _MISSING}), "DELETE", "/app.js")
                self.assert_rejected((404, {"error": _MISSING}), "GET", "/app.js")

    def test_product_stock_is_sorted_by_color_name(self) -> None:
        """GET과 PUT의 Product stock 키는 입력 순서와 상관없이 색상 이름순이다."""
        expected = ["그레이", "네이비", "블랙", "화이트"]
        status, body = self.send("GET", "/api/products/P01")
        self.assertEqual((status, list(body["product"]["stock"])), (200, expected))
        stock = {"화이트": 1, "블랙": 2, "네이비": 3, "그레이": 4}
        status, body = self.send("PUT", "/api/products/P01/stock",
                                 json.dumps({"stock": stock}).encode("ascii"))
        self.assertEqual((status, list(body["product"]["stock"])), (200, expected))
        self.assertEqual(body["product"]["stock"], stock)
        self.assertEqual(list(self.harness.graph.get_product("P01")["stock"]), list(stock))
        self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_long_k_uses_console_digit_rule(self) -> None:
        """10자리 이상 k는 값과 관계없이 한국어 400이고 9자리까지는 범위 검사로 넘어간다."""
        message = "요청 쿼리: k가 너무 깁니다 (9자리 이하)"
        for value in ("9" * 5000, "1234567890", "0000000001"):
            with self.subTest(size=len(value)):
                self.assert_rejected((400, {"error": message}), "GET",
                                     f"/api/groups/G-F-20/popular?k={value}")
                self.assert_rejected((400, {"error": message}), "GET",
                                     f"/api/customers/C01/recommendations?k={value}")
        status, body = self.send("GET", "/api/groups/G-F-20/popular?k=000000001")
        self.assertEqual((status, body["k"]), (200, 1))

    def test_nul_and_overlong_paths_are_json_404(self) -> None:
        """NUL이 든 경로와 파일 이름 한도를 넘는 경로는 영어 문구 없이 JSON 404다."""
        for path in ("/%00", "/app%00.js", "/" + "a" * 5000):
            with self.subTest(size=len(path)):
                self.assert_rejected((404, {"error": _MISSING}), "GET", path)
        status, body = self.send("GET", "/api/customers/%00")
        self.assertEqual(status, 400)
        self.assertIn("존재하지 않는 고객 ID", body["error"])


class TestUI9ScopeLabel(unittest.TestCase):
    """#14 추천 범위 표시 함수의 없는 고객 검증."""

    def test_missing_customer_fails_for_every_scope(self) -> None:
        """없는 고객은 group·gender·all·모르는 범위 모두 고객 오류로 거절한다."""
        g = make_graph()
        before = snapshot(g)
        for scope in ("group", "gender", "all", "other"):
            with self.subTest(scope=scope):
                with self.assertRaisesRegex(ValueError, "존재하지 않는 고객 ID입니다"):
                    recommendation_scope_label(g, "C00", scope)
        self.assertEqual(snapshot(g), before)

    def test_existing_customer_labels_are_unchanged(self) -> None:
        """있는 고객의 표시 이름과 모르는 범위 오류는 이전과 같다."""
        g = make_graph()
        self.assertEqual(recommendation_scope_label(g, "C01", "group"), "같은 그룹")
        self.assertEqual(recommendation_scope_label(g, "C01", "gender"), "여성 전체")
        self.assertEqual(recommendation_scope_label(g, "C04", "gender"), "남성 전체")
        self.assertEqual(recommendation_scope_label(g, "C01", "all"), "전체 고객")
        with self.assertRaisesRegex(ValueError, "알 수 없는 추천 범위입니다"):
            recommendation_scope_label(g, "C01", "other")


class TestUI9MissedMutants(_WireCase):
    """0-2 외부 검토의 변이가 살아남은 경계를 고정한다."""

    def test_body_size_boundary_is_exact(self) -> None:
        """정확히 65,536바이트는 201, 65,537바이트는 413이다."""
        raw = _customer_body().ljust(65536)
        self.assertEqual(len(raw), 65536)
        connection = HTTPConnection(*self.address, timeout=3)
        try:
            connection.request("POST", "/api/customers", body=raw,
                               headers={"Content-Type": "application/json"})
            self.assertEqual(connection.getresponse().status, 201)
        finally:
            connection.close()
        self.assertEqual(self.harness.graph.check_integrity(), [])
        self.assert_rejected((413, {"error": "요청 본문이 너무 큽니다 (64KiB 이하)"}),
                             "POST", "/api/customers", raw + b" ")

    def test_fullwidth_digit_k_is_rejected(self) -> None:
        """전각 숫자 k는 ASCII 숫자가 아니므로 400이다."""
        self.assert_rejected((400, {"error": "요청 쿼리: k는 정수여야 합니다 (입력: １)"}),
                             "GET", "/api/groups/G-F-20/popular?k=%EF%BC%91")

    def test_cache_control_is_no_store(self) -> None:
        """성공·오류 응답 모두 Cache-Control: no-store를 보낸다."""
        for path, status in (("/api/stats", 200), ("/api/customers/C99", 400), ("/not-there.js", 404)):
            with self.subTest(path=path):
                actual, headers, _ = self.wire(self.message("GET", path))
                self.assertEqual((actual, headers["cache-control"]), (status, "no-store"))

    def test_port_65535_is_allowed(self) -> None:
        """--port 인자는 65535까지 허용하고 65536은 거절한다."""
        self.assertEqual(main._web_port("65535"), 65535)
        with self.assertRaisesRegex(ValueError, "포트: 0~65535이어야 합니다"):
            main._web_port("65536")

    def test_gender_menu_rejects_leading_zero(self) -> None:
        """성별 메뉴 번호 "01"은 1로 읽지 않고 거절한다 (현재 동작 고정)."""
        with self.assertRaisesRegex(ValueError, "성별:"):
            main._to_gender("01")


if __name__ == "__main__":
    unittest.main()
