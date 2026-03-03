# FinanceFlow — Getting Started

## What is this?

FinanceFlow is a personal finance tracker built as a single React component (`finance-tracker.jsx`). It tracks dual-currency (EUR/USD) household spending against top-down budgets, with traffic-light indicators, a "Can I Spend?" decision tool, trend analysis, and isolated project/trip tracking.

## Prerequisites

You need **Node.js 18+** and **npm** installed. Verify with:

```bash
node --version   # Should show v18.x or higher
npm --version
```

## Quick Start

### Option A: Vite (recommended)

Create a new Vite project and drop the component in:

```bash
npm create vite@latest financeflow -- --template react
cd financeflow
```

Replace the contents of `src/App.jsx` with a one-line wrapper:

```jsx
import FinanceTracker from './FinanceTracker'
export default function App() { return <FinanceTracker /> }
```

Copy the finance tracker into the project:

```bash
cp finance-tracker.jsx financeflow/src/FinanceTracker.jsx
```

Install dependencies and run:

```bash
npm install
npm run dev
```

Open the URL shown in the terminal (typically `http://localhost:5173`).

### Option B: Claude.ai artifact

If you received this file through Claude.ai, the app renders directly as a React artifact — no setup needed. Just open the artifact preview in the conversation.

### Option C: Add to an existing React project

Copy `finance-tracker.jsx` into your `src/` directory and import it:

```jsx
import FinanceTracker from './finance-tracker'

// Use it anywhere in your component tree:
<FinanceTracker />
```

The component has no external dependencies beyond React itself. It uses only `useState`, `useMemo`, `useCallback`, and `useEffect` from React.

## What you'll see

The app loads with 12 months of sample data so you can explore immediately. No login, no database, no configuration needed. The sample data includes:

- 17 merchants across EU and US (Albert Heijn, Whole Foods, Shell, Netflix, etc.)
- Monthly salary income in both EUR and USD
- A sample project ("Italy Trip 2026") with 3 transactions
- 6 auto-categorization rules

## First steps after launching

1. **Dashboard** — see your dual-currency budget meters and traffic-light category indicators at a glance
2. **Can I Spend?** — enter an amount and category to get an instant go/no-go verdict
3. **Transactions** — click "+ Add" to enter your own transactions (expense or income, with optional project tagging and splits)
4. **Trends** — view 12-month spending trends and year-over-year comparisons
5. **Projects** — create a new trip or project to track spending separately from your regular budget
6. **Rules** — view and manage the auto-categorization rules

Use the **◀ ▶ arrows** in the header to navigate between months. Click any **category row** on the dashboard to drill down into subcategories and individual transactions.

## Customizing budgets and categories

The default budgets and categories are defined at the top of the file. To customize, edit the constants:

- `DEFAULT_CATEGORIES` — the two-level category hierarchy (lines 4–73)
- `SAMPLE_BUDGETS_EUR` and `SAMPLE_BUDGETS_USD` — monthly budget per parent category (lines 75–84)
- `incomeEUR` / `incomeUSD` — monthly household income (lines 393–394 inside the component)
- `savingsGoalPct` — target savings rate, default 20% (line 395)

## Data persistence

Currently all data lives in React state and resets on page reload. The sample data generator runs on every fresh load. To add persistence, you would connect `transactions`, `projects`, and `rules` state to localStorage, a database, or the Claude artifact persistent storage API.

## Related files

- `finance-tracker.jsx` — the complete application (single file, ~1300 lines)
- `walkthrough.md` — detailed code walkthrough explaining every section, view, and end-to-end flow
