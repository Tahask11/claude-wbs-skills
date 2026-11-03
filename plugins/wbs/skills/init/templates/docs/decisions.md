# Decisions — {{NAME}}

Append-only. Never edit Decision or Reason of an existing row; only Status may change.
To change: add row with Supersedes = old ID; set old Status to "Superseded by D-xx".
Status: Active | Superseded by D-xx | Reversed. Source: user | stakeholder:name.

| ID | Date | Decision | Source | Reason | Status | Supersedes |
|---|---|---|---|---|---|---|
| D-00 (example) | 2027-01-04 | Move on weekend of 2027-03-20 | stakeholder:Anna | Minimises downtime | Active | |
