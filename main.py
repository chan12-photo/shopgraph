"""ShopGraph 프로그램의 유일한 진입점.

메뉴 흐름(계획서 5.4), 입력 문자열 변환(성별 1/2 → 남/여, 숫자 문자열 → 정수, "색상=수량" → 재고
딕셔너리), ValueError를 메시지로 보여 주고 메뉴로 돌아가는 일, 삭제 확인을 맡는다 (5.3.1·5.5).
데이터 변경은 ShopGraph 메서드로만 하고, 화면은 view.py 함수와 이 모듈의 짧은 안내 줄로만 출력한다.
입력이 끝나거나(EOF) Ctrl+C를 누르면 "종료합니다"를 출력하고 끝낸다.
"""

import re
import sys
import webbrowser
from collections.abc import Callable
from types import MappingProxyType
from typing import Final, TypeVar

from data import initial_records
from graph import GROUP_IDS, GROUP_LABELS, K_DEFAULT, K_MAX, KINDS, STYLES, ShopGraph
from search import customers_of, find_products, group_popular, members_of, products_of, recommend
from view import print_group_tree, print_neighbors, print_recommendation, print_table

_T = TypeVar("_T")

# 메인 메뉴 화면 (5.4 그대로)
_MENU = (
    "\n[1] CREATE      고객 / 상품 / 구매\n"
    "[2] READ        조회(ID·이름·조건) / 검색 S1~S4\n"
    "[3] UPDATE      고객 / 상품 / 구매\n"
    "[4] DELETE      고객 / 상품 / 구매\n"
    "[5] PRINT       그룹별 고객 / 상품 목록 / 인접 리스트 / 통계·무결성 검사\n"
    "[6] RECOMMEND   고객별 추천\n"
    "[0] Exit"
)
_MENU_ERROR = "[오류] 메뉴 번호를 다시 입력해 주세요"

# 성별 메뉴 번호 순서 → 저장 값 (5.4·부록 B.3 "메뉴에서는 1/2를 고르게 하고 main.py가 변환")
_GENDER_CHOICES: Final[tuple[str, ...]] = ("남", "여")

# 숫자 입력의 최대 자릿수. 범위 검사는 graph.py가 하고, 여기서는 변환 가능한 길이만 막는다
_MAX_DIGITS = 9

# 표 머리 (ID 조회·이름 조회·조건 조회·목록에서 같은 모양을 쓴다)
_CUSTOMER_HEADERS: Final[tuple[str, ...]] = ("ID", "이름", "성별", "나이", "그룹")
_PRODUCT_HEADERS: Final[tuple[str, ...]] = ("ID", "상품명", "종류", "스타일", "가격", "색상별 재고", "상태")
_PURCHASE_HEADERS: Final[tuple[str, ...]] = ("ID", "고객", "상품", "색상", "수량", "구매일")

# g.stats() 키 → 화면 이름 (B.2 stats 반환 키 순서)
_STAT_LABELS: Final[tuple[tuple[str, str], ...]] = (
    ("groups", "그룹 노드"), ("customers", "고객 노드"), ("products", "상품 노드"),
    ("membership_edges", "소속 간선"), ("purchase_edges", "구매 간선"), ("purchases", "구매 기록"),
)

# 선택 입력에서 Enter의 뜻
_KEEP = "Enter: 그대로"
_ANY = "Enter: 조건 없음"


def run() -> None:
    """data.py의 초기 데이터로 ShopGraph를 만들고 메뉴 루프를 실행한다.

    잘못된 입력으로 생긴 ValueError는 메시지로 보여 주고 메뉴로 돌아간다.
    입력이 끝나거나(EOF) Ctrl+C(KeyboardInterrupt)를 받으면 "종료합니다"를 출력하고 끝낸다.

    인자:
        없음.

    반환:
        없음.

    예외:
        ValueError: data.py의 초기 데이터가 생성자 검증(부록 B.1)을 통과하지 못할 때.
    """
    g = ShopGraph(*initial_records())
    try:
        _menu_loop(g)
    except (EOFError, KeyboardInterrupt):
        print()
        print("종료합니다")


def _run_web(port: int) -> None:
    """초기 데이터로 로컬 웹 서버를 시작하고 중단 시 소켓을 닫는다."""
    from web import create_server

    graph = ShopGraph(*initial_records())
    try:
        server = create_server(graph, port)
    except OSError as error:
        raise SystemExit(f"[오류] 웹 서버를 시작할 수 없습니다: {error} (다른 포트는 --port PORT)") from error
    address = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        print(f"웹 서버를 시작했습니다: {address}")
        webbrowser.open(address)
        server.serve_forever()
    except KeyboardInterrupt:
        print("웹 서버를 종료합니다")
    finally:
        server.server_close()


def _web_port(text: str) -> int:
    """--port 인자를 0~65535 정수로 변환한다."""
    port = _to_int(text, "포트")
    if port > 65535:
        raise ValueError(f"포트: 0~65535이어야 합니다 (입력: {port})")
    return port


def main(argv: list[str] | None = None) -> None:
    """인자 없이 콘솔을, ``--web``로 로컬 웹 화면을 시작한다."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        run()
        return
    if args[0] != "--web":
        raise SystemExit("사용법: python main.py [--web [--port PORT]]")
    if len(args) == 1:
        _run_web(8000)
        return
    if len(args) != 3 or args[1] != "--port":
        raise SystemExit("사용법: python main.py [--web [--port PORT]]")
    try:
        port = _web_port(args[2])
    except ValueError as error:
        raise SystemExit(f"[오류] {error}") from error
    _run_web(port)


def _menu_loop(g: ShopGraph) -> None:
    """메인 메뉴를 보여 주고 고른 기능을 실행하는 일을 [0]을 고를 때까지 되풀이한다.

    인자:
        g: 메뉴 기능이 다룰 ShopGraph.

    반환:
        없음.

    예외:
        EOFError: 입력이 끝났을 때 (run()이 받아 종료한다).
        KeyboardInterrupt: Ctrl+C를 눌렀을 때 (run()이 받아 종료한다).
    """
    while True:
        print(_MENU)
        choice = input("메뉴 선택: ").strip()
        if choice == "0":
            print("종료합니다")
            return
        action = _choose_action(choice)
        if action is None:
            continue
        try:
            action(g)
        except ValueError as error:
            print(f"[오류] {error}")


def _choose_action(choice: str) -> Callable[[ShopGraph], None] | None:
    """메인 메뉴 번호에 해당하는 하위 메뉴를 보여 주고 고른 기능 함수를 돌려준다.

    하위 기능이 하나뿐인 메뉴([6] RECOMMEND)는 하위 메뉴 없이 바로 그 기능을 돌려준다.

    인자:
        choice: 메인 메뉴에서 입력한 문자열 (앞뒤 공백을 지운 값).

    반환:
        실행할 기능 함수. 잘못된 번호이거나 [0] 이전 메뉴를 고르면 None.

    예외:
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    if choice not in _SUBMENUS:
        print(_MENU_ERROR)
        return None
    title, actions = _SUBMENUS[choice]
    if len(actions) == 1:
        return actions[0][1]
    print(f"\n[{title}]")
    for number, (label, _) in enumerate(actions, start=1):
        print(f"[{number}] {label}")
    print("[0] 이전 메뉴")
    sub = input("번호 선택: ").strip()
    if sub == "0":
        return None
    if sub not in {str(number) for number in range(1, len(actions) + 1)}:
        print(_MENU_ERROR)
        return None
    return actions[int(sub) - 1][1]


# ---------- 입력 변환 ----------

def _to_int(text: str, label: str) -> int:
    """숫자 문자열을 정수로 바꾼다. 범위 검사는 graph.py·search.py가 맡는다 (부록 B.3).

    인자:
        text: 사용자가 입력한 문자열.
        label: 오류 메시지에 쓸 항목 이름 (예: "나이").

    반환:
        변환한 정수.

    예외:
        ValueError: 앞뒤 공백을 지운 값이 0~9 숫자로만 이루어지지 않았거나 _MAX_DIGITS자리를 넘을 때.
    """
    digits = text.strip()
    if not re.fullmatch(r"[0-9]+", digits):
        raise ValueError(f"{label}: 숫자로 입력해 주세요")
    if len(digits) > _MAX_DIGITS:
        # int()의 자릿수 제한(4300자리) 오류는 영어 메시지라 그 전에 거른다
        raise ValueError(f"{label}: 숫자가 너무 깁니다 ({_MAX_DIGITS}자리 이하)")
    return int(digits)


def _to_choice(text: str, values: tuple[str, ...], label: str,
               names: tuple[str, ...] | None = None) -> str:
    """메뉴 번호 문자열(1부터)을 해당 값으로 바꾼다 (성별·종류·스타일·그룹 고르기).

    인자:
        text: 사용자가 입력한 문자열.
        values: 번호 순서대로의 값.
        label: 오류 메시지에 쓸 항목 이름 (예: "성별").
        names: 오류 메시지에 보일 이름. None이면 values를 그대로 보인다.

    반환:
        고른 값.

    예외:
        ValueError: 앞뒤 공백을 지운 값이 1~len(values) 번호가 아닐 때.
    """
    choice = text.strip()
    numbers = [str(number) for number in range(1, len(values) + 1)]
    if choice not in numbers:
        shown = [f"{number}({name})" for number, name in zip(numbers, names or values)]
        joined = f"{', '.join(shown[:-1])} 또는 {shown[-1]}"
        raise ValueError(f"{label}: {joined}로 입력해 주세요")
    return values[int(choice) - 1]


def _to_gender(text: str) -> str:
    """성별 메뉴 번호 문자열을 저장 값("남"·"여")으로 바꾼다.

    인자:
        text: 사용자가 입력한 문자열.

    반환:
        "남" 또는 "여".

    예외:
        ValueError: 앞뒤 공백을 지운 값이 "1"·"2"가 아닐 때.
    """
    return _to_choice(text, _GENDER_CHOICES, "성별")


def _to_stock(text: str) -> dict[str, int]:
    """"블랙=5, 화이트=3" 형식의 입력을 색상별 재고 딕셔너리로 바꾼다.

    색상명은 앞뒤 공백을 지워 키로 쓴다 (쉼표 뒤 공백 때문에 같은 색상이 다른 키가 되지 않게).
    딕셔너리로 바꾸면 겹친 색상이 조용히 하나로 합쳐지므로 여기서 거른다. 색상명 길이 검사는
    graph.py가 맡는다 (부록 B.3).

    인자:
        text: 사용자가 입력한 문자열.

    반환:
        색상 → 재고 새 딕셔너리.

    예외:
        ValueError: "색상=수량"이 쉼표로 이어진 형식이 아니거나, 수량이 숫자가 아니거나,
            앞뒤 공백을 지운 색상명이 두 번 나올 때.
    """
    stock: dict[str, int] = {}
    for part in text.split(","):
        raw_color, sep, qty = part.partition("=")
        color = raw_color.strip()
        if not sep or not color or "=" in qty:
            raise ValueError("색상별 재고: 색상=수량을 쉼표로 이어 입력해 주세요 (예: 블랙=5, 화이트=3)")
        if color in stock:
            raise ValueError(f"색상별 재고: 같은 색상이 두 번 나옵니다 (입력: {color})")
        stock[color] = _to_int(qty, f"재고({color})")
    return stock


def _optional(text: str, convert: Callable[[str], _T]) -> _T | None:
    """빈 입력(공백뿐 포함)이면 None, 아니면 convert로 바꾼 값을 돌려준다 (수정·조건 조회의 Enter).

    인자:
        text: 사용자가 입력한 문자열.
        convert: 빈 입력이 아닐 때 쓸 변환 함수.

    반환:
        None 또는 변환한 값.

    예외:
        ValueError: convert가 낸 것을 그대로 전달한다.
    """
    return None if not text.strip() else convert(text)


def _choice_prompt(label: str, names: tuple[str, ...], hint: str = "") -> str:
    """번호 고르기 입력의 안내 문구를 만든다 (예: "성별 (1 남 / 2 여): ").

    인자:
        label: 항목 이름.
        names: 번호 순서대로의 보일 이름.
        hint: 덧붙일 안내 (예: "Enter: 그대로"). 빈 문자열이면 붙이지 않는다.

    반환:
        input()에 넘길 안내 문자열.

    예외:
        없음.
    """
    options = " / ".join(f"{number} {name}" for number, name in enumerate(names, start=1))
    extra = f", {hint}" if hint else ""
    return f"{label} ({options}{extra}): "


def _ask_group() -> str:
    """그룹 번호를 입력받아 그룹 ID로 바꾼다 (S3·S4).

    인자:
        없음.

    반환:
        그룹 ID.

    예외:
        ValueError: 1~8 번호가 아닐 때.
    """
    names = tuple(GROUP_LABELS[group_id] for group_id in GROUP_IDS)
    return _to_choice(input(_choice_prompt("그룹", names)), GROUP_IDS, "그룹", names)


def _confirm_delete(target: str, count: int) -> bool:
    """삭제 확인을 묻는다 (5.3.1 "구매 기록 N건도 함께 삭제됩니다. 계속할까요?").

    인자:
        target: 삭제할 대상 표시 (예: "고객2(C02)").
        count: 함께 삭제될 구매 기록 수.

    반환:
        "y"(대소문자 무관)를 입력하면 True. 그 밖의 입력이면 취소 안내를 출력하고 False.

    예외:
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    detail = f"구매 기록 {count}건도 함께 삭제됩니다" if count else "함께 삭제되는 구매 기록은 없습니다"
    answer = input(f"{target} 삭제: {detail}. 계속할까요? (y/n): ").strip().lower()
    if answer == "y":
        return True
    print("[취소] 삭제하지 않았습니다")
    return False


# ---------- 표 행 만들기 ----------

def _customer_row(g: ShopGraph, customer_id: str) -> list[object]:
    """고객 한 명을 _CUSTOMER_HEADERS 순서의 표 행으로 만든다.

    인자:
        g: 조회할 ShopGraph.
        customer_id: 고객 ID.

    반환:
        [ID, 이름, 성별, 나이, 그룹 표시 이름].

    예외:
        ValueError: 없는 고객 ID일 때 g가 낸 것을 그대로 전달한다.
    """
    customer = g.get_customer(customer_id)
    return [customer_id, customer["name"], customer["gender"], customer["age"],
            GROUP_LABELS[g.group_of(customer_id)]]


def _product_row(g: ShopGraph, product_id: str) -> list[object]:
    """상품 하나를 _PRODUCT_HEADERS 순서의 표 행으로 만든다 (재고는 색상 이름순).

    인자:
        g: 조회할 ShopGraph.
        product_id: 상품 ID.

    반환:
        [ID, 상품명, 종류, 스타일, 가격, "색상 재고, …", "품절" 또는 "판매 중"].

    예외:
        ValueError: 없는 상품 ID일 때 g가 낸 것을 그대로 전달한다.
    """
    product = g.get_product(product_id)
    stock = ", ".join(f"{color} {qty}" for color, qty in sorted(product["stock"].items()))
    status = "품절" if g.is_sold_out(product_id) else "판매 중"
    return [product_id, product["name"], product["kind"], product["style"], product["price"], stock, status]


def _purchase_row(g: ShopGraph, purchase_id: str) -> list[object]:
    """구매 기록 하나를 _PURCHASE_HEADERS 순서의 표 행으로 만든다.

    인자:
        g: 조회할 ShopGraph.
        purchase_id: 구매 ID.

    반환:
        [ID, 고객 ID, 상품 ID, 색상, 수량, 구매일].

    예외:
        ValueError: 없는 구매 ID일 때 g가 낸 것을 그대로 전달한다.
    """
    record = g.get_purchase(purchase_id)
    return [purchase_id, record["customer_id"], record["product_id"], record["color"], record["qty"],
            record["date"]]


def _print_rows(title: str, unit: str, headers: tuple[str, ...], rows: list[list[object]]) -> None:
    """제목 줄과 표를 출력한다. 행이 없으면 "결과가 없습니다" 한 줄만 출력한다.

    인자:
        title: 제목 (예: "[상품 목록]").
        unit: 개수 단위 (예: "개", "명").
        headers: 표 머리.
        rows: 표 행.

    반환:
        없음.

    예외:
        없음.
    """
    if not rows:
        print(f"{title} 결과가 없습니다")
        return
    print(f"{title} {len(rows)}{unit}")
    print_table(list(headers), rows)


# ---------- [1] CREATE ----------

def _register_and_recommend(g: ShopGraph) -> None:
    """고객 정보를 입력받아 등록하고, 그 고객의 추천(K 기본값 K_DEFAULT)을 바로 출력한다 (5.3.1).

    인자:
        g: 고객을 등록할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 입력 변환 또는 등록 검증(부록 B.3)에 실패할 때. 이때 g는 바뀌지 않는다.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    name = input("이름: ")
    gender = _to_gender(input(_choice_prompt("성별", _GENDER_CHOICES)))
    age = _to_int(input("나이: "), "나이")
    customer_id = g.add_customer(name, gender, age)
    stored = g.get_customer(customer_id)["name"]
    print(f"[등록] {stored}({customer_id}) → {GROUP_LABELS[g.group_of(customer_id)]} 그룹에 연결")
    print_recommendation(g, customer_id, recommend(g, customer_id, K_DEFAULT), K_DEFAULT)


def _create_product(g: ShopGraph) -> None:
    """상품 정보를 입력받아 등록한다.

    인자:
        g: 상품을 등록할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 입력 변환 또는 등록 검증(부록 B.3)에 실패할 때. 이때 g는 바뀌지 않는다.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    name = input("상품명: ")
    kind = _to_choice(input(_choice_prompt("종류", KINDS)), KINDS, "종류")
    style = _to_choice(input(_choice_prompt("스타일", STYLES)), STYLES, "스타일")
    price = _to_int(input("가격: "), "가격")
    stock = _to_stock(input("색상별 재고 (예: 블랙=5, 화이트=3): "))
    product_id = g.add_product(name, kind, style, price, stock)
    print(f"[등록] {g.get_product(product_id)['name']}({product_id})")


def _create_purchase(g: ShopGraph) -> None:
    """구매 정보를 입력받아 등록하고, 등록 뒤 그 고객–상품 간선의 가중치를 보여 준다.

    인자:
        g: 구매를 등록할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 입력 변환 또는 등록 검증(부록 B.3)에 실패할 때. 이때 g는 바뀌지 않는다.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    customer_id = input("고객 ID: ").strip()
    product_id = input("상품 ID: ").strip()
    color = input("색상: ")
    qty = _to_int(input("수량: "), "수량")
    day = input("구매일 (YYYY-MM-DD): ").strip()
    purchase_id = g.add_purchase(customer_id, product_id, color, qty, day)
    row = _purchase_row(g, purchase_id)
    print(f"[등록] {purchase_id}: {row[1]} → {row[2]}, {row[3]}, {row[4]}개, {row[5]} "
          f"(가중치 {g.weight(customer_id, product_id)})")


# ---------- [2] READ ----------

def _read_by_id(g: ShopGraph) -> None:
    """종류(고객·상품·구매)와 ID를 입력받아 한 건을 표로 보여 준다.

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 잘못된 종류 번호이거나 없는 ID일 때.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    kinds = ("고객", "상품", "구매")
    kind = _to_choice(input(_choice_prompt("종류", kinds)), kinds, "종류")
    record_id = input("ID: ").strip()
    if kind == "고객":
        print_table(list(_CUSTOMER_HEADERS), [_customer_row(g, record_id)])
    elif kind == "상품":
        print_table(list(_PRODUCT_HEADERS), [_product_row(g, record_id)])
    else:
        print_table(list(_PURCHASE_HEADERS), [_purchase_row(g, record_id)])


def _read_by_name(g: ShopGraph) -> None:
    """종류(고객·상품)와 이름을 입력받아 완전 일치하는 것을 모두 ID 순으로 보여 준다 (5.3.1).

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 잘못된 종류 번호이거나 공백뿐인 이름일 때.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    kinds = ("고객", "상품")
    kind = _to_choice(input(_choice_prompt("종류", kinds)), kinds, "종류")
    name = input("이름: ")
    if kind == "고객":
        rows = [_customer_row(g, cid) for cid in g.find_customers_by_name(name)]
        _print_rows("[고객 이름 조회]", "명", _CUSTOMER_HEADERS, rows)
    else:
        rows = [_product_row(g, pid) for pid in g.find_products_by_name(name)]
        _print_rows("[상품 이름 조회]", "개", _PRODUCT_HEADERS, rows)


def _read_by_condition(g: ShopGraph) -> None:
    """종류·스타일·색상·가격 범위를 입력받아(빈 입력은 조건 없음) 맞는 상품을 보여 준다.

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 입력 변환 또는 조건 검증(부록 B.3 조건 조회)에 실패할 때.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    kind = _optional(input(_choice_prompt("종류", KINDS, _ANY)),
                     lambda text: _to_choice(text, KINDS, "종류"))
    style = _optional(input(_choice_prompt("스타일", STYLES, _ANY)),
                      lambda text: _to_choice(text, STYLES, "스타일"))
    color = _optional(input(f"색상 ({_ANY}): "), str)
    price_min = _optional(input(f"최저 가격 ({_ANY}): "), lambda text: _to_int(text, "최저 가격"))
    price_max = _optional(input(f"최고 가격 ({_ANY}): "), lambda text: _to_int(text, "최고 가격"))
    product_ids = find_products(g, kind, style, color, price_min, price_max)
    _print_rows("[조건 조회]", "개", _PRODUCT_HEADERS, [_product_row(g, pid) for pid in product_ids])


def _search_s1(g: ShopGraph) -> None:
    """S1: 고객 ID를 입력받아 그 고객이 산 상품과 간선 집계를 보여 준다.

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 없는 고객 ID일 때.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    customer_id = input("고객 ID: ").strip()
    items = products_of(g, customer_id)
    rows = [[item["product_id"], item["name"], ", ".join(item["colors"]), item["weight"], item["count"],
             item["total_qty"], item["last_date"]] for item in items]
    title = f"[S1 고객이 산 상품] {g.get_customer(customer_id)['name']}({customer_id})"
    _print_rows(title, "개", ("상품 ID", "상품명", "구매 색상", "가중치", "기록 수", "총수량", "최근 구매일"),
                rows)


def _search_s2(g: ShopGraph) -> None:
    """S2: 상품 ID를 입력받아 그 상품을 산 고객과 그룹·구매 색상을 보여 준다.

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 없는 상품 ID일 때.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    product_id = input("상품 ID: ").strip()
    items = customers_of(g, product_id)
    rows = [[item["customer_id"], item["name"], GROUP_LABELS[item["group_id"]], ", ".join(item["colors"])]
            for item in items]
    title = f"[S2 상품을 산 고객] {g.get_product(product_id)['name']}({product_id})"
    _print_rows(title, "명", ("고객 ID", "이름", "그룹", "구매 색상"), rows)


def _search_s3(g: ShopGraph) -> None:
    """S3: 그룹 번호를 입력받아 소속 고객을 보여 준다.

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 잘못된 그룹 번호일 때.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    group_id = _ask_group()
    rows = [_customer_row(g, cid) for cid in members_of(g, group_id)]
    _print_rows(f"[S3 그룹 소속 고객] {GROUP_LABELS[group_id]}({group_id})", "명", _CUSTOMER_HEADERS, rows)


def _search_s4(g: ShopGraph) -> None:
    """S4: 그룹 번호와 개수(빈 입력은 전체)를 입력받아 그룹 인기 상품을 보여 준다.

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 잘못된 그룹 번호이거나 k가 1~K_MAX 정수가 아닐 때.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    group_id = _ask_group()
    k = _optional(input(f"개수 (1~{K_MAX}, Enter: 전체): "), lambda text: _to_int(text, "개수"))
    items = group_popular(g, group_id, k)
    rows = [[rank, item["product_id"], g.get_product(item["product_id"])["name"], item["score"],
             item["buyers"], "품절" if item["sold_out"] else "판매 중"]
            for rank, item in enumerate(items, start=1)]
    _print_rows(f"[S4 그룹 인기 상품] {GROUP_LABELS[group_id]}({group_id})", "개",
                ("순위", "상품 ID", "상품명", "점수", "구매 고객 수", "상태"), rows)


# ---------- [3] UPDATE ----------

def _update_customer(g: ShopGraph) -> None:
    """고객 ID와 바꿀 값(빈 입력은 그대로)을 입력받아 수정하고, 수정 뒤 그룹을 보여 준다.

    인자:
        g: 수정할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 없는 ID, 입력 변환 실패, 수정 검증 실패, 바꿀 항목이 없을 때. 이때 g는 바뀌지 않는다.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    customer_id = input("고객 ID: ").strip()
    print_table(list(_CUSTOMER_HEADERS), [_customer_row(g, customer_id)])
    name = _optional(input(f"이름 ({_KEEP}): "), str)
    gender = _optional(input(_choice_prompt("성별", _GENDER_CHOICES, _KEEP)), _to_gender)
    age = _optional(input(f"나이 ({_KEEP}): "), lambda text: _to_int(text, "나이"))
    g.update_customer(customer_id, name=name, gender=gender, age=age)
    stored = g.get_customer(customer_id)["name"]
    print(f"[수정] {stored}({customer_id}) → {GROUP_LABELS[g.group_of(customer_id)]} 그룹")


def _update_product(g: ShopGraph) -> None:
    """상품 ID와 바꿀 값(빈 입력은 그대로)을 입력받아 수정한다. 재고는 통째로 교체한다 (B.3).

    인자:
        g: 수정할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 없는 ID, 입력 변환 실패, 수정 검증 실패(구매 기록이 있는 색상 삭제 포함),
            바꿀 항목이 없을 때. 이때 g는 바뀌지 않는다.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    product_id = input("상품 ID: ").strip()
    print_table(list(_PRODUCT_HEADERS), [_product_row(g, product_id)])
    name = _optional(input(f"상품명 ({_KEEP}): "), str)
    kind = _optional(input(_choice_prompt("종류", KINDS, _KEEP)), lambda text: _to_choice(text, KINDS, "종류"))
    style = _optional(input(_choice_prompt("스타일", STYLES, _KEEP)),
                      lambda text: _to_choice(text, STYLES, "스타일"))
    price = _optional(input(f"가격 ({_KEEP}): "), lambda text: _to_int(text, "가격"))
    stock = _optional(input(f"색상별 재고, 통째로 교체 (예: 블랙=5, 화이트=3, {_KEEP}): "), _to_stock)
    g.update_product(product_id, name=name, kind=kind, style=style, price=price, stock=stock)
    print_table(list(_PRODUCT_HEADERS), [_product_row(g, product_id)])
    print(f"[수정] {product_id}")


def _update_purchase(g: ShopGraph) -> None:
    """구매 ID와 바꿀 색상·수량(빈 입력은 그대로)을 입력받아 수정한다 (고객·상품·날짜는 못 바꿈).

    인자:
        g: 수정할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 없는 ID, 입력 변환 실패, 수정 검증 실패, 바꿀 항목이 없을 때. 이때 g는 바뀌지 않는다.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    purchase_id = input("구매 ID: ").strip()
    print_table(list(_PURCHASE_HEADERS), [_purchase_row(g, purchase_id)])
    color = _optional(input(f"색상 ({_KEEP}): "), str)
    qty = _optional(input(f"수량 ({_KEEP}): "), lambda text: _to_int(text, "수량"))
    g.update_purchase(purchase_id, color=color, qty=qty)
    row = _purchase_row(g, purchase_id)
    print(f"[수정] {purchase_id}: {row[3]}, {row[4]}개 (가중치 {g.weight(row[1], row[2])})")


# ---------- [4] DELETE ----------

def _delete_customer(g: ShopGraph) -> None:
    """고객 ID를 입력받아, 함께 삭제될 구매 기록 수를 알리고 확인을 받은 뒤 삭제한다 (5.3.1).

    인자:
        g: 삭제할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 없는 고객 ID일 때 (확인을 묻기 전에 낸다).
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    customer_id = input("고객 ID: ").strip()
    target = f"{g.get_customer(customer_id)['name']}({customer_id})"
    count = sum(item["count"] for item in products_of(g, customer_id))
    if _confirm_delete(target, count):
        deleted = g.delete_customer(customer_id)
        print(f"[삭제] {target}, 구매 기록 {deleted}건 함께 삭제")


def _delete_product(g: ShopGraph) -> None:
    """상품 ID를 입력받아, 함께 삭제될 구매 기록 수를 알리고 확인을 받은 뒤 삭제한다 (5.3.1).

    인자:
        g: 삭제할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 없는 상품 ID일 때 (확인을 묻기 전에 낸다).
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    product_id = input("상품 ID: ").strip()
    target = f"{g.get_product(product_id)['name']}({product_id})"
    count = sum(g.edge(item["customer_id"], product_id)["count"] for item in customers_of(g, product_id))
    if _confirm_delete(target, count):
        deleted = g.delete_product(product_id)
        print(f"[삭제] {target}, 구매 기록 {deleted}건 함께 삭제")


def _delete_purchase(g: ShopGraph) -> None:
    """구매 ID를 입력받아 그 기록을 삭제한다 (5.3.1은 고객·상품 삭제에만 확인을 둔다).

    인자:
        g: 삭제할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 없는 구매 ID일 때.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    purchase_id = input("구매 ID: ").strip()
    row = _purchase_row(g, purchase_id)
    g.delete_purchase(purchase_id)
    print(f"[삭제] {purchase_id}: {row[1]} → {row[2]}, {row[3]} (남은 가중치 {g.weight(row[1], row[2])})")


# ---------- [5] PRINT · [6] RECOMMEND ----------

def _print_products(g: ShopGraph) -> None:
    """전체 상품 목록을 표로 보여 준다 (ID 순).

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        없음.
    """
    _print_rows("[상품 목록]", "개", _PRODUCT_HEADERS, [_product_row(g, pid) for pid in g.product_ids()])


def _print_adjacency(g: ShopGraph) -> None:
    """노드 ID를 입력받아 그 노드의 인접 리스트를, 빈 입력이면 전체 노드(그룹 → 고객 → 상품)를 보여 준다.

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 없는 노드 ID일 때.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    node_id = input("노드 ID (Enter: 전체): ").strip()
    if node_id:
        print_neighbors(g, node_id)
        return
    for each_id in (*GROUP_IDS, *g.customer_ids(), *g.product_ids()):
        print_neighbors(g, each_id)


def _print_stats(g: ShopGraph) -> None:
    """그래프 통계 표와 무결성 검사 결과를 보여 준다 (5.3.5, 상태를 바꾸지 않음).

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        없음.
    """
    stats = g.stats()
    print("[그래프 통계]")
    print_table(["항목", "개수"], [[label, stats[key]] for key, label in _STAT_LABELS])
    violations = g.check_integrity()
    if not violations:
        print("[무결성 검사] 위반 없음: 원본과 그래프가 일치함을 확인")
        return
    print(f"[무결성 검사] 위반 {len(violations)}건")
    for violation in violations:
        print(f"  - {violation}")


def _recommend(g: ShopGraph) -> None:
    """고객 ID와 K(빈 입력은 K_DEFAULT)를 입력받아 추천을 출력한다.

    인자:
        g: 조회할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 없는 고객 ID이거나 K가 1~K_MAX 정수가 아닐 때.
        EOFError, KeyboardInterrupt: 입력 도중 (run()이 받는다).
    """
    customer_id = input("고객 ID: ").strip()
    k = _optional(input(f"추천 개수 K (1~{K_MAX}, Enter: {K_DEFAULT}): "), lambda text: _to_int(text, "추천 개수 K"))
    k = K_DEFAULT if k is None else k
    print_recommendation(g, customer_id, recommend(g, customer_id, k), k)


# 메인 메뉴 번호 → (하위 메뉴 제목, ((기능 이름, 기능 함수), …)). 위 함수들을 쓰므로 맨 뒤에 둔다
_SUBMENUS: Final[MappingProxyType[str, tuple[str, tuple[tuple[str, Callable[[ShopGraph], None]], ...]]]] = (
    MappingProxyType({
        "1": ("CREATE", (("고객 등록 (등록 직후 추천)", _register_and_recommend),
                         ("상품 등록", _create_product), ("구매 등록", _create_purchase))),
        "2": ("READ", (("ID 조회 (고객·상품·구매)", _read_by_id), ("이름 조회 (고객·상품)", _read_by_name),
                       ("조건 조회 (종류·스타일·색상·가격)", _read_by_condition),
                       ("S1 고객이 산 상품", _search_s1), ("S2 상품을 산 고객", _search_s2),
                       ("S3 그룹 소속 고객", _search_s3), ("S4 그룹 인기 상품", _search_s4))),
        "3": ("UPDATE", (("고객 수정", _update_customer), ("상품 수정", _update_product),
                         ("구매 수정", _update_purchase))),
        "4": ("DELETE", (("고객 삭제", _delete_customer), ("상품 삭제", _delete_product),
                         ("구매 삭제", _delete_purchase))),
        "5": ("PRINT", (("그룹별 고객", print_group_tree), ("상품 목록", _print_products),
                        ("인접 리스트", _print_adjacency), ("통계·무결성 검사", _print_stats))),
        "6": ("RECOMMEND", (("고객별 추천", _recommend),)),
    })
)


if __name__ == "__main__":
    main()
