"""X0 측정 도구 계약: 작은 데이터·별도 모드·시드 결정성·ID 패치 복구."""

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

import graph
from tools import bench


class BenchTests(unittest.TestCase):
    """운영 기대값을 바꾸지 않고 측정 도구의 실행 경계를 확인한다."""

    def test_seed_reproduces_records(self) -> None:
        """목적: 시드 결정성 확인. 인자/반환: 없음. 예외: 검증 실패."""
        first = bench.make_records(50, 10, 200, seed=1)
        self.assertEqual(first, bench.make_records(50, 10, 200, seed=1))
        self.assertNotEqual(first, bench.make_records(50, 10, 200, seed=2))
        self.assertEqual(tuple(map(len, first)), (50, 10, 200))

    def test_three_modes_in_separate_processes(self) -> None:
        """목적: 세 CLI 모드와 JSON 확인. 인자/반환: 없음. 예외: 실행/검증 실패."""
        script = pathlib.Path(bench.__file__).resolve()
        with tempfile.TemporaryDirectory() as directory:
            for mode in ("time", "mem", "rss"):
                with self.subTest(mode=mode):
                    output = pathlib.Path(directory) / f"{mode}.json"
                    result = subprocess.run(
                        [sys.executable, "-B", str(script), mode, "50", "10", "200",
                         "--repeat", "1", "--json", str(output)],
                        cwd=directory, capture_output=True, text=True,
                        check=True, timeout=2,
                    )
                    data = json.loads(output.read_text(encoding="utf-8"))
                    self.assertEqual(data["mode"], mode)
                    self.assertIn("Codex 자체 확인", result.stdout)
                    self.assertTrue(data["metrics"])
                    self.assertTrue(data["id_constants_restored"])
                    self.assertEqual(data["tracing_enabled"], mode == "mem")
                    for metric in data["metrics"].values():
                        self.assertEqual(metric["repeat"], 1)
                        self.assertGreaterEqual(metric["max"], metric["median"])
                        self.assertIn(metric["unit"], ("ms", "MB", "MiB"))

    def test_modes_restore_original_constants(self) -> None:
        """목적: 측정 후 원래 상수 객체 확인. 인자/반환: 없음. 예외: 실행/검증 실패."""
        patterns, digits = graph._ID_PATTERNS, graph._ID_DIGITS
        for mode in ("time", "mem", "rss"):
            bench.run_mode(mode, 50, 10, 200, repeat=1)
            self.assertIs(graph._ID_PATTERNS, patterns)
            self.assertIs(graph._ID_DIGITS, digits)
        self.assertEqual(dict(digits), {"C": 2, "P": 2, "T": 3})
        graph.ShopGraph([{"id": "C99", "name": "경계", "gender": "여", "age": 25}])
        with self.assertRaises(ValueError):
            graph.ShopGraph([{"id": "C000001", "name": "확장", "gender": "여", "age": 25}])

    def test_exception_restores_constants(self) -> None:
        """목적: 예외 때도 패치 복구 확인. 인자/반환: 없음. 예외: 검증 실패."""
        patterns, digits = graph._ID_PATTERNS, graph._ID_DIGITS
        with self.assertRaisesRegex(RuntimeError, "측정 중단"):
            with bench.measurement_ids():
                raise RuntimeError("측정 중단")
        self.assertIs(graph._ID_PATTERNS, patterns)
        self.assertIs(graph._ID_DIGITS, digits)
