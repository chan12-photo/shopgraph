"""시연 테스트: 계획서 7장 장면 1~8 (11.3.2 W12).

실행용 data.py(시연 데이터)로 main.run()을 실행하고, docs/verification/w11_scenes.md의 입력 절차대로
장면 1~N을 차례로 넣은 뒤 장면 N의 결과를 확인한다. 기대값은 docs/demo_expected.md에서만 읽는다
(사람이 손계산·승인한 값). 이 파일에는 기대값을 적지 않고, 실행 결과를 저장하지도 않는다.
demo_expected.md에서 필요한 칸이 비어 있으면(양식 상태) 각 테스트는
NotImplementedError("W11 기대값 승인 전")로 멈춘다 (11.3.3 미도래 분류).

화면 문구 확인에 쓰는 글자(안내 줄의 앞부분, "[등록]" 줄 모양)는 W8b·W10 승인 형식이다.
"""

import contextlib
import io
import pathlib
import re
import unittest
from unittest import mock

import main
from data import initial_records
from graph import ShopGraph
from search import group_popular, products_of, recommend

_EXPECTED_PATH = pathlib.Path(__file__).resolve().parent.parent / "docs" / "demo_expected.md"
_NOT_READY = "W11 기대값 승인 전"

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


def _load_expected() -> dict[str, dict[str, list[dict[str, str]]]]:
    """demo_expected.md를 장(## 제목의 마침표 앞) → 표(### 제목) → 행(머리 → 칸 딕셔너리)으로 읽는다.

    인자:
        없음.

    반환:
        {"장면 2": {"추천 (C_new, K=3)": [{"순위": "1", "상품 ID": "", …}, …], …}, …}.
        칸 값은 앞뒤 공백을 지운 문자열(빈칸은 "").

    예외:
        OSError: 파일을 읽지 못할 때.
    """
    sections: dict[str, dict[str, list[dict[str, str]]]] = {}
    section, table, header = "", "", []
    for line in _EXPECTED_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section, table = line[3:].split(".")[0].strip(), ""
            sections[section] = {}
        elif line.startswith("### ") and section:
            table, header = line[4:].strip(), []
            sections[section][table] = []
        elif line.startswith("|") and table:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if header and all(cell and set(cell) <= {"-"} for cell in cells):
                continue  # 머리 아래 구분 줄, 또는 모든 칸이 "-"인 행 (어느 쪽이든 쓰지 않음)
            if not header:
                header = cells
            else:
                sections[section][table].append(dict(zip(header, cells)))
    return sections


def _rows(expected: dict, section: str, table: str) -> list[dict[str, str]]:
    """표의 행 중 해당 없음(첫 칸 말고 모두 "-")이 아닌 행을 돌려준다. 빈칸이 있으면 미도래로 멈춘다.

    인자:
        expected: _load_expected()의 결과.
        section: 장 이름 (예: "장면 2").
        table: 표 제목 (### 뒤 글자 그대로).

    반환:
        채워진 행 리스트 (파일 순서).

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
    """두 칸짜리(이름 | 값) 표에서 key 행의 값을 돌려준다.

    인자:
        expected: _load_expected()의 결과.
        section: 장 이름.
        table: 표 제목.
        key: 첫 칸 글자.

    반환:
        둘째 칸 값.

    예외:
        NotImplementedError: 표나 행이 없거나 값이 비어 있을 때 (기대값 승인 전).
    """
    for row in expected.get(section, {}).get(table, []):
        cells = list(row.values())
        if cells[0] == key:
            if not cells[1]:
                raise NotImplementedError(f"{_NOT_READY}: {section} / {key} 빈칸")
            return cells[1]
    raise NotImplementedError(f"{_NOT_READY}: {section} / {key} 행 없음")


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
            self.assertIn(f"({row['상품 ID']}) - 점수 {row['점수']}, 구매 고객 {row['구매자 수']}명 [{row['범위']}]",
                          screen)
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

    def _check_s4(self, expected: dict, table: str, g: ShopGraph) -> None:
        """S4(G-F-20, 전체) 결과를 표와 대조한다.

        인자:
            expected: _load_expected()의 결과.
            table: "장면 5"의 S4 표 제목.
            g: 비교할 시점의 ShopGraph.

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

    def test_scene1_group_tree(self) -> None:
        """장면 1: 그룹별 고객 트리의 그룹별 인원."""
        expected = _load_expected()
        rows = _rows(expected, "장면 1", "그룹별 인원")
        screen, g = _run_scenes(1, expected)
        self.assertIn("[그룹별 고객]", screen)
        self.assertEqual({row["그룹 ID"]: row["인원"] for row in rows},
                         {row["그룹 ID"]: str(len(g.members(row["그룹 ID"]))) for row in rows})

    def test_scene2_register_recommend(self) -> None:
        """장면 2: "25세 여성" 등록 → 연결 그룹, 즉시 추천과 안내 줄."""
        expected = _load_expected()
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        group_id = _value(expected, "장면 2", "연결 그룹", "C_new 연결 그룹 ID")
        screen, g = _run_scenes(2, expected)
        self.assertIn(f"[등록] 하람({customer_id}) → ", screen)
        self.assertEqual(g.group_of(customer_id), group_id)
        self._check_recommend(expected, "장면 2", g, customer_id, screen)

    def test_scene3_two_colors_s1(self) -> None:
        """장면 3: 추천 1위를 두 색상으로 구매 → 구매 등록 줄 가중치와 S1."""
        expected = _load_expected()
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        rows = _rows(expected, "장면 3", "S1 (C_new)")
        screen, g = _run_scenes(3, expected)
        self._check_weights(expected, "장면 3", "구매 등록 줄 가중치", screen)
        actual = [[item["product_id"], ", ".join(item["colors"]), str(item["weight"]), str(item["count"]),
                   str(item["total_qty"]), item["last_date"]] for item in products_of(g, customer_id)]
        self.assertEqual(actual, [[row["상품 ID"], row["구매 색상"], row["가중치"], row["기록 수"], row["총수량"],
                                   row["최근 구매일"]] for row in rows])

    def test_scene4_recommend_again(self) -> None:
        """장면 4: 다시 추천 → 이미 산 상품이 빠진 결과와 안내 줄."""
        expected = _load_expected()
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        screen, g = _run_scenes(4, expected)
        self._check_recommend(expected, "장면 4", g, customer_id, screen)

    def test_scene5_s4_change(self) -> None:
        """장면 5: C09가 P07을 세 색상으로 구매 → 구매 등록 줄 가중치, S4 구매 전·후."""
        expected = _load_expected()
        _rows(expected, "장면 5", "S4 구매 후 (G-F-20, 전체)")
        _, before = _run_scenes(4, expected)
        self._check_s4(expected, "S4 구매 전 (G-F-20, 전체)", before)
        screen, g = _run_scenes(5, expected)
        self._check_weights(expected, "장면 5", "구매 등록 줄 가중치 (C09–P07)", screen)
        self._check_s4(expected, "S4 구매 후 (G-F-20, 전체)", g)

    def test_scene6_sold_out(self) -> None:
        """장면 6: P_top6 재고를 전부 0으로 → 품절, 다시 추천과 안내 줄."""
        expected = _load_expected()
        customer_id = _value(expected, "확정값", "확정값", "C_new")
        product_id = _value(expected, "확정값", "확정값", "P_top6")
        screen, g = _run_scenes(6, expected)
        self.assertTrue(g.is_sold_out(product_id))
        self._check_recommend(expected, "장면 6", g, customer_id, screen)

    def test_scene7_widen_to_gender(self) -> None:
        """장면 7: 소속 고객이 없는 남성·10대 고객 등록 → 연결 그룹, 넓혀 찾은 추천과 안내 줄."""
        expected = _load_expected()
        customer_id = _value(expected, "확정값", "확정값", "C_new7")
        group_id = _value(expected, "장면 7", "연결 그룹", "C_new7 연결 그룹 ID")
        screen, g = _run_scenes(7, expected)
        self.assertIn(f"[등록] 새싹({customer_id}) → ", screen)
        self.assertEqual(g.group_of(customer_id), group_id)
        self._check_recommend(expected, "장면 7", g, customer_id, screen)

    def test_scene8_integrity(self) -> None:
        """장면 8: 장면 1~7 뒤 통계 표와 무결성 검사."""
        expected = _load_expected()
        rows = _rows(expected, "장면 8", "통계 표")
        violations = _value(expected, "장면 8", "무결성 검사", "위반 수")
        screen, g = _run_scenes(8, expected)
        stats = g.stats()
        self.assertEqual({row["항목"]: row["개수"] for row in rows},
                         {row["항목"]: str(stats[_STAT_KEYS[row["항목"]]]) for row in rows})
        self.assertEqual(str(len(g.check_integrity())), violations)
        self.assertIn("[무결성 검사]", screen)


if __name__ == "__main__":
    unittest.main()
