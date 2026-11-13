"""테스트 고정 데이터 (계획서 6.1 PoC 데이터).

함수를 부를 때마다 새 리스트와 새 딕셔너리(재고 딕셔너리 포함)를 만든다. 모듈 수준의
딕셔너리를 여러 테스트가 공유하면 앞 테스트가 고친 값 때문에 뒤 테스트가 이유 없이
실패하기 때문이다 (계획서 6.4 끝). 실행용 data.py는 읽지 않는다.
"""

from graph import ShopGraph


def customers() -> list[dict]:
    """6.1 고객 6명의 레코드를 새로 만들어 돌려준다.

    인자:
        없음.

    반환:
        {"id", "name", "gender", "age"} 딕셔너리의 새 리스트, ID 오름차순.

    예외:
        없음.
    """
    return [
        {"id": "C01", "name": "고객1", "gender": "여", "age": 23},
        {"id": "C02", "name": "고객2", "gender": "여", "age": 25},
        {"id": "C03", "name": "고객3", "gender": "여", "age": 27},
        {"id": "C04", "name": "고객4", "gender": "남", "age": 24},
        {"id": "C05", "name": "고객5", "gender": "여", "age": 34},
        {"id": "C06", "name": "고객6", "gender": "남", "age": 15},
    ]


def products() -> list[dict]:
    """6.1 상품 5개의 레코드를 새로 만들어 돌려준다.

    인자:
        없음.

    반환:
        {"id", "name", "kind", "style", "price", "stock"} 딕셔너리의 새 리스트, ID 오름차순.
        stock(색상 → 재고)도 매번 새 딕셔너리다.

    예외:
        없음.
    """
    return [
        {"id": "P01", "name": "오버핏 티셔츠", "kind": "상의", "style": "캐주얼", "price": 29000,
         "stock": {"블랙": 5, "화이트": 5, "그레이": 5, "네이비": 5}},
        {"id": "P02", "name": "와이드 슬랙스", "kind": "하의", "style": "미니멀", "price": 39000,
         "stock": {"블랙": 3, "베이지": 3}},
        {"id": "P03", "name": "크롭 가디건", "kind": "상의", "style": "미니멀", "price": 45000,
         "stock": {"아이보리": 2, "네이비": 0}},
        {"id": "P04", "name": "카고 팬츠", "kind": "하의", "style": "스트릿", "price": 49000,
         "stock": {"카키": 4, "블랙": 4}},
        {"id": "P05", "name": "후드 집업", "kind": "아우터", "style": "스트릿", "price": 59000,
         "stock": {"그레이": 0, "블랙": 0}},
    ]


def purchases() -> list[dict]:
    """6.1 구매 기록 13건을 새로 만들어 돌려준다 (수량은 모두 1).

    인자:
        없음.

    반환:
        {"id", "customer_id", "product_id", "color", "qty", "date"} 딕셔너리의 새 리스트, ID 오름차순.

    예외:
        없음.
    """
    rows = [
        ("T001", "C01", "P01", "블랙", "2026-09-01"),
        ("T002", "C01", "P01", "화이트", "2026-09-08"),
        ("T003", "C01", "P01", "그레이", "2026-09-15"),
        ("T004", "C01", "P01", "네이비", "2026-10-01"),
        ("T005", "C01", "P02", "블랙", "2026-09-03"),
        ("T006", "C02", "P02", "블랙", "2026-09-05"),
        ("T007", "C02", "P02", "베이지", "2026-09-20"),
        ("T008", "C02", "P03", "아이보리", "2026-09-10"),
        ("T009", "C03", "P03", "아이보리", "2026-09-12"),
        ("T010", "C03", "P05", "그레이", "2026-09-18"),
        ("T011", "C04", "P04", "카키", "2026-09-22"),
        ("T012", "C04", "P05", "블랙", "2026-09-25"),
        ("T013", "C04", "P01", "블랙", "2026-10-02"),
    ]
    return [
        {"id": tid, "customer_id": cid, "product_id": pid, "color": color, "qty": 1, "date": day}
        for tid, cid, pid, color, day in rows
    ]


def make_graph() -> ShopGraph:
    """6.1 데이터로 새 ShopGraph를 만든다 (처음 상태).

    인자:
        없음.

    반환:
        새로 만든 ShopGraph.

    예외:
        ShopGraph 생성자가 내는 예외를 그대로 전달한다 (W3 전에는 NotImplementedError).
    """
    return ShopGraph(customers(), products(), purchases())


def x1_boundary_records(customer_id: str = "C99", product_id: str = "P99",
                        purchase_id: str = "T999") -> tuple[list[dict], list[dict], list[dict]]:
    """X1 경계 픽스처. 인자: 세 ID. 반환: 각 한 건의 새 원본 리스트. 예외: 없음."""
    return (
        [{"id": customer_id, "name": "경계 고객", "gender": "여", "age": 25}],
        [{"id": product_id, "name": "경계 상품", "kind": "상의", "style": "캐주얼",
          "price": 1000, "stock": {"블랙": 2, "화이트": 1}}],
        [{"id": purchase_id, "customer_id": customer_id, "product_id": product_id,
          "color": "블랙", "qty": 1, "date": "2026-11-01"}],
    )


def x1_sort_records() -> tuple[list[dict], list[dict], list[dict]]:
    """X1 정렬 픽스처. 인자: 없음. 반환: 고객 5·상품 4·구매 8건. 예외: 없음.

    C09·C10·C99·C100이 P99·P100을 각 한 색씩 구매: 두 상품은 점수 4, 구매자 4로 동점.
    C01은 구매가 없어 두 상품을 같은 그룹에서 추천받는다. 삽입 순서는 숫자 순과 다르다.
    """
    cs = [{"id": cid, "name": "동명 고객", "gender": "여", "age": 25}
          for cid in ("C100", "C99", "C10", "C09", "C01")]
    ps = [{"id": pid, "name": "동명 상품", "kind": "상의", "style": "캐주얼",
           "price": 1000, "stock": {"화이트": 1, "블랙": 2}}
          for pid in ("P100", "P99", "P10", "P09")]
    rows = [("T1000", "C100", "P100", "블랙"), ("T999", "C100", "P99", "화이트"),
            ("T998", "C99", "P100", "블랙"), ("T997", "C99", "P99", "화이트"),
            ("T010", "C10", "P100", "블랙"), ("T009", "C10", "P99", "화이트"),
            ("T012", "C09", "P100", "블랙"), ("T011", "C09", "P99", "화이트")]
    ts = [{"id": tid, "customer_id": cid, "product_id": pid,
           "color": color, "qty": 1, "date": "2026-11-01"}
          for tid, cid, pid, color in rows]
    return cs, ps, ts
