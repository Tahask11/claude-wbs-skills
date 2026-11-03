#!/usr/bin/env python3
"""Build WBS exports from the Markdown working files in the current project.

Usage:
  build_wbs.py --check   print a compact issues list only (exit 1 if blocking issues)
  build_wbs.py           write exports/WBS.xlsx and exports/WBS.md

Working files (Markdown tables) are the single source of truth.
Rows containing "(example)" are ignored. Cells equal to [OPEN] count as empty.
"""
import datetime as dt
import re
import sys
from pathlib import Path

WORD_LIMIT = 15
HEADER_NOTE = "Generated from working files. Edit the source files, not this file."
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

FILES = {
    "project": ("docs/project.md", ["Key", "Value"]),
    "requirements": ("docs/requirements.md", ["ID", "Requirement", "Source", "Priority"]),
    "decisions": ("docs/decisions.md",
                  ["ID", "Date", "Decision", "Source", "Reason", "Status", "Supersedes"]),
    "assumptions": ("docs/assumptions.md",
                    ["ID", "Assumption", "Impact if false", "Validate with", "Status", "Related IDs"]),
    "questions": ("docs/open-questions.md", ["ID", "Question", "Blocks (IDs)", "Status"]),
    "dictionary": ("wbs/wbs-dictionary.md",
                   ["WBS ID", "Name", "Deliverable", "Scope", "Owner", "Effort h", "Duration d",
                    "Predecessors", "Req IDs", "Acceptance"]),
}
OUTLINE = "wbs/wbs-outline.md"


class Issues:
    def __init__(self):
        self.rows = []

    def add(self, blocking, rule, element, problem):
        self.rows.append(("BLOCK" if blocking else "WARN", rule, element, problem))

    @property
    def blocking(self):
        return [r for r in self.rows if r[0] == "BLOCK"]


# ---------- parsing ----------

def blank(v):
    return v is None or v.strip() == "" or v.strip().upper() in ("[OPEN]", "-", "—")


def split_ids(v):
    if blank(v):
        return []
    return [x.strip() for x in re.split(r"[,;]", v) if x.strip() and not blank(x)]


def parse_table(path, columns, issues):
    p = Path(path)
    if not p.exists():
        issues.add(True, "Missing file", path, "file not found")
        return []
    rows, header = [], None
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = cells
            if len(cells) != len(columns):
                issues.add(True, "Malformed table", path,
                           f"expected {len(columns)} columns, found {len(cells)}")
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        if any("(example)" in c for c in cells):
            continue
        if len(cells) != len(columns):
            issues.add(True, "Malformed table", f"{path}:{n}",
                       f"expected {len(columns)} cells, found {len(cells)}")
            cells = (cells + [""] * len(columns))[: len(columns)]
        rows.append(dict(zip(columns, cells), _file=path, _line=n))
    return rows


def parse_outline(issues):
    p = Path(OUTLINE)
    if not p.exists():
        issues.add(True, "Missing file", OUTLINE, "file not found")
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if "(example)" in line:
            continue
        m = re.match(r"^\s*(?:[-*+]\s+)?(\d+(?:\.\d+)*)\.?\s+(.+?)\s*$", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def parse_date(v):
    try:
        return dt.date.fromisoformat(v.strip())
    except (ValueError, AttributeError):
        return None


def parse_workdays(v):
    if blank(v):
        return {0, 1, 2, 3, 4}
    s = v.lower().replace("–", "-").replace("—", "-")
    s = re.sub(r"\(.*?\)", "", s)
    days = set()
    for part in re.split(r"[,;/ ]+", s):
        if not part:
            continue
        if "-" in part:
            a, b = (x[:3] for x in part.split("-", 1))
            if a in DAYS and b in DAYS:
                i, j = DAYS.index(a), DAYS.index(b)
                days.update(range(i, j + 1) if i <= j else list(range(i, 7)) + list(range(0, j + 1)))
        elif part[:3] in DAYS:
            days.add(DAYS.index(part[:3]))
    return days or {0, 1, 2, 3, 4}


def num(v):
    if blank(v):
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def fmt_num(x):
    return "" if x is None else (str(int(x)) if float(x).is_integer() else f"{x:g}")


# ---------- model ----------

class Model:
    def __init__(self):
        self.issues = Issues()
        t = {k: parse_table(path, cols, self.issues) for k, (path, cols) in FILES.items()}
        self.tables = t
        self.project = {r["Key"]: r["Value"] for r in t["project"]}
        self.reqs = t["requirements"]
        self.decisions = t["decisions"]
        self.assumptions = t["assumptions"]
        self.questions = t["questions"]
        self.wps = {r["WBS ID"]: r for r in t["dictionary"]}
        self.outline = parse_outline(self.issues)
        self.start = parse_date(self.project_value("Start date"))
        self.workdays = parse_workdays(self.project_value("Workdays"))
        self.holidays = set()
        for h in split_ids(self.project_value("Holidays")):
            d = parse_date(h)
            if d:
                self.holidays.add(d)
            elif h.lower() not in ("none", "n/a"):
                self.issues.add(False, "Bad holiday", "docs/project.md", f"not an ISO date: {h}")
        self.build_tree()

    def project_value(self, prefix):
        for k, v in self.project.items():
            if k.lower().startswith(prefix.lower()):
                return v
        return ""

    def build_tree(self):
        names = {}
        for i, n in self.outline:
            names.setdefault(i, n)
        for i, r in self.wps.items():
            names.setdefault(i, r["Name"])
        ids = set(names)
        # add implicit ancestors
        for i in list(ids):
            parts = i.split(".")
            for k in range(1, len(parts)):
                a = ".".join(parts[:k])
                if a not in ids:
                    ids.add(a)
                    names[a] = "[OPEN]"
        key = lambda i: [int(x) for x in i.split(".")]
        self.order = sorted(ids, key=key)
        self.names = names
        self.children = {i: [] for i in self.order}
        for i in self.order:
            if "." in i:
                self.children[i.rsplit(".", 1)[0]].append(i)
        self.leaves = [i for i in self.order if not self.children[i]]
        self.level = {i: i.count(".") + 1 for i in self.order}

    def descendants_leaves(self, i):
        if not self.children.get(i):
            return [i]
        out = []
        for c in self.children[i]:
            out += self.descendants_leaves(c)
        return out

    # ----- calendar -----
    def is_workday(self, d):
        return d.weekday() in self.workdays and d not in self.holidays

    def next_workday(self, d, inclusive=True):
        if not inclusive:
            d += dt.timedelta(days=1)
        while not self.is_workday(d):
            d += dt.timedelta(days=1)
        return d

    def add_workdays(self, start, n):
        """Finish date of a task starting on `start` lasting n working days."""
        d = start
        for _ in range(max(int(round(n)) - 1, 0)):
            d = self.next_workday(d, inclusive=False)
        return d

    # ----- schedule -----
    def schedule(self):
        self.sched, self.cycle = {}, None
        preds = {}
        for i, r in self.wps.items():
            ps = []
            for p in split_ids(r["Predecessors"]):
                if p in self.children:
                    ps += [x for x in self.descendants_leaves(p) if x in self.wps]
            preds[i] = ps
        # cycle detection (DFS)
        state = {}

        def visit(n, stack):
            if self.cycle:
                return
            state[n] = 1
            stack.append(n)
            for p in preds.get(n, []):
                if state.get(p) == 1:
                    self.cycle = stack[stack.index(p):] + [p]
                    return
                if state.get(p) is None:
                    visit(p, stack)
            stack.pop()
            state[n] = 2

        for n in self.wps:
            if state.get(n) is None:
                visit(n, [])
        if self.cycle or not self.start:
            return
        first = self.next_workday(self.start)
        done = {}

        def calc(n):
            if n in done:
                return done[n]
            dur = num(self.wps[n]["Duration d"])
            pf = [calc(p) for p in preds[n]]
            if dur is None or any(x is None for x in pf):
                done[n] = None
                return None
            s = self.next_workday(max(f for _, f in pf), inclusive=False) if pf else first
            f = self.add_workdays(s, dur) if dur >= 1 else s
            done[n] = (s, f)
            return done[n]

        for n in self.wps:
            calc(n)
        for n, v in done.items():
            if v:
                self.sched[n] = v
        # roll up parents
        for i in reversed(self.order):
            if self.children[i]:
                kids = self.children[i]
                ss = [self.sched[k][0] for k in kids if k in self.sched]
                ff = [self.sched[k][1] for k in kids if k in self.sched]
                if ss:
                    self.sched[i] = (min(ss), max(ff))

    def effort_of(self, i):
        if not self.children[i]:
            return num(self.wps[i]["Effort h"]) if i in self.wps else None
        vals = [self.effort_of(c) for c in self.children[i]]
        vals = [v for v in vals if v is not None]
        return sum(vals) if vals else None

    # ----- checks -----
    def check(self):
        iss = self.issues
        for key, rows in self.tables.items():
            for r in rows:
                for col, v in r.items():
                    if col.startswith("_"):
                        continue
                    if len(v.split()) > WORD_LIMIT:
                        el = r.get("ID") or r.get("WBS ID") or r.get("Key") or f"line {r['_line']}"
                        iss.add(False, "Word limit", f"{el}", f"{r['_file']} {col}: {len(v.split())} words")
        if not self.start:
            iss.add(True, "Start date", "docs/project.md", "missing or not YYYY-MM-DD")
        if not self.wps:
            iss.add(True, "No work packages", "wbs/wbs-dictionary.md", "dictionary is empty")
        req_ids = {r["ID"] for r in self.reqs}
        covered = {}
        for i, r in self.wps.items():
            for q in split_ids(r["Req IDs"]):
                covered.setdefault(q, []).append(i)
                if q not in req_ids:
                    iss.add(False, "Unknown req", i, f"cites unknown requirement {q}")
        for r in self.reqs:
            if r["ID"] not in covered:
                iss.add(False, "Gap", r["ID"], "not covered by any work package")
        self.covered = covered
        outline_ids = {i for i, _ in self.outline}
        for i, r in self.wps.items():
            if not split_ids(r["Req IDs"]):
                iss.add(False, "Scope creep", i, "cites no requirement")
            e = num(r["Effort h"])
            if e is None:
                iss.add(False, "Effort", i, "effort missing")
            elif not 8 <= e <= 80:
                iss.add(False, "Effort", i, f"{fmt_num(e)} h outside 8–80")
            if blank(r["Owner"]):
                iss.add(False, "Owner", i, "owner missing")
            if num(r["Duration d"]) is None:
                iss.add(False, "Duration", i, "duration missing")
            for p in split_ids(r["Predecessors"]):
                if p not in self.children:
                    iss.add(True, "Unknown predecessor", i, f"predecessor {p} not in WBS")
            if self.children.get(i):
                iss.add(False, "Not a work package", i, "dictionary row has child elements")
            if outline_ids and i not in outline_ids:
                iss.add(False, "Outline", i, "dictionary row missing from outline")
        if self.wps:
            for i in self.leaves:
                if i not in self.wps and i in outline_ids:
                    iss.add(False, "Dictionary", i, "outline leaf has no dictionary row")
        for i in self.order:
            if self.level[i] > 4:
                iss.add(False, "Depth", i, "deeper than 4 levels")
        self.schedule()
        if self.cycle:
            iss.add(True, "Cycle", self.cycle[0], "dependency cycle (← = waits on): " + " ← ".join(self.cycle))
        dec_ids = {d["ID"]: d for d in self.decisions}
        for d in self.decisions:
            s = d["Supersedes"]
            for old in split_ids(s):
                if old not in dec_ids:
                    iss.add(False, "Decision log", d["ID"], f"supersedes unknown {old}")
                elif not dec_ids[old]["Status"].lower().startswith("superseded"):
                    iss.add(False, "Decision log", old, f"superseded by {d['ID']} but Status not updated")
        for q in self.questions:
            if q["Status"].strip().lower() == "open" or blank(q["Status"]):
                iss.add(False, "Open question", q["ID"], q["Question"])
        for a in self.assumptions:
            if a["Status"].strip().lower() == "open" or blank(a["Status"]):
                iss.add(False, "Open assumption", a["ID"], a["Assumption"])
        return iss

    def open_questions(self):
        return [q for q in self.questions if q["Status"].strip().lower() in ("open", "", "[open]")]

    def open_assumptions(self):
        return [a for a in self.assumptions if a["Status"].strip().lower() in ("open", "", "[open]")]


# ---------- export helpers ----------

def summary_rows(m):
    rows = [(k, v) for k, v in m.project.items()]
    roots = [i for i in m.order if m.level[i] == 1]
    total = sum(e for e in (m.effort_of(r) for r in roots) if e is not None)
    ss = [m.sched[i] for i in m.leaves if i in m.sched]
    rows += [
        ("Total effort h", int(total) if float(total).is_integer() else total),
        ("Work packages", len(m.wps)),
        ("Requirements", len(m.reqs)),
        ("Project start", min(s for s, _ in ss).isoformat() if ss else "[OPEN]"),
        ("Project finish", max(f for _, f in ss).isoformat() if ss else "[OPEN]"),
        ("Unscheduled work packages", len([i for i in m.wps if i not in m.sched])),
        ("Open questions", len(m.open_questions())),
        ("Open assumptions", len(m.open_assumptions())),
    ]
    return rows


WBS_COLS = ["WBS ID", "Name", "Level", "Deliverable", "Scope", "Owner", "Effort h", "Duration d",
            "Predecessors", "Req IDs", "Acceptance", "Start", "Finish"]


def wbs_rows(m):
    out = []
    for i in m.order:
        r = m.wps.get(i, {})
        s, f = m.sched.get(i, (None, None))
        parent = bool(m.children[i])
        out.append({
            "WBS ID": i, "Name": m.names[i], "Level": m.level[i],
            "Deliverable": r.get("Deliverable", ""), "Scope": r.get("Scope", ""),
            "Owner": r.get("Owner", ""),
            "Effort h": m.effort_of(i),
            "Duration d": None if parent else num(r.get("Duration d", "")),
            "Predecessors": r.get("Predecessors", ""), "Req IDs": r.get("Req IDs", ""),
            "Acceptance": r.get("Acceptance", ""), "Start": s, "Finish": f, "_parent": parent,
        })
    return out


def trace_rows(m):
    return [(r["ID"], r["Requirement"], r["Priority"], ", ".join(m.covered.get(r["ID"], [])))
            for r in m.reqs]


def open_item_rows(m):
    rows = [("Question", q["ID"], q["Question"], q["Blocks (IDs)"], q["Status"]) for q in m.open_questions()]
    rows += [("Assumption", a["ID"], a["Assumption"], a["Related IDs"], a["Status"]) for a in m.open_assumptions()]
    return rows


def week_starts(m):
    ss = [m.sched[i] for i in m.order if i in m.sched]
    if not ss:
        return []
    s = min(x for x, _ in ss)
    f = max(y for _, y in ss)
    w = s - dt.timedelta(days=s.weekday())
    out = []
    while w <= f:
        out.append(w)
        w += dt.timedelta(days=7)
    return out


# ---------- xlsx ----------

def write_xlsx(m, path):
    from openpyxl import Workbook
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    bold = Font(bold=True)
    head_fill = PatternFill("solid", fgColor="D9E1F2")
    grey_font = Font(color="808080", italic=True)
    grey_fill = PatternFill("solid", fgColor="EDEDED")
    red_fill = PatternFill("solid", fgColor="F8CBAD")
    date_fmt = "yyyy-mm-dd"

    wb = Workbook()
    wb.remove(wb.active)

    def sheet(title, headers, rows, widths=None):
        ws = wb.create_sheet(title)
        ws.append([HEADER_NOTE])
        ws["A1"].font = grey_font
        ws.append(headers)
        for c in ws[2]:
            c.font = bold
            c.fill = head_fill
        for r in rows:
            ws.append(list(r))
        ws.freeze_panes = "A3"
        last = get_column_letter(len(headers))
        ws.auto_filter.ref = f"A2:{last}{max(ws.max_row, 2)}"
        for idx, h in enumerate(headers, 1):
            col = get_column_letter(idx)
            if widths and h in widths:
                w = widths[h]
            else:
                vals = [len(str(h))] + [len(str(r[idx - 1])) for r in rows if r[idx - 1] is not None]
                w = min(max(vals) + 2, 50)
            ws.column_dimensions[col].width = w
            if w >= 40:
                for row in ws.iter_rows(min_row=3, min_col=idx, max_col=idx):
                    row[0].alignment = Alignment(wrap_text=True, vertical="top")
        return ws

    # 1 Summary
    sheet("Summary", ["Key", "Value"], summary_rows(m))

    # 2 WBS
    wr = wbs_rows(m)
    ws = sheet("WBS", WBS_COLS, [[r[c] for c in WBS_COLS] for r in wr],
               widths={"Start": 12, "Finish": 12})
    for n, r in enumerate(wr, 3):
        ws.cell(n, 2).alignment = Alignment(indent=r["Level"] - 1)
        for c in (12, 13):
            ws.cell(n, c).number_format = date_fmt
        if r["_parent"]:
            for c in ws[n]:
                c.font = bold

    # 3 Gantt
    weeks = week_starts(m)
    ws = wb.create_sheet("Gantt")
    ws.append([HEADER_NOTE])
    ws["A1"].font = grey_font
    ws.append(["WBS ID", "Name", "Start", "Finish"] + weeks)
    for c in ws[2]:
        c.font = bold
        c.fill = head_fill
    for c in ws[2][4:]:
        c.number_format = "dd-mmm"
        c.alignment = Alignment(text_rotation=90)
    parent_rows, leaf_rows = [], []
    for n, i in enumerate(m.order, 3):
        ws.cell(n, 1, i)
        ws.cell(n, 2, m.names[i]).alignment = Alignment(indent=m.level[i] - 1)
        if m.children[i]:
            # parent dates roll up from the rows below, so edits to child dates propagate
            last = n + len([d for d in m.order if d.startswith(i + ".")])
            ws.cell(n, 3, f'=IF(COUNT(C{n+1}:C{last})=0,"",MIN(C{n+1}:C{last}))')
            ws.cell(n, 4, f'=IF(COUNT(D{n+1}:D{last})=0,"",MAX(D{n+1}:D{last}))')
            for c in ws[n][:4]:
                c.font = bold
            parent_rows.append(n)
        else:
            s, f = m.sched.get(i, (None, None))
            ws.cell(n, 3, s)
            ws.cell(n, 4, f)
            leaf_rows.append(n)
        ws.cell(n, 3).number_format = date_fmt
        ws.cell(n, 4).number_format = date_fmt
    ws.freeze_panes = "E3"
    last_col = get_column_letter(4 + max(len(weeks), 1))
    ws.auto_filter.ref = f"A2:{last_col}{max(ws.max_row, 2)}"
    for col, w in zip("ABCD", (10, 30, 12, 12)):
        ws.column_dimensions[col].width = w
    for k in range(len(weeks)):
        ws.column_dimensions[get_column_letter(5 + k)].width = 4
    if weeks:
        fc = get_column_letter(5)
        for rows, color in ((parent_rows, "305496"), (leaf_rows, "9BC2E6")):
            if rows:
                # relative refs are anchored to the first cell of the rule's range
                r0 = rows[0]
                formula = f'AND(ISNUMBER($C{r0}),ISNUMBER($D{r0}),{fc}$2<=$D{r0},{fc}$2+6>=$C{r0})'
                rng = " ".join(f"E{r}:{last_col}{r}" for r in rows)
                ws.conditional_formatting.add(
                    rng, FormulaRule(formula=[formula], fill=PatternFill("solid", fgColor=color,
                                                                          bgColor=color)))

    # 4 Assumptions
    cols = FILES["assumptions"][1]
    sheet("Assumptions", cols, [[a[c] for c in cols] for a in m.assumptions])

    # 5 Decisions
    cols = FILES["decisions"][1]
    ws = sheet("Decisions", cols, [[d[c] for c in cols] for d in m.decisions])
    for n, d in enumerate(m.decisions, 3):
        if d["Status"].strip().lower() != "active":
            for c in ws[n]:
                c.font = grey_font
                c.fill = grey_fill

    # 6 Traceability
    ws = sheet("Traceability", ["Req ID", "Requirement", "Priority", "Work packages"], trace_rows(m))
    for n, r in enumerate(trace_rows(m), 3):
        if not r[3]:
            for c in ws[n]:
                c.fill = red_fill

    # 7 Open Items
    sheet("Open Items", ["Type", "ID", "Item", "Blocks / Related", "Status"], open_item_rows(m))

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


# ---------- markdown ----------

def md_table(headers, rows):
    def cell(v):
        if isinstance(v, dt.date):
            return v.isoformat()
        if isinstance(v, float):
            return fmt_num(v)
        return "" if v is None else str(v).replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(out) if rows else out[0] + "\n" + out[1] + "\n| " + " | ".join(["—"] * len(headers)) + " |"


def mermaid_text(s):
    return re.sub(r"[:;#]", " ", s).strip() or "Task"


def write_md(m, path):
    name = m.project_value("Name") or "Project"
    L = [f"# WBS — {name}", "", f"_{HEADER_NOTE}_", ""]
    L += ["## Summary", "", md_table(["Key", "Value"], summary_rows(m)), ""]
    L += ["## WBS", ""]
    for r in wbs_rows(m):
        indent = "  " * (r["Level"] - 1)
        txt = f"**{r['WBS ID']} {r['Name']}**" if r["_parent"] else f"{r['WBS ID']} {r['Name']}"
        L.append(f"{indent}- {txt}")
    L.append("")
    cols = [c for c in WBS_COLS if c != "Level"]
    L += ["### Work package details", "",
          md_table(cols, [[r[c] for c in cols] for r in wbs_rows(m) if not r["_parent"]]), ""]
    L += ["## Gantt", "", "```mermaid", "gantt", f"    title {mermaid_text(name)}",
          "    dateFormat YYYY-MM-DD", "    axisFormat %d %b"]
    off = [DAY_NAMES[d] for d in range(7) if d not in m.workdays]
    excl = off + sorted(h.isoformat() for h in m.holidays)
    if excl:
        L.append("    excludes " + ", ".join(excl))
    for root in [i for i in m.order if m.level[i] == 1]:
        tasks = [i for i in m.descendants_leaves(root) if i in m.sched and i in m.wps]
        if not tasks:
            continue
        L.append(f"    section {mermaid_text(root + ' ' + m.names[root])}")
        for i in tasks:
            s, _ = m.sched[i]
            d = num(m.wps[i]["Duration d"])
            tid = "t" + i.replace(".", "_")
            label = mermaid_text(f"{i} {m.names[i]}")
            if d < 1:
                L.append(f"    {label} :milestone, {tid}, {s.isoformat()}, 0d")
            else:
                L.append(f"    {label} :{tid}, {s.isoformat()}, {fmt_num(d)}d")
    L += ["```", ""]
    cols = FILES["assumptions"][1]
    L += ["## Assumptions", "", md_table(cols, [[a[c] for c in cols] for a in m.assumptions]), ""]
    cols = FILES["decisions"][1]
    rows = []
    for d in m.decisions:
        r = [d[c] for c in cols]
        if d["Status"].strip().lower() != "active":
            r = [f"~~{v}~~" if v and c != "Status" else v for v, c in zip(r, cols)]
        rows.append(r)
    L += ["## Decisions", "", md_table(cols, rows), ""]
    tr = [(a, b, c, w or "**NOT COVERED**") for a, b, c, w in trace_rows(m)]
    L += ["## Traceability", "", md_table(["Req ID", "Requirement", "Priority", "Work packages"], tr), ""]
    L += ["## Open Items", "", md_table(["Type", "ID", "Item", "Blocks / Related", "Status"],
                                         open_item_rows(m)), ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L), encoding="utf-8")


# ---------- main ----------

def main(argv):
    check_only = "--check" in argv
    m = Model()
    iss = m.check()
    if check_only:
        if not iss.rows:
            print("No issues.")
        else:
            print("Severity | Rule | Element | Problem")
            for r in sorted(iss.rows, key=lambda r: r[0] != "BLOCK"):
                print(" | ".join(r))
        return 1 if iss.blocking else 0
    if iss.blocking:
        print("Blocking issues; run --check for details.", file=sys.stderr)
        for r in iss.blocking:
            print(" | ".join(r), file=sys.stderr)
        return 1
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("openpyxl is not installed (pip install openpyxl).", file=sys.stderr)
        return 2
    xlsx, md = Path("exports/WBS.xlsx"), Path("exports/WBS.md")
    write_xlsx(m, xlsx)
    write_md(m, md)
    print(xlsx)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
