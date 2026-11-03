# WBS workflow
1. /wbs:init "<name; goal; audience; deadline>": set up the workspace.
2. /wbs:gather: one question round. Answer only where you disagree with the default. Repeat until it says gathering is complete.
3. /clear: drop the brainstorm from context. The files carry everything forward.
4. /wbs:draft outline: levels 1–3. Review and adjust before continuing.
5. /wbs:draft dictionary: work package details, one branch at a time.
6. /wbs:check: validation report, plus open assumptions for stakeholder review.
7. Take open assumptions to stakeholders; record outcomes as decisions with Source stakeholder:name.
8. /wbs:draft export: builds exports/WBS.xlsx and exports/WBS.md

## Sources at a glance
- [OPEN]: still unknown.
- Source user: you decided it (accepted defaults count).
- Source stakeholder:name: confirmed by that stakeholder.
- docs/assumptions.md: Claude's inferences, need review.

## Tips
- Use git diff to see what changed, since Claude won't recap.
- Use /context to check context size.
- Decision history: the Decisions sheet, or git log --oneline
- Resuming later: start a fresh session in the project folder and run the next step. No need to re-explain the project.
