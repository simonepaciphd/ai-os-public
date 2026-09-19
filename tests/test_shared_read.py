"""Native reads under real Windows sharing contention; disposable fixtures only."""
import ctypes
import errno
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime/src'))
from aios_native import sharded


class SharedReadTests(unittest.TestCase):
    def test_errno_only_transient_denial(self):
        path = Mock()
        path.read_bytes.side_effect = [PermissionError(errno.EACCES, 'fixture'), b'current']
        with patch.object(sharded, 'os', types.SimpleNamespace(name='nt')):
            self.assertEqual(sharded.shared_read(path), b'current')
        self.assertEqual(path.read_bytes.call_count, 2)

    def test_persistent_denial_still_raises_with_bounded_wait(self):
        path = Mock()
        failure = PermissionError(errno.EACCES, 'fixture')
        path.read_bytes.side_effect = failure
        elapsed = [0.0]
        def sleep(delay):
            self.assertGreater(delay, 0)
            elapsed[0] += delay
        fake_time = types.SimpleNamespace(monotonic=lambda: elapsed[0], sleep=sleep)
        with patch.object(sharded, 'os', types.SimpleNamespace(name='nt')), patch.object(sharded, 'time', fake_time):
            with self.assertRaises(PermissionError) as raised:
                sharded.shared_read(path)
        self.assertIs(raised.exception, failure)
        self.assertGreater(path.read_bytes.call_count, 1)
        self.assertAlmostEqual(elapsed[0], .25)

    def test_explicit_windows_sharing_errors(self):
        for code in (5, 32, 33):
            with self.subTest(winerror=code):
                failure = OSError(errno.EACCES, 'fixture')
                failure.winerror = code
                path = Mock()
                path.read_bytes.side_effect = [failure, b'ok']
                with patch.object(sharded, 'os', types.SimpleNamespace(name='nt')):
                    self.assertEqual(sharded.shared_read(path), b'ok')

    def test_other_errors_are_not_retried(self):
        cases = [('posix', PermissionError(errno.EACCES, 'fixture')),
                 ('nt', FileNotFoundError(errno.ENOENT, 'fixture')),
                 ('nt', OSError(errno.EIO, 'fixture'))]
        explicit = PermissionError(errno.EACCES, 'fixture')
        explicit.winerror = 123
        cases.append(('nt', explicit))
        for platform, failure in cases:
            with self.subTest(platform=platform, error=repr(failure)):
                path = Mock()
                path.read_bytes.side_effect = failure
                with patch.object(sharded, 'os', types.SimpleNamespace(name=platform)):
                    with self.assertRaises(OSError) as raised:
                        sharded.shared_read(path)
                self.assertIs(raised.exception, failure)
                self.assertEqual(path.read_bytes.call_count, 1)

    @unittest.skipUnless(os.name == 'nt', 'actual Windows sharing semantics')
    def test_actual_windows_exclusive_handle(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'
            path.write_bytes(b'current-state')
            handle, close = exclusive_handle(path)
            try:
                with self.assertRaises(PermissionError) as raised:
                    path.read_bytes()
                self.assertEqual(raised.exception.errno, errno.EACCES)
                self.assertIsNone(getattr(raised.exception, 'winerror', None))
                timer = threading.Timer(.05, close)
                timer.start()
                try:
                    self.assertEqual(sharded.shared_read(path), b'current-state')
                finally:
                    timer.join()
            finally:
                close()

    @unittest.skipUnless(os.name == 'nt', 'actual Windows sharing semantics')
    def test_posttooluse_routing_recovers_without_replaying_tool(self):
        import test_close_recovery as lifecycle
        fixture = lifecycle.CloseRecoveryTests('test_close_verification')
        fixture.setUp()
        try:
            path = fixture.bk.root/'activations'/(fixture.sid+'.json')
            handle, close = exclusive_handle(path)
            timer = threading.Timer(.05, close)
            timer.start()
            try:
                code, output, stderr = fixture.cli(event='PostToolUse')
            finally:
                timer.join()
                close()
            self.assertEqual((code, output, stderr), (0, {}, ''))
            self.assertEqual(fixture.bk._session(fixture.sid)['status'], 'active')
        finally:
            fixture.tearDown()

    @unittest.skipUnless(os.name == 'nt', 'actual Windows sharing semantics')
    def test_persistent_posttooluse_denial_fails_closed(self):
        import test_close_recovery as lifecycle
        fixture = lifecycle.CloseRecoveryTests('test_close_verification')
        fixture.setUp()
        try:
            path = fixture.bk.root/'activations'/(fixture.sid+'.json')
            before = path.read_bytes()
            handle, close = exclusive_handle(path)
            try:
                code, output, stderr = fixture.cli(event='PostToolUse')
            finally:
                close()
            self.assertEqual(code, 0)
            self.assertFalse(output['continue'])
            self.assertIn('publication not-attempted', output['stopReason'])
            self.assertIn('permission-denied', stderr)
            self.assertEqual(path.read_bytes(), before)
        finally:
            fixture.tearDown()


def exclusive_handle(path):
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                               ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    api.CreateFileW.restype = ctypes.c_void_p
    api.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = api.CreateFileW(str(path), 0x80000000, 0, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    opened = [True]
    def close():
        if opened[0]:
            opened[0] = False
            if not api.CloseHandle(handle):
                raise ctypes.WinError(ctypes.get_last_error())
    return handle, close


if __name__ == '__main__':
    unittest.main()
