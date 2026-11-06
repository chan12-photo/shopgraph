# UI8 기록 (2026-11-07)

변경 요약:
- `_RequestHandler.timeout = 2`로 첫 요청·헤더 대기의 무전송 연결을 닫는다. 기존 본문 `settimeout(2.0)`은 유지한다.
- `_run_web`은 브라우저 열기 예외를 수동 접속 안내로 처리하고 서버를 계속 실행한다. Ctrl+C·finally 종료는 유지한다.
- 실제 HTTP 유휴 연결 회귀와 시간 제한 설정 테스트 2개를 추가했다. 단일 처리 설계는 유지한다.
- 외부 검토 #2·#11(찬일 11/07 판정)을 반영하고 A14·A15를 기록했다.

Codex 자체 확인: `python3 -B -m unittest` → `Ran 192 tests in 17.159s`, `OK` (통과 192 / 미도래 0 / 실패 0).
커밋 1은 같은 명령으로 `Ran 190 tests in 12.682s`, `FAILED (errors=1)` (통과 189 / 미도래 0 / 실패 1): `RuntimeError: browser`, 구현 전 예상된 실패다.
추가·변경 회귀 3개는 `Ran 3 tests in 3.011s`, `OK`. 유휴 소켓 종료 응답 없음·표준 logging의 시간 초과 기록도 확인했다.

Codex 자체 확인 — 고장 주입(저장소 밖 임시 사본에서만):

| 주입 | 실행 대상 | 실제 결과 |
|---|---|---|
| `timeout = 2` 줄 삭제 | `tests.test_web_stability` 2개 | `Ran 2 tests in 3.518s`, `FAILED (failures=2)`: `None != 2`, GET 응답 시간 초과 |
| `webbrowser.open`을 별도 try 밖으로 복원 | `test_browser_open_failure_still_closes_server` | `Ran 1 test in 0.506s`, `FAILED (errors=1)`: `RuntimeError: browser` |

Codex 자체 확인 — 브라우저:
- 원래 저장소에서 `python3 main.py --web` 실제 실행(127.0.0.1:8000, 기본 브라우저 자동 열기 호출). 같은 서버에 Headless Chrome/157.0.8103.38으로 접속해 그래프·C01 봄비 고객 상세(S1·추천) 동작과 캡처를 확인했다. 브라우저 예외 0. Ctrl+C 종료도 확인했다.
- 기존 `node docs/verification/ui5_browser_check.mjs`는 결과 파일 덮어쓰기를 피하려고 저장소 밖 동일 코드 사본에서 실행했다. 장면 1~8 전체 대조 통과, 외부 네트워크 0, 브라우저 예외 0. 의존성 설치 없음.
- 로그·캡처는 임시 경로 `shopgraph-ui8-eslo9cew`에만 두었다. 기존 UI5 기록은 변경하지 않았다.

Codex 자체 확인 — 범위: 기존 테스트 변경은 [SPEC]의 지정 메서드 하나뿐이며, 금지 파일·frontend 변경 없음. 이번 확인은 같은 세션의 자기 확인이며 사람 승인 판정은 하지 않았다.

남은 한계: 단일 처리 서버이므로 무전송 유휴 연결 하나에 최악 2초 지연이 남는다.
정정(11/07): 연결당 2초 제한이었고, 무전송 연결이 n개면 뒤 요청은 약 n×2초를 기다렸다(외부 버그 검토 #6). UI9에서 동시 수신으로 해결.

이해 질문(기록만, 미답):
1. 예측: 연결 하나가 아무 데이터도 보내지 않을 때 다른 연결의 GET /api/stats는 언제 처리되며, 첫 연결은 무엇을 받는가?
2. 원인: 이전 코드에서 브라우저 열기가 예외를 내면 server_close는 호출되는데 serve_forever는 호출되지 않은 이유는 무엇인가?
3. 설명: 본문 settimeout(2.0)이 있는데도 핸들러 timeout이 필요한 이유와 단일 처리에서 최악 2초 지연이 남는 이유는 무엇인가?
