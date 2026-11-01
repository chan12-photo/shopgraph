"""화면 출력 테스트: 표(한글 폭), 그룹별 고객 트리, 인접 리스트 (계획서 11.3.2 W9, 5.3.1 PRINT).

tests/fixtures.py의 고정 데이터로 그래프를 만들고, view.py 함수의 출력 문자열을
contextlib.redirect_stdout으로 확인한다. 실행용 data.py는 읽지 않는다.

계획서가 정한 것은 "한글 2칸 폭 정렬"(print_table, unicodedata.east_asian_width),
"전체 → 성별 → 연령대 → 고객 들여쓰기"(print_group_tree), "노드 하나의 인접 리스트"
(print_neighbors)까지다. 그 밖의 글자 형식은 "# [제안 형식]" 주석을 달았다 (W9 G7 승인 대상).
"""

import contextlib
import io
import unittest
from collections.abc import Callable

from graph import ShopGraph
from tests.fixtures import make_graph
from tests.helpers import snapshot
from view import print_group_tree, print_neighbors, print_table


def _capture(func: Callable[..., object], *args: object) -> str:
    """view 함수 하나를 불러 표준 출력을 문자열로 받아 돌려준다.

    인자:
        func: 부를 view 함수.
        *args: func에 넘길 인자.

    반환:
        표준 출력에 찍힌 문자열 전체.

    예외:
        AssertionError: func가 None이 아닌 값을 돌려줄 때 (B.2 view는 None 반환).
        func가 내는 다른 예외는 그대로 전달한다.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        returned = func(*args)
    if returned is not None:
        raise AssertionError(f"{func.__name__}이 None이 아닌 값을 돌려줌: {returned!r}")
    return buffer.getvalue()


def _lines(*lines: str) -> str:
    """줄들을 줄바꿈으로 이어 출력 기대 문자열을 만든다 (마지막 줄 뒤에도 줄바꿈).

    인자:
        *lines: 화면 줄.

    반환:
        기대 출력 문자열.

    예외:
        없음.
    """
    return "".join(line + "\n" for line in lines)


class TestW9Table(unittest.TestCase):
    """W9: print_table 한글 폭 정렬."""

    def test_korean_width_alignment(self) -> None:
        """한글(east_asian_width W)은 2칸으로 세어 열을 맞춘다. 정수 열은 오른쪽 정렬."""
        # [제안 형식] 열 사이 공백 2칸, 머리 줄 아래 열 폭만큼 "-", 정수만 있는 열은 머리까지 오른쪽 정렬,
        # 나머지는 왼쪽 정렬, 줄 끝 공백 없음
        # 열 폭: ID = max(2, 3) = 3 / 상품명 = max(6, "오버핏 티셔츠" 6×2+1 = 13) = 13 / 가격 = max(4, 5) = 5
        text = _capture(print_table, ["ID", "상품명", "가격"],
                        [["P01", "오버핏 티셔츠", 29000], ["P02", "와이드 슬랙스", 39000]])
        self.assertEqual(text, _lines(
            "ID " + "  " + "상품명" + " " * 7 + "  " + " " * 1 + "가격",
            "-" * 3 + "  " + "-" * 13 + "  " + "-" * 5,
            "P01" + "  " + "오버핏 티셔츠" + "  " + "29000",
            "P02" + "  " + "와이드 슬랙스" + "  " + "39000",
        ))

    def test_narrow_and_ambiguous_width(self) -> None:
        """영문·숫자·'·'(east_asian_width A)는 1칸. 짧은 정수는 왼쪽을 공백으로 채운다."""
        # 그룹 열 폭 = "여성·20대" 2+2+1+1+1+2 = 9 ("그룹" 4보다 큼) / 인원 열 폭 = max(4, 2) = 4
        text = _capture(print_table, ["그룹", "인원"], [["여성·20대", 3], ["남성·40대 이상", 12]])
        # "남성·40대 이상" = 남성 4 + · 1 + 40 2 + 대 2 + 공백 1 + 이상 4 = 14 → 그룹 열 폭 14
        self.assertEqual(text, _lines(
            "그룹" + " " * 10 + "  " + "인원",
            "-" * 14 + "  " + "-" * 4,
            "여성·20대" + " " * 5 + "  " + " " * 3 + "3",
            "남성·40대 이상" + "  " + " " * 2 + "12",
        ))

    def test_mixed_column_left_aligned(self) -> None:
        """정수와 문자열이 섞인 열은 왼쪽 정렬, 마지막 열의 줄 끝 공백은 지운다."""
        text = _capture(print_table, ["값", "메모"], [[5, "-"], ["없음", "재고"]])
        # 값 열 폭 = max(2, 1, 4) = 4 / 메모 열 폭 = max(4, 1, 4) = 4
        self.assertEqual(text, _lines(
            "값" + " " * 2 + "  " + "메모",
            "-" * 4 + "  " + "-" * 4,
            "5" + " " * 3 + "  " + "-",
            "없음" + "  " + "재고",
        ))

    def test_bool_column_left_aligned(self) -> None:
        """bool은 정수로 보지 않는다 (B.3 정수 공통 규칙과 같은 기준): bool 열은 왼쪽 정렬."""
        text = _capture(print_table, ["품절여부"], [[True], [False]])
        self.assertEqual(text, _lines("품절여부", "-" * 8, "True", "False"))

    def test_empty_rows(self) -> None:
        """행이 없으면 머리 줄과 구분 줄만 출력한다."""
        # [제안 형식] 빈 표에 "없음" 같은 문구는 view가 붙이지 않는다 (main.py가 상황에 맞게 안내)
        text = _capture(print_table, ["ID", "이름"], [])
        self.assertEqual(text, _lines("ID  이름", "--  ----"))

    def test_row_length_mismatch(self) -> None:
        """행의 칸 수가 머리 칸 수와 다르면 ValueError, 아무것도 출력하지 않는다."""
        # [제안 형식] 계획서에 없는 예외: 호출 실수를 조용히 넘기지 않으려고 ValueError로 둔다
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(ValueError):
                print_table(["ID", "이름"], [["C01", "고객1"], ["C02"]])
        self.assertEqual(buffer.getvalue(), "")


class TestW9GroupTree(unittest.TestCase):
    """W9: print_group_tree 전체 → 성별 → 연령대 → 고객."""

    def test_fixture_tree(self) -> None:
        """6.1 처음 상태: 8개 그룹 전부(빈 그룹 포함) 표시, 그룹 안 고객은 ID 순, 출력 전후 상태 동일."""
        g = make_graph()
        before = snapshot(g)
        text = _capture(print_group_tree, g)
        # [제안 형식] 머리 줄 "[그룹별 고객] 전체 N명", 들여쓰기 2칸씩, 연령대 줄에 그룹 ID와 인원,
        # 고객 줄 "ID 이름 (나이세)". 빈 그룹도 "0명"으로 표시 (7장 시연: 소속 고객이 없는 그룹)
        self.assertEqual(text, _lines(
            "[그룹별 고객] 전체 6명",
            "  여성 4명",
            "    10대 (G-F-10) 0명",
            "    20대 (G-F-20) 3명",
            "      C01 고객1 (23세)",
            "      C02 고객2 (25세)",
            "      C03 고객3 (27세)",
            "    30대 (G-F-30) 1명",
            "      C05 고객5 (34세)",
            "    40대 이상 (G-F-40+) 0명",
            "  남성 2명",
            "    10대 (G-M-10) 1명",
            "      C06 고객6 (15세)",
            "    20대 (G-M-20) 1명",
            "      C04 고객4 (24세)",
            "    30대 (G-M-30) 0명",
            "    40대 이상 (G-M-40+) 0명",
        ))
        self.assertEqual(snapshot(g), before)

    def test_tree_follows_changes(self) -> None:
        """등록·그룹 이동(6.4 C04 나이 수정 → G-M-30)·삭제가 트리에 반영된다."""
        g = make_graph()
        g.add_customer("고객7", "여", 22)
        g.update_customer("C04", age=31)
        g.delete_customer("C06")
        self.assertEqual(g.check_integrity(), [])
        text = _capture(print_group_tree, g)
        self.assertEqual(text, _lines(
            "[그룹별 고객] 전체 6명",
            "  여성 5명",
            "    10대 (G-F-10) 0명",
            "    20대 (G-F-20) 4명",
            "      C01 고객1 (23세)",
            "      C02 고객2 (25세)",
            "      C03 고객3 (27세)",
            "      C07 고객7 (22세)",
            "    30대 (G-F-30) 1명",
            "      C05 고객5 (34세)",
            "    40대 이상 (G-F-40+) 0명",
            "  남성 1명",
            "    10대 (G-M-10) 0명",
            "    20대 (G-M-20) 0명",
            "    30대 (G-M-30) 1명",
            "      C04 고객4 (31세)",
            "    40대 이상 (G-M-40+) 0명",
        ))

    def test_empty_graph_tree(self) -> None:
        """고객이 없는 그래프: 그룹 8개가 모두 0명으로 나온다."""
        text = _capture(print_group_tree, ShopGraph())
        bands = ["10대 (G-{}-10)", "20대 (G-{}-20)", "30대 (G-{}-30)", "40대 이상 (G-{}-40+)"]
        expected = ["[그룹별 고객] 전체 0명"]
        for label, code in (("여성", "F"), ("남성", "M")):
            expected.append(f"  {label} 0명")
            expected.extend(f"    {band.format(code)} 0명" for band in bands)
        self.assertEqual(text, _lines(*expected))


class TestW9Neighbors(unittest.TestCase):
    """W9: print_neighbors 노드 하나의 인접 리스트."""

    def test_customer_node(self) -> None:
        """고객 노드: 소속 그룹 1개와 구매 상품(가중치 = 색상 수, 상한 적용 전 값), ID 순."""
        g = make_graph()
        before = snapshot(g)
        # [제안 형식] 머리 줄 "[인접 리스트] ID 표시 이름 (이웃 N개)", 이웃 줄은 2칸 들여쓰기에
        # "ID 표시 이름 (소속)" 또는 "(구매, 가중치 W)". 가중치는 g.weight() 그대로 (C01–P01은 4, 6.2)
        self.assertEqual(_capture(print_neighbors, g, "C01"), _lines(
            "[인접 리스트] C01 고객1 (이웃 3개)",
            "  G-F-20 여성·20대 (소속)",
            "  P01 오버핏 티셔츠 (구매, 가중치 4)",
            "  P02 와이드 슬랙스 (구매, 가중치 1)",
        ))
        self.assertEqual(snapshot(g), before)

    def test_product_node(self) -> None:
        """상품 노드: 산 고객과 가중치. P02는 C01(1), C02(2)."""
        g = make_graph()
        self.assertEqual(_capture(print_neighbors, g, "P02"), _lines(
            "[인접 리스트] P02 와이드 슬랙스 (이웃 2개)",
            "  C01 고객1 (구매, 가중치 1)",
            "  C02 고객2 (구매, 가중치 2)",
        ))

    def test_group_node(self) -> None:
        """그룹 노드: 소속 고객. 빈 그룹은 머리 줄만 (이웃 0개)."""
        g = make_graph()
        self.assertEqual(_capture(print_neighbors, g, "G-F-20"), _lines(
            "[인접 리스트] G-F-20 여성·20대 (이웃 3개)",
            "  C01 고객1 (소속)",
            "  C02 고객2 (소속)",
            "  C03 고객3 (소속)",
        ))
        self.assertEqual(_capture(print_neighbors, g, "G-M-30"), _lines(
            "[인접 리스트] G-M-30 남성·30대 (이웃 0개)",
        ))

    def test_customer_without_purchase(self) -> None:
        """구매 이력이 없는 신규 고객(B.4): 소속 그룹만."""
        g = make_graph()
        g.add_customer("고객7", "남", 45)
        self.assertEqual(_capture(print_neighbors, g, "C07"), _lines(
            "[인접 리스트] C07 고객7 (이웃 1개)",
            "  G-M-40+ 남성·40대 이상 (소속)",
        ))

    def test_unknown_node(self) -> None:
        """없는 노드 ID(B.4 없는 ID·형식이 틀린 값·빈 문자열): ValueError를 그대로 전달, 출력 없음, 상태 동일."""
        g = make_graph()
        before = snapshot(g)
        for node_id in ("C99", "X", "", " C01", "G-X-10"):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                with self.assertRaises(ValueError, msg=repr(node_id)):
                    print_neighbors(g, node_id)
            self.assertEqual(buffer.getvalue(), "", msg=repr(node_id))
        self.assertEqual(snapshot(g), before)


if __name__ == "__main__":
    unittest.main()
