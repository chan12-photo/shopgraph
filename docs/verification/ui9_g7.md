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

## Codex 확인 1차(불가) → 보완

검토 구분: Claude Code 자체 확인. 독립 검토가 아니다. Codex 재확인과 찬일 승인은 대기 중이다.

| 지적 | 원인 | 조치 |
|---|---|---|
| 차단 1. 서버를 닫은 뒤 남은 연결이 고객을 등록함 (201, 고객 7) | 동시 수신으로 데몬 핸들러가 닫힌 뒤에도 살아 있고, 그래프 처리 전에 서버 상태를 보지 않음 | `shutdown`·`server_close`가 `graph_lock` 안에서 종료 표시를 세운다. `_read_api`·`_change`가 잠금 직후 확인하고 503 `서버가 종료 중입니다`로 끝낸다 |
| 차단 2. 잘못된 헤더 줄 뒤의 외부 Origin·TE·두 번째 Host가 무시됨 (201) | 아래 원인 확인 참고 | `_check_header_lines`가 다른 검사보다 먼저 400 `요청 헤더 형식이 올바르지 않습니다` |
| 길이 표기: 선행 0 4,400개 + 39가 413 | `int()` 자릿수 예외를 한도 초과로 바꿈 | ASCII 십진수 10자리 이하만 허용, 넘으면 400. 413은 값을 읽은 뒤에만 판정 |
| Content-Type 둘이 순서에 따라 201/415 | 첫 값만 읽음 | 400 `요청 헤더가 중복됐습니다 (Content-Type)`. Host·Origin 중복의 403은 유지 |

2번 원인 확인(3.11.15·3.13.12·3.14.7 실제 서버): 지시한 원인이 맞다. 콜론 없는 줄 뒤의 헤더는 `self.headers`에 없고 `defects`에 `MissingHeaderBodySeparatorDefect`가 남는다.

지시와 다른 점: `defects`가 비어 있지 않은 경우를 전부 거절하면 정상 형식의 `multipart/*` 요청도 걸린다. 파서가 본문이 없다는 결함(`NoBoundaryInMultipartDefect` 등)을 남기기 때문이다. 이 요청은 계획서 D1대로 415여야 하므로 multipart 본문 결함 5종만 제외했다. 다른 결함은 전부 400이고, multipart와 헤더 줄 결함이 함께 있어도 400이다.

그 밖의 판단:

- 기존 테스트 기대값 1곳(5,000자리 길이 413 → 400)을 `1d5e528 [SPEC][UI9]`로 분리했다. 테스트 이름과 docstring도 같은 내용이라 함께 고쳤다.
- `TCPServer` 생성자는 바인드 실패 때 `server_close`를 부른다. 재정의가 `OSError`를 가리지 않도록 잠금을 부모 생성자보다 먼저 만든다.
- 앞 절의 "#20·#21은 기록하지 않았다"는 이번에 A43·A44로 기록해 대체한다.

Claude Code 자체 확인: `python3 -B -m unittest`

| 시점 | Python | 원문 | 분류 |
|---|---|---|---|
| `1d5e528` | 3.13.12 | `Ran 237 tests in 38.713s` / `FAILED (failures=1)` | 통과 236 / 미도래 0 / 실패 1 (구현 전 예상된 실패) |
| 보완 | 3.13.12 | `Ran 250 tests in 45.321s` / `OK` | 통과 250 / 미도래 0 / 실패 0 |
| 보완 | 3.11.15 | `Ran 250 tests in 45.315s` / `OK` | 통과 250 / 미도래 0 / 실패 0 |
| 보완 | 3.14.7 | `Ran 250 tests in 45.219s` / `OK` | 통과 250 / 미도래 0 / 실패 0 |

고장 주입(저장소 밖 임시 사본, 3.13.12, `tests.test_web_ui9`): 13종 모두 검출.

| 고장 | 결과 | 잡은 테스트 |
|---|---|---|
| 종료 표시 확인 삭제 (`_change`) | 실패 3 | `test_body_finished_after_close_changes_nothing`, `test_server_close_alone_blocks_later_change`, `test_shutdown_alone_blocks_later_change` |
| 종료 표시 확인 삭제 (`_read_api`) | 실패 1 | `test_read_after_close_is_503` |
| `shutdown`의 종료 표시 삭제 | 실패 2 | `test_read_after_close_is_503`, `test_shutdown_alone_blocks_later_change` |
| `server_close`의 종료 표시 삭제 | 실패 1 | `test_server_close_alone_blocks_later_change` |
| 잠금을 부모 생성자 뒤로 이동 | 오류 1 | `test_port_in_use_keeps_oserror` |
| defects 검사 삭제 | 실패 8 | `test_headers_hidden_after_bad_line_are_rejected`, `test_bad_header_line_checked_before_other_checks`, `test_multipart_does_not_hide_bad_line` |
| defects 검사를 Host 뒤로 이동 | 실패 1 | `test_bad_header_line_checked_before_other_checks` |
| multipart 제외 삭제 (defects 전부 400) | 실패 2 | `test_multipart_content_type_stays_415` |
| multipart가 있으면 defects 무시 | 실패 1 | `test_multipart_does_not_hide_bad_line` |
| 길이 자릿수 제한 삭제 | 실패 3 | `test_zero_padded_content_length_is_400`, `test_content_length_digit_boundary`, `test_huge_content_length_is_400_without_runtime_text` |
| 길이 자릿수 제한 11자리로 완화 | 실패 1 | `test_content_length_digit_boundary` |
| 길이 자릿수 제한 9자리로 강화 | 오류 1 | `test_content_length_digit_boundary` |
| 중복 Content-Type 검사 삭제 | 실패 2 | `test_two_content_types_are_rejected_in_both_orders` |

Codex 재현 스크립트(임시 사본, 3.11.15·3.14.7 같은 결과):

- `concurrency.py`: 나머지 본문 뒤 503, 고객 6 유지. 작업자 24개 300건은 C07–C56, T014–T063, 무결성 위반 0.
- `boundary.py`: 헤더 줄 결함 뒤 Origin·TE·Host 모두 400, 고객 6 유지. 선행 0 4,400개 400, Content-Type 둘 400. `main.py --web` SIGINT 종료 코드 0.
- `http_probe.py` 243건: 분포가 앞 절과 같고 실패 뒤 상태 변경 0.
- `differential.py`: 단언 1,249,149회, 종료 코드 0.
- 브라우저: 사본에서 `ui5_browser_check.mjs` 실행, `PASS 장면 1~8 전체 대조 / 외부 네트워크 0 / 브라우저 예외 0`.

남은 한계:

- `From x`처럼 `From `으로 시작하는 콜론 없는 줄은 첫 줄이나 마지막 줄이면 결함 없이 무시된다. 뒤의 헤더는 사라지지 않아 Host·Origin 검사는 그대로 동작한다(첫 줄 뒤 외부 Origin 403 확인).
- 종료 표시는 그래프 접근만 막는다. 정적 파일 GET은 남은 연결에서 계속 응답한다(코드로만 확인, 실행 안 함).
- 503을 쓰지 못하면 연결만 닫힌다(코드로만 확인, 실행 안 함).
- `ui0_design.md` 263줄의 이해 질문은 옛 단일 처리 구조를 묻는다. 기록 문구라 고치지 않았다.
