"""UI5: 승인된 기대값과 장면 1~8의 실제 HTTP 응답을 직접 비교한다.

한 HTTPServer를 사용한다. 개별 테스트를 골라 실행해도 이전 장면부터 한 번씩
진행하고 결과를 보관하므로, unittest 메서드 실행 순서에 상태가 의존하지 않는다.
"""

import json
import re
import pathlib
import tempfile
import threading
import unittest
from unittest import mock
from urllib.request import Request, urlopen

import web
from tests import demo_expected_adapter as expected_data

_STAT_KEYS = {"그룹 노드": "groups", "고객 노드": "customers", "상품 노드": "products",
              "소속 간선": "membership_edges", "구매 간선": "purchase_edges", "구매 기록": "purchases"}


class DemoHTTP:
    """전체 기대값 검사 후에만 서버를 만들고, 한 서버로 장면 상태를 이어 간다."""

    def __init__(self) -> None:
        """승인/양식 실패는 서버·그래프 생성 전에 예외로 끝낸다."""
        self.expected = expected_data.load_approved()
        from data import initial_records
        from graph import ShopGraph

        self.server = web.create_server(ShopGraph(*initial_records()), port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        try:
            self.thread.start()
        except BaseException:
            self.server.server_close()
            raise
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.scenes: dict[int, dict] = {}

    def close(self) -> None:
        """serve_forever와 소켓을 반드시 종료한다."""
        try:
            self.server.shutdown()
            self.thread.join(timeout=3)
        finally:
            self.server.server_close()

    def request(self, path: str, method: str = "GET", body: dict | None = None) -> dict:
        """실제 HTTP를 보내고 잘못된 성공 상태 코드·깨진 JSON은 예외로 처리한다."""
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(self.base + path, data=data, method=method,
                          headers={} if body is None else {"Content-Type": "application/json"})
        with urlopen(request, timeout=5) as response:
            wanted = 201 if method == "POST" else 200
            if response.status != wanted:
                raise AssertionError(f"HTTP {method} {path}: {response.status} != {wanted}")
            return json.load(response)

    def change(self, path: str, method: str, body: dict) -> dict:
        """변경 후 실제 무결성 결과가 비어 있지 않으면 즉시 실패한다."""
        response = self.request(path, method, body)
        if self.request("/api/integrity")["violations"] != []:
            raise AssertionError("변경 직후 무결성 위반")
        return response

    def recommend(self, customer_id: str) -> dict:
        """K 생략(Enter와 같은 기본값)으로 추천 HTTP 응답을 읽는다."""
        return self.request(f"/api/customers/{customer_id}/recommendations")

    def through(self, last: int) -> dict:
        """장면 1~last를 아직 안 한 것만 수행하고 last 결과를 반환한다."""
        for scene in range(1, last + 1):
            if scene not in self.scenes:
                self.scenes[scene] = self.run_scene(scene)
        return self.scenes[last]

    def run_scene(self, scene: int) -> dict:
        """w11_scenes 순서로 HTTP만 호출한다. 값은 계산하지 않는다."""
        fixed = lambda key: expected_data.fixed(self.expected, key)
        customer = fixed("C_new")
        if scene == 1:
            return self.request("/api/groups")
        if scene == 2:
            created = self.change("/api/customers", "POST", {"name": "하람", "gender": "여", "age": 25})
            return {"created": created, "recommendation": self.recommend(customer)}
        if scene == 3:
            buys = [self.change("/api/purchases", "POST", {"customer_id": customer, "product_id": fixed("P_top"),
                    "color": fixed(name), "qty": 1, "date": day})
                    for name, day in (("장면 3 색상 1", "2026-10-30"), ("장면 3 색상 2", "2026-10-31"))]
            return {"buys": buys, "detail": self.request(f"/api/customers/{customer}")}
        if scene == 4:
            return self.recommend(customer)
        if scene == 5:
            before = self.request("/api/groups/G-F-20/popular")
            buys = [self.change("/api/purchases", "POST", {"customer_id": "C09", "product_id": "P07",
                    "color": color, "qty": 1, "date": day}) for color, day in
                    (("블랙", "2026-10-30"), ("그레이", "2026-10-30"), ("네이비", "2026-10-31"))]
            return {"before": before, "buys": buys, "after": self.request("/api/groups/G-F-20/popular")}
        if scene == 6:
            before = self.recommend(customer)
            product = fixed("P_top6")
            stock = self.request(f"/api/products/{product}")["product"]["stock"]
            updated = self.change(f"/api/products/{product}/stock", "PUT", {"stock": dict.fromkeys(stock, 0)})
            return {"before": before, "updated": updated, "after": self.recommend(customer)}
        if scene == 7:
            created = self.change("/api/customers", "POST", {"name": "새싹", "gender": "남", "age": 15})
            return {"created": created, "recommendation": self.recommend(fixed("C_new7"))}
        return {"stats": self.request("/api/stats"), "integrity": self.request("/api/integrity")}


class TestUI5WebDemo(unittest.TestCase):
    """8장면의 순서·숫자·색상·지지자·표시 문구를 문서와 직접 대조한다."""

    @classmethod
    def setUpClass(cls) -> None:
        """보호 검사를 통과한 서버 한 개를 만들고 종료 함수를 먼저 등록한다."""
        cls.demo = DemoHTTP()
        cls.addClassCleanup(cls.demo.close)

    def assert_recommendation(self, actual: dict, scene: int, before_stock: bool = False) -> None:
        """추천 배열 전체와 색상 수 안내를 비교한다. 출력 함수는 부르지 않는다."""
        wanted = expected_data.recommendation(self.demo.expected, scene, before_stock)
        keys = ("product_id", "scope", "scope_label", "score", "buyers", "supporters", "available_colors")
        self.assertEqual([{key: row[key] for key in keys} for row in actual["items"]],
                         [{key: row[key] for key in keys} for row in wanted["items"]])
        self.assertEqual(actual["k"], 3)
        for rank, (item, row) in enumerate(zip(actual["items"], wanted["items"]), 1):
            lines = item["display_lines"]
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[0], f" {rank}. {item['product_name']} ({row['product_id']}) - "
                             f"점수 {row['score']}, 구매 고객 {row['buyers']}명 [{row['scope_label']}]")
            self.assertEqual(lines[2], "    구매 가능 색상: " + ", ".join(row["available_colors"]))
            note = re.search(r" \((C[0-9]{2}[은는] .+) 색상 구매\)$", lines[1])
            self.assertEqual(note.group(1) if note else "-", row["color_note"])
            proof = lines[1].split(" 구매", 1)[0]
            self.assertEqual(re.findall(r"C[0-9]{2}", proof), row["supporters"])
        notices = actual["notice_lines"]
        marks = {"넓힘 안내": " ※ 같은 그룹(", "개수 부족 안내": "개를 채우지 못함", "점수 비교 안내": " ※ 점수는 각 범위 안에서"}
        self.assertEqual({name: any(mark in line for line in notices) for name, mark in marks.items()}, wanted["notices"])
        # 문구의 고정 틀은 계획서 5.3.3/W8b 승인 형식. 유무는 demo_expected에서만 읽는다.
        expected_notices = ([" ※ 같은 그룹(남성·10대)에 다른 고객이 없어 '남성 전체'로 넓혀 찾음"]
                            if wanted["notices"]["넓힘 안내"] else [])
        self.assertEqual(notices, expected_notices)
        self.assertEqual(actual["lines"], [actual["header_line"],
                         *[line for item in actual["items"] for line in item["display_lines"]], *expected_notices])

    def assert_popular(self, actual: dict, after: bool) -> None:
        """S4 배열 순서·개수·숫자·판매 상태·중복을 표 전체와 비교한다."""
        keys = ("product_id", "score", "buyers", "status_label", "sold_out")
        self.assertEqual([{key: row[key] for key in keys} for row in actual["items"]],
                         expected_data.popular(self.demo.expected, after))

    def test_01_groups(self) -> None:
        """장면 1: 8개 그룹 전부의 인원을 승인 표와 비교한다."""
        actual = self.demo.through(1)
        groups = [group for branch in actual["branches"] for group in branch["groups"]]
        self.assertEqual([(row["id"], row["count"]) for row in groups],
                         [(row["그룹 ID"], int(row["인원"])) for row in expected_data.rows(self.demo.expected, 1, "그룹별 인원")])

    def test_02_register_recommend(self) -> None:
        """장면 2: 새 ID·소속 그룹·별도 GET 추천을 비교한다."""
        actual = self.demo.through(2)
        self.assertEqual(actual["created"]["customer"]["id"], expected_data.fixed(self.demo.expected, "C_new"))
        self.assertEqual(actual["created"]["group"]["id"], expected_data.value(self.demo.expected, 2, "연결 그룹", "C_new 연결 그룹 ID"))
        self.assertEqual(set(actual["created"]), {"customer", "group"})
        self.assert_recommendation(actual["recommendation"], 2)

    def test_03_purchase_s1(self) -> None:
        """장면 3: 두 구매의 가중치와 S1 집계 전체를 비교한다."""
        actual = self.demo.through(3)
        self.assertEqual([row["weight"] for row in actual["buys"]],
                         [int(row["가중치"]) for row in expected_data.rows(self.demo.expected, 3, "구매 등록 줄 가중치")])
        keys = ("product_id", "colors", "weight", "count", "total_qty", "last_date")
        self.assertEqual([{key: row[key] for key in keys} for row in actual["detail"]["purchases"]], expected_data.s1(self.demo.expected))

    def test_04_recommend_again(self) -> None:
        """장면 4: 구매한 상품이 빠진 추천 표 전체와 비교한다."""
        self.assert_recommendation(self.demo.through(4), 4)

    def test_05_popular_before_after(self) -> None:
        """장면 5: S4 전/후와 세 구매의 가중치를 비교한다."""
        actual = self.demo.through(5)
        self.assert_popular(actual["before"], False)
        self.assertEqual([row["weight"] for row in actual["buys"]], [int(row["가중치"]) for row in
                         expected_data.rows(self.demo.expected, 5, "구매 등록 줄 가중치 (C09–P07)")])
        self.assert_popular(actual["after"], True)

    def test_06_stock_before_after(self) -> None:
        """장면 6: 품절 전 추천·1위·품절 응답·품절 후 추천을 비교한다."""
        actual = self.demo.through(6)
        self.assert_recommendation(actual["before"], 6, True)
        self.assertEqual(actual["before"]["items"][0]["product_id"], expected_data.fixed(self.demo.expected, "P_top6"))
        self.assertTrue(actual["updated"]["sold_out"])
        self.assertEqual(actual["updated"]["available_colors"], [])
        self.assert_recommendation(actual["after"], 6)

    def test_07_widen(self) -> None:
        """장면 7: 새 ID·남성10대 그룹·넓힘 안내까지 비교한다."""
        actual = self.demo.through(7)
        self.assertEqual(actual["created"]["customer"]["id"], expected_data.fixed(self.demo.expected, "C_new7"))
        self.assertEqual(actual["created"]["group"]["id"], expected_data.value(self.demo.expected, 7, "연결 그룹", "C_new7 연결 그룹 ID"))
        self.assert_recommendation(actual["recommendation"], 7)

    def test_08_stats_integrity(self) -> None:
        """장면 8: 통계 6항목과 무결성 위반 수를 직접 비교한다."""
        actual = self.demo.through(8)
        wanted = {_STAT_KEYS[row["항목"]]: int(row["개수"]) for row in expected_data.rows(self.demo.expected, 8, "통계 표")}
        self.assertEqual(actual["stats"], {"stats": wanted})
        count = int(expected_data.value(self.demo.expected, 8, "무결성 검사", "위반 수"))
        self.assertEqual(actual["integrity"]["violation_count"], count)
        self.assertEqual(len(actual["integrity"]["violations"]), count)


class TestUI5DemoGuard(unittest.TestCase):
    """시연 문서의 승인·빈칸·형식 훼손은 데이터 실행과 서버 생성 전에 멈춘다."""

    def check_blocked(self, content: str) -> None:
        """임시 문서만 훼손하고 데이터/서버 실행을 즉시 실패하는 대리로 교체한다."""
        with tempfile.TemporaryDirectory(prefix="shopgraph-ui5-guard-", dir="/tmp") as folder:
            path = pathlib.Path(folder) / "demo_expected.md"
            path.write_text(content, encoding="utf-8")
            with (mock.patch.object(expected_data.legacy, "_EXPECTED_PATH", path),
                  mock.patch.object(expected_data.legacy, "initial_records", side_effect=AssertionError("데이터 실행됨")) as data,
                  mock.patch.object(web, "create_server", side_effect=AssertionError("서버 생성됨")) as server):
                with self.assertRaises(NotImplementedError):
                    DemoHTTP()
                data.assert_not_called()
                server.assert_not_called()

    def test_missing_approval(self) -> None:
        """승인 상태 줄 자체를 지우면 서버 생성 전에 멈춘다."""
        text = expected_data.legacy._EXPECTED_PATH.read_text(encoding="utf-8")
        content = "\n".join(line for line in text.splitlines() if not line.startswith("상태:"))
        self.check_blocked(content)

    def test_last_scene_blank(self) -> None:
        """장면 8의 빈칸도 장면 1 실행 전에 검사한다."""
        text = expected_data.legacy._EXPECTED_PATH.read_text(encoding="utf-8")
        row = next(line for line in text.splitlines() if line.startswith("| 구매 기록 |"))
        self.check_blocked(text.replace(row, "| 구매 기록 |  |"))

    def test_invalid_cell_format(self) -> None:
        """장면 8 통계 칸의 숫자를 문자로 바꾸면 실행을 막는다."""
        text = expected_data.legacy._EXPECTED_PATH.read_text(encoding="utf-8")
        row = next(line for line in text.splitlines() if line.startswith("| 구매 기록 |"))
        self.check_blocked(text.replace(row, "| 구매 기록 | invalid |"))


if __name__ == "__main__":
    unittest.main()
