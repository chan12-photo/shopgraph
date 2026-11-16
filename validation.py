"""ShopGraph 입력 검증 (X2에서 graph.py로부터 분리).

입력 값이 부록 B.1·B.3 규칙을 지키는지 확인하고, 저장할 값(앞뒤 공백을 지운 문자열,
새 딕셔너리)을 만들어 돌려준다. 그래프 상태는 읽지도 바꾸지도 않는다. 상태가 필요한 확인은
부르는 쪽(graph.py)이 필요한 레코드를 인자로 넘긴다.

의존 방향: graph.py가 이 모듈을 가져온다. 이 모듈은 graph.py를 가져오지 않는다 (순환 import 금지).
KINDS·STYLES·GENDERS·AGE_BANDS는 graph.py가 다시 내보내므로 다른 모듈은 지금처럼 graph에서 가져온다.
이름이 _로 시작하는 것은 이 모듈 안에서만 쓴다.

공통 입력 규칙 (부록 B.3):
    정수 인자(나이·가격·재고·수량)는 int만 인정한다. bool(True/False)과
    숫자 문자열("3")은 거부한다.
    이름·상품명·색상명(구매 색상 포함)은 앞뒤 공백을 지운 값으로 검증하고, 저장할 때도
    지운 값으로 저장한다.
"""

import datetime
import re
from collections.abc import Callable
from types import MappingProxyType
from typing import Final

# 상품 종류 (부록 B.3)
KINDS: Final[tuple[str, ...]] = ("상의", "하의", "아우터")

# 상품 스타일 (부록 B.3)
STYLES: Final[tuple[str, ...]] = ("캐주얼", "미니멀", "스트릿", "포멀")

# 성별: (입력·저장 값, 그룹 ID에 쓰는 코드). 이 순서가 그룹 ID 오름차순이 된다 (계획서 5.2)
GENDERS: Final[tuple[tuple[str, str], ...]] = (("여", "F"), ("남", "M"))

# 연령대: (그룹 ID에 쓰는 코드, 표시 이름, 최소 나이, 최대 나이) (계획서 5.2, 부록 B.3 나이 10~99)
AGE_BANDS: Final[tuple[tuple[str, str, int, int], ...]] = (
    ("10", "10대", 10, 19),
    ("20", "20대", 20, 29),
    ("30", "30대", 30, 39),
    ("40+", "40대 이상", 40, 99),
)

# 구매일 형식: 정확히 YYYY-MM-DD 10자 (부록 B.3). \d는 다른 문자 체계의 숫자도 받으므로 [0-9]만 쓴다
_DATE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

# 레코드 ID 형식 (X1·v3 5.2): 최소 자릿수보다 앞의 0은 허용하지 않는다.
ID_PATTERNS: Final[MappingProxyType[str, re.Pattern[str]]] = MappingProxyType({
    "C": re.compile(r"C(0[1-9]|[1-9][0-9]+)"),
    "P": re.compile(r"P(0[1-9]|[1-9][0-9]+)"),
    "T": re.compile(r"T(00[1-9]|0[1-9][0-9]|[1-9][0-9]{2,})"),
})

# 초기 레코드의 키 (부록 B.1 내부 딕셔너리 모양)
_CUSTOMER_KEYS: Final[frozenset[str]] = frozenset({"id", "name", "gender", "age"})
_PRODUCT_KEYS: Final[frozenset[str]] = frozenset({"id", "name", "kind", "style", "price", "stock"})
_PURCHASE_KEYS: Final[frozenset[str]] = frozenset({"id", "customer_id", "product_id", "color", "qty", "date"})

# 이름·상품명 최대 길이, 색상명 최대 길이, 구매 수량 범위 (부록 B.3)
NAME_MAX: Final[int] = 20
COLOR_MAX: Final[int] = 10
QTY_MIN: Final[int] = 1
QTY_MAX: Final[int] = 99

# 성별 입력값 ("여", "남")
GENDER_VALUES: Final[tuple[str, ...]] = tuple(gender for gender, _ in GENDERS)


def value_error(label: str | None, rule: str, value: object) -> ValueError:
    """검증 오류를 "항목: 규칙 (입력: 값)" 형식의 ValueError로 만든다 (A04, W10a).

    항목이 None이면 "규칙 (입력: 값)"이다 ("존재하지 않는 … ID입니다"처럼 문장에 항목이 들어 있을 때).
    search.py에는 같은 형식의 내부 함수가 따로 있다 (W10a 구조 그대로, X2에서 합치지 않았다).

    인자:
        label: 항목 이름 (예: "나이"). None이면 앞에 붙이지 않는다.
        rule: 어긴 규칙 문장.
        value: 화면에 보일 입력 값 (repr로 보일지는 부르는 쪽이 정한다).

    반환:
        만든 ValueError (raise는 부르는 쪽이 한다).

    예외:
        없음.
    """
    return ValueError(f"{rule} (입력: {value})" if label is None else f"{label}: {rule} (입력: {value})")


def check_date(value: object) -> str:
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
        raise value_error("구매일", "YYYY-MM-DD 형식이어야 합니다", repr(value))
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise value_error("구매일", "존재하지 않는 날짜입니다", value) from None
    return value


def check_int(value: object, low: int, high: int | None, label: str) -> int:
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
        raise value_error(label, "정수여야 합니다", repr(value))
    if value < low or (high is not None and value > high):
        limit = f"{low} 이상" if high is None else f"{low}~{high}"
        raise value_error(label, f"{limit}이어야 합니다", value)
    return value


def clean_text(value: object, max_len: int, label: str) -> str:
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
        raise value_error(label, "문자열이어야 합니다", repr(value))
    text = value.strip()
    if not 1 <= len(text) <= max_len:
        raise value_error(label, f"앞뒤 공백을 지운 뒤 1~{max_len}자여야 합니다", repr(value))
    return text


def check_choice(value: object, choices: tuple[str, ...], label: str) -> str:
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
        raise value_error(label, f"{'/'.join(choices)} 중 하나여야 합니다", repr(value))
    return value


def clean_stock(stock: object) -> dict[str, int]:
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
        name = clean_text(color, COLOR_MAX, "색상명")
        if name in cleaned:
            raise value_error("색상명", "겹칩니다", name)
        cleaned[name] = check_int(count, 0, None, "재고")
    return cleaned


def _check_record_id(value: object, prefix: str) -> str:
    """초기 레코드의 최소 자릿수·가변 ID 형식을 확인한다 (X1·v3 5.2).

    인자:
        value: 검사할 ID.
        prefix: 종류 글자 "C" | "P" | "T".

    반환:
        검사를 통과한 ID.

    예외:
        ValueError: 문자열이 아니거나 형식이 다르거나 번호가 0일 때.
    """
    if (not isinstance(value, str) or ID_PATTERNS[prefix].fullmatch(value) is None
            or int(value[1:]) == 0):
        raise value_error("ID", "형식이 올바르지 않습니다", repr(value))
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
        raise value_error(f"{label} 레코드", "모양이 올바르지 않습니다", repr(record))
    return record


def clean_customer(record: object) -> dict:
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
        "name": clean_text(rec["name"], NAME_MAX, "이름"),
        "gender": check_choice(rec["gender"], GENDER_VALUES, "성별"),
        "age": check_int(rec["age"], AGE_BANDS[0][2], AGE_BANDS[-1][3], "나이"),
    }


def clean_product(record: object) -> dict:
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
        "name": clean_text(rec["name"], NAME_MAX, "상품명"),
        "kind": check_choice(rec["kind"], KINDS, "종류"),
        "style": check_choice(rec["style"], STYLES, "스타일"),
        "price": check_int(rec["price"], 0, None, "가격"),
        "stock": clean_stock(rec["stock"]),
    }


def clean_purchase(record: object) -> dict:
    """초기 구매 레코드를 검사하고 색상 공백을 지운 새 딕셔너리로 만든다.

    고객·상품 참조와 색상 목록 확인은 고객·상품을 모두 읽은 뒤 check_purchase_refs가 한다.

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
        "color": clean_text(rec["color"], COLOR_MAX, "색상명"),
        "qty": check_int(rec["qty"], QTY_MIN, QTY_MAX, "수량"),
        "date": check_date(rec["date"]),
    }


def clean_purchase_color(color: object, product: dict) -> str:
    """구매 등록·수정의 색상을 공백을 지운 값으로 만들고, 그 상품의 색상 목록에 있는지 확인한다 (부록 B.3).

    재고와는 연동하지 않으므로 재고 0인 색상도 허용한다.

    인자:
        color: 구매 색상.
        product: 구매 대상 상품의 내부 레코드 (stock 키를 색상 목록으로 쓴다).

    반환:
        공백을 지운 색상명 (저장할 값).

    예외:
        ValueError: 색상명이 1~10자가 아니거나 그 상품의 색상 목록에 없을 때.
    """
    name = clean_text(color, COLOR_MAX, "색상명")
    if name not in product["stock"]:
        raise value_error("색상", f"{product['id']}에 없는 색상입니다", name)
    return name


def clean_records(records: object, cleaner: Callable[[object], dict], label: str) -> dict[str, dict]:
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
            raise value_error(f"{label} ID", "중복됩니다", cleaned['id'])
        result[cleaned["id"]] = cleaned
    return result


def check_purchase_refs(purchases: dict[str, dict], customers: dict[str, dict],
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
            raise value_error(rec['id'], "존재하지 않는 고객 ID입니다", repr(cid))
        if not isinstance(pid, str) or pid not in products:
            raise value_error(rec['id'], "존재하지 않는 상품 ID입니다", repr(pid))
        if rec["color"] not in products[pid]["stock"]:
            raise value_error(rec['id'], f"{pid}에 없는 색상입니다", rec['color'])


def clean_query(name: object) -> str:
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
