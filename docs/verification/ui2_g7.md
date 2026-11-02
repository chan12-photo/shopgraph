# UI2 G7 자료

- 단계: UI2 변경 API
- 구현 범위: `web.py`의 POST 고객·구매, PUT 상품 재고, JSON 전송 검증, 실패 상태 불변, 변경 후 예상 밖 예외의 불확실성 500, 지원 메서드 Allow, `webbrowser.open` 예외 뒤 `server_close` 테스트.
- 계산 책임: 추천·점수·가중치·품절·범위 검사는 기존 `graph.py`·`search.py`·`view.py` 공개 API에 맡기고, `web.py`는 JSON 형식·키·9자리 전송 제한과 응답 조립만 담당한다.
- 입력 경계: bool·실수·null·문자열 정수·10자리 정수, 필수/알 수 없는/중복 키, 중첩 stock 키를 400으로 거절한다. JSON 객체가 아니거나 잘못된 UTF-8·JSON·NaN/Infinity도 변경 전에 거절한다.
- 원자성: 각 실패 HTTP 요청 직후 `tests.helpers.snapshot()`으로 고객·상품·구매·그룹·인접 리스트·간선·다음 ID 전체를 비교한다. 성공 변경 뒤 `check_integrity() == []`를 확인한다.
- 예상 밖 예외: 변경 메서드가 상태를 바꾼 뒤 예외를 내는 고장 주입에서 500과 `변경이 반영됐을 수 있습니다. 다시 조회해 확인하세요`를 확인하고, 이어지는 GET으로 서버 생존과 반영 여부를 확인한다.
- 브라우저 예외: `main._run_web()`의 실제 경로에서 `webbrowser.open()` 예외를 주입하고 `server_close()` 호출을 확인한다.

## G7 자기 재검토

- [동의] HTTPServer 단일 처리·127.0.0.1 고정·HTTP/1.0·연결 종료를 유지했다.
- [동의] 정의된 경로의 미지원 메서드는 JSON 405와 정확한 `Allow`, 없는 경로는 JSON 404다.
- [동의] k 범위와 업무 값 범위는 web.py에서 중복 구현하지 않고 공개 함수/메서드의 ValueError를 400으로 전달한다.
- [동의] 성공 응답은 설계 계약대로 고객은 `{customer, group}`만, 구매는 `edge`·`weight`, 재고는 `product`·품절 상태를 돌려준다.

## 실행·고장 주입 결과

```text
$ python3 -B -m unittest -v
Ran 163 tests in 6.696s
OK
```

위 전체 테스트는 UI2 구현·테스트를 포함한 실제 실행 결과다. 예외 주입 테스트가 의도적으로 로거에 traceback 한 줄을 남기는 것은 서버 생존 검증의 일부다.

임시 `/tmp` 사본에서 구현을 고장 낸 뒤 새 테스트를 실행했다(저장소 파일은 수정하지 않음).

```text
키 검사 제거: test_customer_validation... FAIL (500 != 400),
             test_purchase_and_stock_failures... FAIL (201 != 400)
9자리 검사 제거: test_purchase_and_stock_failures... FAIL (200 != 400, stock 1000000000)
변경 후 mutation 플래그 제거: test_unexpected_exception... FAIL
             (일반 500 문구 != 불확실성 500 문구)
```

## 이해 질문(기록만)

1. 변경 후 500에서 화면이 먼저 재조회해야 한다는 안내를 UI4의 공통 오류 영역에 항상 보일 것인가?
2. 재고 PUT 성공 응답의 `available_colors` 순서를 서버가 준 순서 그대로 표시하면 되는가?
3. 고객 등록 성공 직후 화면 전환은 고객 상세로 고정할 것인가, 등록 패널에 새 고객과 추천 링크를 함께 남길 것인가?

## 판정

- UI2 자체 게이트: 통과.
- 독립 검토: Codex 자기 재검토이며 독립 검토가 아니다. 최종 독립 확인은 찬일이 지정한 별도 검토자 절차를 따른다.
