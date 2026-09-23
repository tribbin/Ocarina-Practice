#!/usr/bin/env python3
# Full local test sweep: discovers every suite in tests/ (run_all excluded),
# runs them sequentially with the CURRENT interpreter (Robin's venv python —
# plain python3 lacks playwright; `tests/run_all.py` assumes the same
# interpreter the suites need), prints one PASS/FAIL line per suite plus the
# failing suites' tails, and cleans the __pycache__ the imports leave behind.
#
#   python tests/run_all.py
#   python tests/run_all.py kbd-ish        # substring filter on suite names
#
# Windows/Linux identical: only the interpreter invocation differs
# (see AGENTS.md "Commands").

import subprocess
import sys
import time
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SELF = Path(__file__).name


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else ""
    suites = sorted(p for p in TESTS.glob("*.py")
                    if p.name != SELF and not p.name.startswith("_"))
    if pattern:
        suites = [p for p in suites if pattern in p.name]
    if not suites:
        print("no suites match", pattern or "*")
        return 2

    passed, failures, tail_of = [], [], {}
    t_all = time.monotonic()
    for s in suites:
        t0 = time.monotonic()
        proc = subprocess.run([sys.executable, str(s)],
                              capture_output=True, text=True, timeout=900)
        dur = time.monotonic() - t0
        ok = proc.returncode == 0
        (passed if ok else failures).append(s.name)
        line = f"{'PASS' if ok else 'FAIL'} {s.name} ({dur:.0f}s)"
        print(line, flush=True)
        if not ok:
            tail = (proc.stdout + "\n" + proc.stderr).strip().splitlines()[-6:]
            tail_of[s.name] = "\n    ".join(tail)

    if Path(TESTS / "__pycache__").exists():
        import shutil
        shutil.rmtree(TESTS / "__pycache__", ignore_errors=True)

    print(f"== {len(passed)}/{len(suites)} pass "
          f"({time.monotonic() - t_all:.0f}s total) ==", flush=True)
    for name, tail in tail_of.items():
        print(f"\nFAIL tail — {name}:\n    {tail}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
