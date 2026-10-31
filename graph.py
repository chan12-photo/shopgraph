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

import datetime
import re
from collections.abc import Callable, Iterable
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

# 아래는 이 모듈 안에서만 쓰는 내부 상수·함수다 (다른 모듈은 쓰지 않는다)

# 구매일 형식: 정확히 YYYY-MM-DD 10자 (부록 B.3). \d는 다른 문자 체계의 숫자도 받으므로 [0-9]만 쓴다
_DATE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

# 레코드 ID 형식 (부록 B.1): 종류 글자 → 형식
_ID_PATTERNS: Final[MappingProxyType[str, re.Pattern[str]]] = MappingProxyType({
    "C": re.compile(r"C[0-9]{2}"),
    "P": re.compile(r"P[0-9]{2}"),
    "T": re.compile(r"T[0-9]{3}"),
})

# 초기 레코드의 키 (부록 B.1 내부 딕셔너리 모양)
_CUSTOMER_KEYS: Final[frozenset[str]] = frozenset({"id", "name", "gender", "age"})
_PRODUCT_KEYS: Final[frozenset[str]] = frozenset({"id", "name", "kind", "style", "price", "stock"})
_PURCHASE_KEYS: Final[frozenset[str]] = frozenset({"id", "customer_id", "product_id", "color", "qty", "date"})

# 이름·상품명 최대 길이, 색상명 최대 길이, 구매 수량 범위 (부록 B.3)
_NAME_MAX: Final[int] = 20
_COLOR_MAX: Final[int] = 10
_QTY_MIN: Final[int] = 1
_QTY_MAX: Final[int] = 99

# 성별 입력값 ("여", "남")
_GENDER_VALUES: Final[tuple[str, ...]] = tuple(gender for gender, _ in GENDERS)


def _check_date(value: object) -> str:
    """구매일이 부록 B.3 날짜 규칙을 지키는지 확인한다 (생성자와 W5 구매 등록·수정이 함께 쓴다).

    ① 정확히 "YYYY-MM-DD" 10자(숫자는 0~9만)인지 먼저 확인하고 ② 실제 있는 날짜인지 확인한다.
    ②만 쓰면 Python 3.11부터 "20261023"·"2026-W43-5"도 날짜로 변환돼 통과하므로 ①을 먼저 한다.

    인자:
        value: 검사할 값.

    반환:
        검사를 통과한 날짜 문자열 (입력 그대로).

    예외:
        ValueError: 문자열이 아니거나 형식이 다르거나 없는 날짜(예: 2026-02-30)일 때.
    """
    if not isinstance(value, str) or _DATE_PATTERN.fullmatch(value) is None:
        raise ValueError(f"구매일은 YYYY-MM-DD 형식이어야 합니다: {value!r}")
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"존재하지 않는 날짜입니다: {value}") from None
    return value


def _check_int(value: object, low: int, high: int | None, label: str) -> int:
    """정수 값이 범위 안에 있는지 확인한다. bool과 숫자 문자열은 거부한다 (부록 B.3 정수 공통).

    인자:
        value: 검사할 값.
        low: 허용하는 최솟값.
        high: 허용하는 최댓값. None이면 위쪽 제한이 없다.
        label: 오류 메시지에 쓸 항목 이름 (예: "나이").

    반환:
        검사를 통과한 정수.

    예외:
        ValueError: int가 아니거나(bool 포함) 범위 밖일 때.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label}: 정수여야 합니다: {value!r}")
    if value < low or (high is not None and value > high):
        limit = f"{low} 이상" if high is None else f"{low}~{high}"
        raise ValueError(f"{label}: {limit}이어야 합니다: {value}")
    return value


def _clean_text(value: object, max_len: int, label: str) -> str:
    """이름·상품명·색상명의 앞뒤 공백을 지우고 길이를 확인한다 (부록 B.3 공백 제거 값 저장).

    인자:
        value: 검사할 값.
        max_len: 공백을 지운 뒤 허용하는 최대 글자 수.
        label: 오류 메시지에 쓸 항목 이름 (예: "이름").

    반환:
        앞뒤 공백을 지운 문자열 (저장할 값).

    예외:
        ValueError: 문자열이 아니거나, 공백을 지운 뒤 1~max_len자가 아닐 때.
    """
    if not isinstance(value, str):
        raise ValueError(f"{label}: 문자열이어야 합니다: {value!r}")
    text = value.strip()
    if not 1 <= len(text) <= max_len:
        raise ValueError(f"{label}: 앞뒤 공백을 지운 뒤 1~{max_len}자여야 합니다: {value!r}")
    return text


def _check_choice(value: object, choices: tuple[str, ...], label: str) -> str:
    """값이 정해진 목록(성별·종류·스타일) 안에 있는지 확인한다.

    인자:
        value: 검사할 값.
        choices: 허용하는 값의 튜플.
        label: 오류 메시지에 쓸 항목 이름.

    반환:
        검사를 통과한 값.

    예외:
        ValueError: 목록에 없는 값일 때.
    """
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{label}: {'/'.join(choices)} 중 하나여야 합니다: {value!r}")
    return value


def _clean_stock(stock: object) -> dict[str, int]:
    """색상별 재고 딕셔너리를 검사하고 색상명의 공백을 지운 새 딕셔너리를 만든다 (부록 B.3).

    인자:
        stock: 색상 → 재고 딕셔너리.

    반환:
        색상명 공백을 지운 새 딕셔너리 (입력과 공유하지 않음).

    예외:
        ValueError: 딕셔너리가 아니거나 비었을 때, 색상명이 1~10자가 아닐 때,
            재고가 0 이상 정수가 아닐 때, 공백을 지운 뒤 같은 색상명이 두 번 나올 때.
    """
    if not isinstance(stock, dict) or not stock:
        raise ValueError("색상별 재고는 색상이 1개 이상인 딕셔너리여야 합니다")
    cleaned: dict[str, int] = {}
    for color, count in stock.items():
        name = _clean_text(color, _COLOR_MAX, "색상명")
        if name in cleaned:
            raise ValueError(f"색상명이 겹칩니다: {name}")
        cleaned[name] = _check_int(count, 0, None, "재고")
    return cleaned


def _check_record_id(value: object, prefix: str) -> str:
    """초기 레코드 ID의 형식·범위를 확인한다 (부록 B.1 생성자 계약 2: C01~C99, P01~P99, T001~T999).

    인자:
        value: 검사할 ID.
        prefix: 종류 글자 "C" | "P" | "T".

    반환:
        검사를 통과한 ID.

    예외:
        ValueError: 문자열이 아니거나 형식이 다르거나 번호가 0일 때.
    """
    if (not isinstance(value, str) or _ID_PATTERNS[prefix].fullmatch(value) is None
            or int(value[1:]) == 0):
        raise ValueError(f"ID 형식이 올바르지 않습니다: {value!r}")
    return value


def _check_record_shape(record: object, keys: frozenset[str], label: str) -> dict:
    """초기 레코드가 딕셔너리이고 키가 부록 B.1 모양과 정확히 같은지 확인한다.

    인자:
        record: 검사할 레코드.
        keys: 있어야 하는 키 집합 (빠져도, 남아도 안 됨).
        label: 오류 메시지에 쓸 종류 이름 (예: "고객").

    반환:
        검사를 통과한 레코드 (입력 그대로, 복사는 호출한 쪽이 한다).

    예외:
        ValueError: 딕셔너리가 아니거나 키가 다를 때.
    """
    if not isinstance(record, dict) or set(record) != keys:
        raise ValueError(f"{label} 레코드의 모양이 올바르지 않습니다: {record!r}")
    return record


def _clean_customer(record: object) -> dict:
    """초기 고객 레코드를 검사하고 공백을 지운 새 딕셔너리로 만든다.

    인자:
        record: {"id", "name", "gender", "age"} 딕셔너리.

    반환:
        새 고객 딕셔너리.

    예외:
        ValueError: 모양·ID·이름·성별·나이가 부록 B.1·B.3 규칙을 어길 때.
    """
    rec = _check_record_shape(record, _CUSTOMER_KEYS, "고객")
    return {
        "id": _check_record_id(rec["id"], "C"),
        "name": _clean_text(rec["name"], _NAME_MAX, "이름"),
        "gender": _check_choice(rec["gender"], _GENDER_VALUES, "성별"),
        "age": _check_int(rec["age"], AGE_BANDS[0][2], AGE_BANDS[-1][3], "나이"),
    }


def _clean_product(record: object) -> dict:
    """초기 상품 레코드를 검사하고 공백을 지운 새 딕셔너리로 만든다 (stock도 새 딕셔너리).

    인자:
        record: {"id", "name", "kind", "style", "price", "stock"} 딕셔너리.

    반환:
        새 상품 딕셔너리.

    예외:
        ValueError: 모양·ID·상품명·종류·스타일·가격·재고가 부록 B.1·B.3 규칙을 어길 때.
    """
    rec = _check_record_shape(record, _PRODUCT_KEYS, "상품")
    return {
        "id": _check_record_id(rec["id"], "P"),
        "name": _clean_text(rec["name"], _NAME_MAX, "상품명"),
        "kind": _check_choice(rec["kind"], KINDS, "종류"),
        "style": _check_choice(rec["style"], STYLES, "스타일"),
        "price": _check_int(rec["price"], 0, None, "가격"),
        "stock": _clean_stock(rec["stock"]),
    }


def _clean_purchase(record: object) -> dict:
    """초기 구매 레코드를 검사하고 색상 공백을 지운 새 딕셔너리로 만든다.

    고객·상품 참조와 색상 목록 확인은 고객·상품을 모두 읽은 뒤 _check_purchase_refs가 한다.

    인자:
        record: {"id", "customer_id", "product_id", "color", "qty", "date"} 딕셔너리.

    반환:
        새 구매 딕셔너리.

    예외:
        ValueError: 모양·ID·색상명·수량·구매일이 부록 B.1·B.3 규칙을 어길 때.
    """
    rec = _check_record_shape(record, _PURCHASE_KEYS, "구매")
    return {
        "id": _check_record_id(rec["id"], "T"),
        "customer_id": rec["customer_id"],
        "product_id": rec["product_id"],
        "color": _clean_text(rec["color"], _COLOR_MAX, "색상명"),
        "qty": _check_int(rec["qty"], _QTY_MIN, _QTY_MAX, "수량"),
        "date": _check_date(rec["date"]),
    }


def _clean_records(records: object, cleaner: Callable[[object], dict], label: str) -> dict[str, dict]:
    """초기 레코드 리스트를 레코드마다 검사해 ID → 새 레코드 딕셔너리로 만든다 (생성자 계약 1·2).

    인자:
        records: 레코드 딕셔너리의 리스트 또는 None(빈 리스트로 봄).
        cleaner: 레코드 하나를 검사하고 새 딕셔너리를 돌려주는 함수.
        label: 오류 메시지에 쓸 종류 이름.

    반환:
        ID → 새 레코드 딕셔너리. 입력 순서를 유지한다.

    예외:
        ValueError: 리스트도 None도 아닐 때, 레코드가 규칙을 어길 때, 같은 ID가 두 번 나올 때.
    """
    if records is None:
        return {}
    if not isinstance(records, list):
        raise ValueError(f"{label} 데이터는 리스트 또는 None이어야 합니다")
    result: dict[str, dict] = {}
    for record in records:
        cleaned = cleaner(record)
        if cleaned["id"] in result:
            raise ValueError(f"{label} ID가 중복됩니다: {cleaned['id']}")
        result[cleaned["id"]] = cleaned
    return result


def _check_purchase_refs(purchases: dict[str, dict], customers: dict[str, dict],
                         products: dict[str, dict]) -> None:
    """초기 구매 기록이 함께 받은 고객·상품을 참조하고, 색상이 그 상품의 색상 목록에 있는지 확인한다.

    인자:
        purchases: 검사를 마친 구매 ID → 구매 딕셔너리.
        customers: 검사를 마친 고객 ID → 고객 딕셔너리.
        products: 검사를 마친 상품 ID → 상품 딕셔너리.

    반환:
        없음.

    예외:
        ValueError: 없는 고객·상품을 참조하거나, 색상이 그 상품의 색상 목록에 없을 때.
    """
    for rec in purchases.values():
        cid, pid = rec["customer_id"], rec["product_id"]
        if not isinstance(cid, str) or cid not in customers:
            raise ValueError(f"{rec['id']}: 존재하지 않는 고객 ID입니다: {cid!r}")
        if not isinstance(pid, str) or pid not in products:
            raise ValueError(f"{rec['id']}: 존재하지 않는 상품 ID입니다: {pid!r}")
        if rec["color"] not in products[pid]["stock"]:
            raise ValueError(f"{rec['id']}: {pid}에 없는 색상입니다: {rec['color']}")


def _next_number(records: dict[str, dict]) -> int:
    """다음에 발급할 번호를 정한다: 가장 큰 번호 + 1, 레코드가 없으면 1 (생성자 계약 6).

    인자:
        records: 형식 검사를 마친 ID → 레코드 딕셔너리.

    반환:
        다음 번호.

    예외:
        없음.
    """
    return max((int(record_id[1:]) for record_id in records), default=0) + 1


def _group_id_for(gender: str, age: int) -> str:
    """성별·나이로 소속 그룹 ID를 정한다 (계획서 5.2 연령대 계산).

    인자:
        gender: "여" 또는 "남".
        age: 10~99 정수.

    반환:
        그룹 ID (예: 여·23 → "G-F-20").

    예외:
        ValueError: 성별이나 나이가 어느 그룹에도 맞지 않을 때 (검증을 거친 값에서는 생기지 않음).
    """
    if gender in GROUP_IDS_BY_GENDER:
        for group_id, band in zip(GROUP_IDS_BY_GENDER[gender], AGE_BANDS):
            if band[2] <= age <= band[3]:
                return group_id
    raise ValueError(f"맞는 그룹이 없습니다: {gender}, {age}")


def _aggregate_edges(purchases: Iterable[dict]) -> dict[tuple[str, str], dict]:
    """구매 기록을 (고객 ID, 상품 ID) 쌍별 간선 집계로 모은다 (계획서 5.2 간선 집계값).

    rebuild()가 전체 기록으로 부르고, W5에서 한 쌍의 기록만 넘겨 그 쌍을 다시 계산할 때도 쓴다.

    인자:
        purchases: 구매 딕셔너리들.

    반환:
        (고객 ID, 상품 ID) → {"colors": 색상 집합, "count", "total_qty", "last_date"} 새 딕셔너리.
        최근 구매일은 문자열 최댓값이다 (날짜가 모두 YYYY-MM-DD라 문자열 비교 = 날짜 비교).

    예외:
        없음.
    """
    edges: dict[tuple[str, str], dict] = {}
    for rec in purchases:
        key = (rec["customer_id"], rec["product_id"])
        agg = edges.setdefault(key, {"colors": set(), "count": 0, "total_qty": 0, "last_date": rec["date"]})
        agg["colors"].add(rec["color"])
        agg["count"] += 1
        agg["total_qty"] += rec["qty"]
        agg["last_date"] = max(agg["last_date"], rec["date"])
    return edges


def _lookup(table: dict[str, dict], record_id: object, label: str) -> dict:
    """ID로 내부 레코드를 찾는다. 없거나 형식이 틀린 ID는 "존재하지 않는 ID" 오류다 (부록 B.3 ID).

    돌려주는 값은 내부 객체이므로 부르는 쪽이 복사해서 내보낸다.

    인자:
        table: ID → 레코드 딕셔너리 (_customers·_products·_purchases·_groups).
        record_id: 찾을 ID.
        label: 오류 메시지에 쓸 종류 이름.

    반환:
        내부 레코드.

    예외:
        ValueError: 없는 ID (문자열이 아닌 값 포함).
    """
    if not isinstance(record_id, str) or record_id not in table:
        raise ValueError(f"존재하지 않는 {label} ID입니다: {record_id!r}")
    return table[record_id]


def _clean_query(name: object) -> str:
    """이름 조회어의 앞뒤 공백을 지운다 (부록 B.2 이름 조회).

    인자:
        name: 조회할 이름.

    반환:
        공백을 지운 조회어.

    예외:
        ValueError: 문자열이 아니거나 공백뿐일 때.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("찾을 이름을 입력하세요 (공백뿐인 이름은 안 됩니다)")
    return name.strip()


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
        """
        # 1~4 검증을 모두 끝낸 뒤에만 내부 상태를 만든다 (생성자 계약 5)
        clean_customers = _clean_records(customers, _clean_customer, "고객")
        clean_products = _clean_records(products, _clean_product, "상품")
        clean_purchases = _clean_records(purchases, _clean_purchase, "구매")
        _check_purchase_refs(clean_purchases, clean_customers, clean_products)

        self._customers: dict[str, dict] = clean_customers
        self._products: dict[str, dict] = clean_products
        self._purchases: dict[str, dict] = clean_purchases
        self._groups: dict[str, dict] = {
            group_id: {"id": group_id, "gender": gender, "band": band[1]}
            for gender, _ in GENDERS
            for group_id, band in zip(GROUP_IDS_BY_GENDER[gender], AGE_BANDS)
        }
        self._adj: dict[str, set[str]] = {}
        self._edges: dict[tuple[str, str], dict] = {}
        self.rebuild()
        self._next_ids: dict[str, int] = {
            "C": _next_number(clean_customers),
            "P": _next_number(clean_products),
            "T": _next_number(clean_purchases),
        }

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
        """
        return dict(_lookup(self._customers, customer_id, "고객"))

    def get_product(self, product_id: str) -> dict:
        """상품 정보를 복사본으로 돌려준다. stock 딕셔너리도 복사한다.

        인자:
            product_id: 조회할 상품 ID.

        반환:
            {"id", "name", "kind", "style", "price", "stock"} 딕셔너리의 복사본.

        예외:
            ValueError: 없는 상품 ID (형식이 틀린 ID 포함).
        """
        product = dict(_lookup(self._products, product_id, "상품"))
        product["stock"] = dict(product["stock"])
        return product

    def get_purchase(self, purchase_id: str) -> dict:
        """구매 기록을 복사본으로 돌려준다.

        인자:
            purchase_id: 조회할 구매 ID.

        반환:
            {"id", "customer_id", "product_id", "color", "qty", "date"} 딕셔너리의 복사본.

        예외:
            ValueError: 없는 구매 ID (형식이 틀린 ID 포함).
        """
        return dict(_lookup(self._purchases, purchase_id, "구매"))

    def customer_ids(self) -> list[str]:
        """모든 고객 ID를 돌려준다.

        인자:
            없음.

        반환:
            고객 ID 리스트, ID 오름차순. 고객이 없으면 빈 리스트.

        예외:
            없음.
        """
        return sorted(self._customers)

    def product_ids(self) -> list[str]:
        """모든 상품 ID를 돌려준다.

        인자:
            없음.

        반환:
            상품 ID 리스트, ID 오름차순. 상품이 없으면 빈 리스트.

        예외:
            없음.
        """
        return sorted(self._products)

    def find_customers_by_name(self, name: str) -> list[str]:
        """이름이 완전히 일치하는 고객을 찾는다. 앞뒤 공백을 지운 뒤 비교하고 부분 일치는 하지 않는다.

        인자:
            name: 찾을 이름.

        반환:
            고객 ID 리스트, ID 오름차순. 없으면 빈 리스트.

        예외:
            ValueError: 공백뿐인 이름 (문자열이 아닌 값 포함).
        """
        target = _clean_query(name)
        return sorted(cid for cid, rec in self._customers.items() if rec["name"] == target)

    def find_products_by_name(self, name: str) -> list[str]:
        """상품명이 완전히 일치하는 상품을 찾는다. 앞뒤 공백을 지운 뒤 비교하고 부분 일치는 하지 않는다.

        인자:
            name: 찾을 상품명.

        반환:
            상품 ID 리스트, ID 오름차순. 없으면 빈 리스트.

        예외:
            ValueError: 공백뿐인 이름 (문자열이 아닌 값 포함).
        """
        target = _clean_query(name)
        return sorted(pid for pid, rec in self._products.items() if rec["name"] == target)

    def neighbors(self, node_id: str) -> list[str]:
        """노드(그룹·고객·상품)의 이웃 ID를 돌려준다.

        인자:
            node_id: 그룹·고객·상품 ID.

        반환:
            이웃 ID 리스트, ID 오름차순.

        예외:
            ValueError: 없는 노드 ID.
        """
        if not isinstance(node_id, str) or node_id not in self._adj:
            raise ValueError(f"존재하지 않는 노드 ID입니다: {node_id!r}")
        return sorted(self._adj[node_id])

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
        """
        _lookup(self._customers, customer_id, "고객")
        _lookup(self._products, product_id, "상품")
        agg = self._edges.get((customer_id, product_id))
        if agg is None:
            return None
        return {"colors": sorted(agg["colors"]), "count": agg["count"],
                "total_qty": agg["total_qty"], "last_date": agg["last_date"]}

    def weight(self, customer_id: str, product_id: str) -> int:
        """고객–상품 간선의 가중치(그 고객이 그 상품을 산 서로 다른 색상 수)를 돌려준다.

        인자:
            customer_id: 고객 ID.
            product_id: 상품 ID.

        반환:
            가중치. 두 노드가 모두 있는데 간선이 없으면 0.

        예외:
            ValueError: 없는 고객 ID 또는 없는 상품 ID.
        """
        _lookup(self._customers, customer_id, "고객")
        _lookup(self._products, product_id, "상품")
        agg = self._edges.get((customer_id, product_id))
        return 0 if agg is None else len(agg["colors"])

    def group_of(self, customer_id: str) -> str:
        """고객이 소속된 그룹 ID를 돌려준다.

        성별·나이로 다시 계산하지 않고 그래프(인접 리스트)의 소속 간선을 읽는다. 정상 상태에서는
        소속 그룹이 정확히 하나다(무결성 검사 5.3.5가 확인). 그래프가 고장 나 소속 그룹이 둘 이상이면
        ID가 가장 작은 그룹을 돌려준다. 고장 판정은 check_integrity()가 맡는다.

        인자:
            customer_id: 고객 ID.

        반환:
            그룹 ID (예: "G-F-20").

        예외:
            ValueError: 없는 고객 ID, 또는 그래프가 고장 나 소속 그룹이 하나도 없을 때.
        """
        _lookup(self._customers, customer_id, "고객")
        group_ids = [node for node in self._adj[customer_id] if node in self._groups]
        if not group_ids:
            raise ValueError(f"{customer_id}의 소속 그룹이 없습니다 (무결성 검사가 필요합니다)")
        return min(group_ids)

    def members(self, group_id: str) -> list[str]:
        """그룹에 소속된 고객 ID를 돌려준다.

        인자:
            group_id: 그룹 ID. GROUP_IDS 중 하나.

        반환:
            고객 ID 리스트, ID 오름차순. 소속 고객이 없으면 빈 리스트.

        예외:
            ValueError: 없는 그룹 ID.
        """
        _lookup(self._groups, group_id, "그룹")
        return sorted(node for node in self._adj[group_id] if node in self._customers)

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

        ID 발급 카운터는 바꾸지 않는다 (삭제된 ID를 재사용하지 않기 위해). 그룹 노드는 8개 그대로이고,
        고객은 성별·나이로 정한 그룹 하나에, 구매 기록이 있는 (고객, 상품) 쌍은 서로 연결한다.

        인자:
            없음.

        반환:
            없음.

        예외:
            없음.
        """
        adj: dict[str, set[str]] = {node: set() for node in [*self._groups, *self._customers, *self._products]}
        for cid, rec in self._customers.items():
            group_id = _group_id_for(rec["gender"], rec["age"])
            adj[cid].add(group_id)
            adj[group_id].add(cid)
        edges = _aggregate_edges(self._purchases.values())
        for cid, pid in edges:
            adj[cid].add(pid)
            adj[pid].add(cid)
        self._adj = adj
        self._edges = edges

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
            소속 간선 수는 그래프에서 센다 (그룹 쪽 인접 리스트의 고객 수 합).

        예외:
            없음.
        """
        membership = sum(1 for group_id in self._groups for node in self._adj[group_id]
                         if node in self._customers)
        return {
            "groups": len(self._groups),
            "customers": len(self._customers),
            "products": len(self._products),
            "membership_edges": membership,
            "purchase_edges": len(self._edges),
            "purchases": len(self._purchases),
        }
