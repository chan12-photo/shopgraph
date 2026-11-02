"""UI2 변경 API의 실제 HTTP·원자성·서버 생존 계약 테스트."""

import json
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


if __name__ == "__main__":
    unittest.main()
