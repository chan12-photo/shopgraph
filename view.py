"""화면 출력 전용 함수.

기존 print 공개 함수는 print만 하고 None을 돌려준다. 추천 화면을 웹과 공유하는
recommendation_view·recommendation_scope_label은 출력 없이 표시 구조·문자열을 돌려준다. ShopGraph의 공개
메서드와 graph.py의 대문자 공개 상수(읽기 전용)만 쓴다. 출력 형식은 W1 가고정, W8b 최종 고정 (부록 B.2).
print_table·print_group_tree·print_neighbors의 글자 형식은 W9에서 정한다.
"[남성 전체]" 같은 범위 표시 꾸밈은 이 모듈이 GENDER_LABELS·GROUP_LABELS로 만든다.
"""

import unicodedata

from graph import AGE_BANDS, GENDER_LABELS, GENDERS, GROUP_IDS, GROUP_IDS_BY_GENDER, GROUP_LABELS, ShopGraph

# 숫자로 끝나는 ID 뒤 조사: 끝 숫자를 읽은 소리에 받침이 있으면 (이, 은) 아니면 (가, 는)
# 0 영, 1 일, 3 삼, 6 육, 7 칠, 8 팔 = 받침 있음 / 2 이, 4 사, 5 오, 9 구 = 받침 없음
_DIGITS_WITH_FINAL = frozenset("013678")

# 범위 순서와 넓힐 때 안내에 쓰는 이름. "gender"는 성별에 따라 "여성 전체"·"남성 전체"가 된다
_SCOPE_ORDER = ("group", "gender", "all")
_ALL_LABEL = "전체 고객"
_SCORE_NOTE = " ※ 점수는 각 범위 안에서 계산한 값이라 범위가 다른 항목끼리 비교하지 않습니다"

# 화면에서 2칸을 차지하는 east_asian_width 분류 (전각 F, 넓은 문자 W). 그 밖(A 포함)은 1칸
_WIDE_CLASSES = frozenset("FW")

# 표의 열 사이 공백, 트리·인접 리스트의 한 단계 들여쓰기
_COLUMN_GAP = "  "
_INDENT = "  "


def print_table(headers: list[str], rows: list[list[object]]) -> None:
    """표를 출력한다. 한글은 2칸 폭으로 계산해 열을 맞춘다 (unicodedata.east_asian_width).

    정수(bool 제외)만 있는 열은 머리 칸까지 오른쪽 정렬, 나머지 열은 왼쪽 정렬한다.
    머리 줄 아래에 열 폭만큼 "-"를 긋고, 줄 끝 공백은 지운다. 행이 없으면 머리 줄과 구분 줄만 출력한다.

    인자:
        headers: 열 제목 리스트.
        rows: 행 리스트. 각 행은 열 개수만큼의 값 리스트.

    반환:
        없음.

    예외:
        ValueError: 칸 수가 머리 칸 수와 다른 행이 있을 때. 이때는 아무것도 출력하지 않는다.
    """
    cells = [[str(value) for value in row] for row in rows]
    for row in cells:
        if len(row) != len(headers):
            raise ValueError(f"표의 칸 수가 머리({len(headers)}칸)와 다릅니다: {len(row)}칸")
    widths = [max([_display_width(text) for text in column])
              for column in zip(headers, *cells)]
    numeric = [bool(rows) and all(isinstance(row[i], int) and not isinstance(row[i], bool) for row in rows)
               for i in range(len(headers))]
    print(_table_line(headers, widths, numeric))
    print(_COLUMN_GAP.join("-" * width for width in widths))
    for row in cells:
        print(_table_line(row, widths, numeric))


def _display_width(text: str) -> int:
    """문자열이 화면에서 차지하는 칸 수를 센다 (한글 등 W·F 문자는 2칸, 나머지는 1칸).

    인자:
        text: 셀 문자열.

    반환:
        화면 칸 수.

    예외:
        없음.
    """
    return sum(2 if unicodedata.east_asian_width(char) in _WIDE_CLASSES else 1 for char in text)


def _table_line(texts: list[str], widths: list[int], numeric: list[bool]) -> str:
    """표 한 줄을 열 폭에 맞춰 만든다 (정수 열은 오른쪽, 나머지는 왼쪽 정렬, 줄 끝 공백 제거).

    인자:
        texts: 칸 문자열 리스트.
        widths: 열마다의 화면 폭.
        numeric: 열마다 오른쪽 정렬 여부.

    반환:
        표 한 줄 문자열.

    예외:
        없음.
    """
    padded = []
    for text, width, right in zip(texts, widths, numeric):
        space = " " * (width - _display_width(text))
        padded.append(space + text if right else text + space)
    return _COLUMN_GAP.join(padded).rstrip()


def print_group_tree(g: ShopGraph) -> None:
    """그룹별 고객 목록을 전체 → 성별 → 연령대 → 고객 들여쓰기로 출력한다.

    그룹 8개를 모두(소속 고객이 없는 그룹 포함) 성별 → 연령대 순으로 보여 주고,
    그룹 안 고객은 ID 순으로 "ID 이름 (나이세)"를 출력한다. 들여쓰기는 단계마다 2칸.

    인자:
        g: 출력할 ShopGraph.

    반환:
        없음.

    예외:
        없음.
    """
    print(f"[그룹별 고객] 전체 {len(g.customer_ids())}명")
    for gender, _ in GENDERS:
        group_ids = GROUP_IDS_BY_GENDER[gender]
        members = {group_id: g.members(group_id) for group_id in group_ids}
        print(f"{_INDENT}{GENDER_LABELS[gender]} {sum(len(ids) for ids in members.values())}명")
        # GROUP_IDS_BY_GENDER는 연령대 순이라 AGE_BANDS와 같은 순서로 짝지어진다 (graph.py)
        for group_id, band in zip(group_ids, AGE_BANDS):
            print(f"{_INDENT * 2}{band[1]} ({group_id}) {len(members[group_id])}명")
            for customer_id in members[group_id]:
                customer = g.get_customer(customer_id)
                print(f"{_INDENT * 3}{customer_id} {customer['name']} ({customer['age']}세)")


def recommendation_scope_label(g: ShopGraph, customer_id: str, scope: str) -> str:
    """추천 결과의 범위 코드를 화면 표시 이름으로 바꾼다.

    인자:
        g: 고객의 성별을 조회할 ShopGraph.
        customer_id: 추천 대상 고객 ID.
        scope: recommend() 결과의 ``group``, ``gender`` 또는 ``all``.

    반환:
        ``같은 그룹``, 성별 표시 이름이 붙은 ``여성 전체``·``남성 전체``, 또는 ``전체 고객``.

    예외:
        ValueError: 없는 고객 ID이거나 지원하지 않는 범위 코드일 때.
    """
    gender = g.get_customer(customer_id)["gender"]
    if scope == "group":
        return "같은 그룹"
    if scope == "gender":
        return f"{GENDER_LABELS[gender]} 전체"
    if scope == "all":
        return _ALL_LABEL
    raise ValueError(f"알 수 없는 추천 범위입니다 (입력: {scope})")


def recommendation_view(g: ShopGraph, customer_id: str, result: list[dict], k: int) -> dict:
    """추천 화면을 출력 없이 구조화해 돌려준다.

    인자:
        g: 추천 상품·고객·간선 정보를 조회할 ShopGraph.
        customer_id: 추천 대상 고객 ID.
        result: 같은 고객·K로 호출한 recommend() 결과.
        k: recommend()에 넘긴 추천 개수 K.

    반환:
        ``{"header": str, "items": [[상품줄, 근거줄, 색상줄], ...],
        "notices": [str, ...]}`` 새 딕셔너리. 빈 결과는 header만 의미 있는 값이고
        items·notices는 빈 리스트다.

    예외:
        ValueError: 없는 고객 ID이거나 결과 항목의 고객·상품 ID가 없을 때.
    """
    customer = g.get_customer(customer_id)
    group_label = GROUP_LABELS[g.group_of(customer_id)]
    gender_label = f"{GENDER_LABELS[customer['gender']]} 전체"
    head = f"[추천] {customer['name']}({customer_id}, {group_label})님께 추천"
    if not result:
        return {"header": f"{head}할 상품이 없습니다", "items": [], "notices": []}

    items = [[line for line in _item_lines(g, rank, item, recommendation_scope_label(g, customer_id, item["scope"]))]
             for rank, item in enumerate(result, start=1)]
    widest = len(_SCOPE_ORDER) - 1 if len(result) < k else _SCOPE_ORDER.index(result[-1]["scope"])
    notices = []
    if widest > 0:
        notices.append(_widen_note(g, customer_id, group_label, gender_label, widest, k))
    if len(result) < k:
        notices.append(f" ※ 추천할 수 있는 상품이 {len(result)}개뿐이라 {k}개를 채우지 못함")
    if len({item["scope"] for item in result}) > 1:
        notices.append(_SCORE_NOTE)
    return {"header": f"{head} ({len(result)}개)", "items": items, "notices": notices}


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
    view = recommendation_view(g, customer_id, result, k)
    print(view["header"])
    for lines in view["items"]:
        for line in lines:
            print(line)
    for notice in view["notices"]:
        print(notice)


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


def _item_lines(g: ShopGraph, rank: int, item: dict, scope_label: str) -> list[str]:
    """추천 항목 하나의 세 화면 줄(상품·근거·구매 가능 색상)을 만든다.

    근거에는 지지 고객 ID를 적는다. 같은 성별 범위에서는 지지 고객마다 그룹 표시 이름을 붙이고,
    그 상품을 2가지 이상 색상으로 산 지지 고객은 색상 수를 덧붙인다 (5.3.3 출력 예시).

    인자:
        g: 조회할 ShopGraph.
        rank: 화면 순번 (1부터).
        item: recommend() 결과 항목 하나.
        scope_label: 범위 표시 이름 (예: "남성 전체").

    반환:
        상품·근거·구매 가능 색상 순서의 새 문자열 세 개.

    예외:
        ValueError: 항목의 상품·지지 고객 ID가 g에 없을 때 g의 메서드가 낸 것을 그대로 전달한다.
    """
    product_id = item["product_id"]
    name = g.get_product(product_id)["name"]
    first = (f" {rank}. {name} ({product_id}) - 점수 {item['score']}, "
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
    third = f"    구매 가능 색상: {', '.join(item['available_colors'])}"
    return [first, reason, third]


def _print_item(g: ShopGraph, rank: int, item: dict, scope_label: str) -> None:
    """추천 항목의 세 줄을 출력한다 (기존 내부 호환용)."""
    for line in _item_lines(g, rank, item, scope_label):
        print(line)


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

    머리 줄에 노드의 표시 이름과 이웃 수를 적고, 이웃을 ID 순으로 한 줄씩 출력한다.
    그룹–고객 이웃은 "(소속)", 고객–상품 이웃은 "(구매, 가중치 W)"로 표시한다 (W = g.weight(),
    추천 점수의 상한 적용 전 값). 전체 노드 출력은 main.py가 노드마다 이 함수를 부른다.

    인자:
        g: 조회할 ShopGraph.
        node_id: 그룹·고객·상품 ID.

    반환:
        없음.

    예외:
        ValueError: 없는 노드 ID일 때 g.neighbors()가 낸 ValueError를 그대로 전달한다
            (메시지 표시는 main.py가 맡는다). 이때는 아무것도 출력하지 않는다.
    """
    neighbor_ids = g.neighbors(node_id)
    customer_ids = set(g.customer_ids())
    print(f"[인접 리스트] {node_id} {_node_name(g, node_id, customer_ids)} (이웃 {len(neighbor_ids)}개)")
    for other_id in neighbor_ids:
        name = _node_name(g, other_id, customer_ids)
        if node_id in GROUP_IDS or other_id in GROUP_IDS:
            relation = "소속"
        elif node_id in customer_ids:
            relation = f"구매, 가중치 {g.weight(node_id, other_id)}"
        else:
            relation = f"구매, 가중치 {g.weight(other_id, node_id)}"
        print(f"{_INDENT}{other_id} {name} ({relation})")


def _node_name(g: ShopGraph, node_id: str, customer_ids: set[str]) -> str:
    """노드의 화면 표시 이름을 돌려준다 (그룹은 GROUP_LABELS, 고객·상품은 이름).

    인자:
        g: 조회할 ShopGraph.
        node_id: 그래프에 있는 그룹·고객·상품 ID.
        customer_ids: g의 고객 ID 집합 (고객과 상품을 가르는 데 쓴다).

    반환:
        표시 이름 문자열.

    예외:
        ValueError: 고객·상품 ID가 g에 없을 때 g의 메서드가 낸 것을 그대로 전달한다.
    """
    if node_id in GROUP_IDS:
        return GROUP_LABELS[node_id]
    if node_id in customer_ids:
        return g.get_customer(node_id)["name"]
    return g.get_product(node_id)["name"]
