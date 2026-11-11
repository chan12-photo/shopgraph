# UI9c 기록 (2026-11-12)

검토 구분: Codex 자체 확인. 판정과 승인은 찬일이 한다. 같은 세션의 확인이므로 독립 검토가 아니다.

## 변경 요약

- 기준: `279a6648c7fb12655dfb57d257f59e34dcbb685a`, 브랜치 `ui9c`.
- `web.py`
  - `_HeaderLineReader`: 원래 스트림의 `readline(size)`만 위임하고 반환된 바이트를 목록에 기록한다.
  - `_RequestHandler.parse_request`: 요청마다 `_raw_header_lines`를 비우고, `super().parse_request()` 동안만 `rfile`을 기록기로 바꾼다. `finally`에서 원래 스트림으로 되돌린다. 요청 줄은 부모의 `handle_one_request`가 먼저 읽었으므로 기록되지 않으며, 본문은 복원된 원래 스트림에서 읽는다.
  - `_check_header_lines`: 기존 defects·`_has_leftover` 검사를 보존한다. 기록한 각 줄에서 마지막 LF 하나와 그 바로 앞 CR 하나만 제거하고, 남은 CR이 있으면 `400 / 요청 헤더 형식이 올바르지 않습니다`로 거절한다.
  - docstring에 Python 3.15의 해석 결과 차이와 원시 줄 검사를 반영했다. NUL 등 다른 문자 규칙은 추가하지 않았다.
- `tests/test_web_ui9.py`: 기존 메서드·기대값 변경 없이 새 테스트 메서드 4개, 44줄만 추가했다. 기존 메서드의 AST가 모두 동일하고 삭제 줄이 0임을 확인했다.
  - `test_raw_header_lines_reject_embedded_cr`: 깨끗한 해석 결과를 두고 `b"X-Test: ok\r\r\n"`, `b"X-Test: o\rk\r\n"`를 직접 검사해 400과 정확한 문구를 확인한다.
  - `test_raw_header_lines_accept_normal_endings_and_folding`: CRLF·LF·접힌 줄 `b" b\r\n"`이 통과하는지 확인한다.
  - `test_extra_cr_on_first_header_is_rejected_before_change`: 첫 Host 줄 끝의 여분 CR 뒤에 정상 헤더가 이어지는 POST의 400·전체 snapshot·고객 수 불변을 확인한다.
  - `test_lf_only_header_endings_still_allow_post`: LF로 끝나는 정상 헤더의 POST가 201·C07·고객 수 +1·무결성 정상인지 확인한다. 기존 테스트에는 이 요청을 다루는 메서드가 없어 추가했다.
- frontend/, package.json, lock 파일, project_plan.md, CLAUDE.md, README의 다른 섹션, docs/demo_expected.md 변경 0. 표준 라이브러리 몽키패치·내부 함수 직접 호출·추가 의존성 없음. push·main 병합 없음.

## 원인

헤더 블록 `b"Host: a\r\nX-Test: ok\r\r\n\r\n"`을 `http.client.parse_headers`에 넘기면 `raw_items()`는 정상 헤더와 같을 수 있다. 사용자 제공 배경과 3.13·3.15에서 직접 재현한 결과는 다음과 같다.

| Python | raw_items | payload | 기존 검사의 결과 |
|---|---|---|---|
| 3.11 / 3.13 | `[('Host', 'a'), ('X-Test', 'ok')]` | `'\r\n'` | `_has_leftover`가 거절 |
| 3.15 | `[('Host', 'a'), ('X-Test', 'ok')]` | `''` | 해석 결과만으로 여분 CR을 구별할 수 없음 |

여분 CR 뒤에 Origin 등을 숨긴 경우에는 3.15에서도 payload가 남지만, 마지막 헤더인 경우에는 기존 검사만으로 놓친다. 수신한 원시 헤더 줄에서 검사해야 이 해석 차이에 의존하지 않는다.

## 작업 환경

이 세션은 `~/projects/shopgraph`를 읽을 수 있지만 쓸 수 없다. 현재 작업공간에 로컬 Git 복제본을 만들고 수정·커밋했다. 원본 저장소는 `main 279a664` 그대로다.

작업 경로:

```text
/Users/chan12/Documents/Codex/2026-11-12/ui9c-python-3-15-main-279a664/work/shopgraph
```

브랜치 생성 명령과 출력 원문:

```console
$ git switch -c ui9c 279a664
Switched to a new branch 'ui9c'
```

`python3.11`은 기존 conda 환경의 실행 파일을 PATH에 추가했다. `uv`의 기본 캐시는 쓰기 제한이 있어 임시 캐시를 지정했다. Python을 새로 설치하거나 실행 파일을 바꾸지 않았다.

```sh
export PATH=/opt/homebrew/Caskroom/miniforge/base/envs/ds_study/bin:$PATH
export UV_CACHE_DIR=/tmp/shopgraph-ui9c-uv-cache
```

## 테스트 결과

Codex 자체 확인. **세 버전 전체 OK 조건은 충족하지 못했다.** 발견된 테스트는 모두 268개(기존 264 + 추가 4)지만, 실제 HTTP 서버의 `socket.bind`가 `PermissionError: [Errno 1] Operation not permitted`로 차단된다. `TestUI5WebDemo.setUpClass` 실패로 8개는 실행되지 않아 unittest 요약은 `Ran 260 tests`다.

오류 항목 102개는 소켓 권한 오류 99개(클래스 초기화 오류 포함)와 기존 벤치마크 CLI의 3개 하위 검사 오류다. 벤치마크 오류도 `sysctl -n machdep.cpu.brand_string` 조회의 보안 제한 때문이다. assertion 실패·미도래 테스트는 0이지만 전체 통과 또는 회귀 없음으로 판정할 수 없다. 오류 항목 수에는 하위 검사와 클래스 초기화 오류가 포함되므로 실패한 메서드 수와 같지 않다.

| 버전 | 발견 | 전체 실행 원문(구현 커밋 직전) | 분류 |
|---|---|---|---|
| 3.11.15 | 268 | `Ran 260 tests in 0.270s` / `FAILED (errors=102)` | 환경 오류로 전체 검증 미충족 |
| 3.13.12 | 268 | `Ran 260 tests in 0.305s` / `FAILED (errors=102)` | 환경 오류로 전체 검증 미충족 |
| 3.15.2 | 268 | `Ran 260 tests in 0.545s` / `FAILED (errors=102)` | 환경 오류로 전체 검증 미충족 |

기록 커밋 직전, 요청한 명령과 출력 원문:

```console
$ python3.11 -B -m unittest 2>&1 | tail -3
Ran 260 tests in 0.306s

FAILED (errors=102)
```

```console
$ python3.13 -B -m unittest 2>&1 | tail -3
Ran 260 tests in 0.347s

FAILED (errors=102)
```

```console
$ $(uv python find 3.15) -B -m unittest 2>&1 | tail -3
Ran 260 tests in 0.656s

FAILED (errors=102)
```

### 소켓 없는 보완 확인

전체 테스트와 별도로 수행했다. 실제 서버 테스트를 대체하는 통과 결과가 아니다. 임시 스크립트는 `/tmp/shopgraph-ui9c-checks.py`에 두고 커밋하지 않았다.

- 새 단위 메서드 2개는 `FunctionTestCase`로 본문만 호출했다. 해당 클래스의 공통 setUp은 소켓 서버를 열기 때문에 생략하고, 메서드의 assertion 자체는 바꾸지 않았다. 세 버전 모두 `Ran 2 tests in 0.000s` / `OK`.
- 실제 `_RequestHandler.handle_one_request()`와 그래프를 사용하고 입력·출력만 `BytesIO`로 둔 보완 검사: 마지막·첫 헤더의 여분 CR, 중간 CR → 400·고객 6명·snapshot 불변. 정상 CRLF·LF·접힌 줄 → 201·고객 7명·무결성 정상.
- 여분 CR을 포함한 요청 줄은 기록되지 않으며 기존대로 통과했다. NUL을 포함한 정상 해석의 X-Test도 기존대로 통과했다. JSON 본문에 포함된 CRLF는 원시 헤더 목록에 들어가지 않았고 본문을 끝까지 읽었다.
- `parse_request`가 False를 반환할 때와 원래 reader가 OSError를 발생시킬 때도 `rfile`이 같은 원래 객체로 복원됐다.

세 버전에서 공통으로 나온 보완 검사 출력 원문(위의 단위 테스트 출력 이후):

```text
PASS in-memory handler: extra_cr_on_last_header, status=400, customers=6
PASS in-memory handler: extra_cr_on_first_header, status=400, customers=6
PASS in-memory handler: cr_inside_header, status=400, customers=6
PASS in-memory handler: normal_crlf, status=201, customers=7
PASS in-memory handler: lf_headers, status=201, customers=7
PASS in-memory handler: folded_header, status=201, customers=7
PASS in-memory handler: request_line_excluded, status=201, customers=7
PASS in-memory handler: nul_rule_unchanged, status=201, customers=7
PASS stream restoration: parse_request returns False
PASS stream restoration: parse_request raises OSError
```

## 고장 주입 (임시 변경, 커밋하지 않음)

새 원시 줄 검사의 `for line in handler._raw_header_lines:` 한 줄만 `for line in ():`로 바꿨다. 기존 defects·`_has_leftover` 검사와 줄 기록기는 유지했다. 실행을 마친 뒤 finally에서 `web.py` 전체 바이트를 복원하고 SHA-256 일치를 확인했다.

| 변이 검사 | 결과 | 해석 |
|---|---|---|
| 3.15 기존 `test_extra_cr_on_last_header_is_rejected`, 표준 unittest 실행 | `FAILED (errors=1)` | setUp의 socket.bind에서 막혔으므로 변이 검출로 세지 않음 |
| 3.13 새 `test_raw_header_lines_reject_embedded_cr`, FunctionTestCase로 본문 실행 | `FAILED (failures=1)` | `_RequestError not raised`, 새 검사 무력화 검출 |
| 3.15 기존 테스트 본문, 메모리 핸들러로 wire를 제공 | `FAILED (failures=1)` | 400 기대에 201 실제, 새 검사 무력화 검출. 실제 소켓 검사는 아님 |

3.15 표준 unittest 명령:

```sh
$(uv python find 3.15) -B -m unittest tests.test_web_ui9.TestUI9MalformedHeaders.test_extra_cr_on_last_header_is_rejected
```

해당 실행의 마지막 오류와 요약 원문:

```text
PermissionError: [Errno 1] Operation not permitted

----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (errors=1)
```

3.13 단위 메서드의 별도 실행 명령:

```sh
PYTHONPATH="$PWD" python3.13 -B /tmp/shopgraph-ui9c-checks.py --unit-reject
```

출력 원문:

```text
Python 3.13.12: socket-free supplementary checks
unittest.case.FunctionTestCase (test_raw_header_lines_reject_embedded_cr)
해석 결과가 정상이더라도 원시 헤더 줄의 여분 CR·중간 CR은 400이다. ... FAIL

======================================================================
FAIL: unittest.case.FunctionTestCase (test_raw_header_lines_reject_embedded_cr)
해석 결과가 정상이더라도 원시 헤더 줄의 여분 CR·중간 CR은 400이다.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/chan12/Documents/Codex/2026-11-12/ui9c-python-3-15-main-279a664/work/shopgraph/tests/test_web_ui9.py", line 731, in test_raw_header_lines_reject_embedded_cr
    with self.assertRaises(web._RequestError) as caught:
         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
AssertionError: _RequestError not raised

----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (failures=1)
```

3.15 기존 테스트 본문의 별도 실행 명령:

```sh
PYTHONPATH="$PWD" $(uv python find 3.15) -B /tmp/shopgraph-ui9c-checks.py --existing-last-header-test
```

출력 원문:

```text
Python 3.15.2: socket-free supplementary checks
unittest.case.FunctionTestCase (test_extra_cr_on_last_header_is_rejected)
숨은 헤더가 없어도 헤더 블록이 중간에 끝난 요청은 400이다. ... FAIL

======================================================================
FAIL: unittest.case.FunctionTestCase (test_extra_cr_on_last_header_is_rejected)
숨은 헤더가 없어도 헤더 블록이 중간에 끝난 요청은 400이다.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/chan12/Documents/Codex/2026-11-12/ui9c-python-3-15-main-279a664/work/shopgraph/tests/test_web_ui9.py", line 846, in test_extra_cr_on_last_header_is_rejected
    self.assert_raw_rejected((400, {"error": _BAD_HEADER}), self.raw_request(
    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        "POST", "/api/customers", raw,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        ("Content-Type: application/json", f"Content-Length: {len(raw)}", "X-Test: ok\r")))
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/chan12/Documents/Codex/2026-11-12/ui9c-python-3-15-main-279a664/work/shopgraph/tests/test_web_ui9.py", line 761, in assert_raw_rejected
    self.assertEqual((status, json.loads(body.decode("utf-8"))), expected)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: (201, {'customer': {'id': 'C07', 'name': '[75 chars]대'}}) != (400, {'error': '요청 헤더 형식이 올바르지 않습니다'})

First differing element 0:
201
400

+ (400, {'error': '요청 헤더 형식이 올바르지 않습니다'})
- (201,
-  {'customer': {'age': 22, 'gender': '여', 'id': 'C07', 'name': '새 고객'},
-   'group': {'id': 'G-F-20', 'label': '여성·20대'}})

----------------------------------------------------------------------
Ran 1 test in 0.005s

FAILED (failures=1)
```

복원 후 3.15의 같은 기존 테스트 본문을 메모리 핸들러로 다시 실행한 요약 원문:

```text
Ran 1 test in 0.001s

OK
```

## 남은 위험

- 요청한 세 버전 각각의 실제 서버 포함 `268 tests / OK`는 보안 제한 때문에 확인하지 못했다. 소켓·sysctl 조회가 허용되는 환경에서 세 명령을 다시 실행해야 한다.
- 3.15 기존 테스트의 실제 소켓 뮤테이션 검출은 미확인이다. 메모리 핸들러에서 같은 테스트 본문의 400 기대·201 실제 실패만 확인했다.
- 3.15.0·3.15.0b4는 이 세션에서 실행하지 않았다. 확인한 실행 파일은 3.11.15·3.13.12·3.15.2다.
- 버전 간 원시 줄 규칙은 같지만, 표준 파서 전체 동작의 회귀가 없다는 최종 판정은 전체 테스트 재실행 뒤 찬일이 한다.

## 커밋

1. `8d1be7c` — `UI9c 원시 헤더 줄 CR 검사(Python 3.15 대응)`: web.py와 추가 테스트.
2. `UI9c 기록`: 이 문서와 README 현재 상태의 테스트 수·검증 버전·검증 한계.

판정·승인 기록은 추가하지 않았다.
