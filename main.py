"""ShopGraph 프로그램의 유일한 진입점.

메뉴 흐름, 입력 문자열 변환(성별 1/2 → 남/여 등), ValueError를 메시지로 보여 주고
메뉴로 돌아가는 일을 맡는다 (계획서 5.4·5.5).
"""


def run() -> None:
    """data.py의 초기 데이터로 ShopGraph를 만들고 메뉴 루프를 실행한다.

    인자:
        없음.

    반환:
        없음.

    예외:
        NotImplementedError: W8b(최소 흐름)·W10(전체 메뉴)에서 구현하기 전.
    """
    raise NotImplementedError("W8b에서 최소판, W10에서 전체 메뉴 구현 예정")


if __name__ == "__main__":
    run()
