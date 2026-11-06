# UI9 기록 (2026-11-07)

검토 구분: Claude Code 자체 확인. 찬일 승인 대기. 최종 확인은 Codex가 따로 한다. 같은 세션의 확인이므로 독립 검토가 아니다.

## 변경 요약

- `764d3c9 [SPEC][UI9]`: D-A·D-B 계약. 기대값 2곳(`test_malformed_json_keeps_original_decode_error` 문구, `test_idle_connection_does_not_block_server`의 유휴 소켓 대기 0.5→3초), ui0_design.md 49줄, 계획서 5.5 web.py 행, 19장 행.
- `39b9bdb [UI9]`: web.py·view.py 수정, tests/test_web_ui9.py 45개 추가. 기존 테스트 변경 없음.
- 서버: ThreadingHTTPServer(daemon_threads=True) + 서버당 `graph_lock`. 요청 읽기·전송 검증은 잠금 밖, 그래프 처리·응답 본문 생성은 잠금 안, 소켓 쓰기는 잠금 밖.
- 오류 단계: 변경 메서드가 끝날 때까지의 ValueError만 400. 변경 메서드가 돌아온 뒤의 예외는 종류와 상관없이 불확실성 500.
- 금지 파일(graph.py, search.py, data.py, frontend/, docs/demo_expected.md, CLAUDE.md, README.md) 변경 0.

지시에 없던 판단:

- #10: 3.11과 3.14의 재귀 한도가 달라 RecursionError 변환만으로는 결과가 갈린다. 해독 전 깊이 제한 64를 추가했다.
- 변경 메서드 자신이 낸 ValueError는 graph.py가 상태를 안 바꾸므로 업무 오류 400으로 유지했다(UI0 3.3).
- `k=0000000001`처럼 0을 채운 10자리 k는 이제 400이다. 콘솔의 9자리 규칙과 같다.
- Origin 끝 슬래시 `http://127.0.0.1:포트/`는 이제 403이다. 원문에서 기대값 미지정이던 입력이다.
- `request_queue_size = 32`로 동시 접속 대기열을 늘렸다.

## 테스트 결과

Claude Code 자체 확인: `python3 -B -m unittest`

| 시점 | Python | 원문 | 분류 |
|---|---|---|---|
| 시작 전 869f1f7 | 3.13.12 | `Ran 192 tests in 15.700s` / `OK` | 통과 192 / 미도래 0 / 실패 0 |
| 커밋 1 | 3.13.12 | `Ran 192 tests in 14.743s` / `FAILED (failures=1)` | 통과 191 / 미도래 0 / 실패 1 (구현 전 예상된 실패) |
| 커밋 2 | 3.13.12 | `Ran 237 tests in 38.826s` / `OK` | 통과 237 / 미도래 0 / 실패 0 |
| 커밋 2 | 3.11.15 | `Ran 237 tests in 38.747s` / `OK` | 통과 237 / 미도래 0 / 실패 0 |
| 커밋 2 사본 | 3.14.7 | `Ran 237 tests in 38.692s` / `OK` | 통과 237 / 미도래 0 / 실패 0 |
| 커밋 3 직전 | 3.13.12 | `Ran 237 tests in 38.790s` / `OK` | 통과 237 / 미도래 0 / 실패 0 |
| 커밋 3 직전 | 3.11.15 | `Ran 237 tests in 38.769s` / `OK` | 통과 237 / 미도래 0 / 실패 0 |

## 재현 스크립트 재실행

대상: `git archive 39b9bdb`를 푼 임시 사본. Python 3.13.12와 3.11.15 양쪽 결과가 같았다.

| 결함 | 스크립트·입력 | 결과 | 판정 |
|---|---|---|---|
| #1 | supplement POST·PUT 서로게이트, http_probe surrogate-name·poison-* | 400, 고객 6·다음 C 번호 7 유지, 색상 키 안 남음, 후속 GET 200 | 해결 |
| #6 | http_probe 전체 idle 1·3·5 | 모두 200, 0.0초 | 해결 |
| #7 | cl-plus, cl-conflict, te-cl | 400, 상태 불변 | 해결 |
| #8 | two-host, two-origin, credential-origin | 403 | 해결 |
| #9 | abs-invalid, bad-surrogate-key / oversize-url, many-headers | JSON 400 / JSON 414·431 | 해결. 상태 코드는 지시대로 유지해 스크립트 기대 400과는 2건 다름 |
| #10 | supplement deep, http_probe deep | 3.11·3.13 모두 같은 한국어 400, 후속 GET 200 | 해결 |
| #11 | padded-customer_id, padded-product_id, padded-date, padded-id | 201, 201, 201, 200 | 해결 |
| #14 | console_contract scope unknown C00 | group·gender·all 모두 ValueError | 해결 |
| #16 | static-unknown, api-unknown | 둘 다 404 | 해결 |
| #17 | transport_edges stock-order, put-order | 둘 다 그레이, 네이비, 블랙, 화이트 | 해결 |
| #19 | long-k, nul, bigint, badutf | 한국어 400, JSON 404, 한국어 400, 한국어 400 | 해결 |
| 차등 | differential.py | 1,100개 변경, 단언 1,249,149회, 불일치 0 | 유지 |

http_probe 243건 요약: `{200: 28, 201: 4, 400: 123, 403: 24, 404: 29, 405: 15, 413: 1, 414: 1, 415: 16, 431: 1, 503: 1}`, `status_mismatch 2`(위 414·431), `state_changed_on_failed []`, 응답 없음 0.

스크립트의 `drip [200] 4.03`은 1초씩 네 번 보내는 전체 경과라 GET 지연이 아니다. 지연은 `test_partial_header_does_not_delay_get`이 0.5초 안으로 확인한다.

브라우저: `git archive 39b9bdb` 사본에서 `node docs/verification/ui5_browser_check.mjs` 실행. Chrome/157.0.8103.38, `PASS 장면 1~8 전체 대조 / 외부 네트워크 0 / 브라우저 예외 0`. 저장소의 기존 결과 파일은 덮어쓰지 않았다.

## 고장 주입 (임시 사본, 3.13.12)

- 외부 검토의 놓친 변이 W4·W5·W6·M4·M6과 기존 검출 W1·W2·W3을 `mutations.py`로 다시 돌렸다. 8종 모두 237개 테스트에서 검출됐다.
- 이번 수정을 하나씩 되돌린 19종을 `tests.test_web_ui9`, `tests.test_web_stability`로 돌렸다. 19종 모두 검출됐다. 잠금 제거, HTTPServer 복원, 서로게이트 검사 제거, 오류 본문 strict 인코딩, 응답 실패 감싸기 제거, TE·길이·Host·Origin 검사 제거, 깊이 검사·RecursionError 변환 제거, 공백 정리 제거, 재고 정렬 제거, k 길이·NUL·정적 404·상태 줄 보정 제거, 범위 표시 고객 조회 되돌림이다.
- 저장소 안에는 변이를 넣지 않았다. 재실행한 변이는 지정 18종 중 Python 8종이며, 화면 변이 A1~A6은 UI9b 범위라 돌리지 않았다.

## 남은 한계

- 화면 쪽 #2~#5·#12는 UI9b 예정이고, #13·#15·#18·#22는 기록만 했다.
- #20·#21은 처리 방침이 없어 고치지도 기록하지도 않았다. create_server의 포트 범위 OverflowError는 그대로다.
- 연결 수만큼 스레드를 만들고 상한이 없다. 로컬 전용 시연이라는 전제다.
- 느리게 읽는 클라이언트에 큰 응답을 보내면 2초 쓰기 제한으로 잘린다. 부하 사례(색상 420,000개)에서 8,177,957바이트 중 678,214바이트만 전달됐고 후속 요청은 200이었다.
- 본문을 읽지 않고 거절(400·413·415 일부)하면 응답 뒤 연결 재설정이 올 수 있다. 응답은 모든 재현에서 받았다.
- 숫자로만 된 색상 키는 브라우저 객체 순서 규칙 때문에 이름순으로 보이지 않을 수 있다. 화면에서 확인하지 않았다.
- Windows·Linux·Safari는 확인하지 않았다.

## 이해 질문 (기록만, 미답)

1. 예측: 무전송 연결 5개가 열린 상태에서 GET /api/stats는 언제 응답하고, 그 5개 연결은 언제 어떻게 끝나는가?
2. 원인: 869f1f7에서 이름이 `\ud800`인 등록이 400을 돌려주면서도 고객이 남은 이유는 무엇인가?
3. 설명: 같은 ValueError인데 변경 메서드 안에서 나면 400이고 변경 메서드가 돌아온 뒤에 나면 500이어야 하는 이유는 무엇인가?
