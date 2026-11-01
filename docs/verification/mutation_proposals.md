# 고장 검사에서 찾은 테스트 공백 — 추가 테스트 초안 (tests/에 넣지 않음)

- 출처: docs/verification/mutation_sweep.md의 못 잡은 변형 M04·M05
- 상태(11/02): 찬일 승인, [SPEC][W10b]에서 tests/test_flow.py TestW10bInputs로 추가함 (P2는 구매 삭제를 별도 테스트 test_delete_purchase_id_spaces로 나눔). 아래는 당시 초안 원문이다
- 이 초안은 (당시) tests/에 넣지 않았다. 넣으려면 찬일 승인 뒤 tests/test_flow.py에 **추가만** 한다 (기존 테스트 변경 없음)
- 기대 문구는 W8b·W10·W10a 승인 형식에서 옮겼지만, 이 입력 조합 자체는 문서에 없으므로 모두 **[제안 기대값]**(사람 승인 필요)이다
- 고정 데이터는 tests/fixtures.py(6.1)를 쓰고, 실행용 data.py는 읽지 않는다 (기존 _run_main 도우미 사용)

## P1. 10자리 숫자 입력은 main.py가 먼저 거른다 (M04)

- 노리는 변형: main.py `_to_int`의 자릿수 경계(9자리까지 허용)
- 왜 지금 못 잡나: test_invalid_create_inputs는 "1234567890"을 넣지만 오류 줄 수만 세고, 변형에서는 graph.py 범위 검사가 대신 거절해 줄 수가 같다

```python
    def test_digit_limit_boundary(self) -> None:
        """나이 입력 9자리는 graph.py 범위 검사로, 10자리는 main.py 자릿수 제한으로 거절된다."""
        text, g = _run_main(["1", "1", "고객7", "2", "123456789",
                             "1", "1", "고객7", "2", "1234567890", "0"])
        # [제안 기대값] 9자리: W10a 형식의 graph.py 범위 오류
        self.assertIn("\n[오류] 나이: 10~99이어야 합니다 (입력: 123456789)\n", text)
        # [제안 기대값] 10자리: main.py 자릿수 오류 (A03 수정 문구)
        self.assertIn("\n[오류] 나이: 숫자가 너무 깁니다 (9자리 이하)\n", text)
        self.assertEqual(snapshot(g), snapshot(make_graph()))
```

## P2. 삭제 메뉴의 ID 입력도 앞뒤 공백을 지운다 (M05)

- 노리는 변형: main.py `_delete_customer`(그리고 같은 모양의 `_delete_product`·`_delete_purchase`)의 `.strip()`
- 근거: W10 승인 형식 12번 "ID·구매일·메뉴 번호 입력은 앞뒤 공백을 main.py가 지움"

```python
    def test_delete_id_spaces(self) -> None:
        """삭제 메뉴에서 앞뒤 공백이 있는 ID도 같은 고객·상품·구매로 찾는다 (취소해서 상태는 그대로)."""
        text, g = _run_main(["4", "1", " C02 ", "n", "4", "2", " P01 ", "n", "0"])
        # [제안 기대값] 확인 문장 (W10 승인 형식 5번, 6.1에서 C02 구매 기록 3건·P01 5건)
        self.assertIn("고객2(C02) 삭제: 구매 기록 3건도 함께 삭제됩니다. 계속할까요? (y/n): n\n", text)
        self.assertIn("오버핏 티셔츠(P01) 삭제: 구매 기록 5건도 함께 삭제됩니다. 계속할까요? (y/n): n\n", text)
        self.assertNotIn("[오류]", text)
        self.assertEqual(snapshot(g), snapshot(make_graph()))
```

- 구매 삭제(`_delete_purchase`)의 공백 처리까지 보려면 `["4", "3", " T004 ", "0"]`과 결과 줄 확인을 더한다. 결과 줄 문구는 test_delete_purchase(tests/test_flow.py)의 승인 형식과 같게 둔다

## 넣지 않는 것

- S06(대상 고객을 동료에서 빼지 않음)은 동작이 같은 변형이라 잡는 테스트를 만들 수 없다 (mutation_sweep.md 근거)
