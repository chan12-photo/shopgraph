"""ShopGraph 프로그램의 유일한 진입점.

메뉴 흐름, 입력 문자열 변환(성별 1/2 → 남/여 등), ValueError를 메시지로 보여 주고
메뉴로 돌아가는 일을 맡는다 (계획서 5.4·5.5).

W8b 최소판: 고객 등록 → 추천 → 출력 흐름만 있다. 전체 메뉴 [1]~[6]은 W10에서 만든다.
"""

import re

from data import initial_records
from graph import GROUP_LABELS, K_DEFAULT, ShopGraph
from search import recommend
from view import print_recommendation

# 메뉴 화면 (W8b 최소판, 5.4 형식을 따르되 고객 등록·추천만)
_MENU = (
    "\n[1] CREATE      고객 등록 → 추천\n"
    "[0] Exit"
)

# 성별 메뉴 번호 → 저장 값 (5.4·부록 B.3 "메뉴에서는 1/2를 고르게 하고 main.py가 변환")
_GENDER_CHOICES = {"1": "남", "2": "여"}

# 숫자 입력의 최대 자릿수. 범위 검사는 graph.py가 하고, 여기서는 변환 가능한 길이만 막는다
_MAX_DIGITS = 9


def run() -> None:
    """data.py의 초기 데이터로 ShopGraph를 만들고 메뉴 루프를 실행한다.

    잘못된 입력으로 생긴 ValueError는 메시지로 보여 주고 메뉴로 돌아간다.
    입력이 끝나면(EOF) 종료한다.

    인자:
        없음.

    반환:
        없음.

    예외:
        ValueError: data.py의 초기 데이터가 생성자 검증(부록 B.1)을 통과하지 못할 때.
    """
    g = ShopGraph(*initial_records())
    while True:
        print(_MENU)
        try:
            choice = input("메뉴 선택: ").strip()
        except EOFError:
            print()
            return
        if choice == "0":
            print("종료합니다")
            return
        if choice != "1":
            print("[오류] 메뉴 번호를 다시 입력해 주세요")
            continue
        try:
            _register_and_recommend(g)
        except ValueError as error:
            print(f"[오류] {error}")
        except EOFError:
            print()
            return


def _register_and_recommend(g: ShopGraph) -> None:
    """고객 정보를 입력받아 등록하고, 그 고객의 추천(K 기본값 K_DEFAULT)을 출력한다.

    인자:
        g: 고객을 등록할 ShopGraph.

    반환:
        없음.

    예외:
        ValueError: 입력 변환 또는 등록 검증(부록 B.3)에 실패할 때. 이때 g는 바뀌지 않는다.
        EOFError: 입력 도중 입력이 끝났을 때.
    """
    name = input("이름: ")
    gender = _to_gender(input("성별 (1 남 / 2 여): "))
    age = _to_int(input("나이: "), "나이")
    customer_id = g.add_customer(name, gender, age)
    print(f"등록 완료: {customer_id} → {GROUP_LABELS[g.group_of(customer_id)]} 그룹에 연결")
    print_recommendation(g, customer_id, recommend(g, customer_id, K_DEFAULT), K_DEFAULT)


def _to_gender(text: str) -> str:
    """성별 메뉴 번호 문자열을 저장 값("남"·"여")으로 바꾼다.

    인자:
        text: 사용자가 입력한 문자열.

    반환:
        "남" 또는 "여".

    예외:
        ValueError: 앞뒤 공백을 지운 값이 "1"·"2"가 아닐 때.
    """
    choice = text.strip()
    if choice not in _GENDER_CHOICES:
        raise ValueError("성별: 1(남) 또는 2(여)로 입력해 주세요")
    return _GENDER_CHOICES[choice]


def _to_int(text: str, label: str) -> int:
    """숫자 문자열을 정수로 바꾼다. 범위 검사는 graph.py가 맡는다 (부록 B.3).

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


if __name__ == "__main__":
    run()
