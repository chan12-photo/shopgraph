# docs/verification — 계획서 6장 기대값 검증 자료

이 폴더는 프로그램의 일부가 아니다. 계획서 6장의 기대값이 5.3.3 추천 규칙과 부록 B 계약대로 서로 모순 없이 계산되는지 확인한 기록이다.
실제 프로그램(graph.py, search.py …)이 맞다는 증거가 아니며, 구현 승인을 대신하지 않는다.
AI 에이전트는 이 폴더의 코드를 보고 구현이나 tests/의 테스트를 베끼지 않는다.

## 파일
- shop.py: 검증용 시험 구현 (ShopGraph 전체 메서드 + search.py 함수, 보류 기능·view·main 제외)
- fixtures.py: 6.1 PoC 고정 데이터 (테스트마다 새로 만듦)
- helpers.py: snapshot(g) — 내부 상태 전체 깊은 복사 (테스트 전용)
- test_spec.py: 6.2~6.4 기대값 24개 테스트
- mutants.py: 오류 주입 3종이 어느 테스트에서 걸리는지 확인
- run_output.txt, mutants_output.txt: 2026-10-23 실행 출력

## 실행 (Python 3.11 이상, 표준 라이브러리만)
    python test_spec.py
    python mutants.py

## 범위
- 화면(view.py)·흐름(main.py) 테스트는 검증하지 않았다
- 규칙이 바뀌면(계획서 11.3.8) 이 자료도 다시 돌리고 출력을 갱신한다
