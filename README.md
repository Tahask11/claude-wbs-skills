# WBS plugin for Claude Code

A plugin that turns Claude Code into a work breakdown structure (WBS) assistant.
It scaffolds a project workspace, gathers requirements in batched question rounds,
drafts the outline and dictionary, validates the result and builds `exports/WBS.xlsx`
and `exports/WBS.md` from Markdown working files.

Commands (run only when you type them): `/wbs:init`, `/wbs:gather`, `/wbs:draft`, `/wbs:check`.
Workflow: `plugins/wbs/skills/init/USAGE.md`. The export needs Python 3 and `openpyxl`.

Replace `<owner>` below with the GitHub account that holds this repository.

## Install for you, in every project on a computer

```bash
claude plugin install wbs --marketplace <owner>/claude-wbs-skills
```

Inside a session: `/plugin install wbs --marketplace <owner>/claude-wbs-skills`

## Install for one repository only

Run in the repository:

```bash
claude plugin install wbs --marketplace <owner>/claude-wbs-skills --scope project
```

This writes `enabledPlugins` to `.claude/settings.json`. Commit it; each collaborator
runs the same command once on their machine.

## Claude Code cloud sessions

Cloud sessions don't load locally installed or repo-enabled plugins. Add this line to the
cloud environment's setup script:

```bash
claude plugin install wbs --marketplace <owner>/claude-wbs-skills && pip install -q openpyxl
```

If this repository is private, also add it under Repositories in the environment settings.

## Update

```bash
claude plugin marketplace update wbs-marketplace && claude plugin update wbs@wbs-marketplace
```
