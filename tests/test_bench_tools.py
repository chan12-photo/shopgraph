"""tools/bench.py(정식 ID 규칙 측정 도구) 테스트. 작은 규모로만 실행한다."""

import ast
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

import graph

_TOOL = pathlib.Path(__file__).resolve().parent.parent / "tools" / "bench.py"


def _load_tool():
    """목적: tools/bench.py를 모듈로 읽기. 인자: 없음. 반환: 모듈. 예외: 읽기 실패 전파."""
    spec = importlib.util.spec_from_file_location("shopgraph_bench_tool", _TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBenchTool(unittest.TestCase):
    """측정 도구가 운영 규칙 그대로 동작하는지 확인한다 (측정값 자체는 검사하지 않는다)."""

    def test_same_seed_same_records_with_formal_ids(self) -> None:
        """같은 시드는 같은 데이터, 다른 시드는 다른 데이터이고 ID는 정식 규칙(자릿수 확장)이다."""
        bench = _load_tool()
        first, again, other = (bench.make_records(120, 105, 1005, seed) for seed in (1, 1, 2))
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)
        customers, products, purchases = first
        self.assertEqual([customers[0]["id"], customers[98]["id"], customers[99]["id"], customers[-1]["id"]],
                         ["C01", "C99", "C100", "C120"])
        self.assertEqual([products[0]["id"], products[-1]["id"]], ["P01", "P105"])
        self.assertEqual([purchases[0]["id"], purchases[998]["id"], purchases[999]["id"], purchases[-1]["id"]],
                         ["T001", "T999", "T1000", "T1005"])
        g = graph.ShopGraph(*first)
        self.assertEqual(g.check_integrity(), [])
        self.assertEqual(g.stats()["purchases"], 1005)

    def test_three_modes_in_separate_processes(self) -> None:
        """세 모드가 별도 프로세스에서 끝나고 JSON에 무결성 확인과 정식 ID 발급 결과가 남는다."""
        with tempfile.TemporaryDirectory() as folder:
            for mode in ("time", "mem", "rss"):
                with self.subTest(mode=mode):
                    path = pathlib.Path(folder) / f"{mode}.json"
                    done = subprocess.run(
                        [sys.executable, "-B", str(_TOOL), mode, "120", "10", "1005",
                         *(["--repeat", "1"] if mode == "time" else []), "--json", str(path)],
                        cwd=folder, capture_output=True, text=True, check=True, timeout=2)
                    result = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(result["mode"], mode)
                    self.assertIs(result["integrity_verified"], True)
                    self.assertIn("무결성 확인: True", done.stdout)
                    if mode == "time":
                        changes = result["conditions"]
                        self.assertEqual(changes["recommendation"]["customer_id"], "C121")
                        self.assertEqual(changes["purchases"]["added_ids"], ["T1006"])
                        self.assertEqual(changes["changes"]["added_customer_ids"], ["C122"])

    def test_tool_uses_only_public_names(self) -> None:
        """도구 소스가 _로 시작하는 속성과 validation 모듈을 쓰지 않는다 (CLAUDE.md 운영 모듈 규칙)."""
        tree = ast.parse(_TOOL.read_text(encoding="utf-8"))
        private = sorted({node.attr for node in ast.walk(tree)
                          if isinstance(node, ast.Attribute) and node.attr.startswith("_")})
        self.assertEqual(private, [])
        imported = {alias.name.split(".")[0] for node in ast.walk(tree)
                    if isinstance(node, (ast.Import, ast.ImportFrom))
                    for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])}
        self.assertNotIn("validation", imported)
        self.assertIn("graph", imported)

    def test_run_mode_leaves_operating_rules_unchanged(self) -> None:
        """도구를 실행한 뒤에도 운영 ID 규칙이 그대로다: 고정 여섯 자리 ID는 거부된다."""
        bench = _load_tool()
        result = bench.run_mode("time", 20, 5, 30, repeat=1)
        self.assertIs(result["integrity_verified"], True)
        with self.assertRaises(ValueError):
            graph.ShopGraph([{"id": "C000001", "name": "가", "gender": "여", "age": 20}], [], [])


if __name__ == "__main__":
    unittest.main()
