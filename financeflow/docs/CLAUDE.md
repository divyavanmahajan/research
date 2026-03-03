# docs/

This folder contains all documentation and screenshots for FinanceFlow.

## Contents

| File | Purpose |
|---|---|
| `getting-started.md` | Quick-start guide: prerequisites, setup options, first steps |
| `walkthrough.md` | Complete code walkthrough — data model, budget engine, every view |
| `user-walkthrough.md` | Visual user guide with annotated screenshots of each tab |
| `*.png` | Screenshots referenced by the user walkthrough |

## Conventions

- Write docs in Markdown (GitHub-flavored).
- Keep screenshots in this folder alongside the docs that reference them. Use relative paths (e.g. `![Dashboard](dashboard.png)`).
- Named screenshots (`dashboard.png`, `transactions.png`, etc.) are hand-curated and tracked in git.
- Auto-generated rodney screenshots use the pattern `{uuid}-{date}.png` and are ignored by `.gitignore`.
- When updating a screenshot, replace the file in place — keep the same filename so existing doc references stay valid.

## Adding new docs

1. Create a `.md` file in this folder.
2. Add screenshots here if needed and reference them with relative paths.
3. Link the new doc from `getting-started.md` under "Related files" if it's user-facing.
