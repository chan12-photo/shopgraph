"""시연 테스트: 계획서 7장 장면 1~8 (11.3.2 W12).

실행용 data.py(시연 데이터)로 main.run()을 실행하고, docs/verification/w11_scenes.md의 입력 절차대로
장면 1~N을 차례로 넣은 뒤 장면 N의 결과를 확인한다. 기대값은 docs/demo_expected.md에서만 읽는다
(사람이 손계산·승인한 값). 이 파일에는 기대값을 적지 않고, 실행 결과를 저장하지도 않는다.
demo_expected.md에서 필요한 칸이 비어 있으면(양식 상태) 각 테스트는
NotImplementedError("W11 기대값 승인 전")로 멈춘다 (11.3.3 미도래 분류).

화면 문구 확인에 쓰는 글자(안내 줄의 앞부분, "[등록]" 줄 모양)는 W8b·W10 승인 형식이다.

보호 순서: 각 테스트는 main.run()을 실행하기 전에 그 장면과 앞 장면들의 기대값 칸과 확정값을 모두 먼저 읽어
검사한다(_require_through). 작성 도중이라 칸이 하나라도 비어 있으면 시연을 실행하지 않고 멈춘다. 칸이 다 채워져도
demo_expected.md 상태 줄이 "상태: 승인 (찬일, YYYY-MM-DD) / AI 독립 계산 대조: 일치"가 아니면 멈춘다.
비교: 내부 함수(recommend·products_of·group_popular·stats 등) 결과와 함께, 장면 화면에서 출력 구간(추천 블록,
S1 표, S4 표 구매 전·후, 그룹 트리, 통계 표와 무결성 줄)을 잘라 기대 화면과 통째로 assertEqual 한다 (Codex 2차 검토).
기대 화면은 승인된 출력 함수(view.print_recommendation·print_table·print_group_tree)에 기대값으로 만든 입력을 넣어
만든다. 그래서 출력 형식 자체가 맞는지는 test_view·test_flow가 지키고, 이 파일은 값·순서·개수·빠진 줄·덧붙은 줄을
지킨다. 추천 근거 줄의 색상 수 안내는 print_recommendation이 g.weight()로 정하므로, 기대 화면을 만들 때는
weight()만 기대값 "색상 수 안내" 열에서 읽는 대리 그래프(_ExpectedColorCounts)를 넘긴다. 그룹 트리의 고객 줄(이름·나이)은
기대값이 아니라서 실제 그래프로 만든 트리와 통째로 비교하고, 그룹별 인원은 기대값과 따로 대조한다.
등록 줄("[등록] …")은 발급되는 구매 ID(T번호)만 빼고 줄 전체를 기대값으로 맞춘다.
"""

import contextlib
import datetime
import io
import pathlib
import re
import unittest
from unittest import mock

import main
from data import initial_records
from graph import GROUP_IDS, ShopGraph
from graph import GROUP_LABELS
from search import group_popular, products_of, recommend
from view import print_group_tree, print_recommendation, print_table

_EXPECTED_PATH = pathlib.Path(__file__).resolve().parent.parent / "docs" / "demo_expected.md"
_NOT_READY = "W11 기대값 승인 전"
_NOT_APPROVED = "11.3.8 승인 전"

# demo_expected.md 맨 위 상태 줄이 정확히 이 모양일 때만 장면을 실행한다 (찬일 11/02 판정)
_APPROVED_STATUS = re.compile(r"상태: 승인 \(찬일, [0-9]{4}-[0-9]{2}-[0-9]{2}\) / AI 독립 계산 대조: 일치")

# 장면 사이 구분: 없는 메뉴 번호를 한 번 넣으면 이 줄이 찍힌다 (W10 승인 형식)
_MARKER_INPUT = "9"
_MARKER_LINE = "[오류] 메뉴 번호를 다시 입력해 주세요"

# demo_expected.md 범위 칸(화면 표시) → recommend() 반환의 scope
_SCOPES = {"같은 그룹": "group", "여성 전체": "gender", "남성 전체": "gender", "전체 고객": "all"}

# 안내 줄 이름 → 화면에서 그 줄을 알아보는 글자 (W8b 승인 형식)
_NOTES = (("넓힘 안내", " ※ 같은 그룹("), ("개수 부족 안내", "개를 채우지 못함"),
          ("점수 비교 안내", " ※ 점수는 각 범위 안에서"))

# 통계 표 항목 이름 → g.stats() 키 (W10 승인 형식)
_STAT_KEYS = {"그룹 노드": "groups", "고객 노드": "customers", "상품 노드": "products",
              "소속 간선": "membership_edges", "구매 간선": "purchase_edges", "구매 기록": "purchases"}

# 장면마다 입력이나 확인에 쓰는 확정값 이름 (docs/demo_expected.md 확정값 표, w11_scenes.md)
_FIXED_BY_SCENE = {2: ("C_new",), 3: ("C_new", "P_top", "장면 3 색상 1", "장면 3 색상 2"), 4: ("C_new",),
                   6: ("C_new", "P_top6"), 7: ("C_new7",)}
_FIXED_KEYS = tuple(dict.fromkeys(key for keys in _FIXED_BY_SCENE.values() for key in keys))  # 확정값 표의 필수 행
_NOTE_NAMES = tuple(name for name, _ in _NOTES)

# 행 규칙: 필수 행 이름 튜플(첫 열 값이 정확히 이 집합, 중복 없음), _RANKED(순위 1부터 연속, 뒤쪽 행은 "-"로
# 해당 없음 가능), _LISTED(행 1개 이상, "-" 없음, 첫 열 중복 없음)
_RANKED = "순위 표"
_LISTED = "목록 표"
_REC_COLUMNS = ("순위", "상품 ID", "범위", "점수", "구매자 수", "지지자", "구매 가능 색상", "색상 수 안내")
_S4_COLUMNS = ("순위", "상품 ID", "점수", "구매 고객 수", "상태")
_S1_COLUMNS = ("상품 ID", "구매 색상", "가중치", "기록 수", "총수량", "최근 구매일")
_RECOMMEND_K = 3
_REC_TABLE = {"추천 (C_new, K=3)": (_REC_COLUMNS, _RANKED), "안내 줄": (("안내", "있음/없음"), _NOTE_NAMES)}

# demo_expected.md의 장(## ) → 표(### ) → (정확한 열 목록, 행 규칙). 여기 없는 장(쓰는 법, 검산·승인 기록)은 보지 않는다
_SCHEMA = {
    "확정값": {"확정값": (("이름", "값", "정하는 근거"), _FIXED_KEYS)},
    "장면 1": {"그룹별 인원": (("그룹 ID", "인원", "메모"), GROUP_IDS)},
    "장면 2": {"연결 그룹": (("항목", "값"), ("C_new 연결 그룹 ID",)), **_REC_TABLE},
    "장면 3": {"구매 등록 줄 가중치": (("구매", "가중치"), ("첫 번째 (장면 3 색상 1)", "두 번째 (장면 3 색상 2)")),
               "S1 (C_new)": (_S1_COLUMNS, _LISTED)},
    "장면 4": dict(_REC_TABLE),
    "장면 5": {"S4 구매 전 (G-F-20, 전체)": (_S4_COLUMNS, _RANKED),
               "구매 등록 줄 가중치 (C09–P07)": (("구매", "가중치"), ("첫 번째 (블랙)", "두 번째 (그레이)", "세 번째 (네이비)")),
               "S4 구매 후 (G-F-20, 전체)": (_S4_COLUMNS, _RANKED)},
    "장면 6": dict(_REC_TABLE),
    "장면 7": {"연결 그룹": (("항목", "값"), ("C_new7 연결 그룹 ID",)),
               "추천 (C_new7, K=3)": (_REC_COLUMNS, _RANKED), "안내 줄": (("안내", "있음/없음"), _NOTE_NAMES)},
    "장면 8": {"통계 표": (("항목", "개수"), tuple(_STAT_KEYS)), "무결성 검사": (("항목", "값"), ("위반 수",))},
}

# 칸 값 형식 (docs/demo_expected.md "쓰는 법"). 두 칸 표의 "값" 칸은 행 이름에 따라 _VALUE_FORMATS
_CUSTOMER_ID = r"C[0-9]{2}"
_PRODUCT_ID = r"P[0-9]{2}"
_POSITIVE = r"[1-9][0-9]*"
_NON_NEGATIVE = r"0|[1-9][0-9]*"
_COLOR_NOTE = r"C[0-9]{2}[은는] [2-9][0-9]*가지(, C[0-9]{2}[은는] [2-9][0-9]*가지)*"
_COLUMN_FORMATS = {
    "순위": _POSITIVE, "상품 ID": _PRODUCT_ID, "점수": _POSITIVE, "구매자 수": _POSITIVE,
    "지지자": f"{_CUSTOMER_ID}(, {_CUSTOMER_ID})*", "구매 가능 색상": r"[^,\s][^,]*(, [^,\s][^,]*)*",
    "색상 수 안내": f"-|{_COLOR_NOTE}", "구매 고객 수": _POSITIVE, "가중치": _POSITIVE, "기록 수": _POSITIVE,
    "총수량": _POSITIVE, "구매 색상": r"[^,\s][^,]*(, [^,\s][^,]*)*", "인원": _NON_NEGATIVE, "개수": _NON_NEGATIVE,
}
_COLUMN_CHOICES = {"범위": frozenset(_SCOPES), "상태": frozenset({"판매 중", "품절"}), "있음/없음": frozenset({"있음", "없음"})}
_VALUE_FORMATS = {"C_new": _CUSTOMER_ID, "C_new7": _CUSTOMER_ID, "P_top": _PRODUCT_ID, "P_top6": _PRODUCT_ID,
                  "장면 3 색상 1": r"[^,\s-][^,]*", "장면 3 색상 2": r"[^,\s-][^,]*", "위반 수": _NON_NEGATIVE}

# 화면 구간 첫 줄 글자와 표 머리 (W8b·W9·W10 승인 형식, main.py _search_s1·_search_s4·_print_stats와 같음)
_S1_SCREEN_HEADERS = ["상품 ID", "상품명", "구매 색상", "가중치", "기록 수", "총수량", "최근 구매일"]
_S4_SCREEN_HEADERS = ["순위", "상품 ID", "상품명", "점수", "구매 고객 수", "상태"]
_INTEGRITY_OK = "[무결성 검사] 위반 없음: 원본과 그래프가 일치함을 확인"

# 장면 3·5에서 넣는 구매 (w11_scenes.md): 장면 3은 (확정값 색상 이름, 날짜), 장면 5는 (색상, 날짜). 수량은 모두 1
_SCENE3_BUYS = (("장면 3 색상 1", "2026-10-30"), ("장면 3 색상 2", "2026-10-31"))
_SCENE5_BUYS = (("블랙", "2026-10-30"), ("그레이", "2026-10-30"), ("네이비", "2026-10-31"))


def _load_expected() -> dict[str, dict[str, list[dict[str, str]]]]:
    """demo_expected.md를 장(## 제목의 마침표 앞) → 표(### 제목) → 행(머리 → 칸 딕셔너리)으로 읽는다.

    모든 칸이 "-"인 행은 구분 줄과 같이 버린다. 칸 값은 앞뒤 공백을 지운 문자열(빈칸은 "").

    인자:
        없음.

    반환:
        {"장면 2": {"추천 (C_new, K=3)": [{"순위": "1", "상품 ID": "", …}, …], …}, …}.

    예외:
        OSError: 파일을 읽지 못할 때.
        NotImplementedError: 같은 이름의 장이나 같은 장 안에 같은 이름의 표가 두 번 나올 때, 머리에 같은 열 이름이
            두 번 나올 때, 칸 수가 머리 칸 수와 다른 행이 있을 때 (작성 중이거나 깨진 양식).
    """
    sections: dict[str, dict[str, list[dict[str, str]]]] = {}
    section, table, header = "", "", []
    for line in _EXPECTED_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section, table = line[3:].split(".")[0].strip(), ""
            if section in sections:
                raise NotImplementedError(f"{_NOT_READY}: 같은 이름의 장이 두 번 나옴: {section}")
            sections[section] = {}
        elif line.startswith("### ") and section:
            table, header = line[4:].strip(), []
            if table in sections[section]:
                raise NotImplementedError(f"{_NOT_READY}: {section}에 같은 이름의 표가 두 번 나옴: {table}")
            sections[section][table] = []
        elif line.startswith("|") and table:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if header and all(cell and set(cell) <= {"-"} for cell in cells):
                continue  # 머리 아래 구분 줄, 또는 모든 칸이 "-"인 행 (어느 쪽이든 쓰지 않음)
            if not header:
                if len(set(cells)) != len(cells):
                    raise NotImplementedError(f"{_NOT_READY}: {section} / {table} 머리에 같은 열 이름이 두 번 나옴")
                header = cells
            elif len(cells) != len(header):
                raise NotImplementedError(f"{_NOT_READY}: {section} / {table} 칸 수가 머리({len(header)}칸)와 다름")
            else:
                sections[section][table].append(dict(zip(header, cells)))
    return sections


def _rows(expected: dict, section: str, table: str) -> list[dict[str, str]]:
    """표의 행 중 해당 없음(첫 칸 말고 모두 "-")이 아닌 행을 파일 순서대로 돌려준다. 빈칸이 있으면 멈춘다.

    인자:
        expected: _load_expected()의 결과.
        section: 장 이름 (예: "장면 2").
        table: 표 제목 (### 뒤 글자 그대로).

    반환:
        채워진 행 리스트.

    예외:
        NotImplementedError: 표가 없거나, 행에 빈칸이 있을 때 (기대값 승인 전).
    """
    rows = expected.get(section, {}).get(table)
    if rows is None:
        raise NotImplementedError(f"{_NOT_READY}: {section} / {table} 표 없음")
    filled = []
    for row in rows:
        values = list(row.values())[1:]
        if values and all(value == "-" for value in values):
            continue
        if any(value == "" for value in row.values()):
            raise NotImplementedError(f"{_NOT_READY}: {section} / {table} 빈칸")
        filled.append(row)
    return filled


def _value(expected: dict, section: str, table: str, key: str) -> str:
    """두 칸 표(확정값·연결 그룹·안내 줄·무결성 검사)에서 key 행의 값을 열 제목으로 읽어 돌려준다.

    이름 열과 값 열은 _SCHEMA의 열 목록 첫째·둘째 열 제목이다 (칸 위치로 읽지 않는다).

    인자:
        expected: _load_expected()의 결과.
        section: 장 이름.
        table: 표 제목.
        key: 이름 열의 글자.

    반환:
        값 열의 글자.

    예외:
        NotImplementedError: 표·행·열이 없거나, 같은 이름 행이 둘 이상이거나, 값이 비었거나 "-"일 때.
    """
    key_column, value_column = _SCHEMA[section][table][0][:2]
    found = [row for row in expected.get(section, {}).get(table, []) if row.get(key_column) == key]
    if len(found) != 1:
        raise NotImplementedError(f"{_NOT_READY}: {section} / {table} / {key} 행이 {len(found)}개")
    value = found[0].get(value_column, "")
    if value in ("", "-"):
        raise NotImplementedError(f"{_NOT_READY}: {section} / {key} 값이 비었거나 \"-\"")
    return value


def _require_through(expected: dict) -> None:
    """시연을 실행하기 전에 8개 장면 전체와 확정값의 양식·값을 모두 확인하고, 마지막으로 승인 줄을 확인한다.

    어느 장면 테스트든 장면 하나라도 실행하기 전에 부른다. 장·표가 없거나 남거나, 열 목록(이름·순서)이 다르거나,
    필수 행이 빠지거나 겹치거나, 칸이 비었거나, "-"를 허용하지 않는 칸에 "-"가 있거나, 값 형식이 맞지 않거나,
    확정값끼리 어긋나면(P_top ≠ 장면 2 추천 1위, 장면 3 두 색상이 같음) 실행하지 않고 멈춘다. 칸이 다 맞아도
    상태 줄이 승인 형식이 아니면 멈춘다(_require_approval).

    인자:
        expected: _load_expected()의 결과.

    반환:
        없음.

    예외:
        NotImplementedError: 위 조건 중 하나라도 맞지 않을 때 (기대값 승인 전, 11.3.8 승인 전).
    """
    for section, tables in _SCHEMA.items():
        if section not in expected:
            raise NotImplementedError(f"{_NOT_READY}: {section} 없음")
        if set(expected[section]) != set(tables):
            raise NotImplementedError(f"{_NOT_READY}: {section}의 표 목록이 양식과 다름: {sorted(expected[section])}")
        for table, (columns, rule) in tables.items():
            _check_table(section, table, expected[section][table], columns, rule)
    first = _rows(expected, "장면 2", "추천 (C_new, K=3)")
    if not first or first[0]["상품 ID"] != _value(expected, "확정값", "확정값", "P_top"):
        raise NotImplementedError(f"{_NOT_READY}: P_top이 장면 2 추천 1위 상품 ID와 다름")
    if _value(expected, "확정값", "확정값", "장면 3 색상 1") == _value(expected, "확정값", "확정값", "장면 3 색상 2"):
        raise NotImplementedError(f"{_NOT_READY}: 장면 3 색상 1·2가 같음")
    _require_approval()


def _check_table(section: str, table: str, rows: list[dict[str, str]], columns: tuple[str, ...], rule: object) -> None:
    """표 하나의 열 목록·행 규칙·칸 형식을 확인한다.

    인자:
        section: 장 이름.
        table: 표 제목.
        rows: 그 표의 행 (_load_expected 결과 그대로).
        columns: 정확한 열 목록 (이름·순서).
        rule: 필수 행 이름 튜플, _RANKED, _LISTED 중 하나.

    반환:
        없음.

    예외:
        NotImplementedError: 맞지 않는 것이 있을 때.
    """
    where = f"{_NOT_READY}: {section} / {table}"
    if not rows:
        raise NotImplementedError(f"{where} 행 없음")
    for row in rows:
        if tuple(row) != columns:
            raise NotImplementedError(f"{where} 열 목록이 양식과 다름: {list(row)}")
        if any(value == "" for value in row.values()):
            raise NotImplementedError(f"{where} 빈칸")
    keys = [row[columns[0]] for row in rows]
    if rule == _RANKED:
        _check_ranked(where, rows, table.startswith("추천"))
    elif len(set(keys)) != len(keys):
        raise NotImplementedError(f"{where} 행이 겹침: {keys}")
    elif rule != _LISTED and set(keys) != set(rule):
        raise NotImplementedError(f"{where} 필수 행이 양식과 다름: {keys}")
    for row in rows:
        if rule == _RANKED and all(value == "-" for value in list(row.values())[1:]):
            continue
        for column, value in row.items():
            _check_value(where, column, row[columns[0]], value)
        if table.startswith("추천"):
            _check_recommend_row(where, row)


def _check_ranked(where: str, rows: list[dict[str, str]], recommend_table: bool) -> None:
    """순위 표: 순위가 1부터 연속이고, 해당 없음 행(순위 말고 모두 "-")은 쓰인 행 뒤에만 오며, 그 밖에 "-"가 섞이지 않는다.

    "-"는 해당 없음 행과 추천 표의 "색상 수 안내" 칸에만 쓸 수 있다. 추천 표는 행이 정확히 K(3)개다.

    인자:
        where: 오류 메시지 앞부분.
        rows: 표의 행.
        recommend_table: 추천 표이면 True.

    반환:
        없음.

    예외:
        NotImplementedError: 맞지 않을 때.
    """
    if [row["순위"] for row in rows] != [str(rank) for rank in range(1, len(rows) + 1)]:
        raise NotImplementedError(f"{where} 순위가 1부터 연속이 아님")
    if recommend_table and len(rows) != _RECOMMEND_K:
        raise NotImplementedError(f"{where} 추천 표 행이 {_RECOMMEND_K}개가 아님")
    unused_seen = False
    for row in rows:
        values = list(row.values())[1:]
        if all(value == "-" for value in values):
            unused_seen = True
            continue
        dashes = [column for column, value in row.items() if value == "-" and column != "색상 수 안내"]
        if unused_seen or dashes:
            raise NotImplementedError(f"{where} \"-\"는 해당 없음 행(뒤쪽)과 색상 수 안내 칸에만 쓸 수 있음")


def _check_value(where: str, column: str, key: str, value: str) -> None:
    """칸 하나의 값 형식을 확인한다 (ID 규칙, 실제 날짜, 양의 정수, 정해진 값, 그룹 ID·통계 항목 이름).

    인자:
        where: 오류 메시지 앞부분.
        column: 열 제목.
        key: 그 행의 첫 열 값 (두 칸 표의 "값" 칸 형식을 정할 때 쓴다).
        value: 칸 값.

    반환:
        없음.

    예외:
        NotImplementedError: 형식이 맞지 않을 때.
    """
    if column == "값":
        pattern = _VALUE_FORMATS.get(key)
        ok = value in GROUP_IDS if key.endswith("연결 그룹 ID") else pattern is not None and re.fullmatch(pattern, value)
    elif column in _COLUMN_CHOICES:
        ok = value in _COLUMN_CHOICES[column]
    elif column == "그룹 ID":
        ok = value in GROUP_IDS
    elif column == "최근 구매일":
        ok = _is_real_date(value)
    elif column in _COLUMN_FORMATS:
        ok = re.fullmatch(_COLUMN_FORMATS[column], value) is not None
    else:
        ok = value != "-"  # 이름 열·메모·근거 같은 글자 칸
    if not ok:
        raise NotImplementedError(f"{where} / {column} 형식 확인 필요: {value!r}")


def _check_recommend_row(where: str, row: dict[str, str]) -> None:
    """추천 표 한 행의 칸끼리 일관성: 구매자 수 = 지지자 수, 색상 수 안내의 고객은 지지자 안에 있고 겹치지 않음.

    인자:
        where: 오류 메시지 앞부분.
        row: 쓰인 추천 표 행.

    반환:
        없음.

    예외:
        NotImplementedError: 맞지 않을 때.
    """
    supporters = row["지지자"].split(", ")
    if len(supporters) != int(row["구매자 수"]) or len(set(supporters)) != len(supporters):
        raise NotImplementedError(f"{where} 지지자 수가 구매자 수와 다르거나 겹침: {row['지지자']!r}")
    noted = [] if row["색상 수 안내"] == "-" else re.findall(_CUSTOMER_ID, row["색상 수 안내"])
    if len(set(noted)) != len(noted) or not set(noted) <= set(supporters):
        raise NotImplementedError(f"{where} 색상 수 안내의 고객이 지지자에 없거나 겹침: {row['색상 수 안내']!r}")


def _is_real_date(text: str) -> bool:
    """YYYY-MM-DD 10자(0~9 숫자)이고 실제 있는 날짜인지 (부록 B.3 구매일 규칙과 같은 두 단계).

    인자:
        text: 검사할 글자.

    반환:
        맞으면 True.

    예외:
        없음.
    """
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        return False
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _require_approval() -> None:
    """demo_expected.md의 상태 줄이 승인 형식일 때만 통과한다 (칸이 다 채워져 있어도 승인 전이면 멈춤).

    승인 형식: 맨 처음 나오는 "상태:" 줄 전체가 정확히 "상태: 승인 (찬일, YYYY-MM-DD) / AI 독립 계산 대조: 일치".
    날짜는 YYYY-MM-DD 10자이고 실제 있는 날짜여야 한다. 사람이 손계산·AI 대조·11.3.8 승인을 마치기 전에
    시연 결과를 보지 않으려는 장치다 (찬일 11/02 판정, w12_prep_review.md 질문 4).

    인자:
        없음.

    반환:
        없음.

    예외:
        NotImplementedError: 상태 줄이 없거나 승인 형식이 아닐 때 ("11.3.8 승인 전").
    """
    lines = [line for line in _EXPECTED_PATH.read_text(encoding="utf-8").splitlines() if line.startswith("상태:")]
    status = lines[0] if lines else ""
    if not _APPROVED_STATUS.fullmatch(status):
        raise NotImplementedError(f"{_NOT_APPROVED}: 상태 줄이 승인 형식이 아님: {status!r}")
    if not _is_real_date(re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", status).group(0)):
        raise NotImplementedError(f"{_NOT_APPROVED}: 상태 줄의 승인 날짜가 실제 날짜가 아님: {status!r}")


def _capture(func: object, *args: object) -> str:
    """출력 함수 하나를 불러 표준 출력을 문자열로 받는다.

    인자:
        func: 부를 함수 (승인된 view 출력 함수).
        *args: 넘길 인자.

    반환:
        출력 문자열.

    예외:
        func가 내는 예외를 그대로 전달한다.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        func(*args)
    return buffer.getvalue()


def _screen_blocks(screen: str, mark: str) -> list[str]:
    """화면에서 mark가 들어 있는 줄마다, 그 줄의 mark부터 다음 빈 줄 앞까지를 출력 구간으로 잘라 돌려준다.

    입력 안내(예: "번호 선택: ")가 같은 줄 앞에 붙으므로 첫 줄은 mark 앞을 지운다. 구간 뒤에는 메인 메뉴가
    빈 줄로 시작한다 (main.py _MENU). 구간 안에 덧붙은 줄이 있으면 구간에 같이 들어가 비교에서 드러난다.

    인자:
        screen: 장면 화면.
        mark: 구간 첫 줄 글자 (예: "[추천] ", "[그래프 통계]").

    반환:
        구간 문자열 리스트 (각 구간은 줄마다 줄바꿈으로 끝남). 화면에 나온 순서.

    예외:
        없음.
    """
    lines = screen.splitlines()
    blocks = []
    for index, line in enumerate(lines):
        if mark not in line:
            continue
        block = [line[line.index(mark):]]
        for following in lines[index + 1:]:
            if not following.strip():
                break
            block.append(following)
        blocks.append("".join(text + "\n" for text in block))
    return blocks


def _register_lines(screen: str) -> list[str]:
    """화면의 "[등록] " 줄을 입력 안내를 지운 채 화면 순서대로 돌려준다.

    인자:
        screen: 장면 화면.

    반환:
        "[등록] …" 줄 리스트.

    예외:
        없음.
    """
    return [line[line.index("[등록] "):] for line in screen.splitlines() if "[등록] " in line]


class _ExpectedColorCounts:
    """print_recommendation에 넘기는 그래프 대리: weight()만 기대값 "색상 수 안내" 열에서 읽고 나머지는 실제 그래프에 맡긴다.

    print_recommendation은 근거 줄의 "(C02는 2가지 색상 구매)"를 g.weight()가 2 이상인 지지자로 만든다.
    기대 화면의 그 부분을 기대값으로 만들려고 weight()만 바꾼다 (상품명·그룹 표시 이름 등은 기대값이 아님).
    """

    def __init__(self, g: ShopGraph, counts: dict[tuple[str, str], int]) -> None:
        """대리를 만든다.

        인자:
            g: 실제 그래프 (장면을 진행한 상태).
            counts: (고객 ID, 상품 ID) → 기대 색상 수. 없는 쌍은 1로 본다 (안내에 나오지 않음).

        반환:
            없음.

        예외:
            없음.
        """
        self.graph = g
        self.counts = counts

    def weight(self, customer_id: str, product_id: str) -> int:
        """기대 색상 수를 돌려준다.

        인자:
            customer_id: 고객 ID.
            product_id: 상품 ID.

        반환:
            "색상 수 안내"에 적힌 수, 없으면 1.

        예외:
            없음.
        """
        return self.counts.get((customer_id, product_id), 1)

    def __getattr__(self, name: str) -> object:
        """weight 말고는 실제 그래프의 공개 메서드를 돌려준다.

        인자:
            name: 속성 이름.

        반환:
            실제 그래프의 속성.

        예외:
            AttributeError: 실제 그래프에도 없을 때.
        """
        return getattr(self.graph, name)


def _color_counts(rows: list[dict[str, str]]) -> dict[tuple[str, str], int]:
    """추천 표 행들의 "색상 수 안내"를 (고객 ID, 상품 ID) → 색상 수로 읽는다.

    인자:
        rows: 쓰인 추천 표 행.

    반환:
        딕셔너리 ("-"인 행은 들어가지 않음).

    예외:
        없음.
    """
    return {(customer_id, row["상품 ID"]): int(count) for row in rows
            for customer_id, count in re.findall(r"(C[0-9]{2})[은는] ([0-9]+)가지", row["색상 수 안내"])}


def _expected_recommend_block(g: ShopGraph, customer_id: str, rows: list[dict[str, str]]) -> str:
    """기대 추천 표로 recommend() 결과 모양을 만들어 승인된 print_recommendation으로 기대 추천 블록을 만든다.

    인자:
        g: 장면을 진행한 실제 그래프 (이름·그룹 표시 이름·넓힘 이유용 소속 고객).
        customer_id: 추천 대상 고객 ID.
        rows: 쓰인 추천 표 행 (순위 순).

    반환:
        기대 화면 문자열 (머리 줄부터 안내 줄까지).

    예외:
        ValueError: 기대값의 고객·상품 ID가 그래프에 없을 때 (g가 낸다).
    """
    result = [{"product_id": row["상품 ID"], "score": int(row["점수"]), "buyers": int(row["구매자 수"]),
               "scope": _SCOPES[row["범위"]], "supporters": row["지지자"].split(", "),
               "available_colors": row["구매 가능 색상"].split(", ")} for row in rows]
    return _capture(print_recommendation, _ExpectedColorCounts(g, _color_counts(rows)), customer_id, result,
                    _RECOMMEND_K)


def _scene_inputs(scene: int, expected: dict) -> list[str]:
    """w11_scenes.md의 장면 하나 입력 절차를 메뉴 입력 순서로 만든다 (확정값은 demo_expected.md에서).

    인자:
        scene: 장면 번호 1~8.
        expected: _load_expected()의 결과.

    반환:
        input()에 차례로 줄 문자열 리스트.

    예외:
        NotImplementedError: 그 장면에 필요한 확정값이 비어 있을 때.
    """
    fixed = lambda key: _value(expected, "확정값", "확정값", key)  # noqa: E731
    if scene == 1:
        return ["5", "1"]
    if scene == 2:
        return ["1", "1", "하람", "2", "25"]
    if scene == 3:
        buy = [["1", "3", fixed("C_new"), fixed("P_top"), fixed(name), "1", day] for name, day in _SCENE3_BUYS]
        return buy[0] + buy[1] + ["2", "4", fixed("C_new")]
    if scene == 4:
        return ["6", fixed("C_new"), ""]
    if scene == 5:
        buys = [["1", "3", "C09", "P07", color, "1", day] for color, day in _SCENE5_BUYS]
        return ["2", "7", "2", ""] + buys[0] + buys[1] + buys[2] + ["2", "7", "2", ""]
    if scene == 6:
        stock = {p["id"]: p["stock"] for p in initial_records()[1]}[fixed("P_top6")]
        zero = ", ".join(f"{color}=0" for color in stock)
        return ["3", "2", fixed("P_top6"), "", "", "", "", zero, "6", fixed("C_new"), ""]
    if scene == 7:
        return ["1", "1", "새싹", "1", "15"]
    return ["5", "4"]


def _run_scenes(last: int, expected: dict) -> tuple[str, ShopGraph]:
    """실행용 data.py로 main.run()을 실행해 장면 1~last를 넣고, 장면 last의 화면과 그 뒤 그래프를 돌려준다.

    장면 last 바로 앞에 없는 메뉴 번호를 한 번 넣어 구분 줄을 찍고, 그 뒤 화면만 잘라 돌려준다.

    인자:
        last: 마지막 장면 번호.
        expected: _load_expected()의 결과.

    반환:
        (장면 last의 화면, 장면 last까지 진행한 ShopGraph).

    예외:
        NotImplementedError: 필요한 확정값이 비어 있을 때.
        AssertionError: 장면 진행 중 구분 줄 말고 다른 "[오류]"가 나왔을 때.
    """
    inputs = [value for scene in range(1, last) for value in _scene_inputs(scene, expected)]
    inputs += [_MARKER_INPUT] + _scene_inputs(last, expected) + ["0"]
    feed, created = iter(inputs), []

    def build(*records: list[dict]) -> ShopGraph:
        created.append(ShopGraph(*records))
        return created[-1]

    def fake_input(prompt: str = "") -> str:
        print(prompt, end="")
        value = next(feed, None)
        if value is None:
            raise EOFError("장면 입력이 모자람")
        return value

    buffer = io.StringIO()
    with mock.patch("main.ShopGraph", build), mock.patch("builtins.input", fake_input), \
            contextlib.redirect_stdout(buffer):
        main.run()
    text = buffer.getvalue()
    if text.count("[오류]") != 1:
        raise AssertionError(f"장면 진행 중 오류가 났다: {[line for line in text.splitlines() if '[오류]' in line]}")
    return text.split(_MARKER_LINE)[-1], created[0]


class TestW12Demo(unittest.TestCase):
    """W12: 7장 시연 장면 1~8 (기대값은 docs/demo_expected.md)."""

    def _check_recommend(self, expected: dict, scene: str, g: ShopGraph, customer_id: str, screen: str) -> None:
        """그 장면의 추천을 recommend()·g.weight()와 대조하고, 화면의 추천 블록을 기대 블록과 통째로 비교한다.

        인자:
            expected: _load_expected()의 결과.
            scene: 장 이름 (예: "장면 2").
            g: 그 장면까지 진행한 ShopGraph.
            customer_id: 추천 대상 고객 ID.
            screen: 그 장면의 화면.

        반환:
            없음.

        예외:
            NotImplementedError: 기대값 칸이 비어 있을 때.
            AssertionError: 다를 때.
        """
        table = next((name for name in expected.get(scene, {}) if name.startswith("추천")), None)
        if table is None:
            raise NotImplementedError(f"{_NOT_READY}: {scene} 추천 표 없음")
        rows = _rows(expected, scene, table)
        notes = {name: _value(expected, scene, "안내 줄", name) for name in _NOTE_NAMES}
        result = recommend(g, customer_id, _RECOMMEND_K)
        self.assertEqual([[item["product_id"], item["scope"], str(item["score"]), str(item["buyers"]),
                           ", ".join(item["supporters"]), ", ".join(item["available_colors"])] for item in result],
                         [[row["상품 ID"], _SCOPES[row["범위"]], row["점수"], row["구매자 수"], row["지지자"],
                           row["구매 가능 색상"]] for row in rows])
        self.assertEqual({(cid, item["product_id"]): g.weight(cid, item["product_id"]) for item in result
                          for cid in item["supporters"] if g.weight(cid, item["product_id"]) >= 2},
                         _color_counts(rows))
        gender_label = {"여": "여성 전체", "남": "남성 전체"}[g.get_customer(customer_id)["gender"]]
        self.assertTrue(all(row["범위"] == gender_label for row in rows if _SCOPES[row["범위"]] == "gender"))
        want = _expected_recommend_block(g, customer_id, rows)
        for name, mark in _NOTES:
            self.assertEqual(mark in want, notes[name] == "있음", msg=name)
        self.assertEqual(_screen_blocks(screen, "[추천] "), [want])

    def _check_register_buys(self, screen: str, buys: list[tuple[str, str, str, str, str]]) -> None:
        """구매 등록 줄들을 구매 ID(T번호)만 빼고 줄 전체로 비교한다.

        인자:
            screen: 장면 화면.
            buys: (고객 ID, 상품 ID, 색상, 구매일, 기대 가중치) 리스트, 입력 순서.

        반환:
            없음.

        예외:
            AssertionError: 줄 수가 다르거나 줄이 다를 때.
        """
        lines = _register_lines(screen)
        self.assertEqual(len(lines), len(buys), msg=lines)
        for line, (customer_id, product_id, color, day, weight) in zip(lines, buys):
            rest = f": {customer_id} → {product_id}, {color}, 1개, {day} (가중치 {weight})"
            self.assertRegex(line, "^" + re.escape("[등록] ") + "T[0-9]{3}" + re.escape(rest) + "$")

    def _s4_block(self, g: ShopGraph, rows: list[dict[str, str]]) -> str:
        """기대 S4 표(G-F-20)로 S4 화면 구간을 만든다 (main.py _search_s4·_print_rows 승인 형식).

        인자:
            g: 상품명을 읽을 그래프.
            rows: 쓰인 S4 표 행.

        반환:
            기대 화면 문자열.

        예외:
            ValueError: 없는 상품 ID일 때 (g가 낸다).
        """
        title = f"[S4 그룹 인기 상품] {GROUP_LABELS['G-F-20']}(G-F-20)"
        if not rows:
            return f"{title} 결과가 없습니다\n"
        table = [[int(row["순위"]), row["상품 ID"], g.get_product(row["상품 ID"])["name"], int(row["점수"]),
                  int(row["구매 고객 수"]), row["상태"]] for row in rows]
        return f"{title} {len(rows)}개\n" + _capture(print_table, _S4_SCREEN_HEADERS, table)

    def _check_s4(self, g: ShopGraph, rows: list[dict[str, str]], block: str) -> None:
        """S4(G-F-20, 전체)를 group_popular()와 대조하고 화면 구간을 기대 구간과 통째로 비교한다.

        인자:
            g: 비교할 시점의 ShopGraph.
            rows: 쓰인 S4 표 행.
            block: 화면에서 자른 S4 구간.

        반환:
            없음.

        예외:
            AssertionError: 다를 때.
        """
        actual = [[item["product_id"], str(item["score"]), str(item["buyers"]), "품절" if item["sold_out"] else "판매 중"]
                  for item in group_popular(g, "G-F-20")]
        self.assertEqual(actual, [[row["상품 ID"], row["점수"], row["구매 고객 수"], row["상태"]] for row in rows])
        self.assertEqual(block, self._s4_block(g, rows))

    def test_scene1_group_tree(self) -> None:
        """장면 1: 그룹별 인원을 g.members()와 대조하고, 화면의 그룹 트리 구간을 실제 그래프로 만든 트리와 통째로 비교."""
        expected = _load_expected()
        _require_through(expected)
        counts = {row["그룹 ID"]: row["인원"] for row in _rows(expected, "장면 1", "그룹별 인원")}
        screen, g = _run_scenes(1, expected)
        self.assertEqual({group_id: str(len(g.members(group_id))) for group_id in GROUP_IDS}, counts)
        self.assertEqual(_screen_blocks(screen, "[그룹별 고객]"), [_capture(print_group_tree, g)])

    def test_scene2_register_recommend(self) -> None:
        """장면 2: "25세 여성" 등록 → 등록 줄, 연결 그룹, 즉시 추천 블록."""
        expected = _load_expected()
        _require_through(expected)
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        group_id = _value(expected, "장면 2", "연결 그룹", "C_new 연결 그룹 ID")
        screen, g = _run_scenes(2, expected)
        self.assertEqual(_register_lines(screen), [f"[등록] 하람({customer_id}) → {GROUP_LABELS[group_id]} 그룹에 연결"])
        self.assertEqual(g.group_of(customer_id), group_id)
        self._check_recommend(expected, "장면 2", g, customer_id, screen)

    def test_scene3_two_colors_s1(self) -> None:
        """장면 3: 추천 1위를 두 색상으로 구매 → 등록 줄 2개와 S1 구간 (products_of()와 화면)."""
        expected = _load_expected()
        _require_through(expected)
        fixed = lambda key: _value(expected, "확정값", "확정값", key)  # noqa: E731
        customer_id, product_id = fixed("C_new"), fixed("P_top")
        weights = [row["가중치"] for row in _rows(expected, "장면 3", "구매 등록 줄 가중치")]
        rows = _rows(expected, "장면 3", "S1 (C_new)")
        screen, g = _run_scenes(3, expected)
        self._check_register_buys(screen, [(customer_id, product_id, fixed(name), day, weight)
                                           for (name, day), weight in zip(_SCENE3_BUYS, weights)])
        actual = [[item["product_id"], ", ".join(item["colors"]), str(item["weight"]), str(item["count"]),
                   str(item["total_qty"]), item["last_date"]] for item in products_of(g, customer_id)]
        self.assertEqual(actual, [[row["상품 ID"], row["구매 색상"], row["가중치"], row["기록 수"], row["총수량"],
                                   row["최근 구매일"]] for row in rows])
        table = [[row["상품 ID"], g.get_product(row["상품 ID"])["name"], row["구매 색상"], int(row["가중치"]),
                  int(row["기록 수"]), int(row["총수량"]), row["최근 구매일"]] for row in rows]
        title = f"[S1 고객이 산 상품] {g.get_customer(customer_id)['name']}({customer_id}) {len(rows)}개\n"
        self.assertEqual(_screen_blocks(screen, "[S1 고객이 산 상품]"),
                         [title + _capture(print_table, _S1_SCREEN_HEADERS, table)])

    def test_scene4_recommend_again(self) -> None:
        """장면 4: 다시 추천 → 이미 산 상품이 빠진 추천 블록."""
        expected = _load_expected()
        _require_through(expected)
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        screen, g = _run_scenes(4, expected)
        self._check_recommend(expected, "장면 4", g, customer_id, screen)

    def test_scene5_s4_change(self) -> None:
        """장면 5: C09가 P07을 세 색상으로 구매 → 등록 줄 3개, S4 구매 전·후 구간 (group_popular()와 화면)."""
        expected = _load_expected()
        _require_through(expected)
        before_rows = _rows(expected, "장면 5", "S4 구매 전 (G-F-20, 전체)")
        after_rows = _rows(expected, "장면 5", "S4 구매 후 (G-F-20, 전체)")
        weights = [row["가중치"] for row in _rows(expected, "장면 5", "구매 등록 줄 가중치 (C09–P07)")]
        _, before = _run_scenes(4, expected)
        screen, g = _run_scenes(5, expected)
        blocks = _screen_blocks(screen, "[S4 그룹 인기 상품]")
        self.assertEqual(len(blocks), 2)
        self._check_s4(before, before_rows, blocks[0])
        self._check_register_buys(screen, [("C09", "P07", color, day, weight)
                                           for (color, day), weight in zip(_SCENE5_BUYS, weights)])
        self._check_s4(g, after_rows, blocks[1])

    def test_scene6_sold_out(self) -> None:
        """장면 6: P_top6(장면 5 상태의 1위) 재고를 전부 0으로 → 품절, 다시 추천 블록."""
        expected = _load_expected()
        _require_through(expected)
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        product_id = _value(expected, "확정값", "확정값", "P_top6")
        _, before = _run_scenes(5, expected)
        top = recommend(before, customer_id, _RECOMMEND_K)
        self.assertEqual(top[0]["product_id"] if top else None, product_id, msg="P_top6 = 장면 5 상태의 C_new 추천 1위")
        screen, g = _run_scenes(6, expected)
        self.assertTrue(g.is_sold_out(product_id))
        self._check_recommend(expected, "장면 6", g, customer_id, screen)

    def test_scene7_widen_to_gender(self) -> None:
        """장면 7: 소속 고객이 없는 남성·10대 고객 등록 → 등록 줄, 연결 그룹, 넓혀 찾은 추천 블록."""
        expected = _load_expected()
        _require_through(expected)
        customer_id = _value(expected, "확정값", "확정값", "C_new7")
        group_id = _value(expected, "장면 7", "연결 그룹", "C_new7 연결 그룹 ID")
        screen, g = _run_scenes(7, expected)
        self.assertEqual(_register_lines(screen), [f"[등록] 새싹({customer_id}) → {GROUP_LABELS[group_id]} 그룹에 연결"])
        self.assertEqual(g.group_of(customer_id), group_id)
        self._check_recommend(expected, "장면 7", g, customer_id, screen)

    def test_scene8_integrity(self) -> None:
        """장면 8: 장면 1~7 뒤 통계 6항목·무결성 위반 수를 g와 대조하고, 통계 표와 무결성 줄 구간을 통째로 비교."""
        expected = _load_expected()
        _require_through(expected)
        counts = {row["항목"]: row["개수"] for row in _rows(expected, "장면 8", "통계 표")}
        violations = _value(expected, "장면 8", "무결성 검사", "위반 수")
        screen, g = _run_scenes(8, expected)
        stats = g.stats()
        self.assertEqual({label: str(stats[key]) for label, key in _STAT_KEYS.items()}, counts)
        problems = g.check_integrity()
        self.assertEqual(str(len(problems)), violations)
        verdict = [_INTEGRITY_OK] if not problems else [f"[무결성 검사] 위반 {len(problems)}건"] + [
            f"  - {problem}" for problem in problems]
        want = ("[그래프 통계]\n" + _capture(print_table, ["항목", "개수"],
                                            [[label, int(counts[label])] for label in _STAT_KEYS])
                + "".join(line + "\n" for line in verdict))
        self.assertEqual(_screen_blocks(screen, "[그래프 통계]"), [want])


if __name__ == "__main__":
    unittest.main()
