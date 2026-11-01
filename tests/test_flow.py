"""최소 흐름 테스트: 고객 등록 → 추천 → 출력 (계획서 11.3.2 W8b, 6.3·6.4 P02 품절).

tests/fixtures.py의 고정 데이터로 그래프를 만들고, view.print_recommendation의 출력 문자열을
contextlib.redirect_stdout으로 확인한다. 실행용 data.py는 읽지 않는다.

항목의 상품·점수·구매자 수·범위·지지자·구매 가능 색상은 6.3·6.4 기대값 그대로다.
화면 문자열은 5.3.3 출력 예시(C06)의 틀을 따르고, 예시와 6장에 글자로 없는 부분은
"# [승인 형식]" 주석을 달았다 (W8b 계약 빈칸 B09·B10, 찬일 11/01 승인).
"# [승인 기대값]"은 6장에 없는 상태의 기대값으로, G6 검토자(서브에이전트)의 별도 계산과
일치했고 사람 검산은 아니다 (찬일 11/01 승인).
"""

import contextlib
import io
import re
import unittest
from unittest import mock

import main
from graph import ShopGraph
from search import group_popular, recommend
from tests.fixtures import customers, make_graph, products, purchases
from tests.helpers import snapshot
from view import print_recommendation, print_table

# 5.3.3 출력 예시 끝의 두 번째 안내 줄 (예시 글자 그대로). 범위가 2개 이상 섞였을 때만 나온다 (찬일 11/01)
_SCORE_NOTE = " ※ 점수는 각 범위 안에서 계산한 값이라 범위가 다른 항목끼리 비교하지 않습니다"


def _render(g: ShopGraph, customer_id: str, result: list[dict], k: int) -> str:
    """print_recommendation의 출력을 문자열로 받아 돌려준다.

    인자:
        g: 조회할 ShopGraph.
        customer_id: 추천 대상 고객 ID.
        result: recommend()의 반환값.
        k: 그 recommend() 호출에 넘긴 K.

    반환:
        표준 출력에 찍힌 문자열 전체.

    예외:
        print_recommendation이 내는 예외를 그대로 전달한다.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        returned = print_recommendation(g, customer_id, result, k)
    if returned is not None:
        raise AssertionError(f"print_recommendation이 None이 아닌 값을 돌려줌: {returned!r}")
    return buffer.getvalue()


def _short_note(count: int, k: int) -> str:
    """결과 수가 K보다 적을 때의 안내 줄을 만든다.

    인자:
        count: 결과 수.
        k: 추천 개수 K.

    반환:
        안내 줄 문자열.

    예외:
        없음.
    """
    # 결과 수 < K 안내 문구 (찬일 11/01 지정)
    return f" ※ 추천할 수 있는 상품이 {count}개뿐이라 {k}개를 채우지 못함"


def _p01_group_lines(rank: int) -> list[str]:
    """6.1 처음 상태에서 G-F-20 고객이 받는 P01 항목(점수 3, 1명, 같은 그룹, 지지자 C01) 세 줄.

    인자:
        rank: 화면 순번.

    반환:
        세 줄의 새 리스트.

    예외:
        없음.
    """
    # [승인 형식] 같은 그룹 범위 표시 "[같은 그룹]" (6.3-1 글자 "같은 그룹"), 근거의 조사 이/가,
    # 색상 수 안내는 2가지 이상 산 지지자에게만 붙인다 (C01은 P01을 4가지 색상 구매, 6.1)
    return [
        f" {rank}. 오버핏 티셔츠 (P01) - 점수 3, 구매 고객 1명 [같은 그룹]",
        "    근거: C01이 구매 (C01은 4가지 색상 구매)",
        "    구매 가능 색상: 그레이, 네이비, 블랙, 화이트",
    ]


def _p03_group_lines(rank: int) -> list[str]:
    """6.1 처음 상태에서 G-F-20 고객이 받는 P03 항목(점수 2, 2명, 같은 그룹, 지지자 C02·C03) 세 줄.

    인자:
        rank: 화면 순번.

    반환:
        세 줄의 새 리스트.

    예외:
        없음.
    """
    return [
        f" {rank}. 크롭 가디건 (P03) - 점수 2, 구매 고객 2명 [같은 그룹]",
        "    근거: C02, C03이 구매",
        "    구매 가능 색상: 아이보리",
    ]


def _p04_all_lines(rank: int) -> list[str]:
    """P04 항목(점수 1, 1명, 전체 고객, 지지자 C04) 세 줄.

    인자:
        rank: 화면 순번.

    반환:
        세 줄의 새 리스트.

    예외:
        없음.
    """
    # [승인 형식] 전체 고객 범위에서는 지지자 그룹을 붙이지 않는다 (5.3.3 예시의 3번 항목과 같음)
    return [
        f" {rank}. 카고 팬츠 (P04) - 점수 1, 구매 고객 1명 [전체 고객]",
        "    근거: C04가 구매",
        "    구매 가능 색상: 블랙, 카키",
    ]


def _c07_k3_lines() -> list[str]:
    """6.3-1 C07, K=3 화면의 항목 줄들을 새로 만든다.

    인자:
        없음.

    반환:
        항목 3개(각 3줄)의 새 리스트.

    예외:
        없음.
    """
    return [
        " 1. 와이드 슬랙스 (P02) - 점수 3, 구매 고객 2명 [같은 그룹]",
        "    근거: C01, C02가 구매 (C02는 2가지 색상 구매)",
        "    구매 가능 색상: 베이지, 블랙",
    ] + _p01_group_lines(2) + _p03_group_lines(3)


class TestW8bFlow(unittest.TestCase):
    """W8b: 고객 등록 → 추천 → 출력 최소 흐름."""

    def _register_c07(self, gender: str = "여", age: int = 22) -> ShopGraph:
        """6.1 처음 상태에 C07을 등록한 그래프를 만든다 (기본은 6.3의 C07(여, 22)).

        인자:
            gender: C07의 성별.
            age: C07의 나이.

        반환:
            C07이 등록된 새 ShopGraph.

        예외:
            AssertionError: 발급 ID가 C07이 아니거나 등록 뒤 무결성 위반이 있을 때.
        """
        g = make_graph()
        self.assertEqual(g.add_customer("고객7", gender, age), "C07")
        self.assertEqual(g.check_integrity(), [])  # 5.3.5 W5 이후 변경 뒤 확인
        return g

    def _assert_screen(self, g: ShopGraph, customer_id: str, k: int, expected: list[str]) -> None:
        """recommend(g, customer_id, k)를 출력한 화면이 기대 줄들과 글자까지 같은지 확인한다.

        인자:
            g: 조회할 ShopGraph.
            customer_id: 추천 대상 고객 ID.
            k: 추천 개수 K.
            expected: 기대하는 화면 줄 리스트.

        반환:
            없음.

        예외:
            AssertionError: 화면이 다를 때.
        """
        text = _render(g, customer_id, recommend(g, customer_id, k), k)
        self.assertEqual(text, "\n".join(expected) + "\n")

    def test_c07_screen(self) -> None:
        """6.3-1 C07 등록 → 추천(K=3) → 화면: 점수·근거·구매 가능 색상. 같은 그룹에서 3개를 채워 안내 줄 없음."""
        g = self._register_c07()
        # [승인 형식] 머리 줄은 5.3.3 예시 형식 "[추천] 이름(ID, 그룹 표시 이름)님께 추천 (N개)"
        self._assert_screen(g, "C07", 3, ["[추천] 고객7(C07, 여성·20대)님께 추천 (3개)"] + _c07_k3_lines())

    def test_c07_k4_screen(self) -> None:
        """6.3-2 C07, K=4: 여성 전체에서 새 후보 없이 전체 고객까지 넓혀 P04 추가."""
        g = self._register_c07()
        self._assert_screen(g, "C07", 4, ["[추천] 고객7(C07, 여성·20대)님께 추천 (4개)"] + _c07_k3_lines()
                            + _p04_all_lines(4) + [
            # [승인 형식] 같은 그룹에 다른 고객이 있을 때의 이유 "에서 K개가 안 돼" (5.3.3 예시의 틀)
            " ※ 같은 그룹(여성·20대)에서 4개가 안 돼 '여성 전체'로, 그래도 4개가 안 돼 '전체 고객'으로 넓혀 찾음",
            _SCORE_NOTE,
        ])

    def test_c02_screen(self) -> None:
        """6.3-3 기존 C02, K=3: P01(같은 그룹), P04(전체) 2개만 → 넓힘 안내와 개수 부족 안내."""
        g = make_graph()
        self._assert_screen(g, "C02", 3, ["[추천] 고객2(C02, 여성·20대)님께 추천 (2개)"]
                            + _p01_group_lines(1) + _p04_all_lines(2) + [
            " ※ 같은 그룹(여성·20대)에서 3개가 안 돼 '여성 전체'로, 그래도 3개가 안 돼 '전체 고객'으로 넓혀 찾음",
            _short_note(2, 3),
            _SCORE_NOTE,
        ])

    def test_c06_screen_example(self) -> None:
        """6.3-4 C06(남, 15), K=3: 5.3.3 출력 예시와 글자까지 같다."""
        g = make_graph()
        self._assert_screen(g, "C06", 3, [
            "[추천] 고객6(C06, 남성·10대)님께 추천 (3개)",
            " 1. 오버핏 티셔츠 (P01) - 점수 1, 구매 고객 1명 [남성 전체]",
            "    근거: C04(남성·20대)가 구매",
            "    구매 가능 색상: 그레이, 네이비, 블랙, 화이트",
            " 2. 카고 팬츠 (P04) - 점수 1, 구매 고객 1명 [남성 전체]",
            "    근거: C04(남성·20대)가 구매",
            "    구매 가능 색상: 블랙, 카키",
            " 3. 와이드 슬랙스 (P02) - 점수 3, 구매 고객 2명 [전체 고객]",
            "    근거: C01, C02가 구매 (C02는 2가지 색상 구매)",
            "    구매 가능 색상: 베이지, 블랙",
            " ※ 같은 그룹(남성·10대)에 다른 고객이 없어 '남성 전체'로, 그래도 3개가 안 돼 '전체 고객'으로 넓혀 찾음",
            _SCORE_NOTE,
        ])

    def test_c06_k2_screen(self) -> None:
        """C06(남, 15), K=2: 그룹에 혼자이고 남성 전체에서 2개를 채움 → 넓힘 안내만, 개수 부족·점수 비교 안내 없음."""
        g = make_graph()
        text = _render(g, "C06", recommend(g, "C06", 2), 2)
        self.assertEqual(text, "\n".join([
            "[추천] 고객6(C06, 남성·10대)님께 추천 (2개)",
            " 1. 오버핏 티셔츠 (P01) - 점수 1, 구매 고객 1명 [남성 전체]",
            "    근거: C04(남성·20대)가 구매",
            "    구매 가능 색상: 그레이, 네이비, 블랙, 화이트",
            " 2. 카고 팬츠 (P04) - 점수 1, 구매 고객 1명 [남성 전체]",
            "    근거: C04(남성·20대)가 구매",
            "    구매 가능 색상: 블랙, 카키",
            " ※ 같은 그룹(남성·10대)에 다른 고객이 없어 '남성 전체'로 넓혀 찾음",
        ]) + "\n")
        self.assertNotIn("채우지 못함", text)
        self.assertNotIn(_SCORE_NOTE, text)

    def test_gender_scope_screen(self) -> None:
        """6.3-6 C05가 P04 카키 구매 후 C07, K=4: 4번째 P04가 [여성 전체], 근거에 C05의 그룹(여성·30대)."""
        g = self._register_c07()
        g.add_purchase("C05", "P04", "카키", 1, "2026-10-03")
        self.assertEqual(g.check_integrity(), [])
        self._assert_screen(g, "C07", 4, ["[추천] 고객7(C07, 여성·20대)님께 추천 (4개)"] + _c07_k3_lines() + [
            " 4. 카고 팬츠 (P04) - 점수 1, 구매 고객 1명 [여성 전체]",
            "    근거: C05(여성·30대)가 구매",
            "    구매 가능 색상: 블랙, 카키",
            " ※ 같은 그룹(여성·20대)에서 4개가 안 돼 '여성 전체'로 넓혀 찾음",
            _SCORE_NOTE,
        ])

    def test_p02_sold_out_screen(self) -> None:
        """6.4 C07 등록 후 P02 재고 0 → P01, P03, P04[전체] (값은 test_recommend.test_p02_sold_out과 같음)."""
        g = self._register_c07()
        g.update_product("P02", stock={"블랙": 0, "베이지": 0})
        self.assertEqual(g.check_integrity(), [])
        self._assert_screen(g, "C07", 3, ["[추천] 고객7(C07, 여성·20대)님께 추천 (3개)"]
                            + _p01_group_lines(1) + _p03_group_lines(2) + _p04_all_lines(3) + [
            " ※ 같은 그룹(여성·20대)에서 3개가 안 돼 '여성 전체'로, 그래도 3개가 안 돼 '전체 고객'으로 넓혀 찾음",
            _SCORE_NOTE,
        ])

    def test_widened_without_new_items_screen(self) -> None:
        """결과가 전부 같은 그룹인데 K보다 적음: 결과에 없는 범위(여성 전체·전체 고객)까지 넓혀 본 것을 안내한다."""
        # [승인 기대값] C07 등록 후 P04 재고 0 → 같은 그룹에서 6.3-1의 3개, 여성 전체·전체에서는 P04·P05가
        # 품절이라 새 후보 없음 → K=4에 3개 (5.3.3 규칙). G6 독립 검토가 제시한 반례
        g = self._register_c07()
        g.update_product("P04", stock={"카키": 0, "블랙": 0})
        self.assertEqual(g.check_integrity(), [])
        self._assert_screen(g, "C07", 4, ["[추천] 고객7(C07, 여성·20대)님께 추천 (3개)"] + _c07_k3_lines() + [
            " ※ 같은 그룹(여성·20대)에서 4개가 안 돼 '여성 전체'로, 그래도 4개가 안 돼 '전체 고객'으로 넓혀 찾음",
            _short_note(3, 4),
        ])

    def test_all_scope_only_screen(self) -> None:
        """결과가 전부 전체 고객 범위: 범위가 하나라 점수 비교 안내 없음. K=2는 꽉 참, K=3은 개수 부족 안내."""
        # [승인 기대값] C07(남, 45)은 G-M-40+에 혼자다. P01·P04 재고를 0으로 하면 남성 전체(C04·C06)의
        # 후보 P01·P04·P05가 모두 품절이라 새 후보가 없고, 전체에서 P02(C01 1 + C02 2 = 3, 2명),
        # P03(C02 1 + C03 1 = 2, 2명)만 남는다 (5.3.3 규칙)
        g = self._register_c07("남", 45)
        g.update_product("P01", stock={"블랙": 0, "화이트": 0, "그레이": 0, "네이비": 0})
        g.update_product("P04", stock={"카키": 0, "블랙": 0})
        self.assertEqual(g.check_integrity(), [])
        items = [
            " 1. 와이드 슬랙스 (P02) - 점수 3, 구매 고객 2명 [전체 고객]",
            "    근거: C01, C02가 구매 (C02는 2가지 색상 구매)",
            "    구매 가능 색상: 베이지, 블랙",
            " 2. 크롭 가디건 (P03) - 점수 2, 구매 고객 2명 [전체 고객]",
            "    근거: C02, C03이 구매",
            "    구매 가능 색상: 아이보리",
        ]
        for k, extra in ((2, []), (3, [_short_note(2, 3)])):
            self._assert_screen(g, "C07", k, ["[추천] 고객7(C07, 남성·40대 이상)님께 추천 (2개)"] + items + [
                f" ※ 같은 그룹(남성·40대 이상)에 다른 고객이 없어 '남성 전체'로, 그래도 {k}개가 안 돼 "
                "'전체 고객'으로 넓혀 찾음",
            ] + extra)

    def test_particle_boundaries(self) -> None:
        """조사 경계: ID 끝자리 0·2·6·7·8 (C10·C12·C16·C17·C18·C20) 뒤의 이/가, 은/는과 여러 지지자의 색상 수 안내."""
        g = make_graph()
        for number in range(7, 21):
            self.assertEqual(g.add_customer(f"고객{number}", "남", 35), f"C{number:02d}")
        for cid in ("C10", "C12", "C16", "C17", "C18", "C20"):
            for color in ("블랙", "베이지"):
                g.add_purchase(cid, "P02", color, 1, "2026-10-05")
        g.add_purchase("C16", "P03", "아이보리", 1, "2026-10-05")
        g.add_purchase("C17", "P04", "카키", 1, "2026-10-05")
        g.add_purchase("C18", "P01", "블랙", 1, "2026-10-05")
        self.assertEqual(g.check_integrity(), [])
        # [승인 기대값] C09의 같은 그룹(G-M-30) 동료 중 구매자는 위 6명뿐 → P02: 6명 × 2 = 12,
        # P01·P03·P04: 각 1점 1명으로 동점이라 ID 순. K=4를 같은 그룹에서 채워 안내 줄 없음
        # [승인 형식] 2가지 이상 산 지지자가 여럿이면 "(C10은 2가지, C12는 2가지, … 색상 구매)"
        self._assert_screen(g, "C09", 4, [
            "[추천] 고객9(C09, 남성·30대)님께 추천 (4개)",
            " 1. 와이드 슬랙스 (P02) - 점수 12, 구매 고객 6명 [같은 그룹]",
            "    근거: C10, C12, C16, C17, C18, C20이 구매 (C10은 2가지, C12는 2가지, C16은 2가지, "
            "C17은 2가지, C18은 2가지, C20은 2가지 색상 구매)",
            "    구매 가능 색상: 베이지, 블랙",
            " 2. 오버핏 티셔츠 (P01) - 점수 1, 구매 고객 1명 [같은 그룹]",
            "    근거: C18이 구매",
            "    구매 가능 색상: 그레이, 네이비, 블랙, 화이트",
            " 3. 크롭 가디건 (P03) - 점수 1, 구매 고객 1명 [같은 그룹]",
            "    근거: C16이 구매",
            "    구매 가능 색상: 아이보리",
            " 4. 카고 팬츠 (P04) - 점수 1, 구매 고객 1명 [같은 그룹]",
            "    근거: C17이 구매",
            "    구매 가능 색상: 블랙, 카키",
        ])

    def test_zero_screen(self) -> None:
        """6.3-7 C07 등록 후 모든 상품 재고를 0으로 → 추천 [] → 화면에 "추천할 상품이 없습니다"."""
        g = self._register_c07()
        for pid in g.product_ids():
            g.update_product(pid, stock={color: 0 for color in g.get_product(pid)["stock"]})
        self.assertEqual(g.check_integrity(), [])
        result = recommend(g, "C07", 3)
        self.assertEqual(result, [])
        text = _render(g, "C07", result, 3)
        self.assertIn("추천할 상품이 없습니다", text)  # 6.3-7 글자 그대로
        # [승인 형식] 빈 결과는 머리 줄 한 줄로 끝낸다 (넓힘·개수 부족 안내 없음)
        self.assertEqual(text, "[추천] 고객7(C07, 여성·20대)님께 추천할 상품이 없습니다\n")

    def test_print_keeps_state(self) -> None:
        """출력은 상태를 바꾸지 않는다 (view.py는 출력 전용, 5.5): 출력 전후 snapshot 전체가 같다."""
        g = self._register_c07()
        result = recommend(g, "C07", 4)
        before = snapshot(g)
        _render(g, "C07", result, 4)
        self.assertEqual(snapshot(g), before)
        self.assertEqual(g.check_integrity(), [])

    def test_unknown_customer(self) -> None:
        """B.2 print_recommendation: 없는 고객 ID면 ValueError를 그대로 전달하고 아무것도 출력하지 않는다."""
        g = make_graph()
        before = snapshot(g)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(ValueError):
                print_recommendation(g, "C99", [], 3)
        self.assertEqual(buffer.getvalue(), "")
        self.assertEqual(snapshot(g), before)


def _run_main(inputs: list[object]) -> tuple[str, ShopGraph]:
    """main.run()을 고정 데이터와 정해 둔 입력으로 실행하고 화면과 그래프를 돌려준다.

    main.initial_records를 tests/fixtures.py의 6.1 데이터로 바꿔 실행용 data.py를 읽지 않는다.
    입력은 터미널처럼 안내 문구 뒤에 입력값과 줄바꿈을 화면에 남긴다. 입력이 다 떨어지면
    EOFError, 예외 클래스(KeyboardInterrupt 등)를 넣어 두면 그 자리에서 그 예외를 낸다.

    인자:
        inputs: 차례로 돌려줄 입력 문자열 또는 낼 예외 클래스.

    반환:
        (화면 문자열 전체, run()이 만든 ShopGraph).

    예외:
        run()이 밖으로 내보낸 예외를 그대로 전달한다 (정상이라면 없음).
    """
    feed = iter(inputs)
    created: list[ShopGraph] = []

    def fake_input(prompt: str = "") -> str:
        print(prompt, end="")
        value = next(feed, EOFError)
        if isinstance(value, type) and issubclass(value, BaseException):
            raise value
        print(value)
        return value

    def build(*records: list[dict]) -> ShopGraph:
        g = ShopGraph(*records)
        created.append(g)
        return g

    buffer = io.StringIO()
    with mock.patch("main.initial_records", lambda: (customers(), products(), purchases())), \
            mock.patch("main.ShopGraph", build), mock.patch("builtins.input", fake_input), \
            contextlib.redirect_stdout(buffer):
        returned = main.run()
    if returned is not None:
        raise AssertionError(f"run()이 None이 아닌 값을 돌려줌: {returned!r}")
    return buffer.getvalue(), created[0]


def _table(headers: list[str], rows: list[list[object]]) -> str:
    """print_table(W9에서 형식 확인)이 그 행으로 찍을 표 문자열을 돌려준다.

    인자:
        headers: 표 머리.
        rows: 기대하는 행 (값은 6장 기대값에서 옮김).

    반환:
        표 문자열.

    예외:
        print_table이 내는 예외를 그대로 전달한다.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        print_table(headers, rows)
    return buffer.getvalue()


class TestW10Menu(unittest.TestCase):
    """W10: 전체 메뉴(5.4), 입력 변환, ValueError → 메시지, 삭제 확인, 등록 직후 추천, EOF·Ctrl+C."""

    def _assert_errors_keep_state(self, inputs: list[object], errors: int) -> str:
        """잘못된 입력들을 넣어도 프로그램이 끝까지 돌고, 오류 줄 수가 맞고, 상태가 처음과 같은지 확인한다.

        인자:
            inputs: 메뉴 입력 순서 (마지막에 "0"으로 종료).
            errors: 기대하는 "[오류]" 줄 수 (입력 하나에 오류 하나).

        반환:
            화면 문자열.

        예외:
            AssertionError: 오류 줄 수가 다르거나, 종료하지 않았거나, 상태가 바뀌었을 때.
        """
        text, g = _run_main(inputs)
        self.assertEqual(text.count("\n[오류] "), errors, msg=text)
        self.assertTrue(text.endswith("메뉴 선택: 0\n종료합니다\n"), msg=text[-200:])
        self.assertEqual(snapshot(g), snapshot(make_graph()))  # 원본·그래프·ID 카운터 모두 처음 그대로
        return text

    def test_full_menu_and_exit(self) -> None:
        """5.4 메인 메뉴가 그대로 나오고 [0]으로 종료한다."""
        text, _ = _run_main(["0"])
        self.assertEqual(text, "\n".join([
            "",
            "[1] CREATE      고객 / 상품 / 구매",
            "[2] READ        조회(ID·이름·조건) / 검색 S1~S4",
            "[3] UPDATE      고객 / 상품 / 구매",
            "[4] DELETE      고객 / 상품 / 구매",
            "[5] PRINT       그룹별 고객 / 상품 목록 / 인접 리스트 / 통계·무결성 검사",
            "[6] RECOMMEND   고객별 추천",
            "[0] Exit",
            "메뉴 선택: 0",
            "종료합니다",
        ]) + "\n")

    def test_register_then_recommend(self) -> None:
        """5.3.1 고객 등록 직후 추천: C07(여, 22) 등록 → 6.3-1 화면 (W8b 승인 형식)."""
        text, g = _run_main(["1", "1", "고객7", "2", "22", "0"])
        # [승인 형식] 등록 직후 줄 "[등록] 이름(ID) → 그룹 표시 이름 그룹에 연결" (W8b 임시 형식 교체)
        expected = ["[등록] 고객7(C07) → 여성·20대 그룹에 연결",
                    "[추천] 고객7(C07, 여성·20대)님께 추천 (3개)"] + _c07_k3_lines()
        self.assertIn("나이: 22\n" + "\n".join(expected) + "\n", text)
        self.assertEqual(g.group_of("C07"), "G-F-20")
        self.assertEqual(g.check_integrity(), [])

    def test_submenu_screen_and_back(self) -> None:
        """하위 메뉴 화면과 [0] 이전 메뉴: 아무것도 실행하지 않고 메인 메뉴로 돌아간다."""
        text, g = _run_main(["1", "0", "0"])
        # [승인 형식] 하위 메뉴는 "[제목]" 줄, "[번호] 기능", "[0] 이전 메뉴", "번호 선택: "
        self.assertIn("\n".join([
            "메뉴 선택: 1", "", "[CREATE]", "[1] 고객 등록 (등록 직후 추천)", "[2] 상품 등록", "[3] 구매 등록",
            "[0] 이전 메뉴", "번호 선택: 0", "",
        ]), text)
        self.assertNotIn("[오류]", text)
        self.assertEqual(snapshot(g), snapshot(make_graph()))

    def test_invalid_menu_numbers(self) -> None:
        """없는 메뉴·하위 메뉴 번호, 빈 입력, 문자: 오류 안내 후 메인 메뉴로."""
        # 메인 9·빈 입력·abc, CREATE 하위 9·빈 입력, READ 하위 8(7개뿐), 메인 -1 = 오류 7줄
        self._assert_errors_keep_state(["9", "", "abc", "1", "9", "1", "", "2", "8", "-1", "0"], 7)

    def test_input_error_messages(self) -> None:
        """main.py가 만드는 입력 변환 오류 문구 ("항목: …" 형식, W8b 승인). A03 회귀(긴 숫자) 포함."""
        text, _ = _run_main([
            "1", "1", "고객7", "3",
            "1", "1", "고객7", "1", "스물",
            "1", "1", "고객7", "1", "1" * 4301,
            "1", "2", "새 상품", "4",
            "1", "2", "새 상품", "1", "1", "1000", "블랙",
            "1", "2", "새 상품", "1", "1", "1000", "블랙=1, 블랙=2",
            "0",
        ])
        for line in (
            "[오류] 성별: 1(남) 또는 2(여)로 입력해 주세요",
            "[오류] 나이: 숫자로 입력해 주세요",
            "[오류] 나이: 숫자가 너무 깁니다 (9자리 이하)",
            # [승인 형식] 번호 고르기 오류, 재고 입력 형식 오류 문구
            "[오류] 종류: 1(상의), 2(하의) 또는 3(아우터)로 입력해 주세요",
            "[오류] 색상별 재고: 색상=수량을 쉼표로 이어 입력해 주세요 (예: 블랙=5, 화이트=3)",
            # [SPEC][W10b] 찬일 11/02: W10 승인 형식 7번의 재고 겹침 문구를 W10a 형식 "(입력: 값)"으로 변경
            "[오류] 색상별 재고: 같은 색상이 두 번 나옵니다 (입력: 블랙)",
        ):
            self.assertIn("\n" + line + "\n", text)

    def test_invalid_create_inputs(self) -> None:
        """B.4 잘못된 입력(CREATE): 없는 ID, 형식이 틀린 값, 범위 밖 숫자(나이 5·수량 0·100 → graph.py 범위 검사),
        음수(나이 -3 → main.py 숫자 변환에서 거절), 빈 문자열, 숫자가 아닌 값, 날짜 함정 4종."""
        cases = [
            ["1", "1", "고객7", "3"], ["1", "1", "고객7", "1", "abc"], ["1", "1", "고객7", "1", "5"],
            ["1", "1", "   ", "1", "20"], ["1", "1", "고객7", "2", ""], ["1", "1", "고객7", "2", "-3"],
            ["1", "1", "고객7", "2", "1234567890"], ["1", "1", "고객7", "2", "２０"],
            ["1", "2", "새 상품", "4"], ["1", "2", "새 상품", "1", "5"], ["1", "2", "새 상품", "1", "1", "1만"],
            ["1", "2", "새 상품", "1", "1", "1000", "블랙"], ["1", "2", "새 상품", "1", "1", "1000", "블랙=1, 블랙=2"],
            ["1", "2", "새 상품", "1", "1", "1000", "카키=1, 카키 =2"], ["1", "2", "새 상품", "1", "1", "1000", "블랙=-1"],
            ["1", "2", "", "1", "1", "1000", "블랙=1"], ["1", "2", "새 상품", "1", "1", "1000", ""],
            ["1", "3", "C99", "P01", "블랙", "1", "2026-10-01"], ["1", "3", "C01", "P99", "블랙", "1", "2026-10-01"],
            ["1", "3", "C01", "P01", "레드", "1", "2026-10-01"], ["1", "3", "C01", "P01", "블랙", "0", "2026-10-01"],
            ["1", "3", "C01", "P01", "블랙", "100", "2026-10-01"], ["1", "3", "", "P01", "블랙", "1", "2026-10-01"],
            ["1", "3", "C01", "P01", "블랙", "1", "20261023"], ["1", "3", "C01", "P01", "블랙", "1", "2026-W43-5"],
            ["1", "3", "C01", "P01", "블랙", "1", "2026-02-30"], ["1", "3", "C01", "P01", "블랙", "1", "2026-1-5"],
        ]
        text = self._assert_errors_keep_state([value for case in cases for value in case] + ["0"], len(cases))
        # 음수 나이 "-3"은 graph.py 범위 검사까지 가지 않고 main.py 숫자 변환에서 거절된다 (통합 검토 R4)
        self.assertIn("나이: -3\n[오류] 나이: 숫자로 입력해 주세요\n", text)

    def test_invalid_read_inputs(self) -> None:
        """B.4 잘못된 입력(READ·PRINT·RECOMMEND): 없는 ID, 소문자 ID, 공백 이름, 가격 범위 거꾸로, 범위 밖 K·k, bool 글자."""
        cases = [
            ["2", "1", "4"], ["2", "1", "1", "C99"], ["2", "1", "2", "p01"], ["2", "1", "3", "T999"],
            ["2", "2", "1", "   "], ["2", "3", "", "", "", "50000", "1000"], ["2", "3", "9"],
            ["2", "3", "", "", "", "abc"], ["2", "4", "C99"], ["2", "5", "X"], ["2", "6", "0"], ["2", "7", "9"],
            ["2", "7", "2", "11"], ["2", "7", "2", "0"], ["6", "C99", ""], ["6", "C01", "0"], ["6", "C01", "11"],
            ["6", "C01", "True"], ["5", "3", "C99"],
        ]
        self._assert_errors_keep_state([value for case in cases for value in case] + ["0"], len(cases))

    def test_invalid_update_delete_inputs(self) -> None:
        """B.4 잘못된 입력(UPDATE·DELETE): 바꿀 항목 없음, 유효한 값과 틀린 값 섞기, 구매 기록이 있는 색상 삭제, 없는 ID.

        음수 가격 "-5"는 graph.py 범위 검사까지 가지 않고 main.py 숫자 변환에서 거절된다.
        """
        cases = [
            ["3", "1", "C99"], ["3", "1", "C01", "", "", ""], ["3", "1", "C01", "", "3"],
            ["3", "1", "C01", "", "", "120"], ["3", "1", "C01", "새이름", "1", "5"],
            ["3", "2", "P01", "", "", "", "", "블랙=1"], ["3", "2", "P01", "", "", "", "-5"],
            ["3", "2", "P04", "", "", "", "", "카키=1, 카키 =2"], ["3", "3", "T001", "", ""],
            ["3", "3", "T001", "레드", ""], ["3", "3", "T001", "", "0"],
            ["4", "1", "C99"], ["4", "2", "P99"], ["4", "3", "T999"],
        ]
        text = self._assert_errors_keep_state([value for case in cases for value in case] + ["0"], len(cases))
        # 음수 가격 "-5"는 main.py 숫자 변환에서 거절된다 (통합 검토 R4)
        self.assertIn("): -5\n[오류] 가격: 숫자로 입력해 주세요\n", text)

    def test_eof_and_ctrl_c(self) -> None:
        """입력 끝(EOF)·Ctrl+C: 입력 도중이든 메뉴에서든 "종료합니다"로 끝나고 반쯤 받은 등록은 하지 않는다."""
        for inputs in (["1", "1", "고객7"], ["1", "1", "고객7", "2", KeyboardInterrupt], [KeyboardInterrupt],
                       ["2", KeyboardInterrupt], []):
            text, g = _run_main(inputs)
            # [승인 형식] EOF·Ctrl+C 뒤에는 빈 줄 하나와 "종료합니다"
            self.assertTrue(text.endswith("\n종료합니다\n"), msg=repr(inputs))
            self.assertEqual(snapshot(g), snapshot(make_graph()), msg=repr(inputs))

    def test_delete_customer_confirm(self) -> None:
        """5.3.1 고객 삭제 확인: C02의 구매 기록 3건(T006·T007·T008) 안내 → y → 연쇄 삭제 (6.4 C02 삭제)."""
        text, g = _run_main(["4", "1", "C02", "y", "0"])
        # [승인 형식] 확인 줄 "이름(ID) 삭제: 구매 기록 N건도 함께 삭제됩니다. 계속할까요? (y/n): ", 결과 줄 "[삭제] …"
        self.assertIn("고객2(C02) 삭제: 구매 기록 3건도 함께 삭제됩니다. 계속할까요? (y/n): y\n"
                      "[삭제] 고객2(C02), 구매 기록 3건 함께 삭제\n", text)
        self.assertNotIn("C02", g.customer_ids())
        self.assertEqual(g.members("G-F-20"), ["C01", "C03"])
        self.assertEqual(g.stats()["purchases"], 10)
        self.assertEqual(g.check_integrity(), [])

    def test_delete_product_confirm(self) -> None:
        """5.3.1 상품 삭제 확인: P01의 구매 기록 5건(T001~T004, T013) 안내 → Y(대문자) → 연쇄 삭제."""
        text, g = _run_main(["4", "2", "P01", "Y", "0"])
        self.assertIn("오버핏 티셔츠(P01) 삭제: 구매 기록 5건도 함께 삭제됩니다. 계속할까요? (y/n): Y\n"
                      "[삭제] 오버핏 티셔츠(P01), 구매 기록 5건 함께 삭제\n", text)
        self.assertNotIn("P01", g.product_ids())
        self.assertEqual(g.stats()["purchases"], 8)
        self.assertEqual(g.check_integrity(), [])

    def test_delete_cancel(self) -> None:
        """삭제 확인에서 y가 아니면 취소: 상태 그대로. 구매 기록이 없는 고객(C06)의 확인 문구."""
        text, g = _run_main(["4", "1", "C02", "n", "4", "2", "P01", "", "4", "1", "C06", "예", "0"])
        # [승인 형식] y(대소문자 무관)만 삭제, 그 밖은 "[취소] 삭제하지 않았습니다". 구매 기록 0건이면 다른 문구
        self.assertEqual(text.count("[취소] 삭제하지 않았습니다"), 3)
        self.assertIn("고객6(C06) 삭제: 함께 삭제되는 구매 기록은 없습니다. 계속할까요? (y/n): 예\n", text)
        self.assertEqual(snapshot(g), snapshot(make_graph()))

    def test_delete_purchase(self) -> None:
        """구매 삭제(확인 없음, 5.3.1): T004 삭제 → (C01,P01) 간선 유지, 가중치 3 (6.4 T004 삭제)."""
        text, g = _run_main(["4", "3", "T004", "0"])
        self.assertIn("[삭제] T004: C01 → P01, 네이비 (남은 가중치 3)\n", text)
        self.assertEqual(g.edge("C01", "P01")["last_date"], "2026-09-15")
        self.assertEqual(g.check_integrity(), [])

    def test_update_customer_moves_group(self) -> None:
        """고객 수정(빈 입력은 그대로): C04 나이 34 → G-M-30 이동 (6.4: 24 → 34)."""
        text, g = _run_main(["3", "1", "C04", "", "", "34", "0"])
        # [승인 형식] 수정 결과 줄 "[수정] 이름(ID) → 그룹 표시 이름 그룹"
        self.assertIn("[수정] 고객4(C04) → 남성·30대 그룹\n", text)
        self.assertEqual(g.group_of("C04"), "G-M-30")
        self.assertEqual(g.get_customer("C04")["name"], "고객4")
        self.assertEqual(g.check_integrity(), [])

    def test_update_product_stock(self) -> None:
        """상품 수정: P04 재고를 통째로 교체해 색상 추가 (6.4 P04 재고 교체), 나머지 항목 그대로."""
        _, g = _run_main(["3", "2", "P04", "", "", "", "", "카키=4, 블랙=4, 베이지=2", "0"])
        product = g.get_product("P04")
        self.assertEqual(product["stock"], {"카키": 4, "블랙": 4, "베이지": 2})
        self.assertEqual((product["name"], product["price"]), ("카고 팬츠", 49000))
        self.assertEqual(g.check_integrity(), [])

    def test_purchase_register_weight(self) -> None:
        """구매 등록 화면에 가중치: 신규 C07이 P02를 블랙·베이지로 사면 가중치 1 → 2 (7장 장면 3의 흐름)."""
        text, g = _run_main(["1", "1", "고객7", "2", "25",
                             "1", "3", "C07", "P02", "블랙", "1", "2026-10-05",
                             "1", "3", " C07 ", "P02", " 베이지 ", "2", " 2026-10-06 ", "0"])
        # [승인 형식] "[등록] 구매 ID: 고객 → 상품, 색상, 수량개, 구매일 (가중치 W)". ID·날짜 입력의 앞뒤 공백은 main이 지움
        self.assertIn("[등록] T014: C07 → P02, 블랙, 1개, 2026-10-05 (가중치 1)\n", text)
        self.assertIn("[등록] T015: C07 → P02, 베이지, 2개, 2026-10-06 (가중치 2)\n", text)
        self.assertEqual(g.weight("C07", "P02"), 2)
        self.assertEqual(g.check_integrity(), [])

    def test_read_screens(self) -> None:
        """조회·검색 화면: 이름 조회(공백 제거, 완전 일치), 조건 조회, S1(C01), S4(G-F-20) — 값은 6.2."""
        text, _ = _run_main(["2", "2", "1", " 고객1 ", "2", "2", "1", "고객", "2", "3", "", "", "네이비", "", "",
                             "2", "4", "C01", "2", "7", "2", "", "0"])
        # [승인 형식] 목록 화면은 "[제목] N개(명)" 줄 + 표, 결과가 없으면 "[제목] 결과가 없습니다"
        self.assertIn("[고객 이름 조회] 1명\n" + _table(
            ["ID", "이름", "성별", "나이", "그룹"], [["C01", "고객1", "여", 23, "여성·20대"]]), text)
        self.assertIn("[고객 이름 조회] 결과가 없습니다\n", text)
        self.assertIn("[조건 조회] 2개\n" + _table(
            ["ID", "상품명", "종류", "스타일", "가격", "색상별 재고", "상태"],
            [["P01", "오버핏 티셔츠", "상의", "캐주얼", 29000, "그레이 5, 네이비 5, 블랙 5, 화이트 5", "판매 중"],
             ["P03", "크롭 가디건", "상의", "미니멀", 45000, "네이비 0, 아이보리 2", "판매 중"]]), text)
        self.assertIn("[S1 고객이 산 상품] 고객1(C01) 2개\n" + _table(
            ["상품 ID", "상품명", "구매 색상", "가중치", "기록 수", "총수량", "최근 구매일"],
            [["P01", "오버핏 티셔츠", "그레이, 네이비, 블랙, 화이트", 4, 4, 4, "2026-10-01"],
             ["P02", "와이드 슬랙스", "블랙", 1, 1, 1, "2026-09-03"]]), text)
        self.assertIn("[S4 그룹 인기 상품] 여성·20대(G-F-20) 4개\n" + _table(
            ["순위", "상품 ID", "상품명", "점수", "구매 고객 수", "상태"],
            [[1, "P02", "와이드 슬랙스", 3, 2, "판매 중"], [2, "P01", "오버핏 티셔츠", 3, 1, "판매 중"],
             [3, "P03", "크롭 가디건", 2, 2, "판매 중"], [4, "P05", "후드 집업", 1, 1, "품절"]]), text)

    def test_print_screens(self) -> None:
        """PRINT 메뉴: 그룹 트리, 상품 목록, 전체 인접 리스트(노드 19개, 6.2), 통계(6.2)와 무결성 검사."""
        text, g = _run_main(["5", "1", "5", "2", "5", "3", "", "5", "4", "0"])
        self.assertIn("[그룹별 고객] 전체 6명\n", text)
        self.assertIn("[상품 목록] 5개\n", text)
        self.assertEqual(text.count("[인접 리스트] "), 19)
        # [승인 형식] 통계 표의 항목 이름, 무결성 검사 결과 줄 (7장 8번 발표 표현, 찬일 11/01 지정)
        self.assertIn("[그래프 통계]\n" + _table(["항목", "개수"], [
            ["그룹 노드", 8], ["고객 노드", 6], ["상품 노드", 5], ["소속 간선", 6], ["구매 간선", 9], ["구매 기록", 13],
        ]) + "[무결성 검사] 위반 없음: 원본과 그래프가 일치함을 확인\n", text)
        self.assertEqual(snapshot(g), snapshot(make_graph()))

    def test_recommend_menu(self) -> None:
        """[6] 고객별 추천: K 빈 입력은 3, 숫자를 넣으면 그 K (6.3-3 C02, 6.3-4 C06)."""
        text, _ = _run_main(["6", "C02", "", "6", " C06 ", "3", "0"])
        self.assertIn("[추천] 고객2(C02, 여성·20대)님께 추천 (2개)\n", text)
        self.assertIn(_short_note(2, 3), text)
        self.assertIn("[추천] 고객6(C06, 남성·10대)님께 추천 (3개)\n", text)


# W10a 검증 오류 메시지 형식 "항목: 규칙 (입력: 값)" (찬일 11/01, A04)
_MESSAGE_FORMAT = re.compile(r"^[^:]+: .+ \(입력: .+\)$")


class TestW10aMessages(unittest.TestCase):
    """W10a: 메뉴 오류 화면 문구와 graph·search 검증 오류 메시지 형식 (A04 콜론 두 번 수정)."""

    def test_age_error_screen(self) -> None:
        """고객 등록에서 나이 5 → "[오류] 나이: 10~99이어야 합니다 (입력: 5)", 상태 그대로."""
        text, g = _run_main(["1", "1", "고객7", "1", "5", "0"])
        self.assertIn("\n[오류] 나이: 10~99이어야 합니다 (입력: 5)\n", text)
        self.assertEqual(snapshot(g), snapshot(make_graph()))

    def test_recommend_k_error_screen(self) -> None:
        """[6] 추천에서 K=0 → 항목 이름이 입력 안내와 같은 "추천 개수 K"."""
        text, _ = _run_main(["6", "C01", "0", "0"])
        self.assertIn("\n[오류] 추천 개수 K: 1~10이어야 합니다 (입력: 0)\n", text)

    def test_s4_count_error_screen(self) -> None:
        """S4 그룹 인기 상품에서 개수 0 → 항목 이름이 입력 안내와 같은 "개수"."""
        text, _ = _run_main(["2", "7", "2", "0", "0"])
        self.assertIn("\n[오류] 개수: 1~10이어야 합니다 (입력: 0)\n", text)

    def test_graph_and_search_same_format(self) -> None:
        """graph.py 오류(나이 범위)와 search.py 오류(K 범위)의 메시지가 같은 형식 정규식에 맞는다."""
        g = make_graph()
        with self.assertRaises(ValueError) as graph_error:
            g.add_customer("고객7", "여", 5)
        with self.assertRaises(ValueError) as search_error:
            group_popular(g, "G-F-20", 0)
        for error in (graph_error.exception, search_error.exception):
            self.assertRegex(str(error), _MESSAGE_FORMAT)
        self.assertEqual(snapshot(g), snapshot(make_graph()))


class TestW10bInputs(unittest.TestCase):
    """W10b: 고장 검사에서 찾은 입력 처리 테스트 공백 (docs/verification/mutation_proposals.md P1·P2)."""

    def test_digit_limit_boundary(self) -> None:
        """나이 입력 9자리는 graph.py 범위 검사로, 10자리는 main.py 자릿수 제한으로 거절된다 (고장 검사 M04)."""
        text, g = _run_main(["1", "1", "고객7", "2", "123456789",
                             "1", "1", "고객7", "2", "1234567890", "0"])
        # [승인 기대값] (찬일 11/02) 9자리: W10a 형식의 graph.py 범위 오류
        self.assertIn("\n[오류] 나이: 10~99이어야 합니다 (입력: 123456789)\n", text)
        # [승인 기대값] (찬일 11/02) 10자리: main.py 자릿수 오류 (A03 수정 문구)
        self.assertIn("\n[오류] 나이: 숫자가 너무 깁니다 (9자리 이하)\n", text)
        self.assertEqual(snapshot(g), snapshot(make_graph()))

    def test_delete_id_spaces(self) -> None:
        """삭제 메뉴에서 앞뒤 공백이 있는 고객·상품 ID도 같은 대상을 찾는다 (취소해서 상태 그대로, 고장 검사 M05)."""
        text, g = _run_main(["4", "1", " C02 ", "n", "4", "2", " P01 ", "n", "0"])
        # [승인 기대값] (찬일 11/02) 확인 문장 (W10 승인 형식 5번, 6.1에서 C02 구매 기록 3건·P01 5건)
        self.assertIn("고객2(C02) 삭제: 구매 기록 3건도 함께 삭제됩니다. 계속할까요? (y/n): n\n", text)
        self.assertIn("오버핏 티셔츠(P01) 삭제: 구매 기록 5건도 함께 삭제됩니다. 계속할까요? (y/n): n\n", text)
        self.assertNotIn("[오류]", text)
        self.assertEqual(snapshot(g), snapshot(make_graph()))

    def test_delete_purchase_id_spaces(self) -> None:
        """구매 삭제에서 앞뒤 공백이 있는 구매 ID도 같은 기록을 지운다 (6.4 T004 삭제)."""
        text, g = _run_main(["4", "3", " T004 ", "0"])
        # [승인 기대값] (찬일 11/02) 결과 줄은 test_delete_purchase(W10 승인 형식)와 같다
        self.assertIn("[삭제] T004: C01 → P01, 네이비 (남은 가중치 3)\n", text)
        self.assertNotIn("[오류]", text)
        self.assertEqual(g.edge("C01", "P01")["last_date"], "2026-09-15")
        self.assertEqual(g.check_integrity(), [])

    def test_recommend_k_not_number(self) -> None:
        """[6] 추천에서 숫자가 아닌 K도 범위 밖 K와 같은 항목 이름 "추천 개수 K"로 안내한다 (통합 검토 R1)."""
        text, _ = _run_main(["6", "C01", "abc", "0"])
        # [승인 기대값] (찬일 11/02)
        self.assertIn("\n[오류] 추천 개수 K: 숫자로 입력해 주세요\n", text)


if __name__ == "__main__":
    unittest.main()
