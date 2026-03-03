# Complete Example: Using GitHub Artifacts in Claude Code

This document shows a real-world example of creating artifacts in Claude, pushing them to GitHub, and then using them in a Claude Code session.

---

## Scenario: Build a Finance Analytics Dashboard

### Step 1: Create Artifacts in Claude (Main Chat)

**Artifact 1: Utility Functions**
```javascript
// finance/utilities/finance-helpers.js
function formatCurrency(amount, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(amount);
}

function calculateROI(invested, gained) {
  if (invested === 0) return 0;
  return Number(((gained / invested) * 100).toFixed(2));
}

module.exports = { formatCurrency, calculateROI };
```

**Artifact 2: React Dashboard Component**
```jsx
// finance/components/FinanceDashboard.jsx
import React, { useState } from 'react';

export default function FinanceDashboard() {
  const [portfolio] = useState({
    invested: 10000,
    currentValue: 12500,
    income: 5000,
    expenses: 3000
  });

  const roi = ((portfolio.currentValue - portfolio.invested) / portfolio.invested * 100).toFixed(2);
  const savings = portfolio.income - portfolio.expenses;

  return (
    <div className="p-8 bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-6">Financial Dashboard</h1>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-gray-600 text-sm">ROI</p>
          <p className="text-2xl font-bold text-green-600">{roi}%</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-gray-600 text-sm">Monthly Savings</p>
          <p className="text-2xl font-bold text-blue-600">${savings}</p>
        </div>
      </div>
    </div>
  );
}
```

**Artifact 3: Data Processing Script**
```python
# finance/scripts/analyze_investments.py
import json

def analyze_portfolio(investments):
    """Analyze investment portfolio performance."""
    total_invested = sum(inv['amount'] for inv in investments)
    total_current = sum(inv['current_value'] for inv in investments)
    
    return {
        'total_invested': total_invested,
        'total_current': total_current,
        'total_gain': total_current - total_invested,
        'roi_percent': round((total_current - total_invested) / total_invested * 100, 2),
        'investments_count': len(investments)
    }

if __name__ == "__main__":
    sample_data = [
        {'name': 'Stock A', 'amount': 5000, 'current_value': 5500},
        {'name': 'Stock B', 'amount': 3000, 'current_value': 3200},
        {'name': 'Bond C', 'amount': 2000, 'current_value': 2150}
    ]
    
    analysis = analyze_portfolio(sample_data)
    print(json.dumps(analysis, indent=2))
```

---

### Step 2: Organize and Push to GitHub

**Local folder structure:**
```
finance/
├── components/
│   └── FinanceDashboard.jsx
├── utilities/
│   └── finance-helpers.js
├── scripts/
│   └── analyze_investments.py
├── README.md
└── .gitignore
```

**Push to GitHub:**
```bash
cd ~/projects/research/finance

# Download all three artifacts and place them above

git add components/ utilities/ scripts/
git commit -m "Add: Finance dashboard components, utilities, and analysis script"
git push origin main
```

---

### Step 3: Use in Claude Code Session

**New Claude Code session:**

```bash
# Step 1: Clone your repository
git clone https://github.com/divyavanmahajan/research.git
cd research/finance

# Step 2: View what's available
ls -la components/
ls -la utilities/
ls -la scripts/
```

**Example 1: Use Python script to analyze data**

```bash
python scripts/analyze_investments.py

# Output:
# {
#   "total_invested": 10000,
#   "total_current": 10850,
#   "total_gain": 850,
#   "roi_percent": 8.5,
#   "investments_count": 3
# }
```

**Example 2: Use JavaScript utilities in Node.js**

```javascript
// test_utilities.js
const { formatCurrency, calculateROI } = require('./utilities/finance-helpers.js');

console.log("=== Finance Calculator ===");
console.log(`Investment value: ${formatCurrency(10000)}`);
console.log(`Current value: ${formatCurrency(10850)}`);
console.log(`ROI: ${calculateROI(10000, 850)}%`);

// Output:
// === Finance Calculator ===
// Investment value: $10,000.00
// Current value: $10,850.00
// ROI: 8.5%
```

```bash
node test_utilities.js
```

**Example 3: Create new React app using existing component**

```jsx
// finance/app.jsx
import React from 'react';
import FinanceDashboard from './components/FinanceDashboard.jsx';
import { formatCurrency, calculateROI } from './utilities/finance-helpers.js';

export default function App() {
  return (
    <div>
      <FinanceDashboard />
      
      <div className="p-8 bg-white">
        <h2 className="text-xl font-bold mb-4">Calculator</h2>
        <p>Formatted: {formatCurrency(12500)}</p>
        <p>ROI: {calculateROI(10000, 2500)}%</p>
      </div>
    </div>
  );
}
```

**Example 4: Create a new Python script that uses existing Python code**

```python
# finance/scripts/advanced_analysis.py
import json
import sys
sys.path.append('../')

# Import the analysis function
from scripts.analyze_investments import analyze_portfolio

# Extend with additional analysis
def full_financial_report(investments, monthly_income, monthly_expenses):
    """Generate comprehensive financial report."""
    
    # Get portfolio analysis
    portfolio = analyze_portfolio(investments)
    
    # Add income/expense analysis
    monthly_savings = monthly_income - monthly_expenses
    annual_savings = monthly_savings * 12
    
    return {
        'portfolio': portfolio,
        'monthly_savings': monthly_savings,
        'annual_savings': annual_savings,
        'savings_rate': round((monthly_savings / monthly_income) * 100, 2)
    }

if __name__ == "__main__":
    data = [
        {'name': 'Stock A', 'amount': 5000, 'current_value': 5500},
        {'name': 'Bond B', 'amount': 5000, 'current_value': 5350}
    ]
    
    report = full_financial_report(
        investments=data,
        monthly_income=5000,
        monthly_expenses=3000
    )
    
    print(json.dumps(report, indent=2))
```

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE CHAT: Create Artifacts                              │
│  - React component                                          │
│  - Python script                                            │
│  - JavaScript utilities                                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  LOCAL: Organize & Commit                                   │
│  - Download artifacts                                       │
│  - Place in finance/components/, finance/scripts/, etc.    │
│  - git add, commit, push                                    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  GITHUB: Store                                              │
│  - Repository: divyavanmahajan/research                     │
│  - Folder: finance/                                         │
│  - Accessible from anywhere                                │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE CODE: Use & Build                                   │
│  - git clone                                                │
│  - Import components, utilities, scripts                    │
│  - Create new artifacts on top of existing ones            │
│  - Push improvements back to GitHub                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Commands Reference

| Task | Command |
|------|---------|
| Clone repo in Claude Code | `git clone https://github.com/divyavanmahajan/research.git && cd research/finance` |
| List all artifacts | `ls -la components/ utilities/ scripts/` |
| Test Python script | `python scripts/analyze_investments.py` |
| Test JS utilities | `node -e "const u = require('./utilities/finance-helpers.js'); console.log(u.formatCurrency(1000))"` |
| View a file | `cat utilities/finance-helpers.js` |
| Import in Python | `from scripts.analyze_investments import analyze_portfolio` |
| Import in JS | `const { func } = require('./utilities/finance-helpers.js');` |
| Create new script using existing | Copy and extend the existing script |
| Push improvements back | `git add . && git commit -m "Update: ..." && git push origin main` |

---

## What You Can Do Now

✅ **Create artifact in Claude chat**
✅ **Download and organize in finance/ folder**
✅ **Push to GitHub**
✅ **Clone in Claude Code session**
✅ **Import and use existing artifacts**
✅ **Build new things on top of existing code**
✅ **Push improvements back to GitHub**

You now have a complete, reusable, version-controlled library of finance tools!

---

## Real-World Improvements You Can Make

```python
# Create a comprehensive finance tracker
# - Import existing analysis function
# - Add tax calculations
# - Add retirement planning
# - Generate PDF reports
# - Push updated version back to GitHub
```

```javascript
// Build advanced dashboard
// - Import existing utilities and components
// - Add real-time data fetching
// - Add charts and graphs
// - Add export functionality
// - Push as new component
```

```bash
# Create automation script
# - Use existing analysis script
# - Add scheduled data processing
# - Generate reports automatically
# - Store in scripts/ folder
```

The power is in building on what you've already created! 🚀
