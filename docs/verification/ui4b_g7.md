# UI4b G7 자료

- 작업일: 2026-11-03. 승인자: 찬일. 기준 커밋: UI4 `111591e`.
- G1: 찬일의 UI4b 지시 0~6을 화면 표시·입력·화면 이동으로 반영한다. Python 계산·API·기존 기대값·직접 의존성은 변경하지 않는다.
- G2/G4: 실제 Chromium의 DOM·HTTP 응답·노드 좌표·화면 이동을 검사하는 `ui4b_browser_check.mjs`를 추가했다. 개발 중 검사 실패(그래프 세로 스크롤)를 확인하고 여백·SVG 높이를 보정했다. 이 검사는 UI5 장면 1~8의 기대값 검증이 아니다.
- G3: `frontend/src/App.tsx`, `styles.css`, `frontend/dist/`와 검증 기록·캡처 변경.
- G5/G6: Codex 자체 재검토. 독립 검토가 아니다. Claude의 선행 검토는 UI4 캡처 검토이며 이번 구현의 독립 실행 확인으로 기록하지 않는다.
- G7: UI4b 구현·검증 완료 자료 제출. UI5는 미착수.
- G8: `[UI4b]` 커밋으로 구현·dist·기록·캡처를 함께 보관한다. push·main 합치기 없음.

## 요구사항별 확인

| 항목 | 반영 및 실제 확인 |
|---|---|
| 바닥 안내 | `저장하지 않음 · 서버를 다시 켜면 처음 상태`로 교체. DOM 원문 비교 통과 |
| 그래프 한 화면 | SVG viewBox 1120×516, 열별 노드 수에 따른 좌표·행 간격·원 크기·글자 크기. 1440×900에서 전체 노드의 원이 SVG 경계 안이고 `documentElement.scrollHeight == 900`인 것을 실제 측정 |
| 그래프 수 | 현재 초기 데이터는 그룹 8+고객 30+상품 22=60노드다. C31을 화면에서 등록한 뒤 61노드 전체를 확인했다. 요청의 54개를 고정 상수로 사용하지 않았다 |
| 그래프 열·라벨 | viewBox 안 배경과 각 열 좌표를 함께 구성. 그룹 왼쪽 여백 26 좌표, 원 오른쪽에 그룹 label 또는 고객·상품 ID+짧은 이름. 긴 이름은 title/선택 정보에서 전체 표시 |
| 간선·선택 | 소속 회색 점선·구매 파란 실선, 굵기는 서버 weight 그대로. 범례·선택 해제 제공. 기본 간선은 옅게, 선택 노드와 이웃/직접 연결 간선만 강조. C31 선택 시 강조 노드 2개·소속 간선 1개, 나머지는 흐리게인 것을 DOM 확인 |
| 고객 상세 | 콘솔 원문은 닫힌 details로 제공하며 펼치기 동작 확인. 범위 코드를 CSS 색상에만 대응하고 이름은 서버 scope_label 사용. notices 원문 배열을 목록 위 안내 상자에 표시하고 HTTP 원문과 비교. 고객 요약의 성별 중복 제거 |
| S4 막대·목록 | 최대 응답 점수를 차트 너비로 바꾸는 좌표 변환만 사용. 항목 수에 따라 viewBox/높이 증가. 모든 응답 항목의 SVG 행 수와 목록 행 수 일치, 최대 막대 너비 464 좌표 확인. 목록에 점수·구매자 수·상태 표시 |
| S4 비교 | 버튼으로 현재 응답을 '전'으로 보관. 탭 이동·구매 후 재진입에서도 보존, 이후 조회는 '후'만 교체. 두 배열에서 같은 상품의 순번이 다를 때만 주황색 강조. 그룹과 개수 변경 각각 비교 해제 확인 |
| 한국어 통계 | 그룹 노드·고객 노드·상품 노드·소속 간선·구매 간선·구매 기록. main.py의 통계 라벨과 대조하고 DOM 6항목 원문 검사 |
| 구매 입력 | 고객은 서버 그래프 고객 목록 select, 마지막 등록 C31 자동 선택. 상품별 GET product.stock의 모든 키를 색상 select로 사용(재고 0도 포함). 실제 옵션과 서버 키 전체 일치 확인 |
| 재고 → 추천 | PUT 응답에는 S2가 없으므로 GET 상품 상세로 재조회. 성공 상자에 마지막으로 본 고객 이름·ID의 추천 복귀 버튼. 실제 품절 저장 → 해당 고객으로 복귀 → 새 추천 GET 및 화면 확인. 예외 0건 |

변경 중 요청 버튼은 비활성화하고, 느린 이전 GET은 AbortController로 폐기한다. 고객 등록 후 추천은 별도 GET을 유지했다. S4 전 상태를 포함한 화면 상태는 React에서만 보관하며 서버 계산 결과를 수정하지 않는다.

## 실행 결과

전체 Python 회귀(승인된 test_demo 포함):

```text
$ python3 -B -m unittest -v
Ran 163 tests in 6.686s

OK
```

분류: **통과 163 / 미도래 0 / 실패 0**. 커밋 직전 전체 원문은 실행 시 `/tmp/shopgraph-ui4b-unittest-final.log`에 보관했다. 고장 주입 테스트의 의도된 `RuntimeError: after C07` 로깅은 실패가 아니다. 기존 테스트·기대값 수정 없음.

타입 검사·빌드 원문(고정 버전 유지):

```text
$ npm run typecheck

> shopgraph-web@0.0.0 typecheck
> tsc --noEmit

$ npm run build

> shopgraph-web@0.0.0 build
> vite build

vite v8.3.4 building client environment for production...
transforming...
✓ 16 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.39 kB │ gzip:  0.26 kB
dist/assets/index-Bb8d13ZX.css    7.02 kB │ gzip:  2.40 kB
dist/assets/index-BhGfTfEb.js   238.80 kB │ gzip: 74.48 kB

✓ built in 53ms
```

처음 타입 검사에서 통계 응답 nullable 값의 콜백 참조 오류가 발생해 지역 변수로 좁힌 뒤 통과했다. 패키지 버전 변경·추가 설치 없음. Node `v25.8.1`; 찬일 결정에 따라 짝수 LTS의 npm ci·build 재현 확인은 UI5 마지막에 수행 예정이며 이번에는 미실행.

실제 브라우저 검사 원문:

```text
$ node docs/verification/ui4b_browser_check.mjs
browser Chrome/156.0.8078.74
PASS customer POST -> separate recommendations GET
graph measurements {"count":61,"viewport":[1440,900],"scrollHeight":900,"circlesInside":true,"labelsRight":true,"restEdges":130,"activeEdges":0}
PASS graph layout {"count":61,"viewport":[1440,900],"scrollHeight":900,"circlesInside":true,"labelsRight":true,"restEdges":130,"activeEdges":0}
capture 01_graph_overview.png
capture 02_graph_C31.png
capture 03_customer_mixed_scopes.png
PASS mixed badges, notices before cards, console collapsed/expand
PASS server customer/color options and last registration selection
capture 04_popular_before_after.png
PASS frozen before, changed ranks, full chart rows, max width, filter reset
PASS stock save -> last viewed customer -> fresh recommendations; no render exception
capture 05_integrity.png
PASS external HTTP resources=0; browser exceptions=0
PASS all UI4b browser checks; UI5 scene sequence not run
```

스크립트는 새 Python 서버(port=0)와 임시 프로필 Chrome을 띄우며 finally에서 둘 다 종료한다. Node 내장 fetch/WebSocket만 사용한다. Chrome 실행 경로가 다르면 `CHROME_BIN`을 지정한다. 기대값 계산을 새로 하거나 demo_expected를 수정하지 않았다.

## 원칙 재확인

```text
$ rg -n -i 'https?://|cdn|@import|url\(' frontend/src frontend/index.html
일치 0건
$ rg -n 'sort\(|WEIGHT_CAP|Math\.min\([^\n]*score|score\s*\+=' frontend/src
일치 0건
$ git diff -- frontend/package.json frontend/package-lock.json graph.py search.py view.py main.py web.py
변경 없음
```

grep만으로 판단하지 않고 TS의 score·scope·stock·notice 참조 전체를 코드 대조했다. 계산 관련 TS 산술은 **SVG 좌표·원/문자 크기, 서버 score/maxScore를 너비로 변환, 두 응답에서의 상품 배열 순번 비교**뿐이다. 추천 점수·상한·순위 정렬·품절·범위 확장·안내 문구 조건은 Python 응답 그대로다. notices 배열의 빈 여부 검사는 화면 상자 존재 여부만 정한다. scope 코드는 배지 색상 선택에만 쓰며 표시 문구를 재조합하지 않는다.

직접 의존 6개 및 lockfile 변경 없음. 런타임 Network 이벤트에서도 외부 HTTP 리소스 요청 0건. 번들에 포함된 React 오류 도움말 URL과 SVG namespace는 외부 리소스 로드가 아니다.

## 캡처

`docs/verification/ui4b_screens/`에 실제 Chrome 렌더링 PNG 5장을 보관했다.

| 파일 | 상태 |
|---|---|
| `01_graph_overview.png` | C31 등록 뒤 전체 61노드, 선택 전, 1440×900 |
| `02_graph_C31.png` | C31 및 소속 그룹·간선만 강조, 1440×900 |
| `03_customer_mixed_scopes.png` | C01, 같은 그룹/여성 전체 배지·안내 상자·접힌 콘솔 블록, 전체 페이지 |
| `04_popular_before_after.png` | S4 '전' 고정 뒤 별도 구매 2건, '후'에서 순번 변경 상품 강조, 전체 페이지 |
| `05_integrity.png` | 한국어 통계 6항목·무결성 결과, 1440×900 |

캡처 상태는 **UI4b 개별 동작 점검용**이다. C31(화면확인, 여, 25) 등록, C31→P07 색상 2개 구매, C01 추천 상품 재고 저장을 사용했으며 장면 1~8의 진행 상태·기대값 검증 자료로 쓰지 않는다. 사람이 직접 실행했다고 기록하지 않는다. Codex가 실행하고 캡처를 직접 확인했다.

## 이해 질문(기록만)

1. 시연에서 S4 비교를 마친 뒤 '전'을 새 시점으로 고정할 때, 현재 버튼으로 다시 고정하는 조작을 발표 순서에 적을 것인가?
2. 긴 지지자 근거 줄을 설명할 때 콘솔 출력을 펼칠 것인가, 기본 카드의 원문 근거 줄만 사용할 것인가?
3. UI5 마지막 LTS 재현 확인에 사용할 짝수 LTS 버전과 시연 PC의 Chrome/Edge 버전은 무엇인가?

미정 사항으로 구현을 막은 항목 없음. UI4b 자료 제출 후 멈추며 UI5 착수는 찬일 지시를 기다린다.
