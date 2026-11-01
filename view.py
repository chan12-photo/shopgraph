"""화면 출력 전용 함수.

모든 함수는 print만 하고 None을 돌려준다. ShopGraph의 공개 메서드와 graph.py의 대문자
공개 상수(읽기 전용)만 쓴다. 출력 형식은 W1에서 가고정, W8b에서 최종 고정한다 (부록 B.2).
"[남성 전체]" 같은 범위 표시 꾸밈은 이 모듈이 GENDER_LABELS·GROUP_LABELS로 만든다.
"""

from graph import GENDER_LABELS, GROUP_LABELS, ShopGraph

# 숫자로 끝나는 ID 뒤 조사: 끝 숫자를 읽은 소리에 받침이 있으면 (이, 은) 아니면 (가, 는)
# 0 영, 1 일, 3 삼, 6 육, 7 칠, 8 팔 = 받침 있음 / 2 이, 4 사, 5 오, 9 구 = 받침 없음
_DIGITS_WITH_FINAL = frozenset("013678")

# 범위 순서와 넓힐 때 안내에 쓰는 이름. "gender"는 성별에 따라 "여성 전체"·"남성 전체"가 된다
_SCOPE_ORDER = ("group", "gender", "all")
_ALL_LABEL = "전체 고객"
_SCORE_NOTE = " ※ 점수는 각 범위 안에서 계산한 값이라 범위가 다른 항목끼리 비교하지 않습니다"


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


def print_recommendation(g: ShopGraph, customer_id: str, result: list[dict], k: int) -> None:
    """추천 결과를 근거(지지 고객)·구매 가능 색상·범위 안내와 함께 출력한다.

    결과가 비어 있으면 "추천할 상품이 없습니다"를 출력한다. 넓혀 본 범위는 k로 판정한다:
    결과 수 < k이면 전체 고객까지 넓힌 것이고, 결과 수 == k이면 마지막 항목의 범위까지 넓힌 것이다
    (그 사이 범위는 거쳤지만 새 후보가 없었던 것). 결과 수 < k이면 그 사실도 한 줄로 안내한다.
    범위가 2개 이상 섞였을 때만 점수 비교 안내를 출력한다.

    전제: result는 같은 k로 부른 search.recommend()의 반환값이며 len(result) ≤ k이다.

    인자:
        g: 조회할 ShopGraph.
        customer_id: 추천 대상 고객 ID.
        result: search.recommend()의 반환값.
        k: 그 recommend() 호출에 넘긴 추천 개수 K.

    반환:
        없음.

    예외:
        ValueError: 없는 고객 ID일 때 g의 메서드가 낸 ValueError를 그대로 전달한다
            (메시지 표시는 main.py가 맡는다). 이때는 아무것도 출력하지 않는다.
    """
    customer = g.get_customer(customer_id)
    group_label = GROUP_LABELS[g.group_of(customer_id)]
    gender_label = f"{GENDER_LABELS[customer['gender']]} 전체"
    head = f"[추천] {customer['name']}({customer_id}, {group_label})님께 추천"
    if not result:
        print(f"{head}할 상품이 없습니다")
        return
    print(f"{head} ({len(result)}개)")
    scope_labels = {"group": "같은 그룹", "gender": gender_label, "all": _ALL_LABEL}
    for rank, item in enumerate(result, start=1):
        _print_item(g, rank, item, scope_labels[item["scope"]])
    widest = len(_SCOPE_ORDER) - 1 if len(result) < k else _SCOPE_ORDER.index(result[-1]["scope"])
    if widest > 0:
        print(_widen_note(g, customer_id, group_label, gender_label, widest, k))
    if len(result) < k:
        print(f" ※ 추천할 수 있는 상품이 {len(result)}개뿐이라 {k}개를 채우지 못함")
    if len({item["scope"] for item in result}) > 1:
        print(_SCORE_NOTE)


def _id_particle(item_id: str, with_final: str, without_final: str) -> str:
    """숫자로 끝나는 ID 뒤에 붙일 조사를 고른다 (예: C01이, C02가).

    인자:
        item_id: 고객 ID 등 숫자로 끝나는 ID.
        with_final: 끝 숫자 소리에 받침이 있을 때의 조사 ("이" 또는 "은").
        without_final: 받침이 없을 때의 조사 ("가" 또는 "는").

    반환:
        고른 조사 문자열.

    예외:
        없음.
    """
    return with_final if item_id[-1] in _DIGITS_WITH_FINAL else without_final


def _print_item(g: ShopGraph, rank: int, item: dict, scope_label: str) -> None:
    """추천 항목 하나를 세 줄(상품·점수·범위 / 근거 / 구매 가능 색상)로 출력한다.

    근거에는 지지 고객 ID를 적는다. 같은 성별 범위에서는 지지 고객마다 그룹 표시 이름을 붙이고,
    그 상품을 2가지 이상 색상으로 산 지지 고객은 색상 수를 덧붙인다 (5.3.3 출력 예시).

    인자:
        g: 조회할 ShopGraph.
        rank: 화면 순번 (1부터).
        item: recommend() 결과 항목 하나.
        scope_label: 범위 표시 이름 (예: "남성 전체").

    반환:
        없음.

    예외:
        ValueError: 항목의 상품·지지 고객 ID가 g에 없을 때 g의 메서드가 낸 것을 그대로 전달한다.
    """
    product_id = item["product_id"]
    name = g.get_product(product_id)["name"]
    print(f" {rank}. {name} ({product_id}) - 점수 {item['score']}, "
          f"구매 고객 {item['buyers']}명 [{scope_label}]")
    supporters = item["supporters"]
    if item["scope"] == "gender":
        names = ", ".join(f"{cid}({GROUP_LABELS[g.group_of(cid)]})" for cid in supporters)
    else:
        names = ", ".join(supporters)
    reason = f"    근거: {names}{_id_particle(supporters[-1], '이', '가')} 구매"
    multi = [f"{cid}{_id_particle(cid, '은', '는')} {g.weight(cid, product_id)}가지"
             for cid in supporters if g.weight(cid, product_id) >= 2]
    if multi:
        reason += f" ({', '.join(multi)} 색상 구매)"
    print(reason)
    print(f"    구매 가능 색상: {', '.join(item['available_colors'])}")


def _widen_note(g: ShopGraph, customer_id: str, group_label: str, gender_label: str,
                widest: int, k: int) -> str:
    """범위를 넓혀 찾았다는 안내 줄을 5.3.3 출력 예시와 같은 틀로 만든다.

    같은 그룹에 대상 말고 다른 고객이 없으면 "에 다른 고객이 없어", 있으면 "에서 K개가 안 돼"를
    이유로 쓴다. 전체 고객까지 넓혔으면 "그래도 K개가 안 돼 '전체 고객'으로"를 덧붙인다.

    인자:
        g: 조회할 ShopGraph.
        customer_id: 추천 대상 고객 ID.
        group_label: 대상 고객의 그룹 표시 이름.
        gender_label: 같은 성별 범위 표시 이름 (예: "여성 전체").
        widest: 넓혀 본 가장 넓은 범위의 _SCOPE_ORDER 위치 (1 또는 2).
        k: 추천 개수 K.

    반환:
        안내 줄 문자열.

    예외:
        ValueError: 없는 고객 ID일 때 g의 메서드가 낸 것을 그대로 전달한다.
    """
    alone = g.members(g.group_of(customer_id)) == [customer_id]
    why = "에 다른 고객이 없어" if alone else f"에서 {k}개가 안 돼"
    note = f" ※ 같은 그룹({group_label}){why} '{gender_label}'로"
    if widest == 2:
        note += f", 그래도 {k}개가 안 돼 '{_ALL_LABEL}'으로"
    return note + " 넓혀 찾음"


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
