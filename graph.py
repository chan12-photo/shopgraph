"""ShopGraph 그래프 엔진.

원본 데이터(고객·상품·구매 기록), 그래프(그룹 노드·인접 리스트·간선 집계),
ID 발급 카운터와 모든 변경 메서드를 한 객체에 둔다. 데이터를 바꾸는 유일한 통로다
(계획서 5.5). 다른 모듈은 ShopGraph의 공개 메서드와 이 모듈의 대문자 공개 상수
(읽기 전용)만 쓴다. 그룹 ID 문자열을 만들거나 해석하는 코드는 이 모듈에만 둔다.

공통 입력 규칙 (부록 B.3):
    정수 인자(나이·가격·재고·수량)는 int만 인정한다. bool(True/False)과
    숫자 문자열("3")은 거부한다.
    이름·상품명·색상명(구매 색상 포함)은 앞뒤 공백을 지운 값으로 검증하고, 저장할 때도
    지운 값으로 저장한다.
"""

from types import MappingProxyType
from typing import Final

# 상품 종류 (부록 B.3)
KINDS: Final[tuple[str, ...]] = ("상의", "하의", "아우터")

# 상품 스타일 (부록 B.3)
STYLES: Final[tuple[str, ...]] = ("캐주얼", "미니멀", "스트릿", "포멀")

# 성별: (입력·저장 값, 그룹 ID에 쓰는 코드). 이 순서가 그룹 ID 오름차순이 된다 (계획서 5.2)
GENDERS: Final[tuple[tuple[str, str], ...]] = (("여", "F"), ("남", "M"))

# 성별 → 화면 표시 이름. "[남성 전체]" 같은 꾸밈은 view.py가 맡는다
GENDER_LABELS: Final[MappingProxyType[str, str]] = MappingProxyType({"여": "여성", "남": "남성"})

# 연령대: (그룹 ID에 쓰는 코드, 표시 이름, 최소 나이, 최대 나이) (계획서 5.2, 부록 B.3 나이 10~99)
AGE_BANDS: Final[tuple[tuple[str, str, int, int], ...]] = (
    ("10", "10대", 10, 19),
    ("20", "20대", 20, 29),
    ("30", "30대", 30, 39),
    ("40+", "40대 이상", 40, 99),
)

# 아래 그룹 상수 3개는 GENDERS·GENDER_LABELS·AGE_BANDS에서 만들어 낸다 (부록 B.1 그룹 ID 형식)

# 성별 → 같은 성별의 그룹 ID 4개, 연령대 순 (추천의 "gender" 범위, 계획서 5.3.3)
GROUP_IDS_BY_GENDER: Final[MappingProxyType[str, tuple[str, ...]]] = MappingProxyType({
    gender: tuple(f"G-{code}-{band[0]}" for band in AGE_BANDS)
    for gender, code in GENDERS
})

# 그룹 ID 8개, ID 오름차순 (부록 B.1)
GROUP_IDS: Final[tuple[str, ...]] = tuple(
    group_id for gender, _ in GENDERS for group_id in GROUP_IDS_BY_GENDER[gender]
)

# 그룹 ID → 화면 표시 이름, 예: "여성·20대" (계획서 5.2 그림, 5.3.3 출력 예시)
GROUP_LABELS: Final[MappingProxyType[str, str]] = MappingProxyType({
    group_id: f"{GENDER_LABELS[gender]}·{band[1]}"
    for gender, _ in GENDERS
    for group_id, band in zip(GROUP_IDS_BY_GENDER[gender], AGE_BANDS)
})

# 추천·S4 점수에서 고객 1명이 한 상품에 주는 점수 기여의 상한 (계획서 5.3.3)
WEIGHT_CAP: Final[int] = 3

# 추천 개수 K의 기본값과 최댓값 (부록 B.1·B.3, 허용 범위 정수 1~10)
K_DEFAULT: Final[int] = 3
K_MAX: Final[int] = 10


class ShopGraph:
    """고객·상품·구매 데이터와 그 그래프를 함께 관리하는 객체.

    내부 상태 (부록 B.1, 모두 _로 시작하며 다른 모듈은 쓰지 않는다):
        _customers: 고객 ID → {"id", "name", "gender", "age"}
        _products: 상품 ID → {"id", "name", "kind", "style", "price", "stock"}
        _purchases: 구매 ID → {"id", "customer_id", "product_id", "color", "qty", "date"}
        _groups: 그룹 ID → {"id", "gender", "band"}
        _adj: 노드 ID → 이웃 ID 집합 (그룹·고객·상품 모두)
        _edges: (고객 ID, 상품 ID) → {"colors": 색상 집합, "count", "total_qty", "last_date"}
        _next_ids: {"C": 다음 고객 번호, "P": 다음 상품 번호, "T": 다음 구매 번호}

    조회 메서드는 모두 새로 만든 객체(새 리스트·새 딕셔너리)를 돌려준다. 돌려받은 값을
    고쳐도 내부는 바뀌지 않는다 (부록 B.2). 정수·공백 규칙은 모듈 설명의 공통 입력 규칙을 따른다.
    """

    def __init__(
        self,
        customers: list[dict] | None = None,
        products: list[dict] | None = None,
        purchases: list[dict] | None = None,
    ) -> None:
        """초기 데이터를 검증한 뒤 복사해서 보관하고 그래프를 구성한다 (부록 B.1 생성자 계약).

        모든 검증이 끝난 뒤에 레코드를 복사해서 보관한다. 상품의 stock 딕셔너리까지 복사하므로
        호출자가 넘긴 딕셔너리를 나중에 고쳐도 내부는 바뀌지 않는다. 이름·상품명·색상명은
        앞뒤 공백을 지운 값으로 저장한다. 그룹 노드 8개를 만들고, 원본에서 그래프를 구축하고,
        ID 발급 카운터를 종류별로 초기 레코드의 가장 큰 번호 + 1(없으면 1)로 정한다.

        인자:
            customers: 고객 레코드 딕셔너리의 리스트 또는 None(빈 리스트로 봄).
                레코드 모양은 {"id", "name", "gender", "age"}.
            products: 상품 레코드 딕셔너리의 리스트 또는 None.
                레코드 모양은 {"id", "name", "kind", "style", "price", "stock"}.
            purchases: 구매 레코드 딕셔너리의 리스트 또는 None.
                레코드 모양은 {"id", "customer_id", "product_id", "color", "qty", "date"}.

        반환:
            없음.

        예외:
            ValueError: 인자가 리스트도 None도 아니거나, 레코드가 딕셔너리가 아니거나 키가
                위 레코드 모양과 다를 때, 초기 레코드 ID의 형식·범위가 틀리거나 같은 종류 안에서 중복될 때,
                값이 부록 B.3 규칙(구매일 형식·실제 날짜 포함)을 어길 때, 구매 기록이
                함께 받은 고객·상품에 없는 ID를 참조할 때. 이때 객체는 만들어지지 않는다.
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def add_customer(self, name: str, gender: str, age: int) -> str:
        """고객을 등록하고 성별·연령대에 맞는 그룹에 자동으로 연결한다.

        인자:
            name: 이름. 앞뒤 공백을 지운 뒤 1~20자. 지운 값으로 저장한다.
            gender: "남" 또는 "여".
            age: 나이. 정수 10~99.

        반환:
            새로 발급한 고객 ID (예: "C07").

        예외:
            ValueError: 입력이 부록 B.3 규칙을 어기거나 ID 한도(C99)를 넘을 때.
                실패하면 아무것도 바꾸지 않고 ID도 발급하지 않는다.
            NotImplementedError: W4에서 구현하기 전.
        """
        raise NotImplementedError("W4에서 구현 예정")

    def update_customer(
        self,
        customer_id: str,
        name: str | None = None,
        gender: str | None = None,
        age: int | None = None,
    ) -> None:
        """고객의 이름·성별·나이를 수정한다. 그룹이 달라지면 소속 간선을 새 그룹으로 옮긴다.

        인자:
            customer_id: 수정할 고객 ID.
            name: 새 이름(앞뒤 공백을 지운 뒤 1~20자, 지운 값으로 저장). None이면 바꾸지 않는다.
            gender: 새 성별("남" 또는 "여"). None이면 바꾸지 않는다.
            age: 새 나이(정수 10~99). None이면 바꾸지 않는다.

        반환:
            없음.

        예외:
            ValueError: 없는 고객 ID, 바꿀 항목이 하나도 없음, 값이 부록 B.3 규칙을 어김.
                하나라도 실패하면 유효한 값까지 아무것도 반영하지 않는다.
            NotImplementedError: W4에서 구현하기 전.
        """
        raise NotImplementedError("W4에서 구현 예정")

    def delete_customer(self, customer_id: str) -> int:
        """고객과 그 고객의 구매 기록을 함께 삭제하고 노드·간선을 제거한다.

        삭제 확인 메시지는 main.py가 맡는다.

        인자:
            customer_id: 삭제할 고객 ID.

        반환:
            함께 삭제된 구매 기록 수.

        예외:
            ValueError: 없는 고객 ID.
            NotImplementedError: W4에서 구현하기 전.
        """
        raise NotImplementedError("W4에서 구현 예정")

    def add_product(
        self,
        name: str,
        kind: str,
        style: str,
        price: int,
        stock: dict[str, int],
    ) -> str:
        """상품을 등록하고 상품 노드를 만든다. stock은 복사해서 보관한다.

        인자:
            name: 상품명. 앞뒤 공백을 지운 뒤 1~20자. 지운 값으로 저장한다.
            kind: 종류. KINDS 중 하나.
            style: 스타일. STYLES 중 하나.
            price: 가격. 정수 0 이상.
            stock: 색상 → 재고. 색상 1개 이상, 색상명은 앞뒤 공백을 지운 뒤 1~10자,
                재고는 정수 0 이상. 공백을 지운 뒤 같은 색상명이 두 번 나오면 거부.
                색상명은 지운 값으로 저장한다.

        반환:
            새로 발급한 상품 ID (예: "P06").

        예외:
            ValueError: 입력이 부록 B.3 규칙을 어기거나 ID 한도(P99)를 넘을 때.
                실패하면 아무것도 바꾸지 않고 ID도 발급하지 않는다.
            NotImplementedError: W4에서 구현하기 전.
        """
        raise NotImplementedError("W4에서 구현 예정")

    def update_product(
        self,
        product_id: str,
        name: str | None = None,
        kind: str | None = None,
        style: str | None = None,
        price: int | None = None,
        stock: dict[str, int] | None = None,
    ) -> None:
        """상품의 이름·종류·스타일·가격·색상별 재고를 수정한다.

        stock은 통째로 교체하고 복사해서 보관한다. 새 딕셔너리에 없는 색상은 삭제로 보며,
        그 색상의 구매 기록이 하나라도 있으면 수정 전체를 거절한다.

        인자:
            product_id: 수정할 상품 ID.
            name: 새 상품명(add_product와 같은 규칙). None이면 바꾸지 않는다.
            kind: 새 종류. None이면 바꾸지 않는다.
            style: 새 스타일. None이면 바꾸지 않는다.
            price: 새 가격. None이면 바꾸지 않는다.
            stock: 새 색상 → 재고 딕셔너리(add_product와 같은 규칙, 색상 비교는 공백을
                지운 이름으로). None이면 바꾸지 않는다.

        반환:
            없음.

        예외:
            ValueError: 없는 상품 ID, 바꿀 항목이 하나도 없음, 값이 부록 B.3 규칙을 어김,
                구매 기록이 있는 색상 삭제. 하나라도 실패하면 아무것도 반영하지 않는다.
            NotImplementedError: W4에서 구현하기 전.
        """
        raise NotImplementedError("W4에서 구현 예정")

    def delete_product(self, product_id: str) -> int:
        """상품과 그 상품의 구매 기록을 함께 삭제하고 노드·간선을 제거한다.

        삭제 확인 메시지는 main.py가 맡는다.

        인자:
            product_id: 삭제할 상품 ID.

        반환:
            함께 삭제된 구매 기록 수.

        예외:
            ValueError: 없는 상품 ID.
            NotImplementedError: W4에서 구현하기 전.
        """
        raise NotImplementedError("W4에서 구현 예정")

    def add_purchase(
        self,
        customer_id: str,
        product_id: str,
        color: str,
        qty: int,
        date: str,
    ) -> str:
        """구매 기록을 등록하고 그 (고객, 상품) 쌍의 간선 집계를 원본에서 다시 계산한다.

        간선이 없으면 새로 만든다. 재고와는 연동하지 않는다.

        인자:
            customer_id: 구매한 고객 ID.
            product_id: 구매한 상품 ID.
            color: 구매 색상. 앞뒤 공백을 지운 값이 그 상품의 색상 목록에 있어야 한다
                (재고 0이어도 가능). 지운 값으로 저장한다.
            qty: 수량. 정수 1~99.
            date: 구매일. 정확히 "YYYY-MM-DD" 10자이고 실제 있는 날짜.

        반환:
            새로 발급한 구매 ID (예: "T014").

        예외:
            ValueError: 입력이 부록 B.3 규칙을 어기거나 ID 한도(T999)를 넘을 때.
                실패하면 아무것도 바꾸지 않고 ID도 발급하지 않는다.
            NotImplementedError: W5에서 구현하기 전.
        """
        raise NotImplementedError("W5에서 구현 예정")

    def update_purchase(
        self,
        purchase_id: str,
        color: str | None = None,
        qty: int | None = None,
    ) -> None:
        """구매 기록의 색상·수량을 수정하고 그 쌍의 간선 집계를 다시 계산한다.

        고객·상품·날짜는 바꾸지 않는다 (바꾸려면 삭제 후 새로 등록).

        인자:
            purchase_id: 수정할 구매 ID.
            color: 새 색상. 앞뒤 공백을 지운 값이 그 상품의 색상 목록에 있어야 하고,
                지운 값으로 저장한다. None이면 바꾸지 않는다.
            qty: 새 수량. 정수 1~99. None이면 바꾸지 않는다.

        반환:
            없음.

        예외:
            ValueError: 없는 구매 ID, 바꿀 항목이 하나도 없음, 값이 부록 B.3 규칙을 어김.
                하나라도 실패하면 아무것도 반영하지 않는다.
            NotImplementedError: W5에서 구현하기 전.
        """
        raise NotImplementedError("W5에서 구현 예정")

    def delete_purchase(self, purchase_id: str) -> None:
        """구매 기록을 삭제하고 그 쌍의 간선 집계를 다시 계산한다. 마지막 기록이면 간선을 지운다.

        인자:
            purchase_id: 삭제할 구매 ID.

        반환:
            없음.

        예외:
            ValueError: 없는 구매 ID.
            NotImplementedError: W5에서 구현하기 전.
        """
        raise NotImplementedError("W5에서 구현 예정")

    def get_customer(self, customer_id: str) -> dict:
        """고객 정보를 복사본으로 돌려준다.

        인자:
            customer_id: 조회할 고객 ID.

        반환:
            {"id", "name", "gender", "age"} 딕셔너리의 복사본.

        예외:
            ValueError: 없는 고객 ID (형식이 틀린 ID 포함).
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def get_product(self, product_id: str) -> dict:
        """상품 정보를 복사본으로 돌려준다. stock 딕셔너리도 복사한다.

        인자:
            product_id: 조회할 상품 ID.

        반환:
            {"id", "name", "kind", "style", "price", "stock"} 딕셔너리의 복사본.

        예외:
            ValueError: 없는 상품 ID (형식이 틀린 ID 포함).
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def get_purchase(self, purchase_id: str) -> dict:
        """구매 기록을 복사본으로 돌려준다.

        인자:
            purchase_id: 조회할 구매 ID.

        반환:
            {"id", "customer_id", "product_id", "color", "qty", "date"} 딕셔너리의 복사본.

        예외:
            ValueError: 없는 구매 ID (형식이 틀린 ID 포함).
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def customer_ids(self) -> list[str]:
        """모든 고객 ID를 돌려준다.

        인자:
            없음.

        반환:
            고객 ID 리스트, ID 오름차순. 고객이 없으면 빈 리스트.

        예외:
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def product_ids(self) -> list[str]:
        """모든 상품 ID를 돌려준다.

        인자:
            없음.

        반환:
            상품 ID 리스트, ID 오름차순. 상품이 없으면 빈 리스트.

        예외:
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def find_customers_by_name(self, name: str) -> list[str]:
        """이름이 완전히 일치하는 고객을 찾는다. 앞뒤 공백을 지운 뒤 비교하고 부분 일치는 하지 않는다.

        인자:
            name: 찾을 이름.

        반환:
            고객 ID 리스트, ID 오름차순. 없으면 빈 리스트.

        예외:
            ValueError: 공백뿐인 이름.
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def find_products_by_name(self, name: str) -> list[str]:
        """상품명이 완전히 일치하는 상품을 찾는다. 앞뒤 공백을 지운 뒤 비교하고 부분 일치는 하지 않는다.

        인자:
            name: 찾을 상품명.

        반환:
            상품 ID 리스트, ID 오름차순. 없으면 빈 리스트.

        예외:
            ValueError: 공백뿐인 이름.
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def neighbors(self, node_id: str) -> list[str]:
        """노드(그룹·고객·상품)의 이웃 ID를 돌려준다.

        인자:
            node_id: 그룹·고객·상품 ID.

        반환:
            이웃 ID 리스트, ID 오름차순.

        예외:
            ValueError: 없는 노드 ID.
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def edge(self, customer_id: str, product_id: str) -> dict | None:
        """고객–상품 구매 간선의 집계값을 복사본으로 돌려준다.

        인자:
            customer_id: 고객 ID.
            product_id: 상품 ID.

        반환:
            {"colors": 정렬 리스트, "count", "total_qty", "last_date"} 새 딕셔너리.
            두 노드가 모두 있는데 간선이 없으면 None.

        예외:
            ValueError: 없는 고객 ID 또는 없는 상품 ID.
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def weight(self, customer_id: str, product_id: str) -> int:
        """고객–상품 간선의 가중치(그 고객이 그 상품을 산 서로 다른 색상 수)를 돌려준다.

        인자:
            customer_id: 고객 ID.
            product_id: 상품 ID.

        반환:
            가중치. 두 노드가 모두 있는데 간선이 없으면 0.

        예외:
            ValueError: 없는 고객 ID 또는 없는 상품 ID.
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def group_of(self, customer_id: str) -> str:
        """고객이 소속된 그룹 ID를 돌려준다.

        인자:
            customer_id: 고객 ID.

        반환:
            그룹 ID (예: "G-F-20").

        예외:
            ValueError: 없는 고객 ID.
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def members(self, group_id: str) -> list[str]:
        """그룹에 소속된 고객 ID를 돌려준다.

        인자:
            group_id: 그룹 ID. GROUP_IDS 중 하나.

        반환:
            고객 ID 리스트, ID 오름차순. 소속 고객이 없으면 빈 리스트.

        예외:
            ValueError: 없는 그룹 ID.
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def is_sold_out(self, product_id: str) -> bool:
        """상품의 모든 색상이 품절(재고 0)인지 알려준다.

        인자:
            product_id: 상품 ID.

        반환:
            모든 색상의 재고가 0이면 True, 아니면 False.

        예외:
            ValueError: 없는 상품 ID.
            NotImplementedError: W4에서 구현하기 전.
        """
        raise NotImplementedError("W4에서 구현 예정")

    def available_colors(self, product_id: str) -> list[str]:
        """상품에서 구매 가능한(재고가 1 이상인) 색상을 돌려준다.

        인자:
            product_id: 상품 ID.

        반환:
            색상 리스트, 문자열 오름차순.

        예외:
            ValueError: 없는 상품 ID.
            NotImplementedError: W4에서 구현하기 전.
        """
        raise NotImplementedError("W4에서 구현 예정")

    def rebuild(self) -> None:
        """원본 데이터에서 그래프(그룹 소속·인접 리스트·간선 집계)를 다시 만든다.

        ID 발급 카운터는 바꾸지 않는다 (삭제된 ID를 재사용하지 않기 위해).

        인자:
            없음.

        반환:
            없음.

        예외:
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")

    def check_integrity(self) -> list[str]:
        """원본과 그래프의 일관성(계획서 5.3.5의 불변 조건)을 검사한다.

        상태를 하나도 바꾸지 않는다. 재구축 비교는 원본에서 따로 만든 임시 그래프와
        현재 그래프를 비교하는 방식으로 하며, 검사 중에 rebuild()를 부르지 않는다.

        인자:
            없음.

        반환:
            위반 설명 문자열의 리스트. 정상이면 빈 리스트.

        예외:
            NotImplementedError: W5에서 구현하기 전.
        """
        raise NotImplementedError("W5에서 구현 예정")

    def stats(self) -> dict[str, int]:
        """그래프의 개수 통계를 돌려준다.

        인자:
            없음.

        반환:
            {"groups", "customers", "products", "membership_edges", "purchase_edges",
            "purchases"} 딕셔너리. 값은 모두 정수.

        예외:
            NotImplementedError: W3에서 구현하기 전.
        """
        raise NotImplementedError("W3에서 구현 예정")
