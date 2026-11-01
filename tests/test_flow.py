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
import unittest

from graph import ShopGraph
from search import recommend
from tests.fixtures import make_graph
from tests.helpers import snapshot
from view import print_recommendation

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


if __name__ == "__main__":
    unittest.main()
