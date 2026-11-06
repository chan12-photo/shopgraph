"""UI2 변경 API의 실제 HTTP·원자성·서버 생존 계약 테스트."""

import json
from http.client import HTTPConnection
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tests.helpers import snapshot
from tests.test_web import _ServerHarness


class TestUI2WebWriteAPI(unittest.TestCase):
    """고객·구매·재고 변경 API를 고정 fixture와 상태 snapshot으로 검증한다."""

    def setUp(self) -> None:
        self.harness = _ServerHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def request_json(self, path: str, payload: object, method: str = "POST") -> tuple[int, dict]:
        if isinstance(payload, bytes):
            data = payload
        else:
            data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = Request(self.harness.base + path, data=data, method=method,
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                return error.code, json.loads(error.read().decode("utf-8"))
            finally:
                error.close()

    def test_customer_success_then_recommendation_is_separate(self) -> None:
        before = snapshot(self.harness.graph)
        status, body = self.request_json("/api/customers", {"name": " 새 고객 ", "gender": "여", "age": 34})
        self.assertEqual(status, 201)
        self.assertEqual(body, {
            "customer": {"id": "C07", "name": "새 고객", "gender": "여", "age": 34},
            "group": {"id": "G-F-30", "label": "여성·30대"},
        })
        self.assertNotIn("recommend", body)
        self.assertEqual(self.harness.graph.check_integrity(), [])
        self.assertNotEqual(snapshot(self.harness.graph), before)
        status, recommendations = self.harness.request("/api/customers/C07/recommendations?k=3")
        self.assertEqual(status, 200)
        self.assertEqual(recommendations["customer_id"], "C07")

    def test_customer_validation_and_id_counter_are_atomic(self) -> None:
        bad_payloads = [
            {"name": "새 고객", "gender": "여"},
            {"name": "새 고객", "gender": "여", "age": 34, "extra": 1},
            {"name": "새 고객", "gender": "여", "age": True},
            {"name": "새 고객", "gender": "여", "age": 34.0},
            {"name": "새 고객", "gender": "여", "age": None},
            {"name": "새 고객", "gender": "여", "age": "34"},
            {"name": "새 고객", "gender": "여", "age": 1000000000},
        ]
        for payload in bad_payloads:
            before = snapshot(self.harness.graph)
            status, body = self.request_json("/api/customers", payload)
            self.assertEqual(status, 400, msg=payload)
            self.assertIn("error", body, msg=payload)
            self.assertEqual(snapshot(self.harness.graph), before, msg=payload)
        before = snapshot(self.harness.graph)
        status, body = self.request_json(
            "/api/customers", '{"name":"새 고객","gender":"여","age":34,"age":35}'.encode("utf-8"))
        self.assertEqual(status, 400)
        self.assertIn("error", body)
        self.assertEqual(snapshot(self.harness.graph), before)
        status, body = self.request_json("/api/customers", {"name": "새 고객", "gender": "여", "age": 34})
        self.assertEqual(status, 201)
        self.assertEqual(body["customer"]["id"], "C07")

    def test_purchase_success_returns_edge_and_weight(self) -> None:
        status, body = self.request_json("/api/purchases", {
            "customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": 2,
            "date": "2026-10-03",
        })
        self.assertEqual(status, 201)
        self.assertEqual(body, {
            "purchase_id": "T014", "customer_id": "C01", "product_id": "P03",
            "edge": {"colors": ["네이비"], "count": 1, "total_qty": 2,
                     "last_date": "2026-10-03"},
            "weight": 1,
        })
        self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_purchase_and_stock_failures_do_not_change_state(self) -> None:
        bad_purchase = [
            {"customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": True,
             "date": "2026-10-03"},
            {"customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": 2.0,
             "date": "2026-10-03"},
            {"customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": None,
             "date": "2026-10-03"},
            {"customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": "2",
             "date": "2026-10-03"},
            {"customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": 1000000000,
             "date": "2026-10-03"},
            {"customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": 2,
             "date": "2026-10-03", "unknown": 1},
        ]
        for payload in bad_purchase:
            before = snapshot(self.harness.graph)
            status, body = self.request_json("/api/purchases", payload)
            self.assertEqual(status, 400, msg=payload)
            self.assertIn("error", body, msg=payload)
            self.assertEqual(snapshot(self.harness.graph), before, msg=payload)
        before = snapshot(self.harness.graph)
        status, body = self.request_json(
            "/api/purchases",
            ('{"customer_id":"C01","product_id":"P03","color":"네이비","qty":2,'
             '"qty":3,"date":"2026-10-03"}').encode("utf-8"))
        self.assertEqual(status, 400)
        self.assertEqual(snapshot(self.harness.graph), before)

        status, body = self.request_json("/api/products/P03/stock", {"stock": {"아이보리": 0, "네이비": 0}},
                                         method="PUT")
        self.assertEqual(status, 200)
        self.assertEqual(body, {
            "product": {"id": "P03", "name": "크롭 가디건", "kind": "상의", "style": "미니멀",
                         "price": 45000, "stock": {"아이보리": 0, "네이비": 0}},
            "sold_out": True, "available_colors": [], "status_label": "품절",
        })
        self.assertEqual(self.harness.graph.check_integrity(), [])

        for payload in ({"stock": {"아이보리": True}}, {"stock": {"아이보리": 1000000000}},
                        {"stock": {}}, {"stock": {"아이보리": 0}, "extra": 1}):
            before = snapshot(self.harness.graph)
            status, body = self.request_json("/api/products/P03/stock", payload, method="PUT")
            self.assertEqual(status, 400, msg=payload)
            self.assertIn("error", body)
            self.assertEqual(snapshot(self.harness.graph), before, msg=payload)

    def test_unexpected_exception_after_mutation_returns_uncertain_500_and_survives(self) -> None:
        original = self.harness.graph.add_customer

        def mutate_then_fail(*args: object, **kwargs: object) -> str:
            customer_id = original(*args, **kwargs)
            raise RuntimeError(f"after {customer_id}")

        with mock.patch.object(self.harness.graph, "add_customer", side_effect=mutate_then_fail):
            status, body = self.request_json("/api/customers", {"name": "예외 고객", "gender": "남", "age": 24})
        self.assertEqual(status, 500)
        self.assertEqual(body, {"error": "변경이 반영됐을 수 있습니다. 다시 조회해 확인하세요"})
        status, customer = self.harness.request("/api/customers/C07")
        self.assertEqual(status, 200)
        self.assertEqual(customer["customer"]["name"], "예외 고객")
        self.assertEqual(self.harness.graph.check_integrity(), [])


    def _assert_raw_rejected(self, path: str, raw: bytes, status: int, message: str,
                             method: str = "POST", content_type: str | None = "application/json") -> None:
        """실제 HTTP의 오류 코드·문구와 원본·그래프·ID 카운터 전체 불변을 확인한다.

        인자: 경로, 원시 본문, 기대 코드·문구, 메서드, Content-Type(None이면 헤더 생략).
        반환: 없음. 예외: HTTP 전송 실패 또는 계약 불일치 시 테스트 실패.
        """
        before = snapshot(self.harness.graph)
        connection = HTTPConnection(*self.harness.server.server_address, timeout=2)
        headers = {} if content_type is None else {"Content-Type": content_type}
        try:
            # urllib는 본문이 있으면 Content-Type을 자동 추가하므로 누락 검사는 http.client로 보낸다.
            connection.request(method, path, body=raw, headers=headers)
            response = connection.getresponse()
            actual_status, body = response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()
        self.assertEqual(snapshot(self.harness.graph), before)
        self.assertEqual((actual_status, body), (status, {"error": message}))

    def test_stock_mixed_valid_invalid_is_atomic(self) -> None:
        """P03 아이보리 2→3 뒤 네이비 -1 거절 시 유효한 앞 항목도 반영되지 않는다."""
        raw = '{"stock":{"아이보리":3,"네이비":-1}}'.encode("utf-8")
        self._assert_raw_rejected("/api/products/P03/stock", raw, 400,
                                  "재고: 0 이상이어야 합니다 (입력: -1)", method="PUT")

    def test_stock_nested_duplicate_key_is_rejected(self) -> None:
        """중첩 stock의 아이보리 중복은 마지막 값 덮어쓰기 없이 요청 전체를 거절한다."""
        raw = '{"stock":{"아이보리":3,"아이보리":4,"네이비":0}}'.encode("utf-8")
        self._assert_raw_rejected("/api/products/P03/stock", raw, 400,
                                  "요청 JSON: 중복 키입니다 (입력: 아이보리)",
                                  method="PUT")

    def test_nonfinite_json_numbers_are_rejected(self) -> None:
        """NaN·Infinity·-Infinity는 업무 검증 이전에 JSON 상수 오류로 거절한다."""
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                raw = ('{"name":"새 고객","gender":"여","age":' + value + '}').encode("utf-8")
                self._assert_raw_rejected("/api/customers", raw, 400,
                                          "요청 JSON: 허용하지 않는 숫자입니다 "
                                          f"(입력: {value})")

    def test_body_over_64kib_is_rejected(self) -> None:
        """유효한 고객 JSON 뒤 공백을 붙인 65537바이트 요청은 파싱·변경 전에 413이다."""
        raw = '{"name":"새 고객","gender":"여","age":25}'.encode("utf-8")
        raw += b" " * (65537 - len(raw))
        self._assert_raw_rejected("/api/customers", raw, 413, "요청 본문이 너무 큽니다 (64KiB 이하)")

    def test_non_json_content_types_rejected_before_mutation(self) -> None:
        """세 변경 경로 모두 text/plain·Content-Type 누락을 415로 거절하고 상태를 보존한다."""
        requests = [
            ("POST", "/api/customers", {"name": "새 고객", "gender": "여", "age": 25}),
            ("POST", "/api/purchases", {"customer_id": "C01", "product_id": "P03", "color": "네이비",
                                      "qty": 1, "date": "2026-10-03"}),
            ("PUT", "/api/products/P03/stock", {"stock": {"아이보리": 3, "네이비": 1}}),
        ]
        for method, path, payload in requests:
            for content_type in ("text/plain", None):
                with self.subTest(method=method, path=path, content_type=content_type):
                    self._assert_raw_rejected(path, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                              415, "요청 본문은 application/json이어야 합니다",
                                              method, content_type)

    def test_purchased_color_removal_is_rejected(self) -> None:
        """P03 아이보리는 T008·T009의 구매 색상이므로 재고 교체에서 뺄 수 없다."""
        self._assert_raw_rejected("/api/products/P03/stock", '{"stock":{"네이비":3}}'.encode("utf-8"),
                                  400, "구매 기록이 있는 색상은 삭제할 수 없습니다: 아이보리", method="PUT")

    def test_impossible_purchase_date_is_rejected(self) -> None:
        """2026-02-30 구매는 거절하며, 이어지는 정상 구매에는 다음 ID T014가 발급된다."""
        payload = {"customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": 1,
                   "date": "2026-02-30"}
        self._assert_raw_rejected("/api/purchases", json.dumps(payload).encode("utf-8"), 400,
                                  "구매일: 존재하지 않는 날짜입니다 (입력: 2026-02-30)")
        status, body = self.request_json("/api/purchases", {**payload, "date": "2026-02-28"})
        self.assertEqual((status, body["purchase_id"]), (201, "T014"))
        self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_customer_id_limit_over_http(self) -> None:
        """공개 등록으로 C98까지 만든 뒤 HTTP C99 성공·다음 등록 거절과 불변을 확인한다."""
        g = self.harness.graph
        for number in range(7, 99):
            self.assertEqual(g.add_customer("한도 준비", "여", 25), f"C{number:02}")
            self.assertEqual(g.check_integrity(), [])
        status, body = self.request_json("/api/customers", {"name": "마지막 고객", "gender": "여", "age": 25})
        self.assertEqual((status, body["customer"]["id"]), (201, "C99"))
        self.assertEqual(g.check_integrity(), [])
        raw = '{"name":"한도 초과","gender":"여","age":25}'.encode("utf-8")
        self._assert_raw_rejected("/api/customers", raw, 400, "ID 한도 초과: C 번호는 99까지입니다")

    def test_purchase_id_limit_over_http(self) -> None:
        """공개 등록으로 T998까지 만든 뒤 HTTP T999 성공·다음 등록 거절과 불변을 확인한다."""
        g = self.harness.graph
        for number in range(14, 999):
            self.assertEqual(g.add_purchase("C01", "P03", "네이비", 1, "2026-10-03"), f"T{number:03}")
            self.assertEqual(g.check_integrity(), [])
        payload = {"customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": 1,
                   "date": "2026-10-03"}
        status, body = self.request_json("/api/purchases", payload)
        self.assertEqual((status, body["purchase_id"]), (201, "T999"))
        self.assertEqual(g.check_integrity(), [])
        self._assert_raw_rejected("/api/purchases", json.dumps(payload).encode("utf-8"),
                                  400, "ID 한도 초과: T 번호는 999까지입니다")

    def test_stock_exception_after_mutation_returns_uncertain_500(self) -> None:
        """재고 반영 뒤 예외는 불확실성 500이며, 다음 GET으로 반영된 재고를 확인한다."""
        original = self.harness.graph.update_product

        def mutate_then_fail(*args: object, **kwargs: object) -> None:
            """공개 재고 변경 뒤 응답 생성에 해당하는 예외를 주입한다."""
            original(*args, **kwargs)
            raise RuntimeError("after stock update")

        with (mock.patch.object(self.harness.graph, "update_product", side_effect=mutate_then_fail),
              self.assertLogs("web", level="ERROR")):
            status, body = self.request_json("/api/products/P03/stock",
                                             {"stock": {"아이보리": 3, "네이비": 1}}, method="PUT")
        self.assertEqual((status, body), (500, {"error": "변경이 반영됐을 수 있습니다. 다시 조회해 확인하세요"}))
        status, product = self.harness.request("/api/products/P03")
        self.assertEqual(status, 200)
        self.assertEqual(product["product"]["stock"], {"아이보리": 3, "네이비": 1})
        self.assertEqual(self.harness.graph.check_integrity(), [])

    def test_purchase_exception_after_mutation_returns_uncertain_500(self) -> None:
        """구매 반영 뒤 예외의 500 안내와 다음 GET·저장된 T014·무결성을 확인한다."""
        original = self.harness.graph.add_purchase

        def mutate_then_fail(*args: object, **kwargs: object) -> str:
            """공개 구매 등록 뒤 응답 생성에 해당하는 예외를 주입한다."""
            purchase_id = original(*args, **kwargs)
            raise RuntimeError(f"after {purchase_id}")

        payload = {"customer_id": "C01", "product_id": "P03", "color": "네이비", "qty": 2,
                   "date": "2026-10-03"}
        with (mock.patch.object(self.harness.graph, "add_purchase", side_effect=mutate_then_fail),
              self.assertLogs("web", level="ERROR")):
            status, body = self.request_json("/api/purchases", payload)
        self.assertEqual((status, body), (500, {"error": "변경이 반영됐을 수 있습니다. 다시 조회해 확인하세요"}))
        status, customer = self.harness.request("/api/customers/C01")
        self.assertEqual(status, 200)
        self.assertEqual([row["product_id"] for row in customer["purchases"]], ["P01", "P02", "P03"])
        self.assertEqual(self.harness.graph.get_purchase("T014"), {"id": "T014", **payload})
        self.assertEqual(self.harness.graph.check_integrity(), [])


if __name__ == "__main__":
    unittest.main()
