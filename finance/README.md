# Finance — Reusable Artifacts

A collection of reusable React component templates, Python scripts, and JavaScript utility functions for finance-related UIs and data processing. Intended as a starter library for Claude Code sessions.

## Structure

```
finance/
├── components/                    React components
│   └── finance_component_template.jsx   Dashboard with metric cards
├── scripts/                       Standalone Python scripts
│   └── finance_script_template.py
├── utilities/                     Shared helper functions
│   └── finance_helpers_template.js      formatCurrency, calculateROI, etc.
├── data/                          Sample data and config files
└── docs/
    ├── QUICK_REFERENCE.md         Git workflow cheat sheet
    ├── GITHUB_WORKFLOW_SETUP.md   Detailed git workflow guide
    └── COMPLETE_EXAMPLE.md        End-to-end usage example
```

## Usage

### Use a component in React

```jsx
import FinanceDashboard from './components/finance_component_template.jsx';
```

### Use a utility in JS

```js
const { formatCurrency, calculateROI } = require('./utilities/finance_helpers_template.js');
```

### Use a utility in Python

```python
from scripts.finance_script_template import main
```

## Adding Artifacts

1. Place React components in `components/`
2. Place standalone scripts in `scripts/`
3. Place shared helper functions in `utilities/`
4. Place sample data or configs in `data/`

See [`docs/QUICK_REFERENCE.md`](docs/QUICK_REFERENCE.md) for the git workflow.
