# Design C 검토 자료 — "구매 장부"

- 작업일: 2026-11-03. 승인자: 찬일. 브랜치: `web-design-c`(git worktree `~/projects/shopgraph_design_c`), 시작점 `78ac972` [UI5].
- 성격: 다른 디자인안과 비교하려고 만든 **디자인 전용 C안**이다. 채택되지 않을 수 있다.
- 작성: Claude(이 세션). 아래 검토는 같은 대화 안의 자기 점검이며 **독립 검토가 아니다**. 사람이 직접 실행한 결과도 아니다.
- 기대값의 출처는 `docs/demo_expected.md`(찬일 승인) 하나다. 실행 결과를 보고 기대값을 옮겨 적지 않았다.

## 1. 바꾼 범위

| 파일 | 내용 |
|---|---|
| `frontend/src/App.tsx` | 마크업·클래스, 그래프 그리는 방식(칩 모양 노드·곡선 간선·선택 시 가중치 표시), S4 막대를 HTML 막대로 변경, 좌측 레일 배치 |
| `frontend/src/styles.css` | 전체 새로 작성(색 체계·글자 크기·여백) |
| `frontend/dist/` | 위 소스로 다시 빌드 |
| `docs/verification/design_c_browser_check.mjs` | `ui5_browser_check.mjs` 사본. 캡처 폴더·포트(8011)·결과 파일 이름만 바꾸고, 그래프 배치 측정 `checkGraph`를 더했다 |
| `docs/verification/design_c_browser_results.json`, `design_c_screens/*.png`, 이 문서 | 실행 결과와 기록 |

바꾸지 않은 것(확인 방법 포함):

- `web.py`·Python 전부, `tests/`, `docs/demo_expected.md`, 계획서, CLAUDE.md: `git diff --stat`에 나오지 않는다.
- `frontend/package.json`·`package-lock.json`: 변경 없음. 직접 의존 6개 그대로, 추가 설치 없음.
- API 호출 경로·메서드·본문, `useApi`·AbortController, 상태(`useState`) 구성, 화면 이동 함수: diff에서 상태·핸들러가 들어 있는 줄은 들여쓰기만 바뀌었다.
- 버튼 동작: S4 "지금을 '전'으로 고정"·"비교 해제"·그룹/개수 변경 시 비교 해제, 장면 6 재고 저장 뒤 "○○(C31) 고객 추천 다시 보기", 고객·상품·색상 선택 상자는 그대로다. 버튼 글자도 그대로 두었다.

응답을 쓰는 방식에서 바뀐 점 하나(판단 필요):

- S4 품절 막대와 상품 상세의 품절 배지 색을 정할 때 서버가 이미 보내는 `sold_out` 불리언을 읽는다. `ProductDetail.sold_out`은 원래 타입에 있었다. `PopularItem`에는 타입 선언만 `sold_out: boolean`으로 추가했다(API 계약 3.1의 PopularItem에 있는 필드). 계산은 하지 않고 CSS 클래스만 고른다. 이것도 "응답 사용 방식 변경"으로 본다면 `status_label` 문자열로 고르는 방식으로 되돌릴 수 있다.

## 2. 디자인 의도

장부 종이 바탕에 먹색 레일을 둔 "구매 장부" 인상이다. 장식은 노드 모양(사각·알약·가격표)과 레일의 번호 칸 정도로 줄였다. 화면 대부분은 그래프에 썼다.

### 2.1 색 체계 — 색 하나에 뜻 하나

대비는 WCAG 공식으로 계산했다(괄호 안은 글자색:배경 대비).

| 뜻 | 색 | 쓰는 곳 | 대비 |
|---|---|---|---|
| 범위: 같은 그룹 | 초록 `#246b35` / 배경 `#e3f1e3` | 추천 카드 왼쪽 띠·범위 배지 | 5.6:1 |
| 범위: 성별 전체(여성/남성 전체) | 청록 `#0b6f80` / 배경 `#dcf0f3` | 같음 | 4.9:1 |
| 범위: 전체 고객 | 보라 `#6741d9` / 배경 `#ece6fc` | 같음 | 5.2:1 |
| 소속 간선 | 흙회색 `#736a5b`, 점선 | 그래프 소속 간선·범례 | 종이 위 4.8:1, 카드 위 5.2:1 |
| 구매 간선 | 코발트 `#2f54d0`, 실선, 굵기 = 서버 weight(px) | 그래프 구매 간선·선택 시 "가중치 n"·범례 | 6.3:1 |
| 품절 | 빨강 `#c92a2a` | 상품 상세 "품절" 배지(흰 글자 5.5:1), S4 품절 막대(빗금)·글자 | 5.4:1 |
| 순위 변경 | 주황 `#c2410c`(글자) / `#f0781e`(막대) | S4 전·후에서 순번이 다른 상품 | 5.1:1 |
| 선택 강조 | 형광 노랑 `#ffd43b`(선택 칩) / `#fff1b8`(이웃 칩) | 그래프 선택 노드·이웃, 선택 정보 띠 | 먹색 글자 11.7:1 / 14.7:1 |
| 주요 동작 | 먹색 `#1d1e22`(바탕 흰 글자) | 모든 버튼·현재 탭·포커스 테두리 | 16.4:1 |
| 바탕·본문 | 종이 `#f6f2ea`, 카드 `#fffdf8`, 먹 `#1d1e22` | 뜻 없음 | 본문 16.4:1, 보조 글자 `#5f5a51` 6.1:1 |

- 노드 종류(그룹·고객·상품)는 색 대신 **모양**으로 구별한다. 색 뜻이 겹치지 않게 하려는 것이다.
- 오류·성공 상자와 무결성 결과도 색을 쓰지 않는다. 먹색 테두리와 기호(⚠·✓·✕)로 표시한다. 초록은 "같은 그룹", 빨강은 "품절"에만 남겨 두었다.
- 품절과 순위 변경은 색만으로 구별하지 않고 글자("품절", "순위 변경 · 전 4위")와 빗금을 함께 쓴다.

### 2.2 글자

- 외부 글꼴 없이 시스템 글꼴만 쓴다: `system-ui, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif`. ID·숫자는 `ui-monospace, "SF Mono", Menlo, Consolas`.
- 기본 15px, 가장 작은 본문 글자 14.25px(.95rem), 제목 h2 21.75px.
- 그래프(1440×900에서 viewBox와 화면이 1:1): 그룹·상품 칩 14px, 고객 칩 13px, 열 제목 15px, 간선 안내 13px, 선택 시 가중치 표시 12px.
- 실측(브라우저, 선택 전): 본문 최소 **14.25px**, 그래프 최소 **13px**. 가중치 표시 12px는 선택 뒤에만 나오며 CSS 값이다(따로 측정하지 않음).

### 2.3 그래프 표현

- 3열 배치: 그룹(왼쪽) — 고객(가운데) — 상품(오른쪽). 각 열은 서버 배열 순서 그대로 위에서 아래로 놓는다. 재정렬하지 않는다.
- 노드는 이름이 들어간 **칩**이다. 그룹은 사각 칩(오른쪽에 서버 인원 "8명"), 고객은 알약 칩(`C01 봄비`), 상품은 가격표 모양 칩(`P03 와이드 슬랙스`).
- 간선은 칩 옆면끼리 잇는 S자 곡선이다. 소속 간선은 그룹 칩 오른쪽에서 고객 칩 왼쪽으로, 구매 간선은 고객 칩 오른쪽에서 상품 칩 왼쪽으로 간다. 그래서 **간선이 글자를 가리지 않는다**. 구매 간선 칸(약 420px)을 가장 넓게 두어 구매 관계가 가장 잘 보이게 했다.
- 그룹 칩은 소속 고객 칩 y좌표의 평균에 놓는다(UI4c와 같은 좌표 변환). 빈 그룹은 다른 그룹 칩과 40 이상 떨어진 빈자리에 서버 순서대로 놓는다.
- 선택하지 않은 상태: 모든 칩과 글자가 불투명도 1이다. 간선만 반투명(구매 0.4, 소속 0.75)이다.
- 칩을 누르면: 선택 칩은 노랑, 이웃 칩은 연노랑이 된다. 연결 간선은 진하게, 나머지 칩은 0.3, 나머지 간선은 0.07로 흐려진다. 연결된 구매 간선마다 선택하지 않은 쪽 칩 옆에 "가중치 n"(서버 weight)을 붙인다. 장면 3에서 C31을 누르면 P03 옆에 "가중치 2"가 보인다.
- 상단 범례에 가중치 1·2·3·4 굵기 견본, 그래프 머리줄에 "소속 간선"·"구매 간선 · 굵기 = 가중치" 안내를 두었다.
- 화면 공유를 고려해 상단 머리 대신 좌측 레일(216px)에 메뉴를 두고, 세로 공간을 그래프에 썼다.

### 2.4 다른 화면

- 고객 상세: 추천 카드 왼쪽 띠와 배지를 범위 색으로 칠했다. 큰 순번 숫자, 점수·구매 고객 수는 굵은 숫자로 표시한다. 근거·구매 가능 색상·콘솔 원문은 서버 문자열 그대로다.
- 그룹 인기 S4: 한 행에 상품명 / 막대+점수 / `P03 · 점수 11 · 구매자 8명 · 판매 중`을 두 줄로 넣어 9행 비교가 1440×900 한 화면에 들어간다. 순번이 다르면 주황과 "순위 변경 · 전 n위"(또는 "후 n위")로 표시한다.
- 상품 상세: 품절 배지 빨강, S2 구매 고객 장부 줄, 재고 수정 폼은 그대로다.
- 무결성: 통계 6항목을 한 줄 6칸 숫자로, 결과는 먹색 테두리와 ✓로 표시한다.

## 3. 확인 결과

### 3.1 빌드

```text
$ (cd frontend && npm ci && npm run typecheck && npm run build)
added 24 packages, and audited 25 packages in 544ms
found 0 vulnerabilities
> tsc --noEmit
vite v8.3.4 building client environment for production...
✓ 16 modules transformed.
dist/index.html                   0.39 kB │ gzip:  0.26 kB
dist/assets/index-B6Bj6H_a.css   12.20 kB │ gzip:  3.39 kB
dist/assets/index-1DVqppCK.js   242.44 kB │ gzip: 75.60 kB
✓ built in 205ms
```

종료 코드 0. dist의 이전 자산(`index-DiRU8-w6.css`, `index-DqtovMSA.js`)은 지워지고 위 두 파일로 바뀌었다. Node `v25.8.1`(짝수 LTS 재현은 UI5와 같이 미실행).

### 3.2 Python 전체 테스트

```text
$ python3 -B -m unittest -v
Ran 174 tests in 7.274s

OK
```

분류: **통과 174 / 미도래 0 / 실패 0**. 이 가운데 `tests.test_web_demo` 11개(시연 8 + 보호 3) 모두 통과. 최종 dist로 빌드한 뒤 다시 실행한 결과다.

### 3.3 실제 브라우저 시연

- 실행: `node docs/verification/design_c_browser_check.mjs`. 스크립트가 `python3 -u -B main.py --web --port 8011`을 띄운다(원래 폴더 서버와 겹치지 않게 8011). 자동 열기만 `BROWSER=/usr/bin/true`로 막았다.
- 브라우저: Chrome/156.0.8078.74(headless, 임시 프로필), viewport 1440×900, deviceScaleFactor 1.
- 기대값: 서버를 만들기 전에 `tests/demo_expected_adapter.browser_expected()`로 `demo_expected.md`에서 읽는다(승인 줄·8장면 양식 검사 포함). DOM에서 읽은 추천·S1·S4·통계를 그 값과 `assert.deepEqual`로 비교한 뒤 캡처한다.
- 입력: `w11_scenes.md` 순서와 값 그대로(하람/여/25, C31·P03 블랙 10/30·베이지 10/31, C09·P07 블랙·그레이 10/30·네이비 10/31, P07 4색 모두 0, 새싹/남/15).
- 그래프 배치 측정(`checkGraph`, 선택 전):

```text
PASS 배치 장면 1 선택 없음: {"nodes":60,"api_nodes":60,"viewport":[1440,900],"scrollHeight":900,"scrollWidth":1440,"outside":[],"graphMinFont":13,"bodyMinFont":14.25,"dimWithoutSelection":0}
PASS 배치 장면 3 C_new 등록 뒤 선택 전: {"nodes":61,"api_nodes":61,"viewport":[1440,900],"scrollHeight":900,"scrollWidth":1440,"outside":[],"graphMinFont":13,"bodyMinFont":14.25,"dimWithoutSelection":0}
```

61노드(서버 stats의 그룹+고객+상품과 같음)가 모두 SVG 안에 있고 세로·가로 스크롤이 없다. 선택하지 않았을 때 흐린 노드는 0개다.

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

### 3.4 캡처와 demo_expected 대조

모든 파일은 `docs/verification/design_c_screens/`에 있고, `ui5_screens`와 같은 장면·같은 순간·같은 파일 이름이다. 12장 모두 1440×900이다(C안은 모든 장면이 한 화면에 들어가 전체 페이지 캡처도 900px 높이). 아래는 스크립트의 DOM 비교와 별도로 Claude가 캡처 12장을 직접 보고 demo_expected 값과 대조한 결과다. 새 기대값의 출처가 아니다.

| 장면 | 파일 | demo_expected 대조 |
|---|---|---|
| 1 | 01_groups.png | 그룹 칩 인원 여성 10대 3·20대 8·30대 5·40대 이상 2, 남성 10대 0·20대 6·30대 4·40대 이상 2. 일치. 선택 전 60노드 전부 진한 글자 |
| 2 | 02_registered_recommendation.png | 하람(C31), 여성·20대. P03 9점/7명 → P01 7/3 → P05 6/5, 모두 같은 그룹. 지지자·구매 가능 색상·색상 수 안내(C05는 2가지, C08은 2가지 / C04는 4가지, C05는 3가지 / C11은 2가지) 일치. 안내 상자 없음 |
| 3 | 03a_purchase_s1.png | S1 P03 "가중치 2 · 베이지, 블랙" 일치(구매 가중치 1→2는 스크립트가 성공 문구로 확인). 기록 수 2·총수량 2·최근 구매일 10/31은 화면에 없으며 test_web_demo가 HTTP로 확인 |
| 3 | 03b_graph_weight2.png | C31 선택: 이웃 여성·20대(소속 그룹)·와이드 슬랙스(구매 · 가중치 2), P03 칩 옆 "가중치 2". 일치. 61노드 |
| 4 | 04_recommend_again.png | P01 7/3 → P05 6/5 → P07 5/4, 같은 그룹, P03 제외. 지지자·색상·색상 수 안내(C07은 2가지) 일치. 안내 없음 |
| 5 전 | 05a_popular_before.png | 여성·20대 S4 9행: P03 11/8, P01 7/3, P05 6/5, P07 5/4, P06 3/3, P15 3/3, P02·P04·P17 1/1, 모두 판매 중. 고정 직후라 전·후가 같다. 일치 |
| 5 후 | 05b_popular_after.png | 전 고정 유지. 후: P03 11/8, P07 8/5, P01 7/3, P05 6/5, P06, P15, P02, P04, P17. P07·P01·P05에 주황 "순위 변경". 구매 가중치 1→2→3은 스크립트가 확인. 일치 |
| 6 전 | 06a_before_stock.png | P07 8/5 → P01 7/3 → P05 6/5. P07 근거 "C07은 2가지, C09는 3가지" 일치. 안내 없음 |
| 6 재고 | 06b_zero_stock.png | P07 블랙·그레이·베이지·네이비 모두 0, 빨간 "품절", 구매 가능 색상 없음, "하람(C31) 고객 추천 다시 보기" 버튼 |
| 6 후 | 06c_after_stock.png | P01 7/3 → P05 6/5 → P06 3/3. P07 제외. P06 지지자 C06·C08·C10, 색상 베이지·스카이블루·화이트, 색상 수 안내 없음. 일치 |
| 7 | 07_widen_gender.png | 새싹(C32), 남성·10대. P09 6/4 → P08 5/4 → P11 5/4, 모두 "남성 전체"(청록). 색상 수 안내 C20은 3가지 / C19는 2가지 / C20은 2가지. 넓힘 안내 한 줄만 있음. 일치 |
| 8 | 08_integrity.png | 그룹 노드 8·고객 노드 32·상품 노드 22·소속 간선 32·구매 간선 101·구매 기록 127, 위반 없음(0). 일치 |

### 3.5 외부 리소스 0

```text
$ rg -n -i 'https?://|cdn|@import|url\(|@font-face|fonts\.' frontend/src frontend/index.html
(일치 0건, 종료 코드 1)
$ rg -n -i 'https?://|@import|url\(|@font-face' frontend/dist/index.html frontend/dist/assets/*.css
(일치 0건, 종료 코드 1)
$ rg -o -i 'https?://[a-zA-Z0-9./_-]+' frontend/dist/assets/*.js | sort | uniq -c
   3 http://www.w3.org/1998/Math/MathML
   7 http://www.w3.org/1999/xlink
   5 http://www.w3.org/2000/svg
   3 http://www.w3.org/XML/1998/namespace
   2 https://react.dev/errors/
```

JS의 문자열은 React 번들의 XML 이름공간과 오류 도움말 주소다. 불러오는 리소스가 아니다(UI4b 기록과 같은 판단). 브라우저 실측: Chrome Fetch 가로채기로 127.0.0.1 밖 요청을 막은 상태에서 Network 이벤트의 외부 요청 **0건**, JS 예외 **0건**(`design_c_browser_results.json`의 `external: []`, `exceptions: []`). 운영체제 전체의 인터넷 연결은 끄지 않았다.

### 3.6 TypeScript 계산 없음

```text
$ rg -n 'sort\(|WEIGHT_CAP|Math\.min\([^\n]*score|score\s*\+=|reduce\(' frontend/src
frontend/src/App.tsx:104:      boxes[node.id].y = members.reduce((sum, box) => sum + box.y, 0) / members.length;
```

유일한 일치는 그룹 칩의 y좌표(소속 고객 칩 좌표의 평균)다. 좌표 변환이며 UI4c에도 같은 식이 있었다. grep만으로 판단하지 않고 TS의 산술을 모두 대조했다.

| 위치 | 산술 | 분류 |
|---|---|---|
| `graphLayout` | 열별 간격·칩 높이·그룹 평균 y·빈 그룹 빈자리 | 좌표 변환 |
| `edgePath` | 칩 끝점과 곡선 중간 x | 좌표 변환 |
| `shortLabel` | 긴 이름 자르기(전체 이름은 title·선택 정보에 표시) | 표시 |
| `PopularChart` | `score / maxScore` → 막대 너비 %, 두 응답 배열의 `findIndex` 비교와 `+1` 순번 표시 | 좌표 변환 · 표시용 순위 비교 |
| 순번 `index + 1` | 서버 배열 순서의 번호 | 표시 |

점수·가중치·추천 범위·품절 판정·안내 조건·인원·통계는 모두 서버 응답 값 그대로다. 정렬은 없다. 간선을 두 번 나눠 그리는 `filter`는 선택 간선을 위에 그리려는 그리기 순서일 뿐 데이터 순서를 바꾸지 않는다.

## 4. 남은 점과 판단 필요

1. **판단 필요**: `PopularItem` 타입에 서버 필드 `sold_out` 선언을 추가해 품절 막대 색에 사용했다(1절).
2. S4 비교 화면은 1440×900 한 화면에 9행 전·후가 들어간다. 15행처럼 행이 많으면 세로 스크롤이 생긴다(이번 시연 데이터에서는 미발생, 미확인).
3. 760px 이하 좁은 화면은 레일을 위로 올리고 그래프를 가로 스크롤로 보게 했다. **실제 좁은 창 확인은 하지 않았다(검증 안 함)**.
4. Safari·Edge와 실제 화면 공유 상태에서 읽히는지는 확인하지 않았다(검증 안 함). Chrome headless 캡처만 있다.
5. 짝수 LTS Node 재현 빌드는 UI5와 같이 미실행이다.
6. 그래프의 "가중치 n" 표시는 가까운 간선 곡선 위에 겹칠 수 있어 글자에 바탕색 외곽선을 둘렀다. 같은 상품을 여러 고객이 산 상품을 선택하면 고객 쪽에 줄지어 표시된다(고객 칩 간격 약 21px, 글자 12px).
