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
비교: 내부 함수(recommend·products_of·group_popular·stats 등) 결과와 함께, 실제 화면에서 표 행·추천 항목을
순서대로 뽑아 기대값과 비교한다 (Codex 검토 9784473 1·2번).
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
from search import group_popular, products_of, recommend

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
_FIXED_KEYS = ("C_new", "P_top", "장면 3 색상 1", "장면 3 색상 2", "P_top6", "C_new7")
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

# 화면 줄 모양 (W8b·W9·W10 승인 형식)
_TREE_GROUP = re.compile(r"^ {4}\S.*? \((G-[FM]-\d+\+?)\) (\d+)명$", re.M)
_REC_ITEM = re.compile(r"^ (\d+)\. .+ \((P\d{2})\) - 점수 (\d+), 구매 고객 (\d+)명 \[(.+)\]$")
_REC_REASON = re.compile(r"^ {4}근거: (.+?)(?:이|가) 구매")
_REC_COLORS = "    구매 가능 색상: "


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


def _screen_tables(screen: str, title: str) -> list[list[list[str]]]:
    """화면에서 title이 들어 있는 줄 뒤의 print_table 표를 모두 찾아 행(칸 리스트)으로 돌려준다.

    표는 제목 줄 → 머리 줄 → 구분 줄 → 행들 순서다 (W9·W10 승인 형식). 행은 빈 줄, "["로 시작하는 줄,
    "메뉴 선택" 줄 앞에서 끝난다. 칸은 공백 2칸 이상으로 나눈다 (열 사이 공백 2칸, W9).
    "[제목] 결과가 없습니다" 줄은 빈 표로 센다.

    인자:
        screen: 장면 화면.
        title: 표 제목 글자 (예: "[S4 그룹 인기 상품]").

    반환:
        표마다 행 리스트. 화면에 나온 순서.

    예외:
        없음.
    """
    lines = screen.splitlines()
    tables = []
    for index, line in enumerate(lines):
        if title not in line:
            continue
        if line.endswith("결과가 없습니다"):
            tables.append([])
            continue
        rows = []
        for row in lines[index + 3:]:
            if not row.strip() or row.startswith("[") or row.startswith("메뉴 선택"):
                break
            rows.append(re.split(r" {2,}", row.strip()))
        tables.append(rows)
    return tables


def _screen_recommend(screen: str) -> list[list[str]]:
    """추천 화면에서 항목마다 [순위, 상품 ID, 점수, 구매자 수, 범위, 지지자, 구매 가능 색상]을 화면 순서대로 뽑는다.

    항목 줄 다음 줄이 근거 줄, 그다음 줄이 구매 가능 색상 줄이다 (W8b 승인 형식). 지지자는 근거 줄에서
    "이/가 구매" 앞의 고객 ID들이다 (그룹 표시 이름과 색상 수 안내는 뺌).

    인자:
        screen: 장면 화면.

    반환:
        항목 리스트. 근거·색상 줄 모양이 다르면 그 줄을 그대로 넣어 비교에서 드러나게 한다.

    예외:
        없음.
    """
    lines = screen.splitlines() + ["", ""]
    items = []
    for index, line in enumerate(lines):
        match = _REC_ITEM.match(line)
        if not match:
            continue
        reason = _REC_REASON.match(lines[index + 1])
        supporters = ", ".join(re.findall(r"C\d{2}", reason.group(1))) if reason else lines[index + 1]
        colors = lines[index + 2]
        colors = colors[len(_REC_COLORS):] if colors.startswith(_REC_COLORS) else colors
        items.append(list(match.groups()) + [supporters, colors])
    return items


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
        buy = [["1", "3", fixed("C_new"), fixed("P_top"), fixed(f"장면 3 색상 {n}"), "1", day]
               for n, day in ((1, "2026-10-30"), (2, "2026-10-31"))]
        return buy[0] + buy[1] + ["2", "4", fixed("C_new")]
    if scene == 4:
        return ["6", fixed("C_new"), ""]
    if scene == 5:
        buys = [["1", "3", "C09", "P07", color, "1", day]
                for color, day in (("블랙", "2026-10-30"), ("그레이", "2026-10-30"), ("네이비", "2026-10-31"))]
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
        """그 장면의 추천 표·안내 줄을 recommend() 결과와 화면에 대조한다.

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
        notes = {name: _value(expected, scene, "안내 줄", name) for name, _ in _NOTES}
        result = recommend(g, customer_id, 3)
        self.assertEqual([item["product_id"] for item in result], [row["상품 ID"] for row in rows])
        for item, row in zip(result, rows):
            self.assertEqual(item["scope"], _SCOPES[row["범위"]], msg=row)
            self.assertEqual((str(item["score"]), str(item["buyers"])), (row["점수"], row["구매자 수"]), msg=row)
            self.assertEqual(", ".join(item["supporters"]), row["지지자"], msg=row)
            self.assertEqual(", ".join(item["available_colors"]), row["구매 가능 색상"], msg=row)
        # 화면: 항목 순서·개수·근거 줄·구매 가능 색상 줄을 순서대로 비교
        self.assertEqual(_screen_recommend(screen),
                         [[row["순위"], row["상품 ID"], row["점수"], row["구매자 수"], row["범위"], row["지지자"],
                           row["구매 가능 색상"]] for row in rows])
        if rows:
            self.assertEqual(re.findall(r"님께 추천 \((\d+)개\)", screen), [str(len(rows))])
        else:
            self.assertIn("님께 추천할 상품이 없습니다", screen)
        for name, mark in _NOTES:
            self.assertEqual(mark in screen, notes[name] == "있음", msg=name)

    def _check_weights(self, expected: dict, scene: str, table: str, screen: str) -> None:
        """구매 등록 줄의 "(가중치 W)" 값들을 표와 대조한다.

        인자:
            expected: _load_expected()의 결과.
            scene: 장 이름.
            table: 가중치 표 제목.
            screen: 그 장면의 화면.

        반환:
            없음.

        예외:
            NotImplementedError: 기대값 칸이 비어 있을 때.
            AssertionError: 다를 때.
        """
        rows = _rows(expected, scene, table)
        self.assertEqual(re.findall(r"\(가중치 (\d+)\)", screen), [row["가중치"] for row in rows])

    def _check_s4(self, expected: dict, table: str, g: ShopGraph, screen_rows: list[list[str]]) -> None:
        """S4(G-F-20, 전체) 결과를 내부 함수 결과와 화면 표 행 둘 다 기대 표와 대조한다.

        인자:
            expected: _load_expected()의 결과.
            table: "장면 5"의 S4 표 제목.
            g: 비교할 시점의 ShopGraph.
            screen_rows: 화면의 S4 표 행 (_screen_tables의 표 하나).

        반환:
            없음.

        예외:
            NotImplementedError: 기대값 칸이 비어 있을 때.
            AssertionError: 다를 때.
        """
        rows = _rows(expected, "장면 5", table)
        actual = [[item["product_id"], str(item["score"]), str(item["buyers"]), "품절" if item["sold_out"] else "판매 중"]
                  for item in group_popular(g, "G-F-20")]
        self.assertEqual(actual, [[row["상품 ID"], row["점수"], row["구매 고객 수"], row["상태"]] for row in rows])
        # 화면 표: [순위, 상품 ID, 상품명, 점수, 구매 고객 수, 상태] 중 상품명을 뺀 칸 (행 순서·개수)
        self.assertEqual([[cells[0], cells[1]] + cells[3:] for cells in screen_rows],
                         [[row["순위"], row["상품 ID"], row["점수"], row["구매 고객 수"], row["상태"]] for row in rows])

    def test_scene1_group_tree(self) -> None:
        """장면 1: 그룹별 고객 트리의 그룹별 인원 (화면 줄과 g.members())."""
        expected = _load_expected()
        _require_through(expected)
        rows = _rows(expected, "장면 1", "그룹별 인원")
        screen, g = _run_scenes(1, expected)
        want = [(row["그룹 ID"], row["인원"]) for row in rows]
        self.assertEqual(_TREE_GROUP.findall(screen), want)  # 화면 순서·개수까지
        self.assertEqual([(group_id, str(len(g.members(group_id)))) for group_id, _ in want], want)

    def test_scene2_register_recommend(self) -> None:
        """장면 2: "25세 여성" 등록 → 연결 그룹, 즉시 추천과 안내 줄."""
        expected = _load_expected()
        _require_through(expected)
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        group_id = _value(expected, "장면 2", "연결 그룹", "C_new 연결 그룹 ID")
        screen, g = _run_scenes(2, expected)
        self.assertIn(f"[등록] 하람({customer_id}) → ", screen)
        self.assertEqual(g.group_of(customer_id), group_id)
        self._check_recommend(expected, "장면 2", g, customer_id, screen)

    def test_scene3_two_colors_s1(self) -> None:
        """장면 3: 추천 1위를 두 색상으로 구매 → 구매 등록 줄 가중치와 S1 (화면 표와 products_of())."""
        expected = _load_expected()
        _require_through(expected)
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        rows = _rows(expected, "장면 3", "S1 (C_new)")
        want = [[row["상품 ID"], row["구매 색상"], row["가중치"], row["기록 수"], row["총수량"], row["최근 구매일"]]
                for row in rows]
        screen, g = _run_scenes(3, expected)
        self._check_weights(expected, "장면 3", "구매 등록 줄 가중치", screen)
        actual = [[item["product_id"], ", ".join(item["colors"]), str(item["weight"]), str(item["count"]),
                   str(item["total_qty"]), item["last_date"]] for item in products_of(g, customer_id)]
        self.assertEqual(actual, want)
        tables = _screen_tables(screen, "[S1 고객이 산 상품]")
        self.assertEqual(len(tables), 1)
        self.assertEqual([[cells[0]] + cells[2:] for cells in tables[0]], want)

    def test_scene4_recommend_again(self) -> None:
        """장면 4: 다시 추천 → 이미 산 상품이 빠진 결과와 안내 줄."""
        expected = _load_expected()
        _require_through(expected)
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        screen, g = _run_scenes(4, expected)
        self._check_recommend(expected, "장면 4", g, customer_id, screen)

    def test_scene5_s4_change(self) -> None:
        """장면 5: C09가 P07을 세 색상으로 구매 → 구매 등록 줄 가중치, S4 구매 전·후 (화면 표 2개와 group_popular())."""
        expected = _load_expected()
        _require_through(expected)
        _, before = _run_scenes(4, expected)
        screen, g = _run_scenes(5, expected)
        tables = _screen_tables(screen, "[S4 그룹 인기 상품]")
        self.assertEqual(len(tables), 2)
        self._check_s4(expected, "S4 구매 전 (G-F-20, 전체)", before, tables[0])
        self._check_weights(expected, "장면 5", "구매 등록 줄 가중치 (C09–P07)", screen)
        self._check_s4(expected, "S4 구매 후 (G-F-20, 전체)", g, tables[1])

    def test_scene6_sold_out(self) -> None:
        """장면 6: P_top6 재고를 전부 0으로 → 품절, 다시 추천과 안내 줄."""
        expected = _load_expected()
        _require_through(expected)
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        product_id = _value(expected, "확정값", "확정값", "P_top6")
        _, before = _run_scenes(5, expected)
        top = recommend(before, customer_id, 3)
        self.assertEqual(top[0]["product_id"] if top else None, product_id, msg="P_top6 = 장면 5 상태의 C_new 추천 1위")
        screen, g = _run_scenes(6, expected)
        self.assertTrue(g.is_sold_out(product_id))
        self._check_recommend(expected, "장면 6", g, customer_id, screen)

    def test_scene7_widen_to_gender(self) -> None:
        """장면 7: 소속 고객이 없는 남성·10대 고객 등록 → 연결 그룹, 넓혀 찾은 추천과 안내 줄."""
        expected = _load_expected()
        _require_through(expected)
        customer_id = _value(expected, "확정값", "확정값", "C_new7")
        group_id = _value(expected, "장면 7", "연결 그룹", "C_new7 연결 그룹 ID")
        screen, g = _run_scenes(7, expected)
        self.assertIn(f"[등록] 새싹({customer_id}) → ", screen)
        self.assertEqual(g.group_of(customer_id), group_id)
        self._check_recommend(expected, "장면 7", g, customer_id, screen)

    def test_scene8_integrity(self) -> None:
        """장면 8: 장면 1~7 뒤 통계 표와 무결성 검사 (화면 표·판정 줄과 g.stats()·check_integrity())."""
        expected = _load_expected()
        _require_through(expected)
        rows = _rows(expected, "장면 8", "통계 표")
        violations = _value(expected, "장면 8", "무결성 검사", "위반 수")
        want = [[row["항목"], row["개수"]] for row in rows]
        screen, g = _run_scenes(8, expected)
        stats = g.stats()
        self.assertEqual([[name, str(stats[_STAT_KEYS[name]])] for name, _ in want], want)
        self.assertEqual(str(len(g.check_integrity())), violations)
        tables = _screen_tables(screen, "[그래프 통계]")
        self.assertEqual(tables, [want])
        if violations == "0":
            self.assertIn("\n[무결성 검사] 위반 없음: 원본과 그래프가 일치함을 확인\n", screen)
        else:
            self.assertIn(f"\n[무결성 검사] 위반 {violations}건\n", screen)


if __name__ == "__main__":
    unittest.main()
