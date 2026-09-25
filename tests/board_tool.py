#!/usr/bin/env python3
"""Pure-stdlib tests for tools/board.py structural board moves.

No browser, no fixtures on disk: each case builds a sandbox TODO/DONE pair in
a temp dir and drives the tool's functions directly. Prints PASS/FAIL per
case; exits nonzero on any failure. (Runner supplies the UTF-8 child env;
standalone runs may need PYTHONUTF8=1 if glyphs ever get printed.)
"""

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("board", ROOT / "tools" / "board.py")
board = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(board)

_tmp = tempfile.mkdtemp(prefix="board-payload-")
tmp_txt = Path(_tmp) / "note.txt"
tmp_txt.write_text("note line\n", encoding="utf-8")


def write(path, lines):
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def read(path):
    return path.read_bytes().decode("utf-8").split("\n")


HEADS = ["## 1. Bugs (correctness / data loss)", "## 2. Robustness / error handling",
         "## 3. Security (low today — matters if data files become user-supplied)",
         "## 4. Performance", "## 5. Architecture / maintenance", "## 6. Tests & CI",
         "## 7. Accessibility & UX", "## 8. Housekeeping", "## 9. Functional ideas (features)"]


def todo_fixture():
    body = ["# Ocarina Practice — Working TODO", ""]
    for n, head in enumerate(HEADS, 1):
        body += [head, ""]
        if n == 1:
            body += ["- [ ] **Alpha bug** — first. `🟧 🟡 ⚙M`", ""]
        elif n == 2:
            body += ["- [ ] **Beta bug** — second, no tags yet", ""]
        elif n == 6:
            body += ["Currently covered (fixture): nothing here.", ""]
        elif n == 8:
            body += ["Nothing open — completed housekeeping is archived in `plans/DONE.md` §8.", ""]
        elif n == 9:
            body += ["- [ ] **Delta feature** — last, before standing note. `🟢 🟡 ⚙L`", "",
                     "> **Idle idea pool: `plans/IDEAS.txt`.** standing note.", ""]
    body += ["---", "", "## Hot list (importance across all types)", "",
             "| Item | Section |", "|---|---|", "| do the reno | §9 |", "",
             "---", "", "## Session log", "", board.LOG_STUB,
             "- **2026-09-23 (session X)** — old entry.",
             "- **2026-09-24 (session Y)** — older entry.",
             "- **2026-09-25 (session Z)** — newest entry."]
    return body


def done_fixture():
    lines = ["# Ocarina Practice — DONE (completed-work archive)", "", "preamble.", ""]
    for head in HEADS:
        lines += [head, "", "- [x] ~~**Old bug**~~ ✅ 2026-09-01 `abc` — history.", ""]
    lines += ["---", "", "## Session log", "", "Old archive entries."]
    return lines


def sandbox():
    d = tempfile.mkdtemp(prefix="board-")
    todo, done = Path(d) / "TODO.md", Path(d) / "DONE.md"
    write(todo, todo_fixture())
    write(done, done_fixture())
    return todo, done


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


def expect_error(fn, needle=None):
    try:
        fn()
    except board.BoardError as e:
        if needle:
            assert needle in str(e), f"wrong BoardError: {e}"
        return
    raise AssertionError("expected BoardError")


@case("complete moves item, strikes, sections correctly, blank-sandwiched")
def t1():
    todo, done = sandbox()
    msg = board.complete(todo, done, "Alpha bug", date="2026-09-24")
    assert "Alpha" in msg, msg
    tl = read(todo)
    assert not any("- [x] " in l for l in tl), "corpse left in TODO"
    assert not any("**Alpha bug**" in l for l in tl)
    dl = read(done)
    hits = [l for l in dl if "~~**Alpha bug**" in l]
    assert len(hits) == 1, hits
    assert hits[0].startswith("- [x] ~~**Alpha bug** — first. `🟧 🟡 ⚙M`~~ ✅ ") and hits[0].endswith("`🟧 🟡 ⚙M`~~ ✅ 2026-09-24"), hits[0]
    j = dl.index(hits[0])
    assert dl[j - 1] == "" and dl[j + 1] == "", "missing blank sandwich"
    # section placement: between "## 1." head and "## 2." head-block
    sec1 = next(i for i, l in enumerate(dl) if l.startswith("## 1. "))
    sec2 = next(i for i, l in enumerate(dl) if l.startswith("## 2. "))
    assert sec1 < j < sec2
    # idempotence: completing again refuses cleanly
    expect_error(lambda: board.complete(todo, done, "Alpha bug"), "no open item")


@case("complete refuses ambiguous prefix")
def t2():
    todo, done = sandbox()
    write(todo, read(todo))  # no-op
    # Alpha matches only one; make ambiguity by adding another Alpha item
    lines = read(todo)
    lines.insert(2, "")
    lines.insert(3, "- [ ] **Alpha twin** — another. `🟨 🟡 ⚙S`")
    lines.insert(4, "")
    write(todo, lines)
    expect_error(lambda: board.complete(todo, done, "Alpha"), "ambiguous")


@case("add appends to the right section, before §9 standing blockquote")
def t3():
    todo, done = sandbox()
    line = "- [ ] **Echo feature** — new. `🟢 ⚪`"
    board.add(todo, 9, line)
    tl = read(todo)
    j = tl.index(line)
    assert tl[j - 1] == "" and tl[j + 1] == ""
    bq = next(i for i, l in enumerate(tl) if l.startswith("> **Idle idea pool"))
    assert j < bq, "inserted after the standing blockquote"
    # duplicates refused
    expect_error(lambda: board.add(todo, 9, line), "duplicate")
    # bad item shapes refused
    expect_error(lambda: board.add(todo, 1, "- [x] **Todo corpse**"), "must start")
    expect_error(lambda: board.add(todo, 1, "- [ ] no title here"), "lacks")


@case("note inserts before trailing tags; falls back to line end without tags")
def t4():
    todo, done = sandbox()
    board.note(todo, "Alpha bug", "finding one: bad ref")
    board.note(todo, "Beta bug", "finding two: worse ref")
    tl = read(todo)
    a = next(l for l in tl if "**Alpha bug**" in l)
    assert a.endswith("` 🟧 🟡 ⚙M`") or a.endswith("`🟧 🟡 ⚙M`"), a
    assert "finding one: bad ref" in a and a.index("finding one") < a.index("`🟧")
    b = next(l for l in tl if "**Beta bug**" in l)
    assert b.rstrip().endswith("finding two: worse ref"), b


@case("tag re-scores the trailing span (with and without effort)")
def t5():
    todo, done = sandbox()
    board.note(todo, "Alpha bug", "note then retag")
    board.tag(todo, "Alpha bug", "severe", "next", "l")
    board.tag(todo, "Beta bug", "cosmetic", "idle")
    tl = read(todo)
    a = next(l for l in tl if "**Alpha bug**" in l)
    assert a.rstrip().endswith("`🟥 🔴 ⚙L`"), a
    assert "note then retag" in a and a.index("note") < a.index("`🟥")
    b = next(l for l in tl if "**Beta bug**" in l)
    assert b.rstrip().endswith("`🟢 ⚪`"), b
    expect_error(lambda: board.tag(todo, "Beta bug", "weird", "soon"), "unknown tag word")
    expect_error(lambda: board.tag(todo, "Beta bug", "minor", "soon", "q"), "unknown effort")


@case("verify is green on a clean board and names violations on broken ones")
def t6():
    todo, done = sandbox()
    board.tag(todo, "Beta bug", "minor", "later", "m")  # fixture Beta ships tagless
    ok, report = board.verify(todo, done)
    assert ok, report
    # corpse
    lines = read(todo)
    lines.insert(2, "- [x] ~~**Ghost**~~ ✅OLD")
    write(todo, lines)
    ok, report = board.verify(todo, done)
    assert not ok and any("corpse" in r for r in report), report
    # frozen open item in DONE
    todo, done = sandbox()
    board.tag(todo, "Beta bug", "minor", "later", "m")
    dl = read(done)
    dl[dl.index(HEADS[0]) + 2] = "- [ ] **Frozen** — should not be here. `🟢 ⚪`"
    write(done, dl)
    ok, report = board.verify(todo, done)
    assert not ok and any("frozen" in r for r in report), report
    # numbered hot row flagged
    tl = read(todo)
    tl[tl.index("| do the reno | §9 |")] = "| 1 | do the reno | §9 |"
    write(todo, tl)
    ok, report = board.verify(todo, done)
    assert not ok and any("numbered hot row" in r for r in report), report


@case("log-retire moves all but the newest entry into DONE")
def t7():
    todo, done = sandbox()
    board.log_retire(todo, done, keep=1)
    tl = read(todo)
    assert "session X" not in "\n".join(tl), "old entry stayed in TODO"
    assert any("**2026-09-25 (session Z)**" in l for l in tl), "newest entry moved away"
    assert any(board.LOG_STUB in l for l in tl), "log stub lost"
    dl = read(done)
    dt = "\n".join(dl)
    assert "session X" in dt and "session Y" in dt, "retired entries missing in DONE"
    assert "session Z" not in dt, "newest entry wrongly moved to DONE"
    # ordering preserved
    x = next(i for i, l in enumerate(dl) if "session X" in l)
    y = next(i for i, l in enumerate(dl) if "session Y" in l)
    assert x < y
    # keep too big refuses
    expect_error(lambda: board.log_retire(todo, done, keep=1), "nothing to retire")


@case("log-add appends below existing entries; CRLF bytes refused")
def t8():
    todo, done = sandbox()
    board.log_add(todo, ["- **2026-09-26 (session Q)**", "  - sub line"])
    tl = read(todo)
    j = tl.index("- **2026-09-26 (session Q)**")
    assert tl[j + 1] == "  - sub line"
    assert "\n".join(tl).rstrip().endswith("sub line")
    # CRLF refusal
    todo.write_bytes("# x\r\n- [ ] **R?** `🟢 ⚪`\r\n".encode("utf-8"))
    expect_error(lambda: board.note(todo, "R", "t"), "CRLF")


@case("payload reader honors the complete --notes-file wiring")
def t9():
    # the complete CLI carries its payload as args.notes_file; _payload must
    # read it (it only ever looked at args.file and raised --file-required)
    ns = SimpleNamespace(file=None, notes_file=None)
    try:
        board._payload(ns)
        raise AssertionError("empty args must refuse")
    except board.BoardError as e:
        assert "--file" in str(e), e
    ns = SimpleNamespace(file=None, notes_file=str(tmp_txt))
    assert board._payload(ns) == "note line"
    ns = SimpleNamespace(file=str(tmp_txt), notes_file=None)
    assert board._payload(ns) == "note line"


def main():
    failed = []
    for name, fn in CASES:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:
            failed.append(name)
            print(f"FAIL {name}: {type(e).__name__}: {e}")
    total = len(CASES)
    print(f"board_tool: {total - len(failed)}/{total} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
