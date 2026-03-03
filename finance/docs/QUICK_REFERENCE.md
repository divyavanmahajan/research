# Quick Reference: Claude Artifacts → GitHub Workflow

## TL;DR - Essential Commands

### 1. First Time Setup
```bash
git clone https://github.com/divyavanmahajan/research.git
cd research/finance
mkdir -p {components,scripts,utilities,data,docs}
```

### 2. After Creating an Artifact in Claude
```bash
# Download artifact → save to appropriate folder

cd ~/projects/research/finance
git add .
git commit -m "Add [component/script/utility]: [description]"
git push origin main
```

### 3. Using Artifact in Claude Code Session
```bash
git clone https://github.com/divyavanmahajan/research.git
cd research/finance

# Now use your artifacts:
python scripts/my_script.py
node -e "const utils = require('./utilities/finance-helpers.js')"
```

---

## Folder Structure at a Glance

```
finance/
├── components/          # React/Vue components
│   ├── Dashboard.jsx
│   └── DataChart.jsx
├── scripts/             # Standalone executable scripts
│   ├── processor.py
│   ├── analyzer.js
│   └── report_gen.sh
├── utilities/           # Reusable helper functions
│   ├── finance-helpers.js
│   ├── formatters.js
│   └── validators.py
├── data/                # Sample data, configs
│   ├── sample.csv
│   └── config.json
├── docs/                # Documentation
│   └── HOW_TO_USE.md
├── README.md
└── .gitignore
```

---

## Import Examples

### Python
```python
# Import from utilities
from utilities.finance_helpers import calculate_roi

result = calculate_roi(invested=10000, gained=2500)
print(f"ROI: {result}%")
```

### JavaScript/Node.js
```javascript
// Require from utilities
const { formatCurrency, calculateROI } = require('./utilities/finance-helpers.js');

const formatted = formatCurrency(1234.56);
const roi = calculateROI(10000, 2500);
```

### React Component
```jsx
import Dashboard from './components/Dashboard.jsx';
import { formatCurrency } from './utilities/finance-helpers.js';

export default function App() {
  return <Dashboard formatter={formatCurrency} />;
}
```

---

## Git Commit Message Templates

**When adding a new artifact:**
```bash
git commit -m "Add [type]: [artifact-name] - [brief description]"

# Examples:
git commit -m "Add component: RevenueDashboard - displays monthly revenue metrics"
git commit -m "Add script: csv_processor.py - processes transaction data"
git commit -m "Add utility: finance-helpers.js - calculation functions"
```

**When updating an artifact:**
```bash
git commit -m "Update: [artifact-name] - [what changed]"

# Examples:
git commit -m "Update: Dashboard - added export functionality"
git commit -m "Update: csv_processor.py - improved error handling"
```

**When fixing a bug:**
```bash
git commit -m "Fix: [artifact-name] - [what was fixed]"

# Examples:
git commit -m "Fix: finance-helpers.js - corrected compound interest calculation"
```

---

## Common Tasks

### Add a new React component
1. Create in Claude as artifact
2. Download → `finance/components/YourComponent.jsx`
3. `git add finance/components/YourComponent.jsx`
4. `git commit -m "Add component: YourComponent - [description]"`
5. `git push origin main`

### Add a new Python script
1. Create in Claude as artifact
2. Download → `finance/scripts/your_script.py`
3. `git add finance/scripts/your_script.py`
4. `git commit -m "Add script: your_script.py - [description]"`
5. `git push origin main`

### Add a utility function
1. Create/modify → `finance/utilities/helper.js` (or .py)
2. `git add finance/utilities/helper.js`
3. `git commit -m "Add utility: helper - [functions added]"`
4. `git push origin main`

### Use existing artifact in new Claude Code session
```bash
git clone https://github.com/divyavanmahajan/research.git
cd research/finance

# View available artifacts
ls -la components/
ls -la scripts/
ls -la utilities/

# Import and use in your code
const helpers = require('./utilities/finance-helpers.js');
```

---

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| **"fatal: not a git repository"** | Run `git init` or check you're in the right directory |
| **"permission denied"** | Make sure you have SSH key set up or use HTTPS URLs |
| **"Your branch is ahead by X commits"** | Run `git push origin main` to push changes |
| **"file not found" when importing** | Check file path - use `ls -la` to verify file exists |
| **Can't find my artifact on GitHub** | Make sure you ran `git push origin main` |
| **Python import not working** | Add to top: `import sys; sys.path.append('./finance')` |

---

## Pro Tips

✅ **Best Practices:**
- Always write descriptive commit messages
- Organize files by type (components, scripts, utilities)
- Add comments/docstrings to code
- Keep README.md updated with artifact list
- Test imports before pushing
- Use meaningful file names (not "artifact1.js")

🚀 **Speed Up:**
```bash
# Create an alias for your common command
alias pushfinance='cd ~/projects/research && git add finance/ && git commit -m "Update finance artifacts" && git push origin main'

# Then just run:
pushfinance
```

📚 **Documentation:**
- Keep `finance/README.md` updated with what each artifact does
- Add inline comments in complex code
- Create `finance/docs/` for detailed guides

---

## Next Action

👉 **Choose one of these:**

1. **Just getting started?**
   - Run first-time setup commands above
   - Download one artifact and push it

2. **Have existing artifacts?**
   - Create the folder structure
   - Download and organize all artifacts
   - Do one big commit

3. **Ready to use in Claude Code?**
   - Clone the repo in Claude Code session
   - Import an artifact
   - Build something new with it!

---

**Questions?** Refer back to `GITHUB_WORKFLOW_SETUP.md` for detailed explanations!
