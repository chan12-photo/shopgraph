"""UI8 연결 시간 제한의 설정과 실제 HTTP 회귀를 확인한다."""

import socket
import threading
import time
import unittest
from urllib.request import urlopen

from tests.fixtures import make_graph
import web


class TestUI8WebStability(unittest.TestCase):
    """단일 처리 서버가 유휴 연결 뒤에도 정상 요청을 처리한다."""

    def test_idle_connection_does_not_block_server(self) -> None:
        """무전송 연결은 응답 없이 닫히고 다른 GET은 4초 안에 200을 받는다."""
        server = web.create_server(make_graph(), port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        idle = None
        thread.start()
        try:
            with self.assertLogs("web", level="INFO") as logs:
                idle = socket.create_connection(server.server_address, timeout=1)
                started = time.monotonic()
                address = f"http://127.0.0.1:{server.server_address[1]}/api/stats"
                try:
                    with urlopen(address, timeout=3.5) as response:
                        self.assertEqual(response.status, 200)
                        response.read()
                except TimeoutError:
                    self.fail("유휴 연결 때문에 /api/stats 응답이 시간 안에 오지 않음")
                self.assertLess(time.monotonic() - started, 4)
                idle.settimeout(0.5)
                try:
                    remaining = idle.recv(1)
                except ConnectionError:
                    remaining = b""
                self.assertEqual(remaining, b"", "유휴 연결은 오류 응답 없이 닫혀야 함")
            self.assertTrue(any("Request timed out" in line for line in logs.output))
        finally:
            if idle is not None:
                idle.close()
            try:
                server.shutdown()
                thread.join(timeout=2)
            finally:
                server.server_close()

    def test_handler_timeout_is_set(self) -> None:
        """요청 핸들러의 연결 시간 제한은 2초다."""
        self.assertEqual(web._RequestHandler.timeout, 2)
