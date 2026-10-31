"""테스트 전용 도구.

snapshot(g)은 ShopGraph의 내부 상태 전체를 깊은 복사해 돌려준다 (부록 B.1 내부 상태 접근 범위).
테스트는 이 함수로 상태를 읽고 비교만 한다. 내부 상태를 직접 고치는 것은 고장 주입 테스트에만 허용한다.
"""

import copy

from graph import ShopGraph


def snapshot(g: ShopGraph) -> dict:
    """ShopGraph의 내부 상태 7가지를 깊은 복사해 하나의 딕셔너리로 돌려준다.

    실패 입력 테스트와 검사기 불변 테스트에서 전후 비교에 쓴다 (계획서 6.4).

    인자:
        g: 상태를 읽을 ShopGraph.

    반환:
        {"customers", "products", "purchases", "groups", "adj", "edges", "next_ids"}
        각 값은 내부 속성(_customers 등)의 깊은 복사본.

    예외:
        AttributeError: g에 부록 B.1의 내부 속성이 없을 때.
    """
    return copy.deepcopy({
        "customers": g._customers,
        "products": g._products,
        "purchases": g._purchases,
        "groups": g._groups,
        "adj": g._adj,
        "edges": g._edges,
        "next_ids": g._next_ids,
    })
