# Codex 독립 검토 원문 (기준 커밋 9784473, 2026-11-02 02:04)

- 검토자: Codex (찬일이 실행, 읽기 전용 사본 ~/projects/shopgraph_review에서)
- 이 파일은 Codex 출력 원문을 그대로 옮긴 것이다. 링크의 /Users/chan12/projects/shopgraph_review 경로는 검토용 사본이며 지금은 없을 수 있다

---

지금은 W12 준비를 계속할 수 있지만, 시연 검증 완료나 발표 확정으로 넘어가기는 이릅니다. 핵심 구현에서는 재현 가능한 기능 오류를 찾지 못했고, 일반 테스트 131개와 추가 계약 검사 9개가 통과했습니다. 다만 W12 테스트의 실행 전 기대값 확인과 화면 검증에 공백이 있고, 공부 자료와 복잡도 설명에도 수정할 부분이 있습니다. 사람의 시연 기대값 작성·승인과 아래 필수 수정이 먼저입니다.

검토 대상은 /Users/chan12/projects/shopgraph_review, HEAD는 9784473입니다. 원본 48개 파일의 검토 전후 해시가 같고 Git 상태도 깨끗합니다. 모든 실행 실험은 /tmp에서 했습니다. 시연 데이터 대신 호출 즉시 실패하는 data.py를 넣었으며, test_demo.py와 tools/check_data.py는 실행하지 않았습니다. 알려주신 기존 문제는 재지적하지 않았습니다.
1. [반드시 수정] 시연 기대값을 일부만 작성하면, 나머지 기대값 확인보다 시연 실행이 먼저 일어납니다. — 미실행·정적 판정
   [tests/test_demo.py (line 294)](/Users/chan12/projects/shopgraph_review/tests/test_demo.py:294)에서 장면 2는 C_new와 연결 그룹만 확인한 다음, 296줄에서 _run_scenes(2, expected)를 실행합니다. 추천 표와 안내 줄의 빈칸 검사는 299줄에서 호출되는 _check_recommend()의 [229줄 (line 229)](/Users/chan12/projects/shopgraph_review/tests/test_demo.py:229)에서야 합니다.
   따라서 고객 ID와 그룹만 채우고 추천 기대값은 비워 둔 상태에서도 실제 시연 추천이 먼저 계산됩니다. 장면 4·6·7에도 같은 순서가 있습니다. 장면 5는 구매 후 표를 확인하고 장면 4를 실행한 뒤에야 구매 전 표를 확인합니다.
   현재 전부 빈 양식에서 NotImplementedError로 멈추는 것은 정상입니다. 문제는 작성 도중에도 그 보호가 유지되지 않는다는 것입니다. 실행할 장면과 선행 장면에 필요한 기대값을 모두 검사한 후 _run_scenes()에 진입하도록 순서를 바꿔야 합니다.
   안전한 확인 명령: sed -n '291,347p' tests/test_demo.py — 시연 실행 없이 호출 순서만 확인할 수 있습니다.
2. [반드시 수정] W12의 여러 검사가 실제 시연 화면을 검증하지 않습니다. — 미실행·정적 판정
   위치	실제 검사	놓치는 것
   [test_demo.py (line 287)](/Users/chan12/projects/shopgraph_review/tests/test_demo.py:287)	제목 존재 + g.members() 인원	화면에 표시된 그룹별 인원·고객
   [test_demo.py (line 308)](/Users/chan12/projects/shopgraph_review/tests/test_demo.py:308)	products_of()를 다시 호출	장면 3의 S1 표
   [test_demo.py (line 277)](/Users/chan12/projects/shopgraph_review/tests/test_demo.py:277)	group_popular()를 다시 호출	장면 5의 S4 구매 전·후 화면
   [test_demo.py (line 355)](/Users/chan12/projects/shopgraph_review/tests/test_demo.py:355)	g.stats()와 check_integrity() 재호출	화면의 통계 숫자와 최종 판정 문구
   [test_demo.py (line 238)](/Users/chan12/projects/shopgraph_review/tests/test_demo.py:238)	추천 항목 문자열의 개별 포함 여부	화면 순서·중복·추가 항목·근거·색상
   
   
   예를 들어 S1 메뉴가 입력만 받고 표 출력을 생략해도, 현재 장면 3 검사의 핵심 비교는 별도로 호출한 products_of()로 성립합니다. 추천 화면의 순서가 뒤집혀도 항목별 assertIn()은 이를 구별하지 못합니다.
   내부 결과 비교는 유지하되, 승인된 기대 표와 실제 화면의 행·순서·개수도 비교해야 W12를 시연 검증이라고 부를 수 있습니다. 재현 목적으로 시연을 실행하지 않았습니다.
3. [반드시 수정] 안내서가 빈 추천 결과의 조기 종료를 빠뜨렸습니다. — 기존 테스트로 실행 확인
   [code_guide.md (line 111)](/Users/chan12/projects/shopgraph_review/docs/study/code_guide.md:111)는 추천 출력이 머리 줄→항목→안내 줄로 진행되고, 결과 수가 K보다 적으면 넓힘·개수 부족 안내가 나온다고 설명합니다.
   실제 [view.py (line 151)](/Users/chan12/projects/shopgraph_review/view.py:151)는 결과가 비면 “추천할 상품이 없습니다” 한 줄을 출력하고 즉시 반환합니다. 결과가 0개이면 112·113줄의 설명은 적용되지 않습니다. [test_flow.py (line 350)](/Users/chan12/projects/shopgraph_review/tests/test_flow.py:350)에도 이것이 승인 형식이라고 명시돼 있습니다.
   안내서에 “빈 결과는 한 줄 출력 후 종료하며, 아래 안내 규칙은 결과가 있을 때만 적용한다”는 분기가 필요합니다. [code_guide_check.md (line 7)](/Users/chan12/projects/shopgraph_review/docs/study/code_guide_check.md:7)의 “3.4 추천 문제 없음” 판정에도 추가 발견을 연결해 두는 것이 맞습니다.
   재현: python3 -B -m unittest -q tests.test_flow.TestW8bFlow.test_zero_screen → 1개 통과.
4. [반드시 수정] S2의 현재 구현은 계획서에 적힌 O(d log d)와 다릅니다. — 미실행·정적 판정
   [계획서 5.3.2, 278줄 (line 278)](/Users/chan12/projects/shopgraph_review/docs/project_plan.md:278)은 S2를 상품 차수 기준 O(d log d)라고 설명합니다.
   그러나 [search.py (line 238)](/Users/chan12/projects/shopgraph_review/search.py:238)는 상품의 구매 고객마다 group_of()를 호출하고, [graph.py (line 1033)](/Users/chan12/projects/shopgraph_review/graph.py:1033)의 group_of()는 해당 고객의 전체 이웃을 순회합니다.
   색상 수를 작은 상수로 본다는 계획서 전제에서 현재 비용은 다음과 같습니다.
   O(dₚ log dₚ + Σ d꜀) — 합은 해당 상품의 구매 고객들에 대해 계산.
   상품 구매자가 한 명이어도 그 고객의 구매 상품 수가 늘면 추가 순회가 늘어납니다. 현재 코드를 유지한다면 복잡도 표를 고쳐야 합니다. 또는 고정된 그룹 8개의 ID가 고객 인접 집합에 들어 있는지 검사하도록 group_of()를 바꾸면 이 추가 비용을 상수로 만들 수 있습니다.
   [presentation_outline.md (line 51)](/Users/chan12/projects/shopgraph_review/docs/study/presentation_outline.md:51)의 복잡도 질문은 이 표를 근거로 삼으므로 발표 전에 정리해야 합니다.
5. [반드시 수정] 일부 테스트가 명시된 상태 검사 규칙을 빠뜨립니다. — 미실행·정적 판정
   [CLAUDE.md (line 39)](/Users/chan12/projects/shopgraph_review/CLAUDE.md:39)는 실패 입력 테스트에서 전체 snapshot()을 전후 비교하도록 요구합니다. 하지만 다음은 예외 발생만 확인합니다.
   - [test_graph.py (line 81)](/Users/chan12/projects/shopgraph_review/tests/test_graph.py:81), 88줄: 공백뿐인 고객명·상품명 조회.
   - [test_search.py (line 111)](/Users/chan12/projects/shopgraph_review/tests/test_search.py:111): 없는 ID로 S1·S2·S3 호출.
   또한 [test_view.py (line 229)](/Users/chan12/projects/shopgraph_review/tests/test_view.py:229)는 고객을 등록한 뒤 화면만 확인하고 무결성을 검사하지 않습니다. 이는 [계획서 5.3.5, 362줄 (line 362)](/Users/chan12/projects/shopgraph_review/docs/project_plan.md:362)의 “W5 이후 모든 변경 테스트에서 check_integrity() == []” 요구에 빠집니다.
   현재 구현이 상태를 훼손한다는 발견은 아닙니다. 테스트가 약속한 검증을 수행하지 않는 문제입니다. 이 검사를 보강해야 [code_guide.md (line 173)](/Users/chan12/projects/shopgraph_review/docs/study/code_guide.md:173)의 설명도 사실이 됩니다.
6. [권장] 일반 테스트가 놓치는 계약 위반 네 가지를 실제 변형으로 확인했습니다. — 실행 확인
   원본은 바꾸지 않고 /tmp 사본에서 한 번에 한 곳씩 바꿨습니다.
   의도적으로 넣은 오류	관련 코드·계약	기존 131개	추가 검사
   get_purchase()가 복사본 대신 원본 반환	[graph.py (line 900)](/Users/chan12/projects/shopgraph_review/graph.py:900), B.2	전부 통과	실패
   customer_ids()가 정렬 대신 입력 순서 반환	[graph.py (line 914)](/Users/chan12/projects/shopgraph_review/graph.py:914), B.2	전부 통과	실패
   product_ids()가 정렬 대신 입력 순서 반환	[graph.py (line 928)](/Users/chan12/projects/shopgraph_review/graph.py:928), B.2	전부 통과	실패
   10대 그룹 상한을 19→20으로 변경	[graph.py (line 35)](/Users/chan12/projects/shopgraph_review/graph.py:35), 5.2	전부 통과	실패
   
   
   구매 조회 복사 검사는 [test_graph.py (line 195)](/Users/chan12/projects/shopgraph_review/tests/test_graph.py:195)의 기존 반환값 보호 검사에 추가하면 됩니다. 정렬은 고객·상품·구매 기록 입력 순서를 뒤집어서 생성해야 입력 순서 의존을 잡습니다. 나이는 최소한 19/20, 29/30, 39/40 경계를 직접 확인하는 편이 좋습니다.
   현재 구현은 네 항목 모두 올바릅니다. 추가 검사도 원래 구현에서는 통과했습니다. 비교용으로 추천이 구매 ID 카운터를 증가시키는 오류도 넣었는데, 이것은 기존 메뉴 테스트가 잡았습니다.
   재현 스크립트: [audit_mutations.py](/tmp/shopgraph_9784473_audit_6czmsyus/audit_mutations.py), [audit_contracts.py](/tmp/shopgraph_9784473_audit_6czmsyus/audit_contracts.py). 전자는 사본만 바꾸고 각 실험 뒤 복원합니다.
7. [권장] 검증 기록의 수치·분류·작업 주체를 더 정확히 적어야 합니다.
   잘못된 입력 수는 60개와 메뉴 7개를 구분해야 합니다. [w10_g7.md (line 65)](/Users/chan12/projects/shopgraph_review/docs/verification/w10_g7.md:65)와 커밋 4889d53 본문은 메뉴 번호 7개를 포함해 60가지라고 기록합니다. 실제 목록은 CREATE 27개 + READ 등 19개 + UPDATE/DELETE 14개 = 60개, 여기에 [test_flow.py (line 494)](/Users/chan12/projects/shopgraph_review/tests/test_flow.py:494)의 메뉴 오류 7개가 별도로 있습니다. 합계는 67개입니다. AST로 목록 수를 확인했습니다.
   테스트 작성 오류를 결함 기록에서 제외하는 기준이 일관되지 않습니다. [w10_g7.md (line 146)](/Users/chan12/projects/shopgraph_review/docs/verification/w10_g7.md:146)은 기대 오류 수를 6으로 잘못 적은 일을 “테스트 작성 실수”라서 제외합니다. 반면 [defects.md (line 12)](/Users/chan12/projects/shopgraph_review/docs/defects.md:12)의 A02는 테스트 기대값 객체 공유 문제를 포함합니다. 계획서 11.3.9에도 테스트 작성 실수를 일괄 제외한다는 규칙은 없습니다. 별도 하위 분류로 남기거나 집계에서 제외하는 기준을 명시해야 보고서의 결함 수를 해석할 수 있습니다. 미실행·기록 대조 판정입니다.
   “사람이 고른 52곳”은 남은 자료만으로 확인할 수 없습니다. [mutation_sweep.md (line 87)](/Users/chan12/projects/shopgraph_review/docs/verification/mutation_sweep.md:87)은 그렇게 단정하지만, [overnight_log.md (line 115)](/Users/chan12/projects/shopgraph_review/docs/verification/overnight_log.md:115)와 커밋 491ad40에는 사람이 개별 변형을 선정했다는 근거가 없습니다. 판정은 근거 부족입니다. 사람이 선정했다면 해당 기록을 연결하고, AI가 선정했다면 주체를 고쳐야 합니다. 미실행·기록 대조 판정입니다.
8. [권장] 변형 검사 수치의 재현 자료를 보관해야 합니다. — 미실행·기록 대조 판정
   [mutation_sweep.md (line 4)](/Users/chan12/projects/shopgraph_review/docs/verification/mutation_sweep.md:4)에 따르면 실행 스크립트는 표준 입력으로 전달했고 임시 작업 사본은 삭제했습니다. 표에는 변형 설명과 실패 수가 있지만 정확한 패치와 실행 출력은 남아 있지 않습니다.
   따라서 이번 검토에서 기존 “52종 중 49종 검출”을 재현 확인했다고 말할 수는 없습니다. 위에서 확인한 새 변형 결과와 기존 수치는 별개입니다. 다음 검사부터는 기준 커밋·변형 패치·명령·실패 테스트 이름을 함께 남기는 것이 좋습니다.
9. [권장] view.py 모듈 설명도 안내서와 맞추십시오. — 미실행·정적 판정
   [view.py (line 3)](/Users/chan12/projects/shopgraph_review/view.py:3)은 “모든 함수는 print만 하고 None을 돌려준다”고 적습니다. 실제로 _display_width()는 정수, _table_line() 등은 문자열을 반환합니다. [code_guide.md (line 27)](/Users/chan12/projects/shopgraph_review/docs/study/code_guide.md:27)의 공개 함수 4개와 보조 함수 구분이 정확합니다. 모듈 설명에도 같은 구분이 필요합니다.
[동의] 핵심 계약 구현은 현재 확인 범위에서 타당합니다.

검증 후 반영하는 변경 순서, 입력·조회 복사, 실패 뒤 ID 카운터 보존, 재구축 시 카운터 유지, 결정적인 정렬, 추천의 고객별 상한 3·범위별 재계산·좁은 범위 선택 유지·품절 및 이미 산 상품 제외에 대해 재현 가능한 반례를 찾지 못했습니다.

근거는 [graph.py (line 628)](/Users/chan12/projects/shopgraph_review/graph.py:628)의 수정용 복사본, [graph.py (line 740)](/Users/chan12/projects/shopgraph_review/graph.py:740)의 재고 검증과 색상 제거 검사, [graph.py (line 790)](/Users/chan12/projects/shopgraph_review/graph.py:790)의 구매 검증 후 ID 발급, [graph.py (line 1098)](/Users/chan12/projects/shopgraph_review/graph.py:1098)의 재구축, [search.py (line 401)](/Users/chan12/projects/shopgraph_review/search.py:401)의 추천 제어 흐름입니다.

실행 검사에서도 혼합된 유효·무효 수정의 상태 보존, 실패한 등록 뒤 ID, C/P/T ID 한도 실패의 상태 보존, 복사본 보호, 역순 입력의 정렬, 연령 경계가 모두 통과했습니다. 임의의 실행 중단까지 원자성을 증명한 것은 아니며, 여기서 확인한 실패는 계약상의 입력 검증 실패입니다.

print_recommendation(..., k) 등 plan_pending.md에 승인된 변경은 계약 위반으로 취급하지 않았습니다.

[동의] 6장 주요 기대값을 구매 원자료로 검산한 결과는 맞습니다.

아래는 AI가 기록별 색상 수를 세어 계산한 검산입니다. 사람 손계산 완료로 기록하면 안 됩니다. 계산값을 먼저 고정한 뒤 /tmp 검사로 대조했습니다.

여성·20대의 기여는 C01이 P01에 min(4,3)=3, P02에 1; C02가 P02에 2, P03에 1; C03이 P03에 1, P05에 1입니다. 따라서 P02와 P01은 모두 3점이지만 구매자가 2명인 P02가 먼저입니다.
검산 대상	직접 계산한 기대값	대조
S1(C01)	P01: 색상·가중치·기록·총수량 각각 4, 최근 2026-10-01. P02: 각각 1, 최근 2026-09-03	[test_search.py (line 73)](/Users/chan12/projects/shopgraph_review/tests/test_search.py:73)와 일치
S4(G-F-20)	P02 (3점,2명) → P01 (3점,1명) → P03 (2점,2명) → P05 (1점,1명,품절)	[test_search.py (line 142)](/Users/chan12/projects/shopgraph_review/tests/test_search.py:142)와 일치
C07·K=3	P02 → P01 → P03, 모두 같은 그룹. P05 제외	[test_recommend.py (line 125)](/Users/chan12/projects/shopgraph_review/tests/test_recommend.py:125)와 일치
C07·K=4	앞의 세 항목 뒤 P04 (전체,1점,C04)	[test_recommend.py (line 132)](/Users/chan12/projects/shopgraph_review/tests/test_recommend.py:132)와 일치
C02·K=3	구매한 P02·P03 제외. P01 (같은 그룹,3점,C01) → P04 (전체,1점,C04), 2개뿐	[test_recommend.py (line 139)](/Users/chan12/projects/shopgraph_review/tests/test_recommend.py:139)와 일치
C06·K=3	P01 → P04 각각 (같은 성별,1점,C04), 그 뒤 P02 (전체,3점,C01·C02)	[test_recommend.py (line 149)](/Users/chan12/projects/shopgraph_review/tests/test_recommend.py:149)와 일치


C02에서 이미 선택한 P01을 전체 범위의 4점으로 바꾸지 않는 것, C06에서 전체 범위의 3점 상품을 앞의 1점 상품 위로 올리지 않는 것이 핵심입니다. 현재 코드와 기대값 모두 이를 지킵니다.

검토한 일반 테스트에서 무조건 참인 비교만으로 통과하는 사례는 찾지 못했습니다. 추천 테스트는 상품 ID뿐 아니라 범위·점수·지지자·색상을 포함한 딕셔너리를 비교합니다. 다만 [test_flow.py (line 416)](/Users/chan12/projects/shopgraph_review/tests/test_flow.py:416)의 표 기대 문자열은 실제 print_table()로 만듭니다. 이는 메뉴가 전달한 행 값을 검증하는 데 유효하지만, 표 형식 자체의 독립 검증은 test_view.py가 담당한다는 범위를 분명히 해야 합니다.

[동의] 안내서의 나머지 주요 설명·예시는 코드와 맞습니다.

174줄 전체의 문장·표·예시·줄 번호를 대조했습니다. 위에서 지적한 빈 결과 분기와 상태 검사 설명 외에 새로운 줄 번호 오류나 C07 계산 오류는 찾지 못했습니다. 안내서 기준인 491ad40과 현재 9784473 사이에 관련 코드·테스트·계획서 변경이 없어 기준 커밋 차이로 줄 번호가 어긋난 상태도 아닙니다.

원본 세 종류와 그래프의 역할, 간선 집계 한 곳 저장, 색상 수 가중치, 수정 후 재구축, ID 카운터 유지, 공통 구축 코드를 쓰는 무결성 검사의 한계 설명도 타당합니다. 이 부분은 미실행·정적 대조, 앞의 C07 계산은 실행 대조까지 완료했습니다.

[동의] 주요 커밋의 테스트 수는 재현됐고, 독립 검토 여부도 문서 사이에서는 구분돼 있습니다.

각 커밋의 코드와 일반 테스트만 /tmp에 읽어 내어 실행했습니다. 실제 시연 데이터는 어느 버전에서도 사용하지 않았습니다.
단계·커밋	재현한 통과 / 미구현 오류
W2 2ddf4c5	0 / 73
W3 7512238	16 / 58
W4 bfd900c	38 / 38
W5 7839566	55 / 22
W6 f00dcb7	63 / 14
W7 1dd2dfa	67 / 10
W6·W7 보강 6625809	71 / 10
W8 6cb44e0	81 / 0
W8b bead589	94 / 0
W9 76373a9	108 / 0
W10 4889d53	127 / 0
W10a d5b87f8	131 / 0
현재 9784473, 시연 테스트 제외	131 / 0


모두 해당 기록과 일치하며, 그 밖의 실패·오류는 없었습니다. 현재 시연 테스트 8개는 AST로 개수만 확인했습니다. 8개의 NotImplementedError 발생 자체는 이번에 재실행하지 않았습니다.

[report_materials.md (line 35)](/Users/chan12/projects/shopgraph_review/docs/report_materials.md:35)는 W8b의 두 차례 독립 검토와 W9·W10·W10a·W11의 자기 재검토를 구분합니다. 뒤의 통합 검토 역시 [integrated_review.md (line 3)](/Users/chan12/projects/shopgraph_review/docs/verification/integrated_review.md:3)에 별도로 기록돼 있습니다. 문서 간 모순은 찾지 못했지만, 원래 에이전트 대화 기록까지 확인한 것은 아닙니다.

사람 검산과 AI 계산은 특히 다음 구분을 유지해야 합니다.
- [w8b_g6_review.md (line 45)](/Users/chan12/projects/shopgraph_review/docs/verification/w8b_g6_review.md:45)는 추가 기대값 3건을 서브에이전트 계산이며 사람 검산이 아니라고 정확히 표시합니다.
- 커밋 7839566은 W2 제안 기대값 1~15 중 사람이 확인한 것은 대표 3건이고, 나머지는 AI 교차 확인 후 사람 확인 대기라고 적습니다.
- [계획서 6.6 (line 645)](/Users/chan12/projects/shopgraph_review/docs/project_plan.md:645)의 계산 스크립트·시험 구현 검증도 사람 손계산과 같은 증거가 아닙니다. 보관된 24개 테스트 출력은 읽었지만 해당 보조 구현은 미실행입니다.
[권장] 발표 예상 질문에는 다음을 추가하면 좋겠습니다. — 미실행·정적 제안

현재 22개 질문은 설계 이유와 한계를 잘 다룹니다. 다음처럼 값을 실제로 추적하는 질문이 보강되면 코드 이해 여부를 더 잘 확인할 수 있습니다.
추가 질문	근거
같은 색을 다시 구매하거나 수량만 바꾸면 가중치·기록 수·총수량 중 무엇이 바뀌나요?	[graph.py (line 445)](/Users/chan12/projects/shopgraph_review/graph.py:445), 계획서 6.4
같은 고객·상품의 구매 한 건을 지웠을 때 간선이 남는 조건과 최근 구매일 계산은?	[graph.py (line 854)](/Users/chan12/projects/shopgraph_review/graph.py:854), 6.4
set을 쓰면서 실행마다 순서가 같은 이유는? 점수·구매자 수도 같으면 무엇으로 정하나요?	[search.py (line 106)](/Users/chan12/projects/shopgraph_review/search.py:106), 5.3.2
조회 결과를 바꿔 원본을 훼손하지 못하게 어떻게 막았나요? 재고도 따로 복사해야 하는 이유는?	[graph.py (line 884)](/Users/chan12/projects/shopgraph_review/graph.py:884), B.2
S4에는 품절 상품이 나오는데 추천에서는 빠지는 이유는? 추천이 0개면 무엇을 출력하나요?	[search.py (line 283)](/Users/chan12/projects/shopgraph_review/search.py:283), [view.py (line 151)](/Users/chan12/projects/shopgraph_review/view.py:151)
등록 실패·삭제·재구축 뒤 다음 ID는 어떻게 되며, ID 한도에 도달하면 어떻게 되나요?	[graph.py (line 1171)](/Users/chan12/projects/shopgraph_review/graph.py:1171), B.1
종료 후 다시 실행하면 데이터는 유지되나요? 현재 저장 방식의 범위는 어디까지인가요?	[main.py (line 70)](/Users/chan12/projects/shopgraph_review/main.py:70), 계획서 5.6


직접 실행한 검증 명령과 결과는 다음과 같습니다. 실행 작업 디렉터리는 [임시 검토 폴더](/tmp/shopgraph_9784473_audit_6czmsyus)이며, 반복한 읽기 명령은 종류별로 묶었습니다.
명령	결과
git --no-optional-locks rev-parse HEAD, git --no-optional-locks status --short	9784473…, 변경 없음
git log, git show, git ls-tree	커밋 기록 확인 및 과거 파일을 /tmp로 추출
git --no-optional-locks diff --stat 491ad40 9784473 -- graph.py search.py view.py main.py data.py tests docs/project_plan.md	차이 없음
rg --files, rg -n, nl -ba, sed -n	코드·계약·테스트·검토 기록·안내서 대조
python3 -B -m unittest -q tests.test_graph tests.test_search tests.test_recommend tests.test_view tests.test_flow	131개 통과
python3 -B audit_contracts.py	추가 검사 9개 통과
python3 -B audit_mutations.py	기존 테스트가 변형 4개를 놓침, 비교용 1개 검출. 추가 검사는 5개 모두 검출
python3 -B audit_history.py	13개 버전의 테스트 분류 재현, 예상 밖 실패·오류 없음
python3 -B -m unittest -q tests.test_flow.TestW8bFlow.test_zero_screen	1개 통과
Python AST 검사	일반 테스트 131개·시연 테스트 8개, 오류 입력 목록 27+19+14 확인
Python SHA-256 전후 비교	원본 48개 파일 모두 동일, 사본의 변형도 복원됨
python3 --version	Python 3.13.12


시연 장면 1~8, tests/test_demo.py, tools/check_data.py, 시연 데이터 기반 추천·S1·S4·통계 계산은 미실행입니다.

  
2:04 AM