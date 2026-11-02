"""UI1 읽기 HTTP API 테스트.

서버는 같은 프로세스의 백그라운드 스레드에서 실제 HTTP로 실행한다. 테스트 그래프는
tests/fixtures.py로 만들고, 응답 전후 snapshot으로 읽기 API의 상태 불변을 확인한다.
"""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tests.fixtures import make_graph
from tests.helpers import snapshot
import web
from web import create_server
import main


class _ServerHarness:
    """UI1 테스트용 HTTPServer의 시작·종료를 관리한다."""

    def __init__(self) -> None:
        self.graph = make_graph()
        self.server = create_server(self.graph, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self) -> None:
        """serve_forever를 멈추고 소켓과 테스트 스레드를 닫는다."""
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def request(self, path: str, method: str = "GET", headers: dict[str, str] | None = None) -> tuple[int, dict]:
        """경로를 실제 HTTP로 요청해 상태 코드와 JSON 본문을 돌려준다."""
        request = Request(self.base + path, method=method, headers=headers or {})
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                return error.code, json.loads(error.read().decode("utf-8"))
            finally:
                error.close()


class TestUI1WebReadAPI(unittest.TestCase):
    """UI1 읽기 경로·오류·서버 생존 계약."""

    def setUp(self) -> None:
        self.harness = _ServerHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def test_meta_graph_groups_stats_integrity(self) -> None:
        """메타·그래프·그룹 트리·통계·무결성 응답의 기본 모양과 상태 불변."""
        before = snapshot(self.harness.graph)
        status, meta = self.harness.request("/api/meta")
        self.assertEqual(status, 200)
        self.assertEqual(meta["k_default"], 3)
        self.assertEqual(meta["k_max"], 10)
        self.assertEqual(meta["genders"], [{"value": "여", "label": "여성"}, {"value": "남", "label": "남성"}])

        status, graph = self.harness.request("/api/graph")
        self.assertEqual(status, 200)
        self.assertEqual(len(graph["nodes"]), 19)
        self.assertEqual(len(graph["edges"]), 15)
        self.assertEqual([node["kind"] for node in graph["nodes"][:8]], ["group"] * 8)
        self.assertTrue(all("neighbor_ids" in node for node in graph["nodes"]))

        status, groups = self.harness.request("/api/groups")
        self.assertEqual(status, 200)
        self.assertEqual(groups["total_customers"], 6)
        self.assertEqual(sum(branch["count"] for branch in groups["branches"]), 6)

        status, stats = self.harness.request("/api/stats")
        self.assertEqual(status, 200)
        self.assertEqual(stats["stats"], {"groups": 8, "customers": 6, "products": 5,
                                           "membership_edges": 6, "purchase_edges": 9, "purchases": 13})
        status, integrity = self.harness.request("/api/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(integrity["violations"], [])
        self.assertEqual(integrity["violation_count"], 0)
        self.assertEqual(snapshot(self.harness.graph), before)

    def test_customer_product_popular_recommendation(self) -> None:
        """S1·S2·S4·추천 경로가 공개 함수 결과와 필요한 표시 필드를 전달한다."""
        before = snapshot(self.harness.graph)
        status, customer = self.harness.request("/api/customers/C01")
        self.assertEqual(status, 200)
        self.assertEqual(customer["customer"]["id"], "C01")
        self.assertEqual(customer["group"]["id"], "G-F-20")
        self.assertEqual([row["product_id"] for row in customer["purchases"]], ["P01", "P02"])

        status, product = self.harness.request("/api/products/P05")
        self.assertEqual(status, 200)
        self.assertEqual(product["product"]["id"], "P05")
        self.assertTrue(product["sold_out"])
        self.assertEqual(product["available_colors"], [])
        self.assertEqual([row["customer_id"] for row in product["buyers"]], ["C03", "C04"])

        status, popular = self.harness.request("/api/groups/G-F-20/popular?k=2")
        self.assertEqual(status, 200)
        self.assertEqual(popular["k"], 2)
        self.assertEqual([item["product_id"] for item in popular["items"]], ["P02", "P01"])
        self.assertTrue(all("status_label" in item and "product_name" in item for item in popular["items"]))

        status, recommendations = self.harness.request("/api/customers/C01/recommendations?k=2")
        self.assertEqual(status, 200)
        self.assertEqual(recommendations["customer_id"], "C01")
        self.assertEqual(recommendations["k"], 2)
        self.assertEqual(recommendations["lines"][0], recommendations["header_line"])
        self.assertEqual(len(recommendations["lines"]),
                         1 + 3 * len(recommendations["items"]) + len(recommendations["notice_lines"]))
        self.assertTrue(all(len(item["display_lines"]) == 3 for item in recommendations["items"]))
        self.assertEqual(snapshot(self.harness.graph), before)

    def test_errors_and_server_survives(self) -> None:
        """없는 경로·ID·쿼리·Host·Origin 뒤에도 서버가 다음 정상 요청을 처리한다."""
        before = snapshot(self.harness.graph)
        self.assertEqual(self.harness.request("/not-found")[0], 404)
        self.assertEqual(self.harness.request("/api/customers/C99")[0], 400)
        self.assertEqual(self.harness.request("/api/groups/G-F-20/popular?k=0")[0], 400)
        self.assertEqual(self.harness.request("/api/groups/G-F-20/popular?k=1&k=2")[0], 400)
        self.assertEqual(self.harness.request("/api/stats?k=1")[0], 400)
        self.assertEqual(self.harness.request("/api/stats", headers={"Host": "localhost"})[0], 403)
        self.assertEqual(self.harness.request("/api/stats", headers={"Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.harness.request("/api/customers", method="POST")[0], 405)
        self.assertEqual(self.harness.request("/api/unknown", method="POST")[0], 404)
        with (mock.patch.object(web, "_route_get", side_effect=RuntimeError("고장")),
              mock.patch.object(web._LOGGER, "exception") as log_exception):
            status, error = self.harness.request("/api/stats")
        self.assertEqual(status, 500)
        self.assertEqual(error["error"], "서버 처리 중 오류가 발생했습니다")
        log_exception.assert_called_once()
        status, stats = self.harness.request("/api/stats")
        self.assertEqual(status, 200)
        self.assertEqual(stats["stats"]["customers"], 6)
        self.assertEqual(snapshot(self.harness.graph), before)

    def test_missing_dist_is_not_api_success(self) -> None:
        """UI3 dist가 아직 없을 때 정적 루트는 API 성공으로 가장하지 않는다."""
        status, body = self.harness.request("/")
        self.assertEqual(status, 503)
        self.assertIn("error", body)

    def test_static_dist_file_and_path_escape(self) -> None:
        """dist 파일은 MIME과 바이트를 보존하고, 없는 정적 경로는 제공하지 않는다."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_bytes(b"<html>ok</html>")
            (root / "assets").mkdir()
            (root / "assets" / "app.js").write_bytes(b"console.log('ok');")
            with mock.patch.object(web, "_DIST_ROOT", root):
                with urlopen(Request(self.harness.base + "/assets/app.js"), timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("javascript", response.headers.get_content_type())
                    self.assertEqual(response.read(), b"console.log('ok');")
                self.assertEqual(self.harness.request("/missing.js")[0], 404)

    def test_main_web_dispatch(self) -> None:
        """main.py의 --web와 임의 포트 인자가 웹 실행 함수로 전달된다."""
        with mock.patch.object(main, "_run_web") as run_web:
            main.main(["--web", "--port", "0"])
        run_web.assert_called_once_with(0)
        with mock.patch.object(main, "_run_web") as run_web:
            main.main(["--web"])
        run_web.assert_called_once_with(8000)
        with mock.patch.object(main, "run") as run_console:
            main.main([])
        run_console.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
