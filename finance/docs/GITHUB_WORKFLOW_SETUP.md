# Claude Artifacts → GitHub Workflow Setup Guide

For repository: `divyavanmahajan/research` → `finance/` folder

---

## STEP 1: Initial Repository Setup

### If you don't have the repo locally yet:

```bash
# Navigate to your projects directory
cd ~/projects  # or your preferred location

# Clone the repository
git clone https://github.com/divyavanmahajan/research.git
cd research

# Create the finance folder if it doesn't exist
mkdir -p finance
cd finance

# Initialize git (if needed)
git status
```

### Create the folder structure:

```
finance/
├── README.md
├── .gitignore
├── components/          # React/Vue components
├── scripts/             # Python, Node.js, Bash scripts
├── utilities/           # Reusable functions/helpers
├── data/                # Data files, configs
└── docs/                # Documentation
```

---

## STEP 2: Export Artifacts from Claude

### For each artifact you create in Claude:

1. **Download the artifact**
   - Look for the download/export button in the artifact panel
   - Save with a descriptive name

2. **Organize by type**
   - React component → `components/ComponentName.jsx`
   - Python script → `scripts/script_name.py`
   - JavaScript utility → `utilities/helper_name.js`

---

## STEP 3: Commit Artifacts to GitHub

```bash
# Navigate to finance folder
cd ~/projects/research/finance

# Add all new artifacts
git add .

# Commit with descriptive message
git commit -m "Add [artifact-type]: [description]"

# Examples:
# git commit -m "Add React component: UserDashboard"
# git commit -m "Add Python script: Data processor for finance analysis"
# git commit -m "Add utility: CSV formatter for transaction data"

# Push to GitHub
git push origin main
```

---

## STEP 4: Reference Artifacts in Claude Code

### Option A: Clone within Claude Code Session

```bash
# In a Claude Code session
git clone https://github.com/divyavanmahajan/research.git
cd research/finance

# Now use files directly
python scripts/my_script.py
node scripts/my_script.js
```

### Option B: Import in JavaScript/Node.js

```javascript
// Direct file import
const { calculateMetrics } = require('./utilities/finance-helpers.js');

// Or with ES6
import { analyzeData } from './utilities/finance-helpers.js';
```

### Option C: Import in Python

```python
import sys
sys.path.append('./finance')

from utilities import finance_helpers
from scripts import data_processor

result = finance_helpers.calculate_metrics(data)
```

### Option D: Reference in React Components

```jsx
// If building a finance app in Claude Code
import UserDashboard from './components/UserDashboard.jsx';
import { formatCurrency } from './utilities/formatters.js';

export default function FinanceApp() {
  return <UserDashboard formatter={formatCurrency} />;
}
```

---

## STEP 5: Create a README for Your Finance Folder

Create `finance/README.md`:

```markdown
# Finance Artifacts & Tools

This folder contains Claude-generated artifacts and reusable tools for financial analysis and data processing.

## Structure

- **components/**: React components for finance dashboards and UIs
- **scripts/**: Standalone Python, Node.js, and Bash scripts
- **utilities/**: Reusable helper functions and formatters
- **data/**: Sample data files and configurations
- **docs/**: Documentation for specific tools

## Quick Start

### Running a Python Script
\`\`\`bash
python scripts/data_processor.py
\`\`\`

### Using in Node.js
\`\`\`javascript
const helpers = require('./utilities/finance-helpers.js');
\`\`\`

### Using in React
\`\`\`javascript
import Dashboard from './components/Dashboard.jsx';
\`\`\`

## Artifacts

| Name | Type | Purpose |
|------|------|---------|
| UserDashboard | React Component | Display financial metrics |
| data_processor | Python Script | Process CSV financial data |
| finance-helpers | JavaScript | Utility functions for calculations |

---

*Last updated: [date]*
```

---

## STEP 6: Create a .gitignore

Create `finance/.gitignore`:

```
# Node
node_modules/
npm-debug.log
package-lock.json

# Python
__pycache__/
*.py[cod]
*$py.class
.env
venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Data (optional - uncomment if you want to exclude large data files)
# *.csv
# *.xlsx
```

---

## STEP 7: Common Workflows

### Workflow A: Create New Artifact → Add to Repo

```
1. Create artifact in Claude chat
2. Download artifact file
3. Place in appropriate folder (components/, scripts/, utilities/)
4. Run: git add finance/
5. Run: git commit -m "Add [type]: [description]"
6. Run: git push origin main
```

### Workflow B: Use Existing Artifact in New Claude Code Session

```
1. In Claude Code session, run:
   git clone https://github.com/divyavanmahajan/research.git
   cd research/finance

2. Import the artifact you need:
   - JavaScript: require('./utilities/helper.js')
   - Python: from utilities import helper
   - React: import Component from './components/Component.jsx'

3. Build on top of it
```

### Workflow C: Update an Existing Artifact

```
1. Download the updated version from Claude
2. Replace the file in finance/
3. Commit: git commit -m "Update: [artifact-name] - [what changed]"
4. Push: git push origin main
```

---

## STEP 8: Best Practices

✅ **Do:**
- Use descriptive file names: `revenue_analyzer.py` not `script1.py`
- Add comments/docstrings to explain artifact purpose
- Keep related files together in appropriate folders
- Write meaningful commit messages
- Update README.md when adding new major artifacts
- Use semantic versioning in filenames if needed: `formatter_v2.js`

❌ **Don't:**
- Mix different artifact types in one file
- Use spaces in filenames (use underscores or hyphens)
- Commit without clear commit messages
- Leave artifacts undocumented
- Forget to push changes to GitHub

---

## STEP 9: Accessing Artifacts Later

### From Any Claude Code Session:

```bash
# Quick setup
git clone https://github.com/divyavanmahajan/research.git
cd research/finance

# View what's available
ls -la components/
ls -la scripts/
ls -la utilities/

# Use in your new artifact/code
python scripts/existing_script.py
node -e "const util = require('./utilities/helper.js'); console.log(util.doSomething())"
```

### Create a New Artifact Using Existing Code:

In Claude chat, ask:
```
"I want to create a new component that uses the UserDashboard component 
from my GitHub repo (divyavanmahajan/research/finance/components/UserDashboard.jsx). 
Can you help me extend it?"
```

Claude can then:
1. Ask you to share the code
2. OR clone the repo to read it
3. Build on top of it in a new artifact

---

## Troubleshooting

### "Permission denied" when pushing?
```bash
# Check your SSH key setup
ssh -T git@github.com

# If needed, add your SSH key or use HTTPS:
git remote set-url origin https://github.com/divyavanmahajan/research.git
```

### "File not found" when importing?
```bash
# Check current directory
pwd

# Verify file exists
ls -la utilities/helper.js

# Use correct relative paths
require('./utilities/helper.js')      # if in same folder level
require('../utilities/helper.js')     # if in subfolder
```

### Changes not showing on GitHub?
```bash
# Verify status
git status

# Make sure you committed AND pushed
git log --oneline -5  # see recent commits
git push origin main   # explicitly push
```

---

## Next Steps

1. ✅ Clone your repository locally
2. ✅ Create the `finance/` folder structure
3. ✅ Export your first artifact from Claude
4. ✅ Add it to the appropriate subfolder
5. ✅ Commit and push: `git add . && git commit -m "..." && git push`
6. ✅ In next Claude Code session, clone the repo and import!

You're all set! 🚀
