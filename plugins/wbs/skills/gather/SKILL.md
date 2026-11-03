---
name: gather
description: Run one batched question round to resolve [OPEN] gaps in a WBS workspace.
disable-model-invocation: true
allowed-tools: Read Edit Bash(git add*) Bash(git commit*) Bash(git log*) Bash(grep *)
---

# /wbs:gather — one question round per invocation

## Working style
- Targeted file edits only. No recaps after edits.
- Batched questions, each with a marked default.
- Answers go to docs/decisions.md (Source user or stakeholder:name). Inferences go to docs/assumptions.md.
- [OPEN] marks unknown cells. Never invent facts. Max 15 words per cell; copy example rows' style.

## Phase A: Ask
1. Read CLAUDE.md, docs/project.md, docs/open-questions.md, docs/assumptions.md, wbs/wbs-outline.md.
2. Remaining = questions with Status Open + [OPEN] cells in docs/project.md.
   If 0, reply exactly `Gathering complete. Run /clear, then /wbs:draft outline.` and stop.
3. If Start date, Hours/day or Holidays in docs/project.md is [OPEN], include those questions
   in this round (default suggestions: next Monday, 8 h/day, national public holidays as dates).
4. Fill the round with the open gaps that most change WBS structure
   (level-1 deliverables, scope boundaries, phases, owners/teams, constraints) over detail.
5. Ask 5–8 numbered questions in one message. Multiple-choice (a/b/c) where possible.
   Mark one option per question `(default)`; for free-text questions, propose a default.
   Say: answer only where you disagree; unanswered questions take the default.
6. Stop and wait for my answers. Edit nothing yet.

## Phase B: Record (after I answer)
Targeted edits only; never add facts I did not give.
1. docs/project.md: fill answered Key values (dates YYYY-MM-DD).
2. docs/requirements.md: new rows, next free ID (R-01, R-02 ...).
3. docs/decisions.md: append one row per decision: next D-ID, Date today, Source user
   (explicit answers and accepted defaults alike), Reason, Status Active.
   Changing an earlier decision: new row with Supersedes = old ID; on the old row change only
   Status to "Superseded by D-xx". Never edit an old Decision or Reason.
4. docs/assumptions.md: one row per thing you inferred rather than heard (next A-ID, Status Open).
5. wbs/wbs-outline.md: adjust structure the answers settle.
6. docs/open-questions.md: set resolved rows to Answered; add new Open rows the answers revealed.
7. N = 1 + count of `git log --oneline --grep="^Gather round"`.
   `git add -A && git commit -m "Gather round N: <new D- and A- IDs, comma-separated>"`
8. Reply with one line only: `<remaining> open items remaining.`
   If 0, reply instead: `Gathering complete. Run /clear, then /wbs:draft outline.`
