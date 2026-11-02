"""승인된 demo_expected를 읽는 테스트 전용 어댑터(운영 모듈에서 사용 금지).

기존 W12 파서·승인 보호만 재사용한다. recommend/view 또는 실제 API 응답으로
기대값을 만들지 않는다. 점수·목록·색상 수·안내 유무의 출처는 demo_expected.md다.
"""

from tests import test_demo as legacy


def load_approved() -> dict:
    """승인 줄과 8장면 전체 양식을 검사한다. 불완전하면 서버 생성 전에 예외를 낸다."""
    legacy._require_approval()
    expected = legacy._load_expected()
    legacy._require_through(expected)
    return expected


def rows(expected: dict, scene: int, table: str) -> list[dict[str, str]]:
    """해당 없음 행을 제외한 승인 표를 순서대로 돌려준다. 잘못된 표는 예외다."""
    return legacy._rows(expected, f"장면 {scene}", table)


def fixed(expected: dict, name: str) -> str:
    """확정값 표의 값 하나를 읽는다. 누락·중복·빈칸이면 예외다."""
    return legacy._value(expected, "확정값", "확정값", name)


def value(expected: dict, scene: int, table: str, key: str) -> str:
    """두 칸 표의 값 하나를 읽는다. 누락·중복·빈칸이면 예외다."""
    return legacy._value(expected, f"장면 {scene}", table, key)


def recommendation(expected: dict, scene: int, before_stock: bool = False) -> dict:
    """추천 표를 비교용 JSON으로 바꾼다. 업무 결과를 계산하지 않는다."""
    table = "품절 전 추천 (C_new, K=3)" if before_stock else (
        "추천 (C_new7, K=3)" if scene == 7 else "추천 (C_new, K=3)")
    note_table = "품절 전 안내 줄" if before_stock else "안내 줄"
    items = [{"product_id": row["상품 ID"], "scope": legacy._SCOPES[row["범위"]],
              "scope_label": row["범위"], "score": int(row["점수"]), "buyers": int(row["구매자 수"]),
              "supporters": row["지지자"].split(", "),
              "available_colors": row["구매 가능 색상"].split(", "),
              "color_note": row["색상 수 안내"]} for row in rows(expected, scene, table)]
    notices = {row["안내"]: row["있음/없음"] == "있음" for row in rows(expected, scene, note_table)}
    return {"items": items, "notices": notices}


def popular(expected: dict, after: bool) -> list[dict]:
    """S4 표의 순서·숫자·상태를 읽는다. 상품을 정렬하거나 점수를 계산하지 않는다."""
    when = "후" if after else "전"
    return [{"product_id": row["상품 ID"], "score": int(row["점수"]),
             "buyers": int(row["구매 고객 수"]), "status_label": row["상태"],
             "sold_out": row["상태"] == "품절"}
            for row in rows(expected, 5, f"S4 구매 {when} (G-F-20, 전체)")]


def s1(expected: dict) -> list[dict]:
    """S1 표를 읽어 타입만 변환한다. 없는 표/칸은 예외다."""
    return [{"product_id": row["상품 ID"], "colors": row["구매 색상"].split(", "),
             "weight": int(row["가중치"]), "count": int(row["기록 수"]),
             "total_qty": int(row["총수량"]), "last_date": row["최근 구매일"]}
            for row in rows(expected, 3, "S1 (C_new)")]


def browser_expected() -> dict:
    """브라우저 검사에도 같은 승인 파서의 값만 JSON으로 전달한다."""
    expected = load_approved()
    return {"fixed": {row["이름"]: row["값"] for row in expected["확정값"]["확정값"]},
            "groups": {row["그룹 ID"]: int(row["인원"]) for row in rows(expected, 1, "그룹별 인원")},
            "recommendations": {str(scene): recommendation(expected, scene) for scene in (2, 4, 6, 7)},
            "before_stock": recommendation(expected, 6, True), "s1": s1(expected),
            "popular_before": popular(expected, False), "popular_after": popular(expected, True),
            "purchase_weights_3": [int(row["가중치"]) for row in rows(expected, 3, "구매 등록 줄 가중치")],
            "purchase_weights_5": [int(row["가중치"]) for row in rows(expected, 5, "구매 등록 줄 가중치 (C09–P07)")],
            "stats": {row["항목"]: int(row["개수"]) for row in rows(expected, 8, "통계 표")},
            "violations": int(value(expected, 8, "무결성 검사", "위반 수"))}
