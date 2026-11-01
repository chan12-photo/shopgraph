"""손계산용 원자료표(docs/verification/w11_raw_by_group.md)를 만드는 검증 보조 스크립트.

프로그램 모듈(graph.py·search.py)은 import하지 않고 data.py만 읽는다 (계획서 11.3.2 W11:
계산 보조 스크립트는 프로그램 코드를 import하지 않는 독립 스크립트로 docs/verification/에 둔다).
구매 기록을 그룹 → 고객 → 상품 순으로 다시 배열할 뿐, 색상 가짓수·가중치·점수·합계 같은 집계는 하지 않는다.
그룹 판정(성별 + 연령대 10~19/20~29/30~39/40 이상)은 계획서 5.2 표를 이 스크립트 안에 그대로 적었다.

실행 (저장소 루트에서):
    python docs/verification/make_raw_by_group.py > docs/verification/w11_raw_by_group.md
"""

import pathlib
import sys

# 저장소 루트의 data.py를 찾을 수 있게 한다
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from data import initial_records  # noqa: E402

# 계획서 5.2 그룹 ID와 연령대 (graph.py를 import하지 않으려고 여기에 그대로 적음)
_GROUPS = (
    ("G-F-10", "여", 10, 19, "여성·10대"), ("G-F-20", "여", 20, 29, "여성·20대"),
    ("G-F-30", "여", 30, 39, "여성·30대"), ("G-F-40+", "여", 40, 99, "여성·40대 이상"),
    ("G-M-10", "남", 10, 19, "남성·10대"), ("G-M-20", "남", 20, 29, "남성·20대"),
    ("G-M-30", "남", 30, 39, "남성·30대"), ("G-M-40+", "남", 40, 99, "남성·40대 이상"),
)


def _stock_text(stock: dict[str, int]) -> str:
    """재고 딕셔너리를 "색상 수량" 목록 글자로 바꾼다 (data.py 순서 그대로).

    인자:
        stock: 색상 → 재고.

    반환:
        "블랙 5, 화이트 3" 모양의 문자열.

    예외:
        없음.
    """
    return ", ".join(f"{color} {qty}" for color, qty in stock.items())


def _print_group(group: tuple, customers: list[dict], products: dict[str, dict], purchases: list[dict]) -> None:
    """그룹 하나의 소속 고객 표, 구매 기록 원래 행(고객 → 상품 → 구매 ID 순), 등장 상품 표를 출력한다.

    인자:
        group: _GROUPS의 한 항목.
        customers: data.py 고객 레코드.
        products: 상품 ID → data.py 상품 레코드.
        purchases: data.py 구매 기록 레코드.

    반환:
        없음.

    예외:
        없음.
    """
    group_id, gender, low, high, label = group
    members = sorted((c for c in customers if c["gender"] == gender and low <= c["age"] <= high),
                     key=lambda c: c["id"])
    member_ids = {c["id"] for c in members}
    rows = sorted((p for p in purchases if p["customer_id"] in member_ids),
                  key=lambda p: (p["customer_id"], p["product_id"], p["id"]))
    print(f"## {label} ({group_id})\n")
    print("### 소속 고객\n")
    if not members:
        print("소속 고객 없음\n")
    else:
        print("| 고객 ID | 이름 | 성별 | 나이 |\n|---|---|---|---|")
        print("".join(f"| {c['id']} | {c['name']} | {c['gender']} | {c['age']} |\n" for c in members))
    print("### 구매 기록 (고객 → 상품 → 구매 ID 순, 원래 행 그대로)\n")
    if not rows:
        print("구매 기록 없음\n")
    else:
        print("| 구매 ID | 고객 | 상품 | 색상 | 수량 | 날짜 |\n|---|---|---|---|---|---|")
        print("".join(f"| {p['id']} | {p['customer_id']} | {p['product_id']} | {p['color']} | {p['qty']} | "
                      f"{p['date']} |\n" for p in rows))
    used = sorted({p["product_id"] for p in rows})
    print("### 이 그룹의 구매 기록에 나오는 상품\n")
    if not used:
        print("없음\n")
        return
    print("| 상품 ID | 이름 | 종류 | 스타일 | 색상별 재고 |\n|---|---|---|---|---|")
    print("".join(f"| {pid} | {products[pid]['name']} | {products[pid]['kind']} | {products[pid]['style']} | "
                  f"{_stock_text(products[pid]['stock'])} |\n" for pid in used))


def main() -> None:
    """data.py를 읽어 원자료표 전체를 표준 출력으로 내보낸다.

    인자:
        없음.

    반환:
        없음.

    예외:
        없음.
    """
    customers, products, purchases = initial_records()
    by_id = {p["id"]: p for p in products}
    print("# 손계산용 원자료표 (data.py 시연 데이터, 그룹 → 고객 → 상품 순)\n")
    print("- 만든 방법: `python docs/verification/make_raw_by_group.py` (data.py만 읽음, graph·search import 없음)")
    print("- data.py의 구매 기록을 그룹 → 고객 → 상품 순으로 다시 배열한 것이다. 집계(색상 가짓수·가중치·점수·합계)는 "
          "하지 않았다. 손계산은 이 표의 원래 행으로 한다")
    print("- 그룹 판정은 계획서 5.2 (성별 + 나이 10~19/20~29/30~39/40 이상)")
    print(f"- 원본 개수: 고객 {len(customers)}명, 상품 {len(products)}개, 구매 기록 {len(purchases)}건 "
          "(아래 그룹별 구매 기록 행을 모두 합치면 이 수와 같아야 한다)\n")
    print("## 전체 상품 (data.py 순서)\n")
    print("| 상품 ID | 이름 | 종류 | 스타일 | 가격 | 색상별 재고 |\n|---|---|---|---|---|---|")
    print("".join(f"| {p['id']} | {p['name']} | {p['kind']} | {p['style']} | {p['price']} | "
                  f"{_stock_text(p['stock'])} |\n" for p in products))
    for group in _GROUPS:
        _print_group(group, customers, by_id, purchases)


if __name__ == "__main__":
    main()
