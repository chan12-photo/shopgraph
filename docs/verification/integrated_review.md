# 통합 독립 검토 (2026-11-02, 2회차 야간 작업 1)

- 검토자: 서브에이전트(이 대화의 맥락 없음, 별도 컨텍스트). 저장소를 직접 읽음 (읽기 전용, 파일 생성·수정 없음, git은 log·show·status만)
- 대상: w12-prep 브랜치 (검토 시작 시점 2ccefa7). 계획서 5.1~5.5, 6장, 부록 B.1~B.4, CLAUDE.md 기준. 특히 독립 검토를 받지 않은 W9·W10·W10a·W11과 main → graph/search → view 연결
- 검토자에게 금지한 것: 파일 수정, 시연 장면 1~8 실행, data.py로 추천·S4·S1·통계 결과 출력, docs/verification/의 검증용 시험 구현을 근거로 쓰기
- 이 문서는 검토자 보고를 옮긴 것이다. 지적에 따른 수정은 하지 않았다 (지시: 보고만)

## 검토자가 직접 실행한 것

- `python3 -m unittest -v` (Python 3.13.12): Ran 139, FAILED (errors=8) = 통과 131, 미도래 8(tests/test_demo.py 전부 `NotImplementedError: W11 기대값 승인 전 …`). 그 밖의 실패·오류 0
- `python3 tools/check_data.py > /dev/null`: 종료 코드 0 (출력은 장면 1 기대값과 겹쳐 보지 않음)
- data.py 설명 대조(참/거짓만 출력): 30명·22개·122건, 구매일 범위, 일부 품절 P05·P08·P13, 전부 품절 P16, 미판매 P22, 남성·10대 빈 그룹, initial_records() 두 번 호출 시 재고 딕셔너리가 다른 객체, 생성자 통과, check_integrity() = [] 모두 설명과 같음
- `python3 main.py`에 잘못된 입력 약 60가지: 모두 `[오류] …` 뒤 메뉴 복귀, Traceback 0건. 유효한 값과 틀린 값을 섞은 3가지(이름 변경 + 나이 5, 상품명 변경 + 구매된 색상 삭제, 구매 수량 100) 뒤 ID 조회로 상태 그대로 확인
- 시연 장면 1~8 실행 없음, 추천·S4·S1·통계 결과 출력 없음

## 반드시 수정

없음.

## 권장

| # | 파일:줄 | 지적 | 재현 | 검토자 제안 |
|---|---|---|---|---|
| R1 | main.py:824 | 추천 K 항목 이름이 두 가지: 숫자가 아니면 `[오류] K: 숫자로 입력해 주세요`, 범위 밖이면 `[오류] 추천 개수 K: 1~10이어야 합니다 (입력: 0)`. W10a에서 search.py만 "추천 개수 K"로 맞추고 main.py `_to_int(text, "K")`는 남음 (S4는 두 곳 모두 "개수") | `printf '6\nC01\nabc\n0\n' \| python3 main.py` | main.py:824 라벨을 "추천 개수 K"로 |
| R2 | main.py:227 | main.py 문구 `[오류] 색상별 재고: 같은 색상이 두 번 나옵니다: 블랙`이 "항목: 규칙: 값"(A04 모양). 같은 규칙의 graph.py 경로 문구는 `색상명: 겹칩니다 (입력: 카키)`로 다름. W10 승인 형식 7번이라 바꾸려면 11.3.8 | `printf '1\n2\n새 상품\n1\n1\n1000\n블랙=1, 블랙=2\n0\n' \| python3 main.py` | 판정 필요 |
| R3 | tools/check_data.py:30-61, 183-197 | check_dates docstring "예외: 없음"과 달리 빈 리스트면 `min()`에서 ValueError. main()은 생성자 검증 뒤에 check_dates를 부르므로 형식·없는 날짜 분기는 실행될 수 없음(실제로 일하는 것은 9~10월 범위 검사뿐) | `python3 -c "import sys;sys.path.insert(0,'tools');import check_data;check_data.check_dates([])"` | docstring·분기 정리 |
| R4 | tests/test_flow.py:438-560 | `_assert_errors_keep_state`가 `[오류]` 줄 수와 상태만 보고 어느 규칙에 걸렸는지는 보지 않음. 예: docstring은 "범위 밖 숫자"라 하지만 "-3"(나이)·"-5"(가격)는 main.py "숫자로 입력해 주세요"에서 멈추고 graph.py 범위 검사까지 가지 않음 (graph.py 쪽은 단위 테스트가 덮어 결함은 아님) | 코드 읽기 | 케이스마다 기대 문구 assert 추가 (추가만) |

R4는 2회차 작업 2의 확장 고장 검사에서 못 잡은 M04(숫자 자릿수 경계)와 같은 원인이다 (docs/verification/mutation_sweep.md, mutation_proposals.md P1).

## 질문

| # | 파일:줄 | 질문 |
|---|---|---|
| Q1 | graph.py:1199 | `구매 기록이 있는 색상은 삭제할 수 없습니다: 그레이, 네이비, 화이트`가 W10a 형식이 아님. w10a_g7.md에 "판정 필요하면 다음 단계에서"로 남았고 판정 기록이 없음 |
| Q2 | main.py:156·159·184·225·227 | main.py가 만드는 변환 오류(예: `나이: 숫자로 입력해 주세요`)에는 "(입력: 값)"이 없음. W10a 범위는 graph.py·search.py뿐이라 한 화면에 두 형식이 섞임. 의도인지 |
| Q3 | tools/check_data.py:76-87 | check_groups가 출력하는 그룹별 인원이 곧 demo_expected.md "장면 1 / 그룹별 인원"의 기대값이고 w11_g7.md에도 같은 숫자가 있음. CLAUDE.md "실행 결과를 기대값으로 옮겨 적지 않는다"에 비추어 이 칸을 data.py·w11_raw_by_group.md에서 사람이 직접 셀지 정해 둘 것 (검토자: 손계산 전에 판정 권함) |
| Q4 | docs/verification/make_raw_by_group.py:18 | 계획서 11.3.2 W11은 보조 스크립트가 "프로그램 코드를 import하지 않는" 독립 스크립트여야 한다고 함. graph·search는 import하지 않지만 data.py를 import함. data.py를 "프로그램 코드"로 볼지 |
| Q5 | docs/report_materials.md | 112e4f0([DOC])이 docs/ 바로 아래에 만든 파일이 CLAUDE.md·11.3.2의 공통 수정 허용 경로(defects.md, test_map.md, verification/, README 현재 상태) 밖. 사람이 승인한 위치인지 |

구현 쪽 사실 메모 (이 문서 작성자, 검토자 의견 아님)

- Q5: docs/report_materials.md 경로는 찬일 11/01 밤 야간 작업 6 지시에 적힌 경로 그대로다. docs/study/도 2회차 지시의 경로다. 규칙상 허용 경로 밖이라는 지적 자체는 맞으므로 판정 필요로 둔다
- Q3: w11_g7.md의 그룹별 인원은 W11 앞부분에서 찬일이 요청한 tools/check_data.py 출력과 data.py 요약을 적은 것이다

## 검토자가 문제 없다고 확인한 것 (G6 10항목)

1. 운영 모듈 공개 함수가 5.5와 같음 (print_recommendation k 인자는 [SPEC][W8b] 승인, 계획서 반영 대기). 조회는 복사본 반환
2. W9·W10·W10a·W11 커밋의 파일 목록이 각 G7 기록과 같음 (Q5 제외)
3. B.4 잘못된 입력에서 죽지 않음
4. 일부만 바뀌는 경로 없음: graph.py 변경 메서드는 검증 뒤 원본 변경 → rebuild(), rebuild()는 새 그래프를 다 만든 뒤 한 번에 대입, _check_color_removal은 변경 전 호출, main.py는 변경 메서드를 한 번만 부르고 뒤는 조회·출력뿐
5. main·view·search·tools·data에서 `g._…`·getattr·vars 0건, print는 main·view·tools에만, import는 표준 라이브러리뿐, eval·exec·global·`except:` 0건
6. main이 넘기는 값이 graph·search 전제와 맞음 (성별 "남"/"여", 종류·스타일 상수, int, 새 dict, k는 None 또는 int, ID·날짜 공백은 main이 지움, print_recommendation은 recommend와 같은 k)
7. S1~S4·추천·_check_color_removal·print_group_tree·삭제 확인 건수·check_data 그룹 집계 모두 인접 리스트를 따라감
8. 중복은 승인된 예외(_value_error·정수 검사가 graph·search에 하나씩, W10a)뿐, 그 밖은 R3
9. 항상 통과하는 테스트는 찾지 못함 (약점은 R4)
10. docstring과 동작은 R3 말고 맞음

## 검토자 판정 요약

- 계약 위반, 상태 일부 변경, 운영 모듈의 내부 속성 사용, 인접 관계를 무시한 탐색은 찾지 못했다. 반드시 수정 0건
- 권장 4건은 문구·테스트 품질 수준
- 질문 5건 중 Q3은 W12 기대값 규칙과 직접 이어지므로 손계산 전 판정 권장
- 검토자가 확인하지 않은 것: 터미널에서 직접 누른 Ctrl+C, test_demo의 W12 동작 (범위 밖)
