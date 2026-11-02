# Codex 재현 스크립트를 고친 코드에 돌릴 때 사본에서 바꾼 줄 (2026-11-02, 5회차 [3])

- 원본은 이 폴더의 audit_guards.py·audit_screens.py (출처 주석 말고 원문 그대로). 아래 변경은 저장소 안 임시 사본(.wt_audit, 지움)에서만 했다
- 실행 조건은 Codex와 같게: 사본의 data.py를 `initial_records()`가 바로 AssertionError("DEMO DATA ACCESS BLOCKED")를 내는 가짜로 바꿈 (시연 데이터 사용 없음)

## audit_guards.py (1줄)

- 채움 기본값 딕셔너리에 `'색상 수 안내':'-'` 추가. 이유: 추천 표에 새 열 "색상 수 안내"가 생겼고, 지정 안 된 열은 '1'로 채워져 형식 위반이 되므로

## audit_screens.py (7줄)

| 원본 | 바꾼 것 | 이유 |
|---|---|---|
| `from view import print_recommendation` | `from view import print_recommendation, print_table` | 통계 화면을 실제 형식으로 만들려고 |
| `def row(rank,pid,scope,score,buyers,supporters,colors):` 와 다음 줄 | `note='-'` 인자와 `'색상 수 안내'` 열 추가 | 새 열 |
| C07 기대 행 생성 줄 | P02에 `'C02는 2가지'`, P01에 `'C01은 4가지'` (6.1 고정 데이터: C02의 P02 색상 2, C01의 P01 색상 4) | 새 열 값 |
| C02 기대 행 생성 줄 | P01에 `'C01은 4가지'` | 새 열 값 |
| `first=next(... if d._REC_ITEM.match(x))` | `re.match(r'^ \d+\. ',x)` | test_demo에서 정규식 추출(_REC_ITEM)을 없앴으므로 첫 항목 줄을 찾는 정규식을 스크립트 안에 둠 |
| `statistics_screen()` 두 줄 | `print_table`로 실제 통계 표를 만들고, 표와 무결성 줄 사이 빈 줄을 없앰. header 인자를 주면 머리 줄만 바꿈 | 원본의 합성 "정상" 화면은 실제 출력과 머리 줄 칸 맞춤("항목  개수" / "----  ----")과 빈 줄이 달라, 구간 통째 비교에서는 정상 화면이 거절됨. 잘못된 화면 경우(머리 줄 바꿈, 끝에 줄 덧붙임)의 뜻은 그대로 |
