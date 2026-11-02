# UI4 G7 자료

- 단계: UI4 화면 6개
- 구현: `frontend/src/App.tsx`와 `styles.css`에 그래프, 고객 상세·추천, 등록·구매, S4, 상품 상세·재고, 통계·무결성 화면을 구현했다.
- API 책임: 모든 점수·가중치·추천 범위·품절 여부·안내 줄은 Python 응답을 그대로 렌더링한다. 고객 등록 성공 뒤에는 POST 응답의 고객/그룹만 사용하고 고객 상세가 별도로 GET `/api/customers/{id}/recommendations?k=3`를 호출한다.
- 그래프: 외부 시각화 라이브러리 없이 SVG를 직접 작성했다. 그룹·고객·상품 3열과 서버 간선 `weight`의 선 굵기, 클릭한 노드의 이웃 강조를 화면에서 확인했다.
- 장면 6 흐름: 고객 상세 추천 카드의 상품 상세 버튼 → 재고 전체 0 저장 → 고객 상세 탭 재진입 시 추천 GET 재호출이 이어진다.

## 자체 대조

- TypeScript에서 추천 점수 합산, 고객별 상한, 범위 확장, 구매 상품 제외, 품절 판정, 서버 배열 재정렬, 안내 줄 조건을 구현하지 않았다. `item.score`, `item.scope_label`, `item.status_label`, `item.notice_lines`와 같은 응답 필드를 표시만 한다.
- SVG 막대의 `width`는 서버가 돌려준 `score` 값을 좌표로 직접 사용하며 별도 점수 계산·정규화가 없다. 그래프 좌표와 줄 간격은 화면 배치 값이다.
- `frontend/src`·`frontend/index.html`에서 URL/CDN/외부 글꼴/CSS `@import` 검색 결과는 0건이다.

```text
$ rg -n -i 'https?://|cdn|fonts\.googleapis|@import' frontend/src frontend/index.html
no matches
```

## 실행 결과 원문

```text
$ python3 -B -m unittest -q
Ran 163 tests in 6.679s
OK

$ (cd frontend && npm ci)
added 24 packages, and audited 25 packages in 598ms
found 0 vulnerabilities

$ (cd frontend && npm run typecheck)
> shopgraph-web@0.0.0 typecheck
> tsc --noEmit

$ (cd frontend && npm run build)
> shopgraph-web@0.0.0 build
> vite build
vite v8.3.4 building client environment for production...
✓ 16 modules transformed.
dist/index.html                   0.39 kB │ gzip:  0.26 kB
dist/assets/index-CBS-d9WV.css    4.46 kB │ gzip:  1.64 kB
dist/assets/index-Qk8iJv8E.js   233.80 kB │ gzip: 72.82 kB
✓ built in 205ms
```

예외 주입 테스트가 의도적으로 웹 로거에 traceback을 남기는 것은 정상이며 전체 판정은 `OK`다.

## 실제 브라우저 캡처

Chromium headless를 1440×1000으로 띄워 실제 HTTP `127.0.0.1:8000` 화면을 열고 DevTools Protocol로 각 탭 버튼을 눌러 캡처했다. 기대값을 새로 계산하지 않고 화면 렌더링만 확인했다.

| 파일 | 화면 |
|---|---|
| `docs/verification/ui4_screens/01_graph.png` | 그래프 SVG 3열·간선 |
| `docs/verification/ui4_screens/02_customer.png` | 고객 상세·추천 카드·근거/색상 |
| `docs/verification/ui4_screens/03_mutations.png` | 고객 등록·구매 등록 |
| `docs/verification/ui4_screens/04_popular.png` | 그룹 인기 SVG 막대 |
| `docs/verification/ui4_screens/05_product.png` | 상품 상세·S2·재고 수정 |
| `docs/verification/ui4_screens/06_integrity.png` | 통계·무결성 |

각 파일은 1440×1000 PNG이며, 실행용 `data.py`가 초기 데이터를 제공하는 웹 서버에서 캡처했다.

## 이해 질문(기록만)

1. 발표에서 그래프 간선을 클릭해 강조하는 순서를 고정할 것인가, 고객 상세로 바로 이동하는 순서를 고정할 것인가?
2. S4 전·후 비교는 구매 등록 전후 두 캡처를 나란히 제시할 것인가?
3. 장면 6에서 재고 저장 뒤 고객 상세로 돌아가는 버튼을 별도로 둘 것인가, 현재처럼 탭 이동으로 충분한가?

## 판정

- UI4 자체 게이트: 통과.
- 독립 검토: Codex 자기 재검토이며 독립 검토가 아니다. UI5 전 최종 독립 확인은 별도 검토 절차에서 수행한다.
