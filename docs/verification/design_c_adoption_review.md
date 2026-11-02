# 디자인 C 독립 검토와 채택 기록

- 날짜: 2026-11-03. 결정: 찬일이 C를 채택하고 B는 채택하지 않음. B·C 캡처를 Claude가 대조했다는 찬일의 지시를 기록한다. 이 문서가 사람이 직접 테스트했다는 뜻은 아니다.
- 원본 C 구현자: Claude Code. 검토자: Codex. 검토 대상: `git diff 78ac972..web-design-c`, C HEAD `80c53cd`.
- **원본 독립 검토 판정: 반드시 수정 0 / 합치기 가능.** 검토 중 저장소의 파일·브랜치는 변경하지 않았고, 실험은 `/tmp/shopgraph-design-c-review.uthaqcf1` 사본에서만 했다.
- 이후 찬일 지시에 따라 `web-ui`를 `78ac972`에서 `80c53cd`로 fast-forward 합쳤다. 그 뒤의 다듬기는 Codex 구현·자체 확인이며 독립 검토로 표현하지 않는다. B 브랜치는 `685050c`에 그대로 보존했다.

## 1. 원본 C 독립 검토

아래 줄 번호는 수정 전 **80c53cd의 App.tsx** 기준이다.

| 분류 | 항목·근거 | 판정 |
|---|---|---|
| 동의 | `frontend/src/App.tsx:89` graphLayout, `:117` edgePath, `:125` NodeShape, `:138` shortLabel | 산술은 칩/곡선 좌표·그룹 평균 y·빈 그룹 자리·이름 자르기뿐이다. 그래프 조회나 추천 점수·가중치·범위 계산을 추가하지 않았다. |
| 동의 | `frontend/src/App.tsx:314` PopularChart | 서버 score를 막대 너비로 바꾸고 두 응답의 배열 순번을 표시용으로 비교한다. 서버 items 순서를 유지하며 재정렬·점수 계산을 하지 않는다. |
| 동의 | `frontend/src/App.tsx:23`, `:323`, `:401`; `docs/verification/ui0_design.md:73` | PopularItem의 sold_out 타입 선언·CSS 분기는 승인된 서버 불리언을 그대로 사용한다. 재고로 품절을 다시 판정하지 않는다. 찬일이 이번 지시에서 명시적으로 허용했다. |
| 동의 | `frontend/src/App.tsx:29`, `:220`, `:262`, `:336`, `:373`, `:438` | api/jsonRequest/useApi/NodeSelect, 등록·구매 전체, 고객/S4/상품의 JSX 이전 상태·조회·핸들러, App의 상태·화면 이동 코드를 기준 커밋과 문자열 대조했다. 동일하다. onClick/onChange/onSubmit/onKeyDown **29개 전체**도 공백을 제외한 본문과 개수가 같다. |
| 동의 | `frontend/src/App.tsx:353`, `:362`, `:397`, `:473` | S4 전 고정·비교 해제·필터 변경 해제, 재고 저장 후 마지막 고객 추천 복귀, 선택 상자 이벤트와 App에서 S4 상태를 보존하는 마운트 방식이 그대로다. |
| 동의 | `frontend/package.json`, `frontend/package-lock.json`; 전체 diff 파일 목록 | Python·기존 테스트·기대값·패키지/lock 변경 0. 직접 의존은 react, react-dom, typescript, vite, @types/react, @types/react-dom 6개다. |
| 동의 | `frontend/src/*`, `frontend/index.html`, 임시 브라우저 결과 | 외부 URL·CSS import/url/font-face 소스 검색 0건. 실제 장면 1~8에서 외부 HTTP(S) 요청 0건·JS 예외 0건. React 번들의 XML 이름공간·오류 안내 문자열은 다운로드 리소스가 아니다. |
| 동의 | 임시 사본의 frontend/dist 전체 | npm ci와 build 후 파일 목록과 SHA-256 3개 모두 커밋본과 같았다. 아래 원문·해시 참고. |

### 빌드 재현

`git archive web-design-c`를 저장소 밖 사본에 풀고, 빌드 전 dist 파일 목록·해시를 별도로 보관했다. 아래 명령과 비교는 원본 저장소를 수정하지 않았다. 기존 설치본을 복사하지 않고 사본에서 npm ci를 실행했다.

```text
$ cd /tmp/shopgraph-design-c-review.uthaqcf1/frontend
$ npm ci && npm run build
added 24 packages, and audited 25 packages in 520ms
found 0 vulnerabilities
vite v8.3.4 building client environment for production...
✓ 16 modules transformed.
dist/index.html                   0.39 kB │ gzip:  0.26 kB
dist/assets/index-B6Bj6H_a.css   12.20 kB │ gzip:  3.39 kB
dist/assets/index-1DVqppCK.js   242.44 kB │ gzip: 75.60 kB
✓ built in 267ms
PASS rebuilt dist file list + SHA256 all identical: 3
```

| 원본 C dist 파일 | 빌드 전·후 동일한 SHA-256 |
|---|---|
| index.html | bfd7c4ef3f5882759b02d55ea524a289ef3c08e0d4f66236ad261d1bce34e375 |
| assets/index-B6Bj6H_a.css | 0744818df646396f8334593aad7bad198c2e83950b0c31311bd3e656827c2d0a |
| assets/index-1DVqppCK.js | eb5119e880a51e438bf765a86f089eafecff49916a968a409fcc278788fdd6a8 |

### 원본 C 브라우저 확인

사본에서 `node docs/verification/design_c_browser_check.mjs`를 실행했다. 실제 Python 진입점과 Chrome 156, 1440×900으로 8장면을 이어 갔다. 추천·S1·S4·통계는 기존 승인 어댑터와 DOM 전체를 대조했다. **8장면·12캡처 대조 통과, 외부 요청 0, JS 예외 0.** 그래프 선택 전 60/61개 노드가 화면 안에 있고 최소 글자 13px, 본문 14.25px, 선택 없이 흐린 노드 0개였다.

원본 C 검토 시 S4 비교 해제·필터 변경 해제는 코드 동일성으로 확인했다. 해당 버튼의 실제 클릭 확인은 아래 최종 다듬기 확인에서 추가했다. 원본 C 확인 로그는 `/tmp/shopgraph-design-c-independent-browser.log`에 있다.

## 2. 채택과 최종 다듬기

```text
$ git switch web-ui
Switched to branch 'web-ui'
$ git merge --ff-only web-design-c
Updating 78ac972..80c53cd
Fast-forward
```

- 선택 결정은 찬일에게 받았다. B의 커밋을 C에 합치지 않았다. `web-design-b`는 `685050c`, `web-design-c`는 `80c53cd`에 남긴다.
- `ui5_g7.md`에 다음 문장을 복원했다: **LTS Node 재현: 미실행(짝수 LTS 미설치). 실행에는 Node 불필요(dist 포함)**.
- `frontend/src/styles.css:143`: notices 상자를 기존 성별 전체 범위와 같은 옅은 청록 `#dcf0f3`, 진한 청록 `#0b6f80` 실선 테두리·6px 왼쪽 띠로 강조했다. 조건과 문구는 그대로다.
- `frontend/src/App.tsx:175`: 그래프 머리의 중복 간선 범례 4줄을 삭제했다. 맨 위 오른쪽 범례 1개·그룹/고객/상품 열 제목·구분선은 유지했다. 사용하지 않는 lane-label CSS도 삭제했다.
- Python, API·상태 흐름, 버튼·선택 상자, 패키지·lock, 기존 테스트·기대값은 바꾸지 않았다. dist를 재빌드했다.

## 3. 최종 검증 — Codex 자체 확인

```text
$ (frontend) npm run typecheck
> tsc --noEmit

$ (frontend) npm run build
vite v8.3.4 building client environment for production...
✓ 16 modules transformed.
dist/index.html                   0.39 kB │ gzip:  0.26 kB
dist/assets/index-R21ijBvg.css   12.15 kB │ gzip:  3.37 kB
dist/assets/index-DiXcA22x.js   242.04 kB │ gzip: 75.51 kB
✓ built in 84ms

$ python3 -B -m unittest -v
Ran 174 tests in 7.682s
OK

$ python3 -B -m unittest tests.test_web_demo -v
Ran 11 tests in 0.533s
OK
```

분류: **전체 통과 174 / 미도래 0 / 실패 0**, **웹 시연 통과 11 / 미도래 0 / 실패 0**. 전체 원문: `/tmp/shopgraph-c-adoption-tests.log`, 시연 원문: `/tmp/shopgraph-c-adoption-demo.log`.

### 최종 브라우저와 캡처

기존 `design_c_browser_check.mjs`를 재사용하는 일회성 `/tmp/shopgraph-c-final-browser.mjs`를 실행했다. 입력·기대값·캡처 순간은 그대로다. 캡처 직전에 상단 범례 1개·머리 범례 0개·열 제목 3개와 안내 상자의 실제 청록 배경/실선 테두리 값을 확인했다. 장면 캡처 후 추가로 비교 해제·필터·선택 상자·그래프 선택 해제를 실제 DOM 이벤트로 확인했다. 별도 패키지는 사용하지 않았다.

- **장면 1~8 전체 기대값 대조 통과**, 외부 HTTP(S) 요청 0·브라우저 예외 0.
- 추가 확인: S4 비교 해제, 그룹 변경 시 전 고정 해제, 개수 변경 시 전 고정 해제·3개 표시, 고객 선택 후 추천, 마지막 등록 고객 자동 선택, 상품별 서버 색상 목록과 선택 상자 일치, 그래프 선택 해제 모두 통과. 장면 6 추천 복귀는 원래 시연 흐름에서 통과했다.
- `design_c_screens`의 같은 12장면 순간으로 다시 캡처했다. 실제 바뀐 파일은 **01_groups.png, 03b_graph_weight2.png, 07_widen_gender.png**다. 이 세 이미지를 직접 열어 범례 중복 제거·가중치 2 강조·청록 안내 상자를 확인했다. 다른 장면은 같은 픽셀이라 git 변경이 없다.
- 실행 결과는 `design_c_browser_results.json`의 scenes/layout/decoration/controls에 보관했다. 실행 원문은 `/tmp/shopgraph-c-adoption-browser.log`에 있다.
- 소스·HTML·CSS 외부 리소스 0, 패키지 6개와 lock 불변을 다시 확인했다.

## 4. 실행 범위와 보류

- 짝수 LTS Node 재현은 **미실행**이다. 환경에는 기존 Node v25.8.1을 사용했다. Node 설치는 하지 않았다.
- 이번 두 다듬기의 별도 독립 검토는 **미실행**이다. 원본 80c53cd의 독립 검토와 혼동하지 않는다.
- 다른 브라우저·좁은 창·실제 온라인 화면 공유 확인은 **미실행**이다. 요청한 1440×900 Chrome에서 확인했다.
- 이 문서를 포함하는 `[UI5] 디자인 C 채택 기록 + 다듬기` 커밋 후 멈춘다. push·main 합치기 없음.
