# UI7 G7 자료 (2026-11-07)

검토 구분: Codex 자체 확인. 찬일 승인 대기.

## 범위와 커밋

- 시작 상태: ui7, HEAD 24043b8, 작업 트리 깨끗함. CLAUDE.md 전체를 읽고 시작했다.
- 계약 커밋: `77fb665 [SPEC][UI7] 요청 JSON 오류 문구 기대값에서 이중 접두사 제거`. tests/test_web_write.py의 기대값 두 줄만 변경했다. 근거는 A12, ui0_design.md 3.3, 찬일 11/07 판정이다.
- 구현 커밋 제목: `[UI7] 요청 JSON 오류 문구 정리 + 서버 연결 실패 한국어 안내`. 이 문서와 함께 커밋한다. 자기 커밋 해시를 그 커밋 본문 파일 안에 넣을 수 없으므로 구현 해시는 완료 보고로 제공하며, `git log -1 --format=%h -- web.py`로 조회할 수 있다.
- 변경 파일: web.py, frontend/src/App.tsx, tests/test_web_write.py(새 테스트 1개 추가만), frontend/dist/index.html·해시 JS 교체, docs/defects.md, 이 문서.
- graph.py·search.py·view.py·main.py·data.py·docs/demo_expected.md·docs/project_plan.md·CLAUDE.md·README.md 변경 0. package.json·package-lock.json 변경 0. 패키지 설치·추가·버전 변경 없음.

## 동작과 회귀 보호

web.py는 이미 `요청 JSON:`으로 시작하는 해독 단계 ValueError만 그대로 400으로 반환한다. UnicodeDecodeError·JSONDecodeError의 기존 접두사 경로는 유지했다. 새 테스트는 `{"name":` 문법 오류의 기존 문구와 400, 원본·그래프·다음 ID를 포함한 snapshot 전체 불변을 실제 HTTP로 확인한다. 기존 테스트에서 두 기대값 이외 변경·삭제는 없다.

프런트는 fetch 자체의 실패만 한국어 안내로 바꾼다. AbortSignal 또는 AbortError 취소는 그대로 전달하며, 기존 호출부의 aborted 검사는 유지했다. response.json·response.ok·payload.error 처리는 try/catch 밖의 기존 코드 그대로다. 점수·품절·범위 등 업무 계산은 추가하지 않았다.

## Python 실행 결과

시작 전 `python3 -B -m unittest`:

```text
Ran 189 tests in 11.589s
OK
```

계약 커밋 직전 같은 전체 명령:

```text
Ran 189 tests in 11.599s
FAILED (failures=4)
```

분류: 통과 187 / 미도래 0 / 실패 2(테스트 메서드 기준). 지정된 test_stock_nested_duplicate_key_is_rejected 1건과 test_nonfinite_json_numbers_are_rejected의 NaN·Infinity·-Infinity subTest 3건이 실패했다. unittest의 failures=4를 테스트 메서드 4개로 세지 않는다. 운영 코드는 이 커밋에서 변경하지 않았다.

추가한 test_malformed_json_keeps_original_decode_error를 구현 변경 전에 단독 실행:

```text
Ran 1 test in 0.504s
OK
```

기존 JSON 문법 오류 경로가 이미 처리하므로 통과하는 테스트다. 아래 M02가 이 경로를 깨뜨리면 실패함을 확인했다.

수정 후 위 세 테스트를 `python3 -B -m unittest tests.test_web_write.TestUI2WebWriteAPI.test_stock_nested_duplicate_key_is_rejected tests.test_web_write.TestUI2WebWriteAPI.test_nonfinite_json_numbers_are_rejected tests.test_web_write.TestUI2WebWriteAPI.test_malformed_json_keeps_original_decode_error -v`로 실행:

```text
Ran 3 tests in 1.511s
OK
```

수정 후 전체 `python3 -B -m unittest`:

```text
Ran 190 tests in 13.594s
OK
```

분류: 통과 190 / 미도래 0 / 실패 0. RuntimeError: after C07 출력은 기존 500 처리 고장 주입 테스트의 진단 로그이며 테스트 실패가 아니다.

## 프런트 빌드와 dist

Node `v25.8.1`. 기존 node_modules를 사용해 frontend에서 `npm run typecheck && npm run build`를 실행했다. 설치 명령은 실행하지 않았다.

```text
> shopgraph-web@0.0.0 typecheck
> tsc --noEmit

> shopgraph-web@0.0.0 build
> vite build

vite v8.3.4 building client environment for production...
transforming...
✓ 16 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.39 kB │ gzip:  0.26 kB
dist/assets/index-R21ijBvg.css   12.15 kB │ gzip:  3.37 kB
dist/assets/index-CmKnIgzh.js   242.27 kB │ gzip: 75.63 kB
✓ built in 128ms
```

새 dist 파일 전체 목록과 SHA-256(`shasum -a 256 frontend/dist/index.html frontend/dist/assets/*`):

```text
185d81ca6e0dbdaabb57743e2e3d4d11f9844c879eb61b96260eb40d6f815635  frontend/dist/index.html
7293bba6a9202151c85d704401b53d63eb7656c477fa117a40d620464efa4f07  frontend/dist/assets/index-CmKnIgzh.js
f4f0d2359f2c38f6c72494c776c49a7d2f28728fb941d6acf7a7e48f7433851a  frontend/dist/assets/index-R21ijBvg.css
```

기존 index-DiXcA22x.js는 빌드가 교체했다. CSS는 변경되지 않았다. 짝수 LTS 재빌드는 이번 범위에서 미실행이다.

## 실제 브라우저 확인

Chrome/157.0.8103.38(headless Chromium), 1440×900. Python 운영 진입점 `python3 -u -B main.py --web --port 0`으로 실행했다. 사람 수동 확인이 아닌 Codex 자체 확인이다.

- 요청 취소: CDP로 C01 상세·추천 2요청을 대기시키고, 같은 고객 화면에서 C02를 선택해 취소시켰다. C02 상세·추천이 정상 표시되고 role=alert 0개였다.
- 서버 응답: 상품 재고 -1 요청의 실제 400 응답이 `재고: 0 이상이어야 합니다 (입력: -1)` 원문 그대로 표시됐다.
- 연결 실패: 그래프 화면으로 이동해 서버를 SIGINT로 종료하고, 상품 상세를 선택했다. `서버에 연결할 수 없습니다. 터미널에서 서버(python3 main.py --web)가 켜져 있는지 확인하세요` 원문과 일치했다. Failed to fetch 표시는 없었다. 화면 캡처도 열어 확인했다.
- JavaScript 런타임 예외 0건. 서버와 브라우저 프로세스는 종료 처리했다.

실행: `node /tmp/shopgraph-ui7-qfH1lN/network_check.mjs /Users/chan12/projects/shopgraph /tmp/shopgraph-ui7-qfH1lN/network_result`. 캡처와 보고서는 같은 임시 경로의 network_result.png·network_result.json이다. 최초 검사는 이미 취소된 요청의 CDP interception ID를 다시 해제하려다 Invalid InterceptionId로 중단됐다. 임시 검사 코드에서 이 특정 응답만 '이미 취소됨'으로 기록하도록 고친 뒤 재실행해 위 결과를 얻었다. 제품 코드는 이 보정으로 변경하지 않았다.

기존 UI5 검사도 실행했다. 저장소 밖 `/tmp/shopgraph-ui7-qfH1lN/base`에 git archive HEAD 사본을 만들고 현재 web.py·테스트·App.tsx·dist를 복사한 뒤, 그 폴더에서 원본 그대로 `node docs/verification/ui5_browser_check.mjs`를 실행했다. cmp로 현재 web.py·App.tsx와 실행 사본의 일치를 확인했다. 기존 저장소의 UI5 캡처·결과 파일은 변경하지 않았다.

```text
PASS 장면 1: 01_groups.png / 그룹 8개 인원 전체
PASS 장면 2: 02_registered_recommendation.png / C_new ID·추천 3항목 전체·안내 없음
PASS 장면 3: 03a_purchase_s1.png / 구매 가중치 1→2·S1 색상/가중치
PASS 장면 3: 03b_graph_weight2.png / 선택 정보 이웃 이름·관계·가중치 2
PASS 장면 4: 04_recommend_again.png / 기구매 P_top 제외·추천 전체
PASS 장면 5: 05a_popular_before.png / S4 구매 전 9항목·점수·구매자·상태
PASS 장면 5: 05b_popular_after.png / S4 전 고정·구매 후 9항목·순위 변화
PASS 장면 6: 06a_before_stock.png / 품절 전 P_top6 1위·색상 수 안내 포함 추천 전체
PASS 장면 6: 06b_zero_stock.png / 모든 기존 색상 재고 0·품절·C_new 추천 복귀 버튼
PASS 장면 6: 06c_after_stock.png / 품절 후 P_top6 제외·다음 후보 포함 추천 전체
PASS 장면 7: 07_widen_gender.png / 남성 전체 3항목·점수/지지자/색상·넓힘 안내 원문
PASS 장면 8: 08_integrity.png / 통계 6항목·위반 수
PASS 장면 1~8 전체 대조 / 외부 네트워크 0 / 브라우저 예외 0
```

## 고장 주입 자체 확인

정상 사본 base를 별도 m1·m2로 복사하고 apply_patch로 각 사본의 web.py만 바꿨다. 실제 저장소에는 고장을 주입하지 않았다.

| 고장 | 실제 변형 | 실행 테스트 | 결과 |
|---|---|---|---|
| M01 | startswith 조건과 그대로 반환하는 두 줄 삭제, 기존 이중 접두사로 복귀 | 중복 키·비유한 숫자 두 테스트 | 종료 코드 1, Ran 2 tests in 1.012s, FAILED (failures=4). 두 메서드 모두 검출(숫자 subTest 3개 포함) |
| M02 | 나머지 해독 오류도 str(error)만 반환해 기존 접두사 삭제 | 새 문법 오류 테스트 | 종료 코드 1, Ran 1 test in 0.505s, FAILED (failures=1). 기존 접두사 누락 검출 |

M01 실행 폴더는 `/tmp/shopgraph-ui7-qfH1lN/m1`, 명령은 위 수정 후 세 테스트 명령에서 마지막 문법 오류 테스트를 뺀 것이다. M02 실행 폴더는 `/tmp/shopgraph-ui7-qfH1lN/m2`, 명령은 `python3 -B -m unittest tests.test_web_write.TestUI2WebWriteAPI.test_malformed_json_keeps_original_decode_error -v`다. 모두 AssertionError로 검출했고 실행 오류(ERROR)는 없었다. 정상 저장소의 대상 3개 테스트는 통과했다.

## 이해 질문(기록만)

1. 예측: 고객 선택으로 이전 요청을 취소한 경우와 서버가 꺼진 경우, 화면 안내는 각각 어떻게 달라져야 하나?
2. 원인: 중복 키 오류와 JSON 문법 오류에 동일한 문구 처리를 적용하면 어느 테스트가 왜 실패할까?
3. 설명: fetch 실패만 처리하는 try/catch 밖에 response.ok·payload.error 처리를 두는 이유를 설명해 보자.
