# Shared suite server: the byte-identical QuietHandler + ThreadingTCPServer
# block all browser suites used to copy, in ONE hardened place.
#
# The heal (CI run 36187303217 job 108243773139 — racks of
# BrokenPipeError tracebacks under a PASSING battery): when a browser tears
# down mid-GET the serving thread dies inside socketserver's response write
# and the default handle_error printed a full traceback for an EXPECTED
# teardown. handle_error here swallows ONLY the connection-teardown family
# (BrokenPipe/ConnectionReset/Aborted, the client-closed-mid-response class)
# and forwards everything else to the loud default — real handler failures
# still print (tests/suite_hardened.py pins both directions).
#
# Usage inside a suite:
#     from suite_server import start_server
#     httpd, port = start_server()

import http.server
import socketserver
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass


class SuiteServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, ConnectionError):
            return  # expected mid-response teardown: the browser closed on us
        super().handle_error(request, client_address)


def start_server():
    httpd = SuiteServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]
