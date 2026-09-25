#!/usr/bin/env python3
"""Structural moves for the practice board: plans/TODO.md + plans/DONE.md.

Stdlib only, LF-only, UTF-8 only. Invariants (checked by `verify`):
- every TODO item is ONE line: `- [ ] **Title** — body … `<risk> <circle>( <effort>)?``
- TODO carries no corpses (no `- [x]` lines); DONE carries no open items.
- Section heads ## 1. – ## 9. mirror between the two files.
- TODO's session log appends at the BOTTOM and reads old→new downward;
  log-retire keeps the LAST `keep` entries (the newest) and moves the older
  ones into DONE's log (they land oldest-first). Several sessions working
  one day still append — never hand-place an entry. verify guards the log:
  entry dates non-decreasing downward, no open items inside the log.
Text payloads come from --file (or `-` for stdin); PowerShell 5.1 mangles
emoji/§/backticks in argv, so anything but short ASCII prefixes and the
tag-word args must ride files. Prose stays hand-composed; THIS tool owns
the moves so no session hand-splices the board again.
"""

import argparse
import datetime
import itertools
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TODO = ROOT / "plans" / "TODO.md"
DONE = ROOT / "plans" / "DONE.md"

SEC_HEAD_RE = re.compile(r"^## (\d+)\. ")
TITLE_RE = re.compile(r"^- \[ \] \*\*(.+?)\*\*")
ENTRY_RE = re.compile(r"^- \*\*\d{4}-\d{2}-\d{2}")
TAGS_END_RE = re.compile(r"(`[🟥🟧🟨🟢🟩] [🔴🟠🟡⚪](?: ⚙[SML])?`)\s*$")

RISK = {"severe": "🟥", "moderate": "🟧", "minor": "🟨", "cosmetic": "🟢", "measure": "🟩"}
URGENCY = {"next": "🔴", "soon": "🟠", "later": "🟡", "idle": "⚪"}
EFFORT = {"s": "⚙S", "m": "⚙M", "l": "⚙L", "none": None}

LOG_STUB = "Older entries live in `plans/DONE.md` (session log)."


class BoardError(Exception):
    pass


def _read_lines(path):
    raw = path.read_bytes().decode("utf-8")
    if "\r" in raw:
        raise BoardError(f"{path.name}: CRLF found")
    return raw.split("\n")


def _write_lines(path, lines):
    # Structural writes leave the file with single blank lines: capped runs
    # here are exactly the accumulation the tool grew over time (the IDEAS
    # report, 2026-09-25 — insert seams stacked one blank per move). Every
    # write self-heals the file, so no run can survive a move; verify flags
    # anything still standing.
    lines = _collapse_blank_runs(lines)
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    path.write_bytes(text.encode("utf-8"))


def _collapse_blank_runs(lines):
    out = []
    for l in lines:
        if l == "" and out and out[-1] == "":
            continue
        out.append(l)
    return out


def _payload(args, single=False):
    # complete's CLI names its payload flag --notes-file; the generic
    # subcommands use --file. Both shapes must read through here.
    src = getattr(args, "file", None) or getattr(args, "notes_file", None)
    if src is None:
        raise BoardError("--file <path|-> is required for text payloads")
    text = sys.stdin.read() if src == "-" else Path(src).read_text(encoding="utf-8")
    text = text.strip("\n")
    if single and "\n" in text.strip():
        raise BoardError("payload must be a single line")
    if not text.strip():
        raise BoardError("empty payload")
    return text if not single else text.strip()


def _items(lines):
    items = []
    cur_sec = None
    for i, line in enumerate(lines):
        m = SEC_HEAD_RE.match(line)
        if m:
            cur_sec = int(m.group(1))
        if line.startswith("- [ ] "):
            tm = TITLE_RE.match(line)
            items.append({"i": i, "sec": cur_sec, "line": line,
                          "title": tm.group(1) if tm else None,
                          "bare": tm is None})
    return items


def _pick(items, title_prefix):
    hits = [t for t in items if t["title"] and t["title"].startswith(title_prefix)]
    if not hits:
        raise BoardError(f"no open item title starts with {title_prefix!r}")
    if len(hits) > 1:
        names = "\n  ".join(t["title"] for t in hits)
        raise BoardError(f"title prefix {title_prefix!r} is ambiguous:\n{names}")
    return hits[0]


def _section_bounds(lines, sec):
    start = next((i for i, l in enumerate(lines) if l.startswith(f"## {sec}. ")), None)
    if start is None:
        return None, None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## ") or lines[j].startswith("> ") or lines[j] == "---":
            end = j
            break
    return start, end


def _insert_point(lines, start, end):
    """Index to insert an item line at: section-content bottom (never after a
    trailing ---/blank run, never below a standing blockquote)."""
    k = end
    while k > start + 1 and (lines[k - 1] == "" or lines[k - 1] == "---"):
        k -= 1
    return k


def _insert_line(lines, path, sec, item_line):
    start, end = _section_bounds(lines, sec)
    if start is None:
        raise BoardError(f"{path.name}: section {sec} head missing")
    k = _insert_point(lines, start, end)
    prefix = [] if k > 0 and lines[k - 1] == "" else [""]
    lines[k:k] = prefix + [item_line, ""]
    return lines


def complete(todo, done_path, title_prefix, date=None, sha=None, notes=None):
    """Strike an open item, stamp ✅, move it into DONE's matching section."""
    date = date or datetime.date.today().isoformat()
    lines = _read_lines(todo)
    hit = _pick(_items(lines), title_prefix)
    body = hit["line"][len("- [ ] "):]
    if "~~" in body:
        raise BoardError(f"item body contains strikethrough markers: {hit['title']!r}")
    stamp = " ✅ " + date
    if sha:
        stamp += " `" + sha + "`"
    if notes:
        stamp += " — " + notes
    done_line = "- [x] ~~" + body + "~~" + stamp

    drop = {hit["i"]}
    if hit["i"] + 1 < len(lines) and lines[hit["i"] + 1] == "" and hit["i"] > 0 and lines[hit["i"] - 1] == "":
        drop.add(hit["i"] + 1)
    new_todo = [l for k, l in enumerate(lines) if k not in drop]

    dlines = _read_lines(done_path)
    if not any(l.startswith(f"## {hit['sec']}. ") for l in dlines):
        raise BoardError(f"plans/DONE.md: section {hit['sec']} head missing")
    dlines = _insert_line(dlines, done_path, hit["sec"], done_line)
    _write_lines(todo, new_todo)
    _write_lines(done_path, dlines)
    return f"complete: §{hit['sec']} {hit['title']!r} -> DONE {stamp.strip()}"


def add(todo, sec, item_line):
    if not item_line.startswith("- [ ] "):
        raise BoardError("new item must start with '- [ ] '")
    tm = TITLE_RE.match(item_line)
    if tm is None:
        raise BoardError("new item lacks a **Title** span")
    lines = _read_lines(todo)
    if any((TITLE_RE.match(l) or None) and TITLE_RE.match(l).group(1) == tm.group(1) for l in lines):
        raise BoardError(f"duplicate item title: {tm.group(1)!r}")
    lines = _insert_line(lines, todo, sec, item_line)
    _write_lines(todo, lines)
    return f"add: §{sec} {tm.group(1)!r}"


def note(todo, title_prefix, text):
    """Append a finding INSIDE the item line, before the trailing tag span."""
    lines = _read_lines(todo)
    hit = _pick(_items(lines), title_prefix)
    line = hit["line"]
    m = TAGS_END_RE.search(line)
    if m:
        new = line[:m.start()].rstrip() + " " + text + " " + m.group(1)
    else:
        new = line.rstrip() + " " + text
    lines[hit["i"]] = new
    _write_lines(todo, lines)
    return f"note: {hit['title']!r} (+{len(text)} chars)"


def tag(todo, title_prefix, risk, urgency, effort=None):
    try:
        span_body = RISK[risk] + " " + URGENCY[urgency]
    except KeyError as e:
        raise BoardError(f"unknown tag word: {e} (use {sorted(RISK)} x {sorted(URGENCY)} x {sorted(EFFORT)})")
    if effort is None:
        eff = None
    else:
        eff = EFFORT.get(effort, "BAD")
        if eff == "BAD":
            raise BoardError(f"unknown effort: {effort!r} (use {sorted(EFFORT)})")
    span = "`" + span_body + ((" " + eff) if eff else "") + "`"
    lines = _read_lines(todo)
    hit = _pick(_items(lines), title_prefix)
    line = hit["line"]
    m = TAGS_END_RE.search(line)
    lines[hit["i"]] = (line[:m.start()].rstrip() + " " + span) if m else (line.rstrip() + " " + span)
    _write_lines(todo, lines)
    return f"tag: {hit['title']!r} -> {span}"


def log_add(todo, payload_lines):
    lines = _read_lines(todo)
    try:
        head = lines.index("## Session log")
    except ValueError:
        raise BoardError("TODO.md: '## Session log' head missing")
    k = len(lines) - 1 if lines[-1] == "" else len(lines)
    if k > 0 and lines[k - 1].strip() != "":
        lines.insert(k, "")
        k += 1
    lines[k:k] = payload_lines
    _write_lines(todo, lines)
    return f"log-add: {len(payload_lines)} lines"


def log_retire(todo, done_path, keep=1):
    """Move all but the newest `keep` session-log entries into DONE's log."""
    lines = _read_lines(todo)
    try:
        head = lines.index("## Session log")
    except ValueError:
        raise BoardError("TODO.md: '## Session log' head missing")
    ents = [i for i in range(head + 1, len(lines)) if ENTRY_RE.match(lines[i])]
    if len(ents) <= keep:
        raise BoardError(f"nothing to retire: {len(ents)} entries, keep={keep}")
    blocks = [(ents[b], (ents[b + 1] if b + 1 < len(ents) else len(lines))) for b in range(len(ents))]
    move, kept = blocks[:-keep], blocks[-keep:]
    first_move, tail = move[0][0], kept[0][0]
    moved_lines = list(itertools.chain.from_iterable(lines[s:e] for s, e in move))
    new_todo = lines[:first_move] + lines[tail:]

    dlines = _read_lines(done_path)
    k = len(dlines) - 1 if dlines[-1] == "" else len(dlines)
    if k > 0 and dlines[k - 1].strip() != "":
        dlines.insert(k, "")
        k += 1
    dlines[k:k] = moved_lines
    _write_lines(todo, new_todo)
    _write_lines(done_path, dlines)
    return f"log-retire: {len(move)} entries -> DONE, kept {keep} in TODO"


def verify(todo, done_path):
    """Structural lint; returns (ok, report_lines)."""
    bad = []
    tl, dl = _read_lines(todo), _read_lines(done_path)

    def reg(cond, msg):
        if not cond:
            bad.append(msg)

    reg(not any(l.startswith("- [x] ") for l in tl), "TODO: struck corpse present")
    run = 0
    for i, l in enumerate(tl):
        run = run + 1 if l == "" else 0
        if run > 1:
            bad.append(f"TODO:{i + 1}: {run} consecutive blank lines — the "
                       "board carries single blanks (a structural write "
                       "collapses this; hand edits must not re-stack)")
    run = 0
    for i, l in enumerate(dl):
        run = run + 1 if l == "" else 0
        if run > 1:
            bad.append(f"DONE:{i + 1}: {run} consecutive blank lines — the "
                       "board carries single blanks")
    items = _items(tl)
    for t in items:
        if t["bare"]:
            bad.append(f"TODO:{t['i'] + 1}: open item lacks a parsed **Title**")
    titles = [t["title"] for t in items if not t["bare"]]
    for t in items:
        if not TAGS_END_RE.search(t["line"]):
            bad.append(f"TODO:{t['i'] + 1}: item lacks a trailing tag span")
        if "~~" in t["line"]:
            bad.append(f"TODO:{t['i'] + 1}: strikethrough inside an open item")
    dups = {x for x in titles if titles.count(x) > 1}
    for d in dups:
        bad.append(f"TODO: duplicate item title {d!r}")
    secs = [int(SEC_HEAD_RE.match(l).group(1)) for l in tl if SEC_HEAD_RE.match(l)]
    reg(secs == list(range(1, 10)), f"TODO: section heads not 1..9 in order ({secs})")
    for needle in ("# Ocarina Practice — Working TODO", "## Hot list", "## Session log", LOG_STUB):
        reg(any(needle in l for l in tl), f"TODO: missing {needle!r}")
    hot_start = next((i for i, l in enumerate(tl) if l.startswith("## Hot list")), None)
    if hot_start is not None:
        hot_end = next((i for i in range(hot_start + 1, len(tl)) if tl[i].startswith("## ")), len(tl))
        for i in range(hot_start, hot_end):
            if re.match(r"^\|\s*\d+\s*\|", tl[i]):
                bad.append(f"TODO:{i + 1}: numbered hot row")
        for i in range(hot_start, hot_end):
            if re.match(r"^- \[ \] ", tl[i]):
                bad.append(f"TODO:{i + 1}: open item inside the hot list")
    for i, l in enumerate(tl):
        m = SEC_HEAD_RE.match(l)
        if m:
            sec_end = next((j for j in range(i + 1, len(tl))
                            if SEC_HEAD_RE.match(tl[j]) or tl[j].startswith(("---", "## "))), len(tl))
            for j in range(i + 1, sec_end):
                ok = (tl[j].startswith(("- [ ] ", "> ", "Currently covered", "Nothing open"))
                      or tl[j] == "" or tl[j] == "---")
                reg(ok, f"TODO:{j + 1}: stray line inside §{m.group(1)}")
    # Session log: appended order (old→new downward), nothing open inside it.
    try:
        log_head = tl.index("## Session log")
    except ValueError:
        log_head = None
    if log_head is not None:
        log_tl = tl[log_head + 1:]
        # entry line shape is "- **2026-09-23 …" → the date sits at 5:15
        dates = [l[5:15] for l in log_tl if ENTRY_RE.match(l)]
        reg(dates == sorted(dates),
            "session log: entry dates out of appended order (a newer-dated entry "
            "sits above an older one — log-add appends at the bottom, never "
            "hand-place an entry)")
        reg(not any(l.startswith("- [ ] ") for l in log_tl),
            "session log: open item inside the session log")
    reg(not any(l.startswith("- [ ] ") for l in dl), "DONE: frozen open item(s) present")
    dsecs = [int(SEC_HEAD_RE.match(l).group(1)) for l in dl if SEC_HEAD_RE.match(l)]
    reg(dsecs == list(range(1, 10)), f"DONE: section heads not 1..9 in order ({dsecs})")
    reg(any(l == "## Session log" for l in dl), "DONE: '## Session log' head missing")
    return (not bad, bad or [f"board: ok ({len(items)} open items)"])


def main(argv=None):
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--todo", default=str(TODO))
    ap.add_argument("--done", default=str(DONE))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("complete")
    p.add_argument("--title", required=True)
    p.add_argument("--sha")
    p.add_argument("--date")
    p.add_argument("--notes-file")
    p = sub.add_parser("add")
    p.add_argument("--section", type=int, required=True)
    p.add_argument("--file", required=True)
    p = sub.add_parser("note")
    p.add_argument("--title", required=True)
    p.add_argument("--file", required=True)
    p = sub.add_parser("tag")
    p.add_argument("--title", required=True)
    p.add_argument("--risk", required=True, choices=sorted(RISK))
    p.add_argument("--urgency", required=True, choices=sorted(URGENCY))
    p.add_argument("--effort", choices=sorted(EFFORT), default="none")
    p = sub.add_parser("log-add")
    p.add_argument("--file", required=True)
    p = sub.add_parser("log-retire")
    p.add_argument("--keep", type=int, default=1)
    sub.add_parser("verify")
    args = ap.parse_args(argv)
    todo, done = Path(args.todo), Path(args.done)
    try:
        if args.cmd == "complete":
            print(complete(todo, done, args.title, args.date, args.sha,
                           _payload(args) if args.notes_file else None))
        elif args.cmd == "add":
            print(add(todo, args.section, _payload(args, single=True)))
        elif args.cmd == "note":
            print(note(todo, args.title, _payload(args, single=True)))
        elif args.cmd == "tag":
            print(tag(todo, args.title, args.risk, args.urgency, args.effort))
        elif args.cmd == "log-add":
            print(log_add(todo, _payload(args).split("\n")))
        elif args.cmd == "log-retire":
            print(log_retire(todo, done, args.keep))
        elif args.cmd == "verify":
            ok, report = verify(todo, done)
            print("\n".join(report))
            sys.exit(0 if ok else 1)
    except BoardError as e:
        print(f"board: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
