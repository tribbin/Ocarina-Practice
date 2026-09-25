#!/usr/bin/env python3
# The suite-server teardown noise (IDEAS paste, CI run 36187303217 job
# 108243773139 — racks of BrokenPipeError tracebacks under a PASSING battery):
# every suite carries the same copied server block; when the browser tears
# down mid-GET the serving thread dies inside socketserver's copyfileobj and
# ThreadingTCPServer.handle_error prints a full traceback for an EXPECTED
# teardown. The class fix is one shared hardened server (tests/suite_server.py)
# that all suites import: handle_error swallows ONLY the connection-teardown
# family and forwards everything else to the default loud path.
#
# Legs (pure python, no browser):
#   1. the shared start_server survives a mid-GET client abort SILENTLY
#      (no traceback on stderr) and answers the next request fine;
#   2. the shared handle_error stays LOUD for real failures — a handler
#      defect still lands the traceback (the "without hiding real failures"
#      half of the contract).
#
#   python3 tests/suite_hardened.py

import socket
import sys
import threading
from contextlib import redirect_stderr
from io import StringIO

import suite_server


def _drain_to_baseline(baseline, timeout=3.0):
    # request threads return to the pool: wait until the thread count is
    # back at its reading level (poll, never a fixed sleep)
    import time
    t0 = time.monotonic()
    while threading.active_count() > baseline and time.monotonic() - t0 < timeout:
        time.sleep(0.05)


def _get(port, path, abort=False):
    s = socket.create_connection(("127.0.0.1", port), timeout=2)
    s.send((f"GET {path} HTTP/1.1\r\nHost: suite-test\r\n"
            "Connection: close\r\n\r\n").encode())
    if abort:
        s.recv(16)        # response headers start flowing...
        s.close()         # ...and the client dies mid-GET (the teardown class)
        return None
    chunks = []
    try:
        while True:
            b = s.recv(8192)
            if not b:
                break
            chunks.append(b)
    finally:
        s.close()
    return b"".join(chunks)


def main():
    failures = []
    baseline = threading.active_count()
    httpd, port = suite_server.start_server()
    err = StringIO()
    try:
        with redirect_stderr(err):
            _get(port, "/index.html", abort=True)
            _drain_to_baseline(baseline + 1)
        if "Traceback" in err.getvalue() or "BrokenPipe" in err.getvalue():
            failures.append("expected teardown printed to stderr — the noise "
                            "the CI paste showed: " + err.getvalue()[:400])
        body = _get(port, "/index.html")
        html = (body or b"").split(b"\r\n\r\n", 1)
        if len(html) < 2 or not html[1].startswith(b"<!DOCTYPE html>"):
            failures.append("server did not answer a normal request after "
                            "the teardown-race client")
    finally:
        httpd.shutdown()
        httpd.server_close()

    # Real failures stay loud: a handler defect prints its traceback.
    class BrokenHandler(suite_server.QuietHandler):
        def do_GET(self):
            # no try/except — the exception propagates into the server's
            # process-request thread and lands on handle_error (the loud
            # default for anything outside the connection-teardown family)
            raise RuntimeError("deliberate handler defect (suite pin)")

    import time
    httpd2 = suite_server.SuiteServer(("127.0.0.1", 0), BrokenHandler)
    threading.Thread(target=httpd2.serve_forever, daemon=True).start()
    port2 = httpd2.server_address[1]
    s2 = socket.create_connection(("127.0.0.1", port2), timeout=2)
    err2 = StringIO()
    got_loud = None
    try:
        with redirect_stderr(err2):
            s2.send(b"GET /boom HTTP/1.1\r\nHost: suite-test\r\n\r\n")
            # the traceback prints on the serving thread: keep the redirect
            # window open until the needle lands (poll, 3 s cap)
            t0 = time.monotonic()
            while time.monotonic() - t0 < 3:
                if "deliberate handler defect" in err2.getvalue():
                    got_loud = True
                    break
                time.sleep(0.05)
    finally:
        s2.close()
        httpd2.shutdown()
        httpd2.server_close()
    if not got_loud:
        failures.append("a REAL handler failure was silenced — the shared "
                        "hardening hides defects: " + err2.getvalue()[:400])

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  - " + f)
        return 1
    print("\nPASS: the shared suite server swallows mid-GET teardown "
          "(BrokenPipe/ConnectionReset) silently, keeps serving, and stays "
          "loud for real handler failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
