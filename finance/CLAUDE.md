# Finance — Claude Code Guide

## Project Overview

A library of reusable finance-related code artifacts: React components, Python scripts, and JS utility functions. No server, no build step — just drop-in templates.

## Folder Conventions

| Folder | Contents | File type |
|---|---|---|
| `components/` | React UI components | `.jsx` |
| `scripts/` | Standalone runnable scripts | `.py`, `.js`, `.sh` |
| `utilities/` | Importable helper functions | `.js`, `.py` |
| `data/` | Sample CSVs, JSON configs | `.csv`, `.json` |
| `docs/` | Guides and workflow docs | `.md` |

## Adding New Artifacts

When the user asks to create a finance component, script, or utility:
1. Place it in the appropriate subfolder
2. Name it descriptively (not `artifact1.jsx`)
3. Add a comment at the top describing what it does

## Key Existing Files

- `components/finance_component_template.jsx` — Dashboard with metric cards (balance, expenses, savings, investments)
- `utilities/finance_helpers_template.js` — `formatCurrency`, `calculateROI` and other helpers
- `scripts/finance_script_template.py` — Python script template for data processing

## No Build Required

Files can be imported directly. For React components, assume the consuming project handles bundling.
