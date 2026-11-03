---
name: draft
description: Draft the WBS outline, dictionary, or final export from workspace files.
disable-model-invocation: true
argument-hint: "outline | dictionary | export"
allowed-tools: Read Edit Write Bash(git add*) Bash(git commit*) Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/build_wbs.py*)
---

# /wbs:draft — stage: $ARGUMENTS

## Working style
- Targeted file edits only. No recaps after edits.
- Batched questions, each with a marked default.
- Decisions: Source user or stakeholder:name. Inferences go to docs/assumptions.md.
- [OPEN] marks unknown cells. Never invent facts. Max 15 words per cell; copy example rows' style.

## Inputs
Read only CLAUDE.md, docs/project.md, docs/requirements.md, docs/decisions.md, docs/assumptions.md and wbs/.
Never rely on chat history. If the stage is not outline, dictionary or export, ask which one (default: outline).
Follow the WBS rules in CLAUDE.md: 100% rule, deliverables as nouns, 8–80 h work packages with one owner,
numbering 1 / 1.1 / 1.1.1, max 4 levels.

## outline
1. Build levels 1–3 in wbs/wbs-outline.md from requirements and decisions only.
   Format: `- 1.2.1 Name`, 2-space indent per level, noun names.
2. Every requirement ID must have a home element; add one if missing. Verify before committing.
   (Req IDs are recorded per work package in the dictionary stage.)
3. Structure not backed by a requirement or decision: add a row to docs/assumptions.md (Status Open).
4. `git add -A && git commit -m "Draft WBS outline"`, then stop for my review.

## dictionary
1. Process one level-1 branch at a time, in numbering order, skipping branches already complete.
2. For each work package (lowest level) add one table row to wbs/wbs-dictionary.md:
   WBS ID | Name | Deliverable | Scope | Owner | Effort h | Duration d | Predecessors | Req IDs | Acceptance.
   Duration d = working days. Predecessors = finish-to-start WBS IDs, comma-separated.
3. Missing owner, effort, duration, predecessors or acceptance become [OPEN], never guesses.
   Add a row to docs/open-questions.md for each.
4. After each branch: `git add -A && git commit -m "Dictionary branch <ID>"`.

## export
Claude never writes export content itself; the script assembles it.
1. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/build_wbs.py --check` in the project folder.
2. If any line is BLOCK, list those lines and stop.
3. Otherwise run `python3 ${CLAUDE_SKILL_DIR}/scripts/build_wbs.py`.
   If it reports openpyxl missing, ask me before installing it (`pip install openpyxl`).
4. `git add -A && git commit -m "Export WBS"`
5. Reply only with the output paths the script printed.
