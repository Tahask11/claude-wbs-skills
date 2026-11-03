---
name: init
description: Scaffold a WBS workspace (git repo, CLAUDE.md, docs/, wbs/) from a project context.
disable-model-invocation: true
argument-hint: "\"<name; goal; audience; deadline; [start date; hours/day; holidays]>\""
allowed-tools: Read Write Edit Bash(git init*) Bash(git add*) Bash(git commit*) Bash(mkdir *) Bash(find *)
---

# /wbs:init

Project context: $ARGUMENTS

## Working style
- Targeted file edits only. No recaps after edits.
- Batched questions, each with a marked default.
- Decisions: Source user or stakeholder:name. Inferences go to docs/assumptions.md.
- [OPEN] marks unknown cells. Never invent facts. Max 15 words per cell; copy example rows' style.

## Step 1: Validate context
Required fields: name, goal, audience, deadline.
Optional (else [OPEN], asked in the first gather round): start date, hours/day, holidays.
If the context above is empty or any field is missing:
1. Read `${CLAUDE_SKILL_DIR}/USAGE.md` and print it verbatim.
2. Ask for every missing required field in ONE batched question; give a marked default
   where one is reasonable.
3. Stop. Create no files, run no commands, until all required fields are known.
Do not infer missing fields from the project name.

## Step 2: Scaffold (only when context is complete)
Work in the current directory. If it already contains CLAUDE.md, docs/ or wbs/, stop and ask before overwriting.
1. `git init` (skip if already a repo).
2. Copy the templates. For each path below, Read `${CLAUDE_SKILL_DIR}/templates/<path>` and Write
   its content unchanged to `<path>` in the project. Do not recreate files from memory:
   CLAUDE.md, docs/project.md, docs/requirements.md, docs/decisions.md, docs/assumptions.md,
   docs/open-questions.md, wbs/wbs-outline.md, wbs/wbs-dictionary.md
3. Replace placeholders with targeted edits:
   - CLAUDE.md: {{NAME}}, {{DEADLINE}}.
   - docs/project.md: {{NAME}}, {{GOAL}}, {{AUDIENCE}}, {{START}} (YYYY-MM-DD), {{HOURS}}, {{HOLIDAYS}}
     (ISO dates, comma-separated). Not given = [OPEN].
   - Other files: {{NAME}} only. Keep the "(example)" rows.
4. docs/decisions.md: append D-01 = deadline (Date today, Source user, Reason "Project context", Active).
5. docs/open-questions.md: one row (Q-05 onward, Status Open) per vague or ambiguous field.
6. `git add -A && git commit -m "Set up WBS workspace"`

## Step 3: Reply
1. The file tree (excluding .git), nothing else before it.
2. Read `${CLAUDE_SKILL_DIR}/USAGE.md` and print it verbatim.
