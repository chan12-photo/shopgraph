"""UI1 view 순수 함수 계약 테스트.

tests/fixtures.py의 고정 데이터만 사용한다. recommendation_view가 stdout이나 그래프 상태를
바꾸지 않고 구조를 돌려주며, print_recommendation이 그 구조를 기존 순서로 출력하는지 확인한다.
"""

import contextlib
import copy
import io
import unittest

from search import recommend
from tests.fixtures import make_graph
from tests.helpers import snapshot
from view import print_recommendation, recommendation_scope_label, recommendation_view


def _capture(func: object, *args: object) -> str:
    """호출 한 번의 표준 출력과 반환값을 함께 확인한다."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        returned = func(*args)
    if returned is not None:
        raise AssertionError(f"{getattr(func, '__name__', func)!s}이 None이 아님: {returned!r}")
    return buffer.getvalue()


class TestUI1RecommendationView(unittest.TestCase):
    """recommendation_view·recommendation_scope_label의 UI1 계약."""

    def test_structure_is_pure_and_print_uses_same_order(self) -> None:
        """구조 반환은 조용하고 입력·그래프를 바꾸지 않으며 print가 같은 줄을 출력한다."""
        graph = make_graph()
        result = recommend(graph, "C01", 3)
        result_before = copy.deepcopy(result)
        state_before = snapshot(graph)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            view = recommendation_view(graph, "C01", result, 3)
        self.assertEqual(buffer.getvalue(), "")
        self.assertEqual(result, result_before)
        self.assertEqual(snapshot(graph), state_before)
        self.assertEqual(set(view), {"header", "items", "notices"})
        self.assertEqual(len(view["items"]), len(result))
        self.assertTrue(all(len(lines) == 3 for lines in view["items"]))
        expected_lines = [view["header"], *(line for lines in view["items"] for line in lines), *view["notices"]]
        self.assertEqual(_capture(print_recommendation, graph, "C01", result, 3),
                         "".join(line + "\n" for line in expected_lines))

    def test_empty_result_has_header_only(self) -> None:
        """추천 결과가 비면 기존 빈 결과 문장만 header로 두고 배열은 비운다."""
        graph = make_graph()
        for product_id in graph.product_ids():
            product = graph.get_product(product_id)
            graph.update_product(product_id, stock={color: 0 for color in product["stock"]})
        view = recommendation_view(graph, "C01", [], 3)
        self.assertIn("추천할 상품이 없습니다", view["header"])
        self.assertEqual(view["items"], [])
        self.assertEqual(view["notices"], [])

    def test_scope_labels(self) -> None:
        """group·gender·all 범위가 승인된 표시 이름으로 변환된다."""
        graph = make_graph()
        self.assertEqual(recommendation_scope_label(graph, "C01", "group"), "같은 그룹")
        self.assertEqual(recommendation_scope_label(graph, "C01", "gender"), "여성 전체")
        self.assertEqual(recommendation_scope_label(graph, "C01", "all"), "전체 고객")
        with self.assertRaises(ValueError):
            recommendation_scope_label(graph, "C01", "other")


if __name__ == "__main__":
    unittest.main()
