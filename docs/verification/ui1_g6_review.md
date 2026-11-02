# UI1 G6 독립 검토 원문 (Claude Code, 읽기 전용)

- 1차 검토: web-ui 19cbe5a 기준, 2026-11-02 23:3x. 아래 원문
- 보완: 016657f, 7c28ed3 (Codex). 보완 뒤 Codex 자체 재확인(독립 아님), 최종 독립 확인은 Claude Code(다른 세션, 7c28ed3 기준, 고장 주입 11가지 모두 검출, 승인 가능 판정, 권장 2 브라우저 열기 위치는 테스트 보호 없음)
- 최종 확인 세션은 이 원문을 찾지 못해 항목을 추정 대응했다. 대응 결과는 원문 6건과 일치한다 (Claude 채팅 대조)

---

현재 UI1은 승인하면 안 됩니다. 읽기 경로·추천 문구·장면 6 기대값·기본 보안 구현은 대체로 맞지만, 지원하지 않는 HTTP 메서드가 405가 아니라 501 HTML로 끝나는 실제 계약 위반이 있고, API 테스트가 응답 필드·안내 줄·순서·스냅샷을 충분히 검증하지 않습니다. 아래 “반드시 수정” 항목 처리 후 재검토가 필요합니다.
반드시 수정 1 — 지원하지 않는 메서드가 405가 아님
- 근거: [web.py (line 259)](/Users/chan12/projects/shopgraph/web.py:259), [web.py (line 263)](/Users/chan12/projects/shopgraph/web.py:263)는 POST·PUT만 정의하고 HEAD/DELETE/PATCH/OPTIONS를 정의하지 않습니다. 따라서 BaseHTTPRequestHandler 기본 501 HTML 응답으로 빠집니다.
- 계약: [docs/verification/ui0_design.md (line 154)](/Users/chan12/projects/shopgraph/docs/verification/ui0_design.md:154)의 “메서드” 경계 테스트 및 405 JSON 계약.
- 재현(임시 사본, tests/fixtures.py 사용):
  HEAD /api/stats    501 text/html;charset=utf-8
  DELETE /api/stats  501 text/html;charset=utf-8
  PATCH /api/stats   501 text/html;charset=utf-8
  OPTIONS /api/stats 501 text/html;charset=utf-8
  DELETE /api/unknown 501 text/html;charset=utf-8
  알려진 경로는 405 JSON, 없는 경로는 404 JSON이어야 합니다.
- 현재 테스트 [tests/test_web.py (line 134)](/Users/chan12/projects/shopgraph/tests/test_web.py:134)는 POST 하나만 검사합니다.
반드시 수정 2 — 읽기 API 테스트가 응답 계약을 충분히 검사하지 않음
- [tests/test_web.py (line 61)](/Users/chan12/projects/shopgraph/tests/test_web.py:61)~[tests/test_web.py (line 90)](/Users/chan12/projects/shopgraph/tests/test_web.py:90)는 그래프의 노드·간선 개수와 일부 종류만 확인합니다. 라벨, ID 순서, 간선 source/target/weight/집계값, 중복을 확인하지 않습니다.
- [tests/test_web.py (line 92)](/Users/chan12/projects/shopgraph/tests/test_web.py:92)~[tests/test_web.py (line 122)](/Users/chan12/projects/shopgraph/tests/test_web.py:122)는 S1/S2/S4/추천의 일부 ID와 배열 길이만 확인합니다. notice_lines의 실제 문구, 제품별 점수·범위·지지자·색상, 응답 배열 전체 순서를 확인하지 않습니다.
- snapshot도 각 응답 직후가 아니라 여러 요청 뒤 한 번만 비교합니다([tests/test_web.py (line 90)](/Users/chan12/projects/shopgraph/tests/test_web.py:90), [tests/test_web.py (line 122)](/Users/chan12/projects/shopgraph/tests/test_web.py:122), [tests/test_web.py (line 145)](/Users/chan12/projects/shopgraph/tests/test_web.py:145)).
- 승인 설계는 모든 읽기 응답의 필드·형식·순서·중복·스냅샷을 요구합니다([docs/verification/ui0_design.md (line 153)](/Users/chan12/projects/shopgraph/docs/verification/ui0_design.md:153)).
- 재현: 임시 사본에서 그래프 라벨을 WRONG, 간선 weight를 999로 바꾸고 추천 notice_lines를 제거하도록 web 함수를 고장 내도 기존 두 API 테스트는 다음처럼 통과했습니다.
  Ran 2 tests in 1.022s
  
  OK
  bad-response mutation suite passed: True
  즉, 현재 테스트만으로는 잘못된 API 응답을 놓칩니다.
- 오류 테스트도 [tests/test_web.py (line 127)](/Users/chan12/projects/shopgraph/tests/test_web.py:127)~[tests/test_web.py (line 135)](/Users/chan12/projects/shopgraph/tests/test_web.py:135)에서 대부분 상태 코드만 확인하고 {"error": ...} 문구는 검사하지 않습니다.
반드시 수정 3 — k 범위 검증을 web.py가 중복 수행
- 설계 문서는 숫자 변환 뒤 범위 검사를 search 함수에 맡기도록 했습니다([docs/verification/ui0_design.md (line 59)](/Users/chan12/projects/shopgraph/docs/verification/ui0_design.md:59)).
- 하지만 [web.py (line 212)](/Users/chan12/projects/shopgraph/web.py:212)~[web.py (line 214)](/Users/chan12/projects/shopgraph/web.py:214), [web.py (line 220)](/Users/chan12/projects/shopgraph/web.py:220)~[web.py (line 222)](/Users/chan12/projects/shopgraph/web.py:222)에서 추천/S4 범위를 먼저 검사합니다.
- 재현 결과:
  ValueError 개수: 1~10이어야 합니다 (입력: 11) search_called= False
  group_popular()가 호출되기 전에 web.py가 판정합니다. HTTP 전송 형식 검증은 web.py가 맡되, 업무 범위 검증은 recommend()/`group_popular()`로 일원화해야 합니다.
반드시 수정 4 — 경로 이탈·디렉터리 목록 테스트가 실제로 없음
- 테스트 이름은 test_static_dist_file_and_path_escape지만 [tests/test_web.py (line 153)](/Users/chan12/projects/shopgraph/tests/test_web.py:153)~[tests/test_web.py (line 165)](/Users/chan12/projects/shopgraph/tests/test_web.py:165)에서 실제로 요청하는 것은 정상 JS 파일과 /missing.js뿐입니다.
- ../, %2e%2e, 인코딩된 /, 디렉터리(/assets/) 요청을 검사하지 않습니다.
- 설계는 경로 이탈·디렉터리 목록 노출 방지를 명시합니다([docs/verification/ui0_design.md (line 154)](/Users/chan12/projects/shopgraph/docs/verification/ui0_design.md:154)).
- 구현 자체는 임시 사본에서 다음을 모두 404로 처리했습니다.
  /assets/                         404
  /assets/%2e%2e/%2e%2e/web.py    404
  /%2e%2e%2fweb.py                404
  따라서 현재 발견은 구현 취약점이 아니라 필수 회귀 테스트 누락입니다.
권장 — 웹 시작 예외와 실제 main 진입점 테스트 부족
- [main.py (line 89)](/Users/chan12/projects/shopgraph/main.py:89)~[main.py (line 97)](/Users/chan12/projects/shopgraph/main.py:97)에서 webbrowser.open()이 try/finally 밖에 있습니다. 브라우저 열기 호출이 예외를 내면 이미 만든 서버가 닫히지 않습니다.
- [tests/test_web.py (line 167)](/Users/chan12/projects/shopgraph/tests/test_web.py:167)~[tests/test_web.py (line 177)](/Users/chan12/projects/shopgraph/tests/test_web.py:177)는 _run_web을 mock해 인자 전달만 확인합니다. 실제 서버 생성, 포트 충돌, Ctrl+C 종료는 검사하지 않습니다.
- 이 브라우저 예외 경로는 미실행입니다.
동의한 부분
- 공개 API 사용: [web.py (line 15)](/Users/chan12/projects/shopgraph/web.py:15)~[web.py (line 17)](/Users/chan12/projects/shopgraph/web.py:17)의 graph/search/view import와 호출은 공개 메서드·함수·상수만 사용합니다. _adj, _edges, main.py 내부 함수 접근은 찾지 못했습니다.
- 계산 분리: 추천은 [web.py (line 118)](/Users/chan12/projects/shopgraph/web.py:118)~[web.py (line 130)](/Users/chan12/projects/shopgraph/web.py:130)에서 recommendation_view 결과를 사용하며, 점수·범위·추천 안내 조건을 다시 계산하지 않습니다. 임시 fixture HTTP 확인에서 notice_lines와 화면 줄 모두 view.py 결과와 일치했습니다.
- 서버: [web.py (line 249)](/Users/chan12/projects/shopgraph/web.py:249)의 HTTP/1.0, [web.py (line 336)](/Users/chan12/projects/shopgraph/web.py:336)~[web.py (line 360)](/Users/chan12/projects/shopgraph/web.py:360)의 HTTPServer 및 127.0.0.1 고정 바인드, [web.py (line 323)](/Users/chan12/projects/shopgraph/web.py:323)~[web.py (line 333)](/Users/chan12/projects/shopgraph/web.py:333)의 연결 종료는 설계와 맞습니다. 테스트의 백그라운드 스레드는 서버 자체가 아니라 serve_forever() 실행용입니다.
- recommendation_view: [view.py (line 149)](/Users/chan12/projects/shopgraph/view.py:149)~[view.py (line 183)](/Users/chan12/projects/shopgraph/view.py:183)이 구조를 직접 만들고 [view.py (line 209)](/Users/chan12/projects/shopgraph/view.py:209)~[view.py (line 215)](/Users/chan12/projects/shopgraph/view.py:215)이 같은 구조를 출력합니다. 기존 비시연 콘솔 테스트 147개는 통과했습니다.
- 장면 6: demo_expected.md의 승인 줄과 P07 행은 정확히 C09는 3가지입니다([docs/demo_expected.md (line 3)](/Users/chan12/projects/shopgraph/docs/demo_expected.md:3), [docs/demo_expected.md (line 170)](/Users/chan12/projects/shopgraph/docs/demo_expected.md:170)). [tests/test_demo.py (line 98)](/Users/chan12/projects/shopgraph/tests/test_demo.py:98), [tests/test_demo.py (line 268)](/Users/chan12/projects/shopgraph/tests/test_demo.py:268)~[tests/test_demo.py (line 270)](/Users/chan12/projects/shopgraph/tests/test_demo.py:270), [tests/test_demo.py (line 841)](/Users/chan12/projects/shopgraph/tests/test_demo.py:841)~[tests/test_demo.py (line 856)](/Users/chan12/projects/shopgraph/tests/test_demo.py:856)이 품절 전 표·P_top6·두 화면 블록·내부 recommend 결과를 검사합니다.
- 테스트 서버 정리: [tests/test_web.py (line 33)](/Users/chan12/projects/shopgraph/tests/test_web.py:33)~[tests/test_web.py (line 37)](/Users/chan12/projects/shopgraph/tests/test_web.py:37)의 shutdown()·`server_close()`와 [tests/test_web.py (line 55)](/Users/chan12/projects/shopgraph/tests/test_web.py:55)~[tests/test_web.py (line 59)](/Users/chan12/projects/shopgraph/tests/test_web.py:59)의 tearDown()은 정상 테스트 실패에도 정리됩니다.
- 커밋 수치: 테스트 메서드 정적 집계는 a324dff=149, 1552da5=146, 현재 19cbe5a=155로 커밋 본문과 일치합니다. 현재 독립 실행은 시연 제외 147개가 OK였습니다. tests/test_demo.py 8개는 시연 데이터 실행 금지 때문에 미실행입니다.
직접 실행한 명령과 결과
모든 실행은 /tmp/shopgraph-g6.FpbVcS에 git archive HEAD로 만든 사본에서 수행했습니다.
- python3 -B -m unittest tests.test_flow tests.test_graph tests.test_recommend tests.test_search tests.test_view tests.test_web tests.test_web_view
  - Ran 147 tests ... OK
- HTTP 메서드 경계 probe
  - HEAD/DELETE/PATCH/OPTIONS가 알려진·없는 경로 모두 501 HTML
- 잘못된 k·경로·정적 경로 probe
  - 잘못된 k는 400, 없는 API는 404, 인코딩된 경로 이탈·디렉터리는 404
- API 응답 변조 mutation probe
  - 잘못된 그래프 라벨/weight와 누락 notices를 넣어도 기존 두 web 테스트가 Ran 2 ... OK
- k 위임 probe
  - k=11에서 group_popular 호출 전 web.py가 ValueError를 발생시킴
- 커밋별 테스트 메서드 수 정적 집계
  - a324dff: 149, 1552da5: 146
- git status --short
  - 출력 없음(저장소 변경 없음)
- tests/test_demo.py, 시연 장면, data.py 기반 시연 결과, 브라우저·Node 빌드
  - 미실행