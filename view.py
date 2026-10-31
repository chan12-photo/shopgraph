"""화면 출력 전용 함수.

모든 함수는 print만 하고 None을 돌려준다. ShopGraph의 공개 메서드와 graph.py의 대문자
공개 상수(읽기 전용)만 쓴다. 출력 형식은 W1에서 가고정, W8b에서 최종 고정한다 (부록 B.2).
"[남성 전체]" 같은 범위 표시 꾸밈은 이 모듈이 GENDER_LABELS·GROUP_LABELS로 만든다.
"""

from graph import ShopGraph


def print_table(headers: list[str], rows: list[list[object]]) -> None:
    """표를 출력한다. 한글은 2칸 폭으로 계산해 열을 맞춘다 (unicodedata.east_asian_width).

    인자:
        headers: 열 제목 리스트.
        rows: 행 리스트. 각 행은 열 개수만큼의 값 리스트.

    반환:
        없음.

    예외:
        NotImplementedError: W9에서 구현하기 전.
    """
    raise NotImplementedError("W9에서 구현 예정")


def print_group_tree(g: ShopGraph) -> None:
    """그룹별 고객 목록을 전체 → 성별 → 연령대 → 고객 들여쓰기로 출력한다.

    인자:
        g: 출력할 ShopGraph.

    반환:
        없음.

    예외:
        NotImplementedError: W9에서 구현하기 전.
    """
    raise NotImplementedError("W9에서 구현 예정")


def print_recommendation(g: ShopGraph, customer_id: str, result: list[dict]) -> None:
    """추천 결과를 근거(지지 고객)·구매 가능 색상·범위 안내와 함께 출력한다.

    결과가 비어 있으면 "추천할 상품이 없습니다"를 출력한다.

    인자:
        g: 조회할 ShopGraph.
        customer_id: 추천 대상 고객 ID.
        result: search.recommend()의 반환값.

    반환:
        없음.

    예외:
        ValueError: 없는 고객 ID일 때 g의 메서드가 낸 ValueError를 그대로 전달한다
            (메시지 표시는 main.py가 맡는다).
        NotImplementedError: W8b에서 구현하기 전.
    """
    raise NotImplementedError("W8b에서 구현 예정")


def print_neighbors(g: ShopGraph, node_id: str) -> None:
    """노드 하나의 인접 리스트를 출력한다.

    인자:
        g: 조회할 ShopGraph.
        node_id: 그룹·고객·상품 ID.

    반환:
        없음.

    예외:
        ValueError: 없는 노드 ID일 때 g.neighbors()가 낸 ValueError를 그대로 전달한다
            (메시지 표시는 main.py가 맡는다).
        NotImplementedError: W9에서 구현하기 전.
    """
    raise NotImplementedError("W9에서 구현 예정")
