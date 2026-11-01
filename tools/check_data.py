"""시연 데이터(data.py) 점검 스크립트 (계획서 11.3.2 W11, 7장 시연용 더미 데이터 설계 원칙).

개발용 도구라 프로그램 실행 경로(main.py)에 들어가지 않는다. 데이터의 모양만 점검하고,
시연 장면의 기대 결과(추천 순위·점수 등)는 계산하지 않는다 (기대값은 docs/demo_expected.md, 사람이 손계산).

출력: 개수, 그룹별 인원(빈 그룹·구매가 적은 그룹 확인용 구매 기록 수 포함), 다색 구매자,
품절(전부·일부), 동명이인, 구매일 형식·분포, 무결성 검사.

실행 (저장소 루트에서):
    python tools/check_data.py
"""

import datetime
import pathlib
import re
import sys
from collections import Counter

# 저장소 루트의 data.py·graph.py를 찾을 수 있게 한다 (python tools/check_data.py로 실행할 때)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from data import initial_records  # noqa: E402
from graph import GENDER_LABELS, GENDERS, GROUP_IDS_BY_GENDER, GROUP_LABELS, ShopGraph  # noqa: E402

# 7장 원칙의 구매일 범위 (9~10월)
_DATE_FIRST = "2026-09-01"
_DATE_LAST = "2026-10-31"


def check_dates(purchases: list[dict]) -> None:
    """구매일이 YYYY-MM-DD 10자(0~9 숫자)이고 실제 날짜이며 9~10월 안인지 점검하고 월별 건수를 출력한다.

    ShopGraph 생성자도 형식을 검증하지만, 이 함수는 원본 레코드를 따로 다시 확인한다.

    인자:
        purchases: data.py의 구매 기록 리스트.

    반환:
        없음.

    예외:
        없음.
    """
    bad = []
    for record in purchases:
        day = record["date"]
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", day):
            bad.append(f"{record['id']} 형식 {day!r}")
            continue
        try:
            datetime.date.fromisoformat(day)
        except ValueError:
            bad.append(f"{record['id']} 없는 날짜 {day}")
            continue
        if not _DATE_FIRST <= day <= _DATE_LAST:
            bad.append(f"{record['id']} 9~10월 밖 {day}")
    months = Counter(record["date"][:7] for record in purchases)
    print("[구매일]")
    print(f"  월별 건수: {', '.join(f'{month} {count}건' for month, count in sorted(months.items()))}")
    print(f"  가장 이른 날 {min(r['date'] for r in purchases)}, 가장 늦은 날 {max(r['date'] for r in purchases)}")
    print(f"  형식·날짜·범위 문제: {len(bad)}건" + "".join(f"\n    - {item}" for item in bad))


def check_groups(g: ShopGraph) -> None:
    """그룹 8개의 인원과 소속 고객의 구매 기록 수를 출력하고, 빈 그룹을 따로 적는다.

    인자:
        g: 시연 데이터로 만든 ShopGraph.

    반환:
        없음.

    예외:
        없음.
    """
    print("[그룹별 인원]")
    product_ids = set(g.product_ids())
    empty = []
    for gender, _ in GENDERS:
        for group_id in GROUP_IDS_BY_GENDER[gender]:
            members = g.members(group_id)
            records = sum(g.edge(cid, pid)["count"] for cid in members
                          for pid in g.neighbors(cid) if pid in product_ids)
            print(f"  {GROUP_LABELS[group_id]} ({group_id}): {len(members)}명, 구매 기록 {records}건")
            if not members:
                empty.append(GROUP_LABELS[group_id])
    print(f"  빈 그룹: {', '.join(empty) if empty else '없음'}")


def check_multicolor(g: ShopGraph) -> None:
    """한 상품을 2가지 이상 색상으로 산 고객(다색 구매자)과 같은 색 재구매를 출력한다.

    인자:
        g: 시연 데이터로 만든 ShopGraph.

    반환:
        없음.

    예외:
        없음.
    """
    product_ids = set(g.product_ids())
    multi, repeat = [], []
    for cid in g.customer_ids():
        for pid in g.neighbors(cid):
            if pid not in product_ids:
                continue
            edge = g.edge(cid, pid)
            if len(edge["colors"]) >= 2:
                multi.append(f"{cid} {g.get_customer(cid)['name']} – {pid}: {', '.join(edge['colors'])}")
            if edge["count"] > len(edge["colors"]):
                repeat.append(f"{cid} – {pid}: 기록 {edge['count']}건, 색상 {len(edge['colors'])}가지")
    print(f"[다색 구매자] {len(multi)}쌍")
    print("".join(f"  {line}\n" for line in multi), end="")
    print(f"[같은 색 재구매] {len(repeat)}쌍")
    print("".join(f"  {line}\n" for line in repeat), end="")


def check_stock(g: ShopGraph) -> None:
    """전부 품절인 상품, 일부 색상만 품절인 상품, 아무도 사지 않은 상품을 출력한다.

    인자:
        g: 시연 데이터로 만든 ShopGraph.

    반환:
        없음.

    예외:
        없음.
    """
    all_out, partial, unsold = [], [], []
    for pid in g.product_ids():
        product = g.get_product(pid)
        zero = sorted(color for color, qty in product["stock"].items() if qty == 0)
        if g.is_sold_out(pid):
            all_out.append(f"{pid} {product['name']}")
        elif zero:
            partial.append(f"{pid} {product['name']} (품절 색상: {', '.join(zero)})")
        if not g.neighbors(pid):
            unsold.append(f"{pid} {product['name']}")
    print(f"[품절] 전부 품절 {len(all_out)}개, 일부 색상 품절 {len(partial)}개")
    print("".join(f"  전부: {line}\n" for line in all_out), end="")
    print("".join(f"  일부: {line}\n" for line in partial), end="")
    print(f"[아무도 사지 않은 상품] {', '.join(unsold) if unsold else '없음'}")


def check_same_names(g: ShopGraph) -> None:
    """같은 이름의 고객(동명이인)을 이름 조회(find_customers_by_name)로 찾아 출력한다.

    인자:
        g: 시연 데이터로 만든 ShopGraph.

    반환:
        없음.

    예외:
        없음.
    """
    names = sorted({g.get_customer(cid)["name"] for cid in g.customer_ids()})
    pairs = []
    for name in names:
        ids = g.find_customers_by_name(name)
        if len(ids) >= 2:
            groups = ", ".join(f"{cid}({GROUP_LABELS[g.group_of(cid)]})" for cid in ids)
            pairs.append(f"{name}: {groups}")
    print(f"[동명이인] {len(pairs)}쌍")
    print("".join(f"  {line}\n" for line in pairs), end="")


def main() -> int:
    """data.py로 ShopGraph를 만들고 점검 결과를 차례로 출력한다.

    인자:
        없음.

    반환:
        종료 코드. 생성자 검증 실패나 무결성 위반이 있으면 1, 아니면 0.

    예외:
        없음 (생성자의 ValueError는 메시지로 출력하고 1을 돌려준다).
    """
    customers, products, purchases = initial_records()
    try:
        g = ShopGraph(customers, products, purchases)
    except ValueError as error:
        print(f"[생성자 검증 실패] {error}")
        return 1
    genders = Counter(record["gender"] for record in customers)
    by_gender = ", ".join(f"{GENDER_LABELS[gender]} {count}명" for gender, count in sorted(genders.items()))
    print(f"[개수] 고객 {len(customers)}명({by_gender}), 상품 {len(products)}개, 구매 기록 {len(purchases)}건")
    colors = Counter(len(record["stock"]) for record in products)
    print(f"  상품당 색상 수: {', '.join(f'{k}가지 {v}개' for k, v in sorted(colors.items()))}")
    check_groups(g)
    check_multicolor(g)
    check_stock(g)
    check_same_names(g)
    check_dates(purchases)
    violations = g.check_integrity()
    print(f"[무결성 검사] 위반 {len(violations)}건" + "".join(f"\n  - {line}" for line in violations))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
