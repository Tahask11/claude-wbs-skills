---
name: check
description: Read-only WBS validation; reports issues and open assumptions for stakeholder review.
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash(python3 *build_wbs.py --check)
---

# /wbs:check — read-only

## Working style
- Read-only: edit nothing, commit nothing. Do not fix anything unless I ask.
- No recaps or commentary beyond the output below.
- Never invent facts. Report what the files say.

## Step 1: Script checks
Run `python3 ${CLAUDE_SKILL_DIR}/../draft/scripts/build_wbs.py --check` in the project folder.
It covers word limits, requirement gaps, work packages citing no requirement, effort outside 8–80 h,
missing owners or durations, unknown predecessors, cycles, open questions and open assumptions.
Keep every line it prints; do not re-check those rules yourself.

## Step 2: Judgement checks (only what a script can't do)
Read wbs/wbs-outline.md and wbs/wbs-dictionary.md (Name, Deliverable, Scope).
1. Activity name: element named as an activity (verb or gerund, e.g. "Design…", "Testing")
   instead of a deliverable noun.
2. Sibling overlap: two siblings whose Scope or Deliverable overlap (100% rule, no double counting).

## Output
One compact Markdown table, nothing before it, script issues first:

| Rule | Element | Problem |
|------|---------|---------|

Prefix the Rule with BLOCK for blocking script issues. One row per issue.
If there are no issues, output a single row: `| — | — | No issues |`.

Then the heading `## For stakeholder review` and every assumption with Status Open
from docs/assumptions.md, one line each: `A-xx: <Assumption> (validate with <Validate with>)`.
If there are none, write `None.`
