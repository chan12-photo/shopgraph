# UI3 G7 자료

- 단계: UI3 프런트엔드 뼈대
- Node: `v25.8.1` (홀수 단기 지원이라 짝수 LTS를 권장하지만, UI0 승인 조건상 막는 조건은 아니므로 기록 후 진행)
- npm: `11.11.0`
- Context7 확인: React 공식 `createRoot` 진입점, Vite `vite build`/기본 `dist`, TypeScript `moduleResolution: bundler`·`noEmit` 문서를 확인하고 적용했다.

## 직접 의존성 6개와 게시일

| 패키지 | 고정 버전 | npm 게시일(UTC) | 2주 규칙 |
|---|---:|---|---|
| `react` | 19.3.1 | 2026-10-14 | 11/03 기준 2주 초과 |
| `react-dom` | 19.3.1 | 2026-10-14 | 11/03 기준 2주 초과 |
| `typescript` | 7.0.2 | 2026-07-08 | 2주 초과 |
| `vite` | 8.3.4 | 2026-10-08 | 최신 8.3.5(10/21)가 2주 미만이라 이전 안정 버전 |
| `@types/react` | 19.3.0 | 2026-09-09 | 2주 초과 |
| `@types/react-dom` | 19.3.0 | 2026-09-09 | 2주 초과 |

`frontend/package.json`의 직접 의존성은 위 6개뿐이다. `package-lock.json`의 추가 항목은 이 6개가 필요로 하는 전이 의존성이다.

## 실행 결과 원문

```text
$ npm ci
added 24 packages, and audited 25 packages in 4s
8 packages are looking for funding
found 0 vulnerabilities

$ npm run typecheck
> shopgraph-web@0.0.0 typecheck
> tsc --noEmit

$ npm run build
> shopgraph-web@0.0.0 build
> vite build
vite v8.3.4 building client environment for production...
transforming...
✓ 16 modules transformed.
rendering...
computing gzip size...
dist/index.html                   0.39 kB │ gzip:  0.26 kB
dist/assets/index-B2tFyJ6I.css    0.27 kB │ gzip:  0.23 kB
dist/assets/index-DqhbH1sP.js   219.70 kB │ gzip: 68.73 kB
✓ built in 211ms
```

처음 `typecheck`에서 CSS side-effect import 선언이 없어 실패했지만 `src/vite-env.d.ts`를 추가한 뒤 같은 버전을 바꾸지 않고 재실행해 통과시켰다. 버전 바꿔가며 시도하지 않았다.

## 외부 리소스·구조 확인

```text
$ rg -n -i 'https?://|cdn|fonts\.googleapis|@import' frontend/src frontend/index.html
no matches

$ python3 - <<'PY'
... package.json 직접 의존성 출력 ...
['@types/react', '@types/react-dom', 'react', 'react-dom', 'typescript', 'vite']
PY
```

소스·HTML에는 URL, CDN, 외부 글꼴, CSS 프레임워크가 없다. lockfile의 `registry.npmjs.org` resolved URL은 실행 시 로드하는 리소스가 아니라 npm 설치 무결성 기록이다.

## 이해 질문(기록만)

1. 짝수 LTS Node로 교체할 때 발표·시연 컴퓨터의 버전도 같은 범위로 고정할 것인가?
2. UI4에서 화면 새로고침 시 서버의 초기 상태를 다시 읽는 동작을 안내 문구로 표시할 것인가?
3. 빌드 산출물의 해시 파일명은 시연 문서에 매번 기록할 것인가, `frontend/dist/index.html`만 기준으로 삼을 것인가?

## 판정

- UI3 자체 게이트: 통과.
- 독립 검토: Codex 자기 재검토이며 독립 검토가 아니다. 최종 독립 확인은 별도 검토 절차를 따른다.
