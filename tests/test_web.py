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

    def raw_request(self, path: str, method: str = "GET",
                    headers: dict[str, str] | None = None) -> tuple[int, object, bytes]:
        """실제 HTTP 응답의 상태·헤더·본문을 돌려준다 (HEAD처럼 본문이 없는 메서드용)."""
        request = Request(self.base + path, method=method, headers=headers or {})
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, response.headers, response.read()
        except HTTPError as error:
            try:
                return error.code, error.headers, error.read()
            finally:
                error.close()


class TestUI1WebReadAPI(unittest.TestCase):
    """UI1 읽기 경로·오류·서버 생존 계약."""

    def setUp(self) -> None:
        self.harness = _ServerHarness()

    def tearDown(self) -> None:
        self.harness.close()

    def _request_unchanged(self, path: str, method: str = "GET",
                           headers: dict[str, str] | None = None) -> tuple[int, dict]:
        """요청 직후 같은 그래프의 전체 snapshot이 그대로인지 확인한다."""
        before = snapshot(self.harness.graph)
        result = self.harness.request(path, method=method, headers=headers)
        self.assertEqual(snapshot(self.harness.graph), before, msg=f"요청 뒤 상태 변경: {method} {path}")
        return result

    def test_meta_graph_groups_stats_integrity(self) -> None:
        """메타·그래프·그룹 트리·통계·무결성의 모든 고정 필드·순서를 비교한다."""
        status, meta = self._request_unchanged("/api/meta")
        self.assertEqual(status, 200)
        self.assertEqual(meta, {
            "genders": [{"value": "여", "label": "여성"}, {"value": "남", "label": "남성"}],
            "k_default": 3, "k_max": 10,
        })

        status, graph = self._request_unchanged("/api/graph")
        self.assertEqual(status, 200)
        expected_nodes = [
            {"id": "G-F-10", "kind": "group", "label": "여성·10대", "neighbor_ids": []},
            {"id": "G-F-20", "kind": "group", "label": "여성·20대", "neighbor_ids": ["C01", "C02", "C03"]},
            {"id": "G-F-30", "kind": "group", "label": "여성·30대", "neighbor_ids": ["C05"]},
            {"id": "G-F-40+", "kind": "group", "label": "여성·40대 이상", "neighbor_ids": []},
            {"id": "G-M-10", "kind": "group", "label": "남성·10대", "neighbor_ids": ["C06"]},
            {"id": "G-M-20", "kind": "group", "label": "남성·20대", "neighbor_ids": ["C04"]},
            {"id": "G-M-30", "kind": "group", "label": "남성·30대", "neighbor_ids": []},
            {"id": "G-M-40+", "kind": "group", "label": "남성·40대 이상", "neighbor_ids": []},
            {"id": "C01", "kind": "customer", "label": "고객1", "neighbor_ids": ["G-F-20", "P01", "P02"]},
            {"id": "C02", "kind": "customer", "label": "고객2", "neighbor_ids": ["G-F-20", "P02", "P03"]},
            {"id": "C03", "kind": "customer", "label": "고객3", "neighbor_ids": ["G-F-20", "P03", "P05"]},
            {"id": "C04", "kind": "customer", "label": "고객4", "neighbor_ids": ["G-M-20", "P01", "P04", "P05"]},
            {"id": "C05", "kind": "customer", "label": "고객5", "neighbor_ids": ["G-F-30"]},
            {"id": "C06", "kind": "customer", "label": "고객6", "neighbor_ids": ["G-M-10"]},
            {"id": "P01", "kind": "product", "label": "오버핏 티셔츠", "neighbor_ids": ["C01", "C04"]},
            {"id": "P02", "kind": "product", "label": "와이드 슬랙스", "neighbor_ids": ["C01", "C02"]},
            {"id": "P03", "kind": "product", "label": "크롭 가디건", "neighbor_ids": ["C02", "C03"]},
            {"id": "P04", "kind": "product", "label": "카고 팬츠", "neighbor_ids": ["C04"]},
            {"id": "P05", "kind": "product", "label": "후드 집업", "neighbor_ids": ["C03", "C04"]},
        ]
        expected_edges = [
            {"kind": "membership", "source": "G-F-20", "target": "C01", "weight": None},
            {"kind": "membership", "source": "G-F-20", "target": "C02", "weight": None},
            {"kind": "membership", "source": "G-F-20", "target": "C03", "weight": None},
            {"kind": "membership", "source": "G-F-30", "target": "C05", "weight": None},
            {"kind": "membership", "source": "G-M-10", "target": "C06", "weight": None},
            {"kind": "membership", "source": "G-M-20", "target": "C04", "weight": None},
            {"kind": "purchase", "source": "C01", "target": "P01", "weight": 4,
             "colors": ["그레이", "네이비", "블랙", "화이트"], "count": 4, "total_qty": 4, "last_date": "2026-10-01"},
            {"kind": "purchase", "source": "C01", "target": "P02", "weight": 1,
             "colors": ["블랙"], "count": 1, "total_qty": 1, "last_date": "2026-09-03"},
            {"kind": "purchase", "source": "C02", "target": "P02", "weight": 2,
             "colors": ["베이지", "블랙"], "count": 2, "total_qty": 2, "last_date": "2026-09-20"},
            {"kind": "purchase", "source": "C02", "target": "P03", "weight": 1,
             "colors": ["아이보리"], "count": 1, "total_qty": 1, "last_date": "2026-09-10"},
            {"kind": "purchase", "source": "C03", "target": "P03", "weight": 1,
             "colors": ["아이보리"], "count": 1, "total_qty": 1, "last_date": "2026-09-12"},
            {"kind": "purchase", "source": "C03", "target": "P05", "weight": 1,
             "colors": ["그레이"], "count": 1, "total_qty": 1, "last_date": "2026-09-18"},
            {"kind": "purchase", "source": "C04", "target": "P01", "weight": 1,
             "colors": ["블랙"], "count": 1, "total_qty": 1, "last_date": "2026-10-02"},
            {"kind": "purchase", "source": "C04", "target": "P04", "weight": 1,
             "colors": ["카키"], "count": 1, "total_qty": 1, "last_date": "2026-09-22"},
            {"kind": "purchase", "source": "C04", "target": "P05", "weight": 1,
             "colors": ["블랙"], "count": 1, "total_qty": 1, "last_date": "2026-09-25"},
        ]
        self.assertEqual(graph, {"nodes": expected_nodes, "edges": expected_edges})
        self.assertEqual(len({node["id"] for node in graph["nodes"]}), len(graph["nodes"]))
        self.assertEqual(len({(edge["source"], edge["target"]) for edge in graph["edges"]}), len(graph["edges"]))

        status, groups = self._request_unchanged("/api/groups")
        self.assertEqual(status, 200)
        self.assertEqual(groups, {
            "total_customers": 6,
            "branches": [
                {"gender": "여", "label": "여성", "count": 4, "groups": [
                    {"id": "G-F-10", "label": "여성·10대", "band_label": "10대", "count": 0, "members": []},
                    {"id": "G-F-20", "label": "여성·20대", "band_label": "20대", "count": 3, "members": [
                        {"id": "C01", "name": "고객1", "gender": "여", "age": 23},
                        {"id": "C02", "name": "고객2", "gender": "여", "age": 25},
                        {"id": "C03", "name": "고객3", "gender": "여", "age": 27},
                    ]},
                    {"id": "G-F-30", "label": "여성·30대", "band_label": "30대", "count": 1, "members": [
                        {"id": "C05", "name": "고객5", "gender": "여", "age": 34},
                    ]},
                    {"id": "G-F-40+", "label": "여성·40대 이상", "band_label": "40대 이상", "count": 0, "members": []},
                ]},
                {"gender": "남", "label": "남성", "count": 2, "groups": [
                    {"id": "G-M-10", "label": "남성·10대", "band_label": "10대", "count": 1, "members": [
                        {"id": "C06", "name": "고객6", "gender": "남", "age": 15},
                    ]},
                    {"id": "G-M-20", "label": "남성·20대", "band_label": "20대", "count": 1, "members": [
                        {"id": "C04", "name": "고객4", "gender": "남", "age": 24},
                    ]},
                    {"id": "G-M-30", "label": "남성·30대", "band_label": "30대", "count": 0, "members": []},
                    {"id": "G-M-40+", "label": "남성·40대 이상", "band_label": "40대 이상", "count": 0, "members": []},
                ]},
            ],
        })

        status, stats = self._request_unchanged("/api/stats")
        self.assertEqual(status, 200)
        self.assertEqual(stats["stats"], {"groups": 8, "customers": 6, "products": 5,
                                           "membership_edges": 6, "purchase_edges": 9, "purchases": 13})
        self.assertEqual(set(stats), {"stats"})
        status, integrity = self._request_unchanged("/api/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(integrity, {
            "violations": [], "violation_count": 0,
            "lines": ["[무결성 검사] 위반 없음: 원본과 그래프가 일치함을 확인"],
        })

    def test_customer_product_popular_recommendation(self) -> None:
        """S1·S2·S4·추천의 필드·순서·화면 줄을 고정 기대값과 비교한다."""
        status, customer = self._request_unchanged("/api/customers/C01")
        self.assertEqual(status, 200)
        self.assertEqual(customer, {
            "customer": {"id": "C01", "name": "고객1", "gender": "여", "age": 23},
            "group": {"id": "G-F-20", "label": "여성·20대"},
            "purchases": [
                {"product_id": "P01", "name": "오버핏 티셔츠", "colors": ["그레이", "네이비", "블랙", "화이트"],
                 "weight": 4, "count": 4, "total_qty": 4, "last_date": "2026-10-01"},
                {"product_id": "P02", "name": "와이드 슬랙스", "colors": ["블랙"],
                 "weight": 1, "count": 1, "total_qty": 1, "last_date": "2026-09-03"},
            ],
        })

        status, product = self._request_unchanged("/api/products/P05")
        self.assertEqual(status, 200)
        self.assertEqual(product, {
            "product": {"id": "P05", "name": "후드 집업", "kind": "아우터", "style": "스트릿", "price": 59000,
                         "stock": {"그레이": 0, "블랙": 0}},
            "buyers": [
                {"customer_id": "C03", "name": "고객3", "group_id": "G-F-20", "colors": ["그레이"]},
                {"customer_id": "C04", "name": "고객4", "group_id": "G-M-20", "colors": ["블랙"]},
            ],
            "sold_out": True, "available_colors": [], "status_label": "품절",
        })

        status, popular = self._request_unchanged("/api/groups/G-F-20/popular?k=2")
        self.assertEqual(status, 200)
        self.assertEqual(popular, {
            "group": {"id": "G-F-20", "label": "여성·20대"}, "k": 2,
            "items": [
                {"product_id": "P02", "score": 3, "buyers": 2, "sold_out": False,
                 "product_name": "와이드 슬랙스", "status_label": "판매 중"},
                {"product_id": "P01", "score": 3, "buyers": 1, "sold_out": False,
                 "product_name": "오버핏 티셔츠", "status_label": "판매 중"},
            ],
        })

        status, recommendations = self._request_unchanged("/api/customers/C01/recommendations?k=2")
        self.assertEqual(status, 200)
        self.assertEqual(recommendations, {
            "customer_id": "C01", "k": 2,
            "items": [
                {"product_id": "P03", "score": 2, "buyers": 2, "scope": "group",
                 "supporters": ["C02", "C03"], "available_colors": ["아이보리"],
                 "product_name": "크롭 가디건", "scope_label": "같은 그룹",
                 "display_lines": [
                     " 1. 크롭 가디건 (P03) - 점수 2, 구매 고객 2명 [같은 그룹]",
                     "    근거: C02, C03이 구매",
                     "    구매 가능 색상: 아이보리",
                 ]},
                {"product_id": "P04", "score": 1, "buyers": 1, "scope": "all",
                 "supporters": ["C04"], "available_colors": ["블랙", "카키"],
                 "product_name": "카고 팬츠", "scope_label": "전체 고객",
                 "display_lines": [
                     " 2. 카고 팬츠 (P04) - 점수 1, 구매 고객 1명 [전체 고객]",
                     "    근거: C04가 구매",
                     "    구매 가능 색상: 블랙, 카키",
                 ]},
            ],
            "header_line": "[추천] 고객1(C01, 여성·20대)님께 추천 (2개)",
            "notice_lines": [
                " ※ 같은 그룹(여성·20대)에서 2개가 안 돼 '여성 전체'로, 그래도 2개가 안 돼 '전체 고객'으로 넓혀 찾음",
                " ※ 점수는 각 범위 안에서 계산한 값이라 범위가 다른 항목끼리 비교하지 않습니다",
            ],
            "lines": [
                "[추천] 고객1(C01, 여성·20대)님께 추천 (2개)",
                " 1. 크롭 가디건 (P03) - 점수 2, 구매 고객 2명 [같은 그룹]",
                "    근거: C02, C03이 구매",
                "    구매 가능 색상: 아이보리",
                " 2. 카고 팬츠 (P04) - 점수 1, 구매 고객 1명 [전체 고객]",
                "    근거: C04가 구매",
                "    구매 가능 색상: 블랙, 카키",
                " ※ 같은 그룹(여성·20대)에서 2개가 안 돼 '여성 전체'로, 그래도 2개가 안 돼 '전체 고객'으로 넓혀 찾음",
                " ※ 점수는 각 범위 안에서 계산한 값이라 범위가 다른 항목끼리 비교하지 않습니다",
            ],
        })

    def test_errors_and_server_survives(self) -> None:
        """없는 경로·ID·쿼리·Host·Origin 뒤에도 서버가 다음 정상 요청을 처리한다."""
        status, body = self._request_unchanged("/not-found")
        self.assertEqual((status, body), (404, {"error": "없는 경로입니다"}))
        status, body = self._request_unchanged("/api/customers/C99")
        self.assertEqual((status, body), (400, {"error": "존재하지 않는 고객 ID입니다 (입력: 'C99')"}))
        status, body = self._request_unchanged("/api/groups/G-F-20/popular?k=0")
        self.assertEqual((status, body), (400, {"error": "개수: 1~10이어야 합니다 (입력: 0)"}))
        status, body = self._request_unchanged("/api/customers/C01/recommendations?k=11")
        self.assertEqual((status, body), (400, {"error": "추천 개수 K: 1~10이어야 합니다 (입력: 11)"}))
        status, body = self._request_unchanged("/api/groups/G-F-20/popular?k=1&k=2")
        self.assertEqual((status, body), (400, {"error": "요청 쿼리: k는 한 번만 지정할 수 있습니다"}))
        status, body = self._request_unchanged("/api/groups/G-F-20/popular?k=")
        self.assertEqual((status, body), (400, {"error": "요청 쿼리: k는 정수여야 합니다 (입력: )"}))
        status, body = self._request_unchanged("/api/stats?k=1")
        self.assertEqual((status, body), (400, {"error": "요청 쿼리: 이 경로에는 쿼리를 사용할 수 없습니다"}))
        status, body = self._request_unchanged("/api/stats", headers={"Host": "localhost"})
        self.assertEqual((status, body), (403, {"error": "허용하지 않는 Host 또는 Origin입니다"}))
        status, body = self._request_unchanged("/api/stats", headers={"Origin": "http://evil.example"})
        self.assertEqual((status, body), (403, {"error": "허용하지 않는 Host 또는 Origin입니다"}))
        status, body = self._request_unchanged("/api/customers", method="POST")
        self.assertEqual((status, body), (415, {"error": "요청 본문은 application/json이어야 합니다"}))
        status, body = self._request_unchanged("/api/unknown", method="POST")
        self.assertEqual((status, body), (404, {"error": "없는 경로입니다"}))
        for method in ("DELETE", "PATCH", "OPTIONS", "TRACE", "CONNECT", "FOO"):
            before = snapshot(self.harness.graph)
            status, headers, raw = self.harness.raw_request("/api/stats", method=method)
            self.assertEqual(status, 405, msg=method)
            self.assertEqual(headers.get("Allow"), "GET", msg=method)
            self.assertEqual(json.loads(raw.decode("utf-8")), {"error": "지원하지 않는 메서드입니다"}, msg=method)
            self.assertEqual(snapshot(self.harness.graph), before, msg=method)
            status, headers, raw = self.harness.raw_request("/api/unknown", method=method)
            self.assertEqual(status, 404, msg=method)
            self.assertEqual(json.loads(raw.decode("utf-8")), {"error": "없는 경로입니다"}, msg=method)
            self.assertEqual(snapshot(self.harness.graph), before, msg=method)
        before = snapshot(self.harness.graph)
        status, headers, raw = self.harness.raw_request("/api/stats", method="HEAD")
        self.assertEqual(status, 405)
        self.assertEqual(headers.get("Allow"), "GET")
        self.assertEqual(raw, b"")
        self.assertEqual(snapshot(self.harness.graph), before)
        status, headers, raw = self.harness.raw_request("/api/unknown", method="HEAD")
        self.assertEqual(status, 404)
        self.assertEqual(raw, b"")
        self.assertEqual(snapshot(self.harness.graph), before)
        status, body = self._request_unchanged("/api/unknown", method="DELETE")
        self.assertEqual((status, body), (404, {"error": "없는 경로입니다"}))
        for method, path, allow in (("GET", "/api/customers", "POST"),
                                   ("DELETE", "/api/customers", "POST"),
                                   ("GET", "/api/products/P03/stock", "PUT"),
                                   ("DELETE", "/api/products/P03/stock", "PUT")):
            before = snapshot(self.harness.graph)
            status, headers, raw = self.harness.raw_request(path, method=method)
            self.assertEqual(status, 405, msg=(method, path))
            self.assertEqual(headers.get("Allow"), allow, msg=(method, path))
            self.assertEqual(json.loads(raw.decode("utf-8")), {"error": "지원하지 않는 메서드입니다"})
            self.assertEqual(snapshot(self.harness.graph), before)
        with (mock.patch.object(web, "_route_get", side_effect=RuntimeError("고장")),
              mock.patch.object(web._LOGGER, "exception") as log_exception):
            status, error = self._request_unchanged("/api/stats")
        self.assertEqual(status, 500)
        self.assertEqual(error["error"], "서버 처리 중 오류가 발생했습니다")
        log_exception.assert_called_once()
        status, stats = self._request_unchanged("/api/stats")
        self.assertEqual(status, 200)
        self.assertEqual(stats["stats"]["customers"], 6)

    def test_k_range_is_delegated_to_search(self) -> None:
        """web.py는 k 형식만 확인하고 1~10 범위와 문구는 search 공개 함수에 맡긴다."""
        before = snapshot(self.harness.graph)
        with mock.patch.object(web, "group_popular", side_effect=ValueError("S4 범위 문구")) as popular:
            with self.assertRaisesRegex(ValueError, "S4 범위 문구"):
                web._route_get(self.harness.graph, "/api/groups/G-F-20/popular?k=11")
        popular.assert_called_once_with(self.harness.graph, "G-F-20", 11)
        with mock.patch.object(web, "recommend", side_effect=ValueError("추천 범위 문구")) as recommender:
            with self.assertRaisesRegex(ValueError, "추천 범위 문구"):
                web._route_get(self.harness.graph, "/api/customers/C01/recommendations?k=0")
        recommender.assert_called_once_with(self.harness.graph, "C01", 0)
        self.assertEqual(snapshot(self.harness.graph), before)

    def test_missing_dist_is_not_api_success(self) -> None:
        """UI3 dist가 아직 없을 때 정적 루트는 API 성공으로 가장하지 않는다."""
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_root = Path(temp_dir) / "not-built-dist"
            with mock.patch.object(web, "_DIST_ROOT", missing_root):
                status, body = self.harness.request("/")
        self.assertEqual(status, 503)
        self.assertIn("error", body)

    def test_static_dist_file_and_path_escape(self) -> None:
        """dist 파일은 MIME과 바이트를 보존하고, 없는 정적 경로는 제공하지 않는다."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "dist"
            root.mkdir()
            (root / "index.html").write_bytes(b"<html>ok</html>")
            (root / "assets").mkdir()
            (root / "assets" / "app.js").write_bytes(b"console.log('ok');")
            (root.parent / "secret.txt").write_bytes(b"TOP_SECRET_DO_NOT_LEAK")
            with mock.patch.object(web, "_DIST_ROOT", root):
                before = snapshot(self.harness.graph)
                with urlopen(Request(self.harness.base + "/assets/app.js"), timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("javascript", response.headers.get_content_type())
                    self.assertEqual(response.read(), b"console.log('ok');")
                self.assertEqual(snapshot(self.harness.graph), before)
                for path in ("/missing.js", "/../secret.txt", "/%2e%2e/secret.txt",
                             "/%2e%2e%2fsecret.txt", "/assets/"):
                    before = snapshot(self.harness.graph)
                    status, headers, raw = self.harness.raw_request(path)
                    self.assertEqual(status, 404, msg=path)
                    self.assertEqual(json.loads(raw.decode("utf-8")), {"error": "없는 경로입니다"}, msg=path)
                    self.assertNotIn(b"TOP_SECRET_DO_NOT_LEAK", raw, msg=path)
                    self.assertEqual(snapshot(self.harness.graph), before, msg=path)

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

    def test_port_conflict_is_reported(self) -> None:
        """실행 진입점은 포트 충돌을 한국어 오류와 --port 안내로 끝낸다."""
        port = self.harness.server.server_address[1]
        with self.assertRaises(SystemExit) as raised:
            main._run_web(port)
        self.assertIn("[오류] 웹 서버를 시작할 수 없습니다", str(raised.exception))
        self.assertIn("(다른 포트는 --port PORT)", str(raised.exception))

    def test_browser_open_failure_still_closes_server(self) -> None:
        """브라우저 자동 열기가 실패해도 실제 _run_web 경로가 서버 소켓을 닫는다."""
        fake_server = mock.Mock()
        fake_server.server_address = ("127.0.0.1", 43123)
        with (mock.patch("web.create_server", return_value=fake_server),
              mock.patch.object(main.webbrowser, "open", side_effect=RuntimeError("browser"))):
            with self.assertRaises(RuntimeError):
                main._run_web(43123)
        fake_server.server_close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
