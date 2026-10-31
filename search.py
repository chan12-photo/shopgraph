"""읽기 전용 조회·검색·추천 함수.

모든 함수는 첫 인자로 ShopGraph를 받고 데이터를 바꾸지 않는다. ShopGraph의 공개 메서드와
graph.py의 대문자 공개 상수(읽기 전용)만 쓴다. 반환 형식은 부록 B.2이며 W1에서 가고정,
W8b에서 최종 고정한다.

- find_products(조건 조회)는 상품 목록(product_ids)을 하나씩 걸러 내는 조회다 (계획서 5.3.1).
- S1~S4와 recommend는 구매 기록 전체를 훑지 않고 인접 관계(그룹 → 소속 고객 → 이웃 상품)를
  따라간다 (계획서 5.3.2).
- 정수 인자(가격·k)는 int만 인정하고 bool·숫자 문자열은 거부한다 (부록 B.3 정수 공통).
"""

from graph import K_DEFAULT, ShopGraph


def find_products(
    g: ShopGraph,
    kind: str | None = None,
    style: str | None = None,
    color: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
) -> list[str]:
    """조건(종류·스타일·색상·가격 범위)에 맞는 상품을 찾는다.

    색상 조건은 상품의 색상 목록에 있는지로 판단한다 (재고와 무관, 계획서 5.3.1).
    None인 조건은 적용하지 않는다.

    인자:
        g: 조회할 ShopGraph.
        kind: 종류. KINDS 중 하나 또는 None.
        style: 스타일. STYLES 중 하나 또는 None.
        color: 색상명 또는 None.
        price_min: 최저 가격(정수 0 이상, 포함) 또는 None.
        price_max: 최고 가격(정수 0 이상, 포함) 또는 None.

    반환:
        상품 ID 리스트, ID 오름차순.

    예외:
        ValueError: 종류·스타일이 상수 목록 밖, 가격이 정수 0 이상이 아님,
            price_min > price_max.
        NotImplementedError: W6에서 구현하기 전.
    """
    raise NotImplementedError("W6에서 구현 예정")


def products_of(g: ShopGraph, customer_id: str) -> list[dict]:
    """S1: 고객이 산 상품과 구매 집계를 돌려준다 (고객 → 상품).

    인자:
        g: 조회할 ShopGraph.
        customer_id: 고객 ID.

    반환:
        [{"product_id", "name", "colors": 정렬 리스트, "weight", "count", "total_qty",
        "last_date"}], 상품 ID 오름차순.

    예외:
        ValueError: 없는 고객 ID.
        NotImplementedError: W6에서 구현하기 전.
    """
    raise NotImplementedError("W6에서 구현 예정")


def customers_of(g: ShopGraph, product_id: str) -> list[dict]:
    """S2: 상품을 산 고객과 그 고객의 그룹·구매 색상을 돌려준다 (상품 → 고객).

    인자:
        g: 조회할 ShopGraph.
        product_id: 상품 ID.

    반환:
        [{"customer_id", "name", "group_id", "colors": 정렬 리스트}], 고객 ID 오름차순.

    예외:
        ValueError: 없는 상품 ID.
        NotImplementedError: W6에서 구현하기 전.
    """
    raise NotImplementedError("W6에서 구현 예정")


def members_of(g: ShopGraph, group_id: str) -> list[str]:
    """S3: 그룹에 소속된 고객을 돌려준다 (그룹 → 고객).

    인자:
        g: 조회할 ShopGraph.
        group_id: 그룹 ID.

    반환:
        고객 ID 리스트, ID 오름차순. 소속 고객이 없으면 빈 리스트.

    예외:
        ValueError: 없는 그룹 ID.
        NotImplementedError: W6에서 구현하기 전.
    """
    raise NotImplementedError("W6에서 구현 예정")


def group_popular(g: ShopGraph, group_id: str, k: int | None = None) -> list[dict]:
    """S4: 그룹 소속 고객들의 구매를 모아 인기 상품을 돌려준다 (그룹 → 고객 → 상품).

    점수는 그 상품을 산 소속 고객마다 min(가중치, WEIGHT_CAP)을 더한 값이고, buyers는 그
    상품을 산 소속 고객 수다. 품절 상품도 결과에 넣고 표시만 한다.

    인자:
        g: 조회할 ShopGraph.
        group_id: 그룹 ID.
        k: None이면 전체, 아니면 앞에서 k개 (정수 1~10).

    반환:
        [{"product_id", "score", "buyers", "sold_out": bool}],
        점수 내림차순 → 구매자 수 내림차순 → 상품 ID 오름차순.
        소속 고객이 없거나 소속 고객의 구매가 없으면 빈 리스트.

    예외:
        ValueError: 없는 그룹 ID, k가 None도 정수 1~10도 아님.
        NotImplementedError: W7에서 구현하기 전.
    """
    raise NotImplementedError("W7에서 구현 예정")


def recommend(g: ShopGraph, customer_id: str, k: int = K_DEFAULT) -> list[dict]:
    """고객에게 성별·연령대 그룹의 구매를 집계한 가중 인기 상품을 추천한다 (계획서 5.3.3).

    범위는 같은 그룹(group_of) → 같은 성별 그룹 4개(GROUP_IDS_BY_GENDER) → 그룹 8개 전부
    (GROUP_IDS) 순서로 넓히며, 선택이 k개 미만일 때 부족한 만큼만 넓은 범위에서 채운다.

    범위마다 점수를 새로 계산한다:
        동료 = 그 범위 그룹들의 members() 합집합 − 대상 고객, ID 오름차순
        동료마다 neighbors()의 상품 노드를 따라가며 (그룹 → 고객 → 상품)
            점수(p) += min(weight(동료, p), WEIGHT_CAP), 지지자(p)에 동료 추가
    후보에서 빼는 상품: 대상 고객이 이미 산 상품, 모든 색상이 품절인 상품,
    앞의 좁은 범위에서 이미 선택된 상품.

    인자:
        g: 조회할 ShopGraph.
        customer_id: 추천 대상 고객 ID (구매 이력이 없는 신규 고객 포함).
        k: 추천 개수. 정수 1~10, 기본 K_DEFAULT(3).

    반환:
        [{"product_id", "score", "buyers", "scope": "group" | "gender" | "all",
        "supporters": [고객 ID, ID 오름차순], "available_colors": [색상, 문자열 오름차순]}].
        buyers는 len(supporters)와 같다. available_colors는 g.available_colors()의 값이다.
        좁은 범위에서 고른 항목이 먼저 오고, 같은 범위 안에서는 점수 내림차순 →
        구매자 수 내림차순 → 상품 ID 오름차순. score는 그 항목의 scope 안에서 계산한 값이라
        범위가 다른 항목끼리는 비교하지 않는다. k개보다 적으면 있는 만큼, 없으면 빈 리스트.

    예외:
        ValueError: 없는 고객 ID, k가 정수 1~10이 아님.
        NotImplementedError: W8에서 구현하기 전.
    """
    raise NotImplementedError("W8에서 구현 예정")
