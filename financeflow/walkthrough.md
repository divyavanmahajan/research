# FinanceFlow — Complete Code Walkthrough

> A line-by-line tour of the personal finance tracker: how the data model, budget engine,
> traffic-light system, rule engine, project isolation, and every UI view actually work.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Model: Categories, Budgets & Transactions](#2-data-model)
3. [Sample Data Generator](#3-sample-data-generator)
4. [Design System: CSS Variables & Visual Language](#4-design-system)
5. [Utility Functions: The Engine Room](#5-utility-functions)
6. [App State & Derived Computations](#6-app-state)
7. [View: Dashboard (Traffic Light System)](#7-dashboard)
8. [View: Category Drill-Down](#8-drill-down)
9. [View: "Can I Spend?" Decision Engine](#9-can-i-spend)
10. [View: Transactions List](#10-transactions)
11. [View: Trends & Year-over-Year](#11-trends)
12. [View: Projects (Isolated Tracking)](#12-projects)
13. [View: Auto-Categorization Rules](#13-rules)
14. [Modals: Add Transaction & Add Project](#14-modals)
15. [Navigation & Routing](#15-navigation)
16. [End-to-End Flows](#16-end-to-end-flows)

---

## 1. Architecture Overview

FinanceFlow is a single-file React component (~1300 lines) with no external state management.
Everything lives in React's `useState`, `useMemo`, and `useCallback` hooks. The app is structured
in layers:

```
┌─────────────────────────────────────────────────┐
│  CONSTANTS & DEFAULTS (lines 1–95)              │
│  Category hierarchy, budget tables, utilities    │
├─────────────────────────────────────────────────┤
│  SAMPLE DATA GENERATOR (lines 97–168)           │
│  Creates 12 months of realistic transactions     │
├─────────────────────────────────────────────────┤
│  CSS DESIGN SYSTEM (lines 170–340)              │
│  Dark theme, traffic lights, charts, forms       │
├─────────────────────────────────────────────────┤
│  UTILITY FUNCTIONS (lines 341–383)              │
│  Formatting, category lookups, traffic colors    │
├─────────────────────────────────────────────────┤
│  MAIN COMPONENT (lines 385–1303)                │
│  State, derived data, 7 view renderers, modals   │
└─────────────────────────────────────────────────┘
```

The key architectural decision: **project transactions are stored in the same array as regular
transactions**, distinguished only by a `projectId` field. This means every computation must
consciously filter them out (via `regularExpenses()`) or include them (via direct array access).
This single field is what keeps your trip spending from polluting your monthly budget.

---

## 2. Data Model

### 2.1 Hierarchical Categories

The category system is a **two-level tree**: parent groups with children.

```jsx
// Lines 4–73: Each parent has an id, label, icon, and children array
const DEFAULT_CATEGORIES = [
  { id: "housing", label: "Housing", icon: "🏠", children: [
    { id: "housing-mortgage", label: "Mortgage/Rent" },
    { id: "housing-tax", label: "Property Tax" },
    { id: "housing-maint", label: "Maintenance" },
    { id: "housing-utilities", label: "Utilities" },
    { id: "housing-insurance", label: "Home Insurance" },
    { id: "housing-furnish", label: "Furnishings" },
  ]},
  // ... 10 more parent categories, each with 2-7 children
];
```

The naming convention is `parentId-childSuffix` (e.g., `food-grocery`, `transport-fuel`).
This makes it easy to find a child's parent by splitting on the first hyphen, though the code
actually uses a lookup function (`getParentCat`) for robustness:

```jsx
// Lines 372–379: Walk the tree to find which parent owns a subcategory
function getParentCat(cats, id) {
  for (const g of cats) {
    for (const c of g.children) {
      if (c.id === id) return g.id;
    }
  }
  return id;  // If not found, assume it IS a parent
}
```

There are **11 parent categories** spanning the full EU+US household: Housing, Transport,
Food & Dining, Family & Kids, Health, Personal, Technology, Education, Financial, Giving,
and Miscellaneous. Total of ~55 subcategories.

### 2.2 Dual-Currency Budgets

Budgets are set at the **parent category level**, separately for each currency:

```jsx
// Lines 75–84: Two flat maps, keyed by parent category id
const SAMPLE_BUDGETS_EUR = {
  "housing": 1800, "transport": 400, "food": 800, "family": 500,
  "health": 300, "personal": 300, "tech": 100, "education": 100,
  "financial": 50, "giving": 150, "misc": 100,
};
const SAMPLE_BUDGETS_USD = {
  "housing": 2200, "transport": 500, "food": 900, "family": 600,
  "health": 500, "personal": 350, "tech": 150, "education": 100,
  "financial": 50, "giving": 200, "misc": 100,
};
```

The EUR total is €4,600/month; USD total is $5,650/month. These are the **envelope sizes**
that the traffic-light system monitors against.

### 2.3 Transaction Schema

Every transaction — expense, income, or project spend — follows this shape:

```jsx
{
  id: "a8k2m1x9",        // Random 8-char string
  date: "2026-03-15",     // ISO date string
  amount: 127.50,         // Always positive
  currency: "EUR",        // "EUR" or "USD"
  merchant: "Trattoria",  // Free text
  categoryId: "food-restaurant",  // Subcategory id (null for income)
  tags: ["spouse", "EU"], // Array of free-form strings
  projectId: "x7k2...",   // null = regular spend, string = project
  notes: "Anniversary",   // Free text
  type: "expense",        // "expense" or "income"
  splits: null,           // null or [{categoryId, amount}, ...]
}
```

The `type` field determines sign in displays (red/negative for expenses, green/positive for income).
The `projectId` is the critical field — when non-null, the transaction is **excluded from all
regular budget calculations** but included in project-specific views.

The `splits` field enables one bank transaction to be divided across categories. For example,
a $200 Costco run could be split: $160 to Groceries, $40 to Household. When splits are present,
the main `categoryId` holds the first split's category, and the `splits` array holds all parts.

---

## 3. Sample Data Generator

The `generateSampleData()` function (lines 98–168) creates 12 months of realistic
transactions to populate the app immediately. Here's how it works:

```jsx
// Lines 98–105: Build an array of the last 12 month keys
function generateSampleData() {
  const txns = [];
  const now = new Date();
  const months = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`);
  }
```

It then defines a **merchant table** — 17 merchants, each with a name, category mapping,
currency, and min/max amount range:

```jsx
// Lines 106–124: Each merchant defines its own spending pattern
const merchants = [
  { name: "Whole Foods",    cat: "food-grocery",  cur: "USD", min: 40,  max: 180 },
  { name: "Albert Heijn",   cat: "food-grocery",  cur: "EUR", min: 30,  max: 120 },
  { name: "Netflix",        cat: "personal-subs", cur: "USD", min: 15,  max: 15  },
  // ... min === max means fixed amount (subscriptions)
  { name: "Daycare Little Stars", cat: "family-childcare", cur: "USD", min: 800, max: 800 },
];
```

For each month × merchant combination, it generates 1–3 transactions (or exactly 1 for
fixed-amount merchants like Netflix). Random day within the month, random amount within range:

```jsx
// Lines 126–140: Transaction generation loop
months.forEach(ym => {
  merchants.forEach(m => {
    const count = m.max === m.min ? 1 : Math.floor(Math.random() * 3) + 1;
    for (let i = 0; i < count; i++) {
      const day = Math.floor(Math.random() * 28) + 1;
      const amt = +(m.min + Math.random() * (m.max - m.min)).toFixed(2);
      txns.push({
        id: genId(), date: `${ym}-${String(day).padStart(2,"0")}`,
        amount: amt, currency: m.cur, merchant: m.name,
        categoryId: m.cat, tags: [], projectId: null, // Regular spend
        type: "expense", splits: null,
      });
    }
  });
});
```

Income is added as two fixed monthly entries — €5,500 EU salary + $7,000 US salary:

```jsx
// Lines 142–150: Monthly income entries
months.forEach(ym => {
  txns.push({ ...salary, amount: 5500, currency: "EUR", merchant: "Employer EU - Salary" });
  txns.push({ ...salary, amount: 7000, currency: "USD", merchant: "Employer US - Salary" });
});
```

Finally, a sample project ("Italy Trip 2026") with 3 transactions (flights, hotel, dinner)
is created. Note how `projectId: proj.id` links them:

```jsx
// Lines 152–165: Project transactions with projectId set
const proj = { id: genId(), name: "Italy Trip 2026", budget: 3000,
               currency: "EUR", status: "active" };
const projTxns = [
  { ...base, amount: 450, merchant: "Ryanair", projectId: proj.id },
  { ...base, amount: 680, merchant: "Hotel Roma", projectId: proj.id },
  { ...base, amount: 127.50, merchant: "Trattoria Roma", projectId: proj.id },
];
```

---

## 4. Design System

The CSS (lines 170–340) establishes a dark-mode financial dashboard aesthetic using
CSS custom properties:

```css
/* Lines 174–197: Color palette — 4 background tiers create depth */
:root {
  --bg:  #0a0e17;   /* Deepest background */
  --bg2: #111827;   /* Card background */
  --bg3: #1a2234;   /* Interactive element background */
  --bg4: #243049;   /* Hover/active state */

  /* Traffic light system colors */
  --green:  #22c55e;   --green-bg: rgba(34,197,94,0.1);
  --yellow: #eab308;   --yellow-bg: rgba(234,179,8,0.1);
  --red:    #ef4444;   --red-bg: rgba(239,68,68,0.1);

  /* Typography */
  --font: 'DM Sans', sans-serif;    /* Body text */
  --mono: 'JetBrains Mono', monospace; /* Numbers & data */
}
```

The four-tier background system (`--bg` → `--bg4`) creates visual depth: the page is darkest,
cards sit on `--bg2`, interactive elements within cards use `--bg3`, and hover states light
up to `--bg4`.

Key visual components:

- **Traffic light dots** (lines 241–244): Glowing circles with `box-shadow` in green/yellow/red
- **Progress bars** (lines 239–240): 6px tall with rounded ends and CSS transitions
- **Budget meters** (lines 256–264): 14px bars with a day-progress marker overlaid
- **Stat boxes** (lines 246–254): Centered number displays with labels and color coding
- **Chart bars** (lines 279–286): Flexbox-based bar charts with hover effects

---

## 5. Utility Functions

Six utility functions form the computation engine (lines 341–383):

### Currency Formatting

```jsx
// Lines 341–350: Two formatters — compact and full precision
const fmt = (n, cur) => {
  const sym = cur === "EUR" ? "€" : "$";
  return `${sym}${Math.abs(n).toLocaleString("en", {
    minimumFractionDigits: 0, maximumFractionDigits: 0
  })}`;  // e.g., "€1,800"
};

const fmtFull = (n, cur) => {
  // Same but with 2 decimal places: "$127.50"
};
```

`fmt` is used in dashboards and charts (clean, rounded), `fmtFull` in transaction tables
(precise to the cent).

### Traffic Light Logic

```jsx
// Lines 354–360: The heart of the "should I worry?" system
const trafficColor = (spent, budget) => {
  if (budget === 0) return "green";
  const r = spent / budget;
  if (r <= 0.75) return "green";   // Under 75% — you're fine
  if (r <= 1.0) return "yellow";   // 75–100% — watch it
  return "red";                     // Over 100% — over budget
};
```

This function is called dozens of times across the app. The thresholds are:
- 🟢 **Green**: ≤75% of budget used
- 🟡 **Yellow**: 75–100% of budget used
- 🔴 **Red**: >100% of budget used

### Category Navigation

```jsx
// Lines 363–383: Three functions for navigating the category tree
getCatLabel(cats, id)      // "food-grocery" → "🍽 Groceries"
getParentCat(cats, id)     // "food-grocery" → "food"
getAllSubcatIds(cats, pid)  // "food" → ["food-grocery","food-restaurant",...]
```

These are used everywhere: the dashboard aggregates spending by parent, the drill-down
breaks it out by child, and the transaction table shows the full label.

---

## 6. App State & Derived Computations

The main `FinanceTracker` component (line 386) initializes with this state:

```jsx
// Lines 387–413: All app state
const [data] = useState(() => generateSampleData());      // Run once
const [transactions, setTransactions] = useState(data.transactions);
const [projects, setProjects] = useState(data.projects);
const [categories] = useState(DEFAULT_CATEGORIES);         // Read-only
const [budgetsEUR] = useState(SAMPLE_BUDGETS_EUR);
const [budgetsUSD] = useState(SAMPLE_BUDGETS_USD);
const [incomeEUR] = useState(5500);
const [incomeUSD] = useState(7000);
const [savingsGoalPct] = useState(20);                     // 20% target
const [rules, setRules] = useState([...]);                 // 6 default rules

const [view, setView] = useState("dashboard");             // Current tab
const [selectedMonth, setSelectedMonth] = useState("2026-03"); // Current month
const [drillCat, setDrillCat] = useState(null);            // Drill-down target
const [showAddTxn, setShowAddTxn] = useState(false);       // Modal visibility
const [showAddProject, setShowAddProject] = useState(false);
```

### Critical Derived Data

The most important derived computation is **filtering transactions by month and type**:

```jsx
// Lines 416–434: Memoized and callback-based filters
const monthTxns = useMemo(() =>
  transactions.filter(t => monthKey(t.date) === selectedMonth),
  [transactions, selectedMonth]
);

// These are functions, not values — called with a txn array:
const regularExpenses = useCallback((txns) =>
  txns.filter(t => t.type === "expense" && !t.projectId), []);

const projectExpenses = useCallback((txns) =>
  txns.filter(t => t.type === "expense" && t.projectId), []);

const incomes = useCallback((txns) =>
  txns.filter(t => t.type === "income"), []);
```

The `regularExpenses` filter is the **gatekeeper**: by checking `!t.projectId`, it ensures
that your Italy Trip flights never show up in your Transport budget calculations.

### Spend Aggregation

```jsx
// Lines 436–444: Aggregate spending by parent category and currency
const spendByCat = useCallback((txns, cur) => {
  const map = {};
  regularExpenses(txns).forEach(t => {
    if (t.currency !== cur) return;
    const parent = getParentCat(categories, t.categoryId);
    map[parent] = (map[parent] || 0) + t.amount;
  });
  return map;  // e.g., { food: 742, housing: 1650, ... }
}, [categories, regularExpenses]);
```

This powers the dashboard. It takes all regular (non-project) expenses for a currency,
maps each to its parent category, and sums. The result is a flat object you can compare
directly against the budget tables.

### Day Progress Calculation

```jsx
// Lines 475–480: How far through the month are we?
const dayProgress = useMemo(() => {
  const now = new Date();
  const currentYM = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}`;
  if (selectedMonth !== currentYM) return 100;  // Past months: fully elapsed
  return pct(now.getDate(), daysInMonth(selectedMonth));
}, [selectedMonth]);
```

This is the thin vertical marker on the budget meter bars. If you're 10 days into a 31-day
month, the marker sits at ~32%. If your spend bar is past that marker, you're spending
faster than the month is progressing — a visual "pace" indicator.

---

## 7. Dashboard (Traffic Light System)

The dashboard (`renderDashboard`, lines 485–611) is the primary view. It renders three
sections stacked vertically:

### 7.1 Overall Budget Meters

Two side-by-side cards (EUR and USD), each showing:

```
┌─────────────────────────────────────┐
│  EUR BUDGET                [On Track]│
│                                      │
│  62%        €2,852 of €4,600 budget  │
│  ████████████░░░░░░░|░░░░░░░░░░░░░  │
│  Day 7% through month    Remaining: €1,748  │
│                                      │
│  ┌─────────┐ ┌──────────┐ ┌────────┐│
│  │ Income  │ │ Savings  │ │Remain  ││
│  │ €5,500  │ │   48%    │ │ €1,748 ││
│  │         │ │ Tgt: 20% │ │        ││
│  └─────────┘ └──────────┘ └────────┘│
└─────────────────────────────────────┘
```

The `|` on the progress bar is the **day-progress marker** — showing your pace. The code
computes this with:

```jsx
// Lines 520–523: The budget bar with day marker overlay
<div className="meter-bar-outer">
  <div className="meter-bar-inner" style={{
    width: `${clamp(pct(d.total, d.budget), 0, 100)}%`,
    background: colorVar(d.color) }} />
  <div className="meter-bar-marker" style={{ left: `${dayProgress}%` }} />
</div>
```

The status pill ("On Track" / "Watch It" / "Over Budget") is determined by `trafficColor()`.

### 7.2 Category Traffic Lights

Below the meters, two columns show every budget category with its own mini progress bar:

```jsx
// Lines 548–584: Category list with click-to-drill
{categories.map(g => {
  const spent = spend[g.id] || 0;
  const budget = budgets[g.id] || 0;
  if (budget === 0 && spent === 0) return null;  // Skip empty categories
  const color = trafficColor(spent, budget);
  return (
    <div className="traffic-item"
         onClick={() => { setDrillCat(g.id); setView("drill"); }}>
      <div className="traffic-icon">{g.icon}</div>
      <div className="traffic-info">
        <div className="traffic-label">{g.label}</div>
        <div className="traffic-amounts">
          {fmt(spent, cur)} / {fmt(budget, cur)}
        </div>
        <div className="traffic-bar-wrap">
          <div className="traffic-bar"
               style={{ width: `${p}%`, background: colorVar(color) }} />
        </div>
      </div>
      <div className={`traffic-dot dot-${color}`} />
    </div>
  );
})}
```

Each row is clickable — tapping it navigates to the drill-down view for that category.
The glowing dot on the right gives an instant traffic-light signal.

### 7.3 Project Summary

At the bottom, active projects show their own budget bars, clearly labeled
"excluded from budget":

```jsx
// Lines 586–608: Project cards on the dashboard
{projects.map(p => {
  const spent = transactions.filter(t => t.projectId === p.id)
    .reduce((s, t) => s + t.amount, 0);
  // Note: NO regularExpenses filter — we want ALL project transactions
  const color = trafficColor(spent, p.budget);
  return (
    <div className="project-card">
      <h3>✈️ {p.name} <span className="project-badge">{p.status}</span></h3>
      <div>{fmt(spent, p.currency)} / {fmt(p.budget, p.currency)}</div>
      {/* Progress bar */}
    </div>
  );
})}
```

---

## 8. Category Drill-Down

When you click a category on the dashboard, `renderDrill` (lines 613–690) activates:

```jsx
// Lines 614–630: Load category data
const cat = categories.find(c => c.id === drillCat);
const subIds = getAllSubcatIds(categories, drillCat);
// Get only regular expenses matching this parent's children
const txns = monthTxns.filter(t =>
  t.type === "expense" && !t.projectId && subIds.includes(t.categoryId)
);
```

It shows:

1. **EUR/USD stat boxes** with spent vs budget and remaining
2. **Subcategory breakdown** as horizontal dual-colored bars (blue for EUR, cyan for USD)
3. **Transaction table** sorted newest-first

The subcategory breakdown aggregates by `categoryId-currency` combinations:

```jsx
// Lines 625–630: Build a breakdown map
const subBreakdown = {};
txns.forEach(t => {
  const k = `${t.categoryId}-${t.currency}`;
  subBreakdown[k] = (subBreakdown[k] || 0) + t.amount;
});
// Then render as horizontal bars for each subcategory
```

A "← Back" button returns to the dashboard view.

---

## 9. "Can I Spend?" Decision Engine

This is the real-time spending check (`renderCanISpend`, lines 878–960). It presents an
input form with three fields:

```
┌──────────────────────────────────────┐
│  CAN I SPEND THIS?                   │
│                                      │
│  Amount: [    85.00    ]  [EUR ▼]    │
│  Category: [🍽 Food & Dining  ▼]     │
│                                      │
│              ✅                       │
│    Yes, you can spend this           │
│                                      │
│  ┌──────────┐ ┌──────────┐ ┌───────┐│
│  │ Budget   │ │ Spent    │ │ After ││
│  │ €800     │ │ €540     │ │ €175  ││
│  └──────────┘ └──────────┘ └───────┘│
│                                      │
│  Daily budget for remaining 24       │
│  days: €7/day                        │
└──────────────────────────────────────┘
```

The decision logic is straightforward:

```jsx
// Lines 893–898: The core "can I afford it?" calculation
const budget = budgets[checkCat] || 0;
const spent = spendByCat(monthTxns, checkCur)[checkCat] || 0;
const remaining = Math.max(0, budget - spent);
const amt = parseFloat(checkAmt) || 0;
const afterSpend = remaining - amt;
const canSpend = afterSpend >= 0;   // THE VERDICT
```

If `canSpend` is true, a green panel appears with ✅. If false, a red panel with 🛑.
Both panels show the three stat boxes: category budget, already spent, and after-purchase
remaining.

The daily budget calculation divides the post-purchase remaining by days left in the month:

```jsx
// Lines 935–937: Daily budget remaining
const daysLeft = daysInMonth(selectedMonth) - dayOfMonth(today());
const dailyBudgetRemaining = daysLeft > 0 ? remaining / daysLeft : remaining;
// Displayed as: "Daily budget for remaining 24 days: €7/day"
```

When no amount is entered (amt === 0), it shows a summary of the selected category's
budget status across both currencies — useful for a quick glance without a specific purchase
in mind.

---

## 10. Transactions List

`renderTransactions` (lines 693–725) shows a sortable table of all transactions for the
selected month:

```jsx
// Line 695: Sort newest-first
const sorted = [...monthTxns].sort((a, b) => b.date.localeCompare(a.date));
```

The table has columns: Date, Merchant, Category, Tags, Project, and Amount. Visual coding:

- **Expenses** show in red with a minus sign: `-€127.50`
- **Income** shows in green with a plus: `+$7,000.00`
- **Project tags** appear as purple badges: `Italy Trip 2026`
- **Split transactions** get an orange `SPLIT` badge
- **Custom tags** appear as blue badges: `spouse`, `EU`

The "+ Add" button in the header opens the transaction modal.

---

## 11. Trends & Year-over-Year

`renderTrends` (lines 727–870) generates three chart sections:

### 11.1 Monthly Spending Trend (12 Months)

Builds a 12-month window ending at the selected month:

```jsx
// Lines 729–746: Compute spending data for each of 12 months
const monthKeys = [];
for (let i = 11; i >= 0; i--) {
  const d = new Date(y, m - 1 - i, 1);
  monthKeys.push(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`);
}
const monthData = monthKeys.map(mk => {
  const txns = transactions.filter(t => monthKey(t.date) === mk);
  return {
    key: mk,
    label: `${MONTHS[...]}`,
    eurSpend: totalRegularSpend(txns, "EUR"),
    usdSpend: totalRegularSpend(txns, "USD"),
    eurIncome: totalIncome(txns, "EUR"),
    usdIncome: totalIncome(txns, "USD"),
  };
});
```

Rendered as paired blue (EUR) and cyan (USD) bars, scaled to the maximum value across all
months. Budget reference amounts shown at the bottom.

### 11.2 Year-over-Year Comparison

Compares current year vs previous year, month by month:

```jsx
// Lines 752–768: YoY data generation
const currentYearKey = selectedMonth.slice(0, 4);  // "2026"
const prevYearKey = String(parseInt(currentYearKey) - 1);  // "2025"
const yoyData = MONTHS.map((label, i) => {
  // Compute spending for both years' version of each month
  return {
    currEUR: totalRegularSpend(txns1, "EUR"),
    prevEUR: totalRegularSpend(txns2, "EUR"),
    // ... same for USD
  };
});
```

Displayed as two separate chart groups (EUR and USD), each with current-year bars in
full color and previous-year bars at 40% opacity for comparison.

### 11.3 Savings Rate Trend

Calculates savings rate per month: `(income - spend) / income × 100`:

```jsx
// Lines 846–850: Savings rate per month
const eurRate = d.eurIncome > 0 ? pct(d.eurIncome - d.eurSpend, d.eurIncome) : 0;
const usdRate = d.usdIncome > 0 ? pct(d.usdIncome - d.usdSpend, d.usdIncome) : 0;
const avgRate = Math.round((eurRate + usdRate) / 2);
const c = avgRate >= savingsGoalPct ? "var(--green)"
        : avgRate >= 10 ? "var(--yellow)" : "var(--red)";
```

Bars are colored green if meeting the 20% target, yellow if 10–20%, red if below 10%.
This instantly reveals lifestyle creep: if the bars are trending from green to yellow
over months, spending is growing faster than income.

---

## 12. Projects (Isolated Tracking)

`renderProjects` (lines 877–960 area) manages the parallel tracking lane:

Each project card shows:
- Name and status badge (active/completed)
- Four stat boxes: Budget, Spent, Remaining, # Transactions
- A progress bar with traffic-light coloring
- A transaction table filtered to just that project's expenses

```jsx
// Lines ~893: Project transaction filtering
const txns = transactions.filter(t => t.projectId === p.id)
  .sort((a, b) => b.date.localeCompare(a.date));
const spent = txns.reduce((s, t) => s + t.amount, 0);
```

Key design: project transactions **do** have categories (the hotel is `housing-mortgage`,
the flight is `transport-flights`). This means you can later query "total restaurant spend
including trips" by ignoring the project filter. But for budget purposes, they're invisible
to the regular budget view.

---

## 13. Auto-Categorization Rules

`renderRules` (lines ~960–1000) manages the rule engine:

```jsx
// Lines 396–403: Default rules
const [rules, setRules] = useState([
  { id: "r1", pattern: "WHOLE FOODS", categoryId: "food-grocery", priority: 1 },
  { id: "r2", pattern: "ALBERT HEIJN", categoryId: "food-grocery", priority: 1 },
  { id: "r3", pattern: "SHELL", categoryId: "transport-fuel", priority: 2 },
  { id: "r4", pattern: "NETFLIX", categoryId: "personal-subs", priority: 1 },
  { id: "r5", pattern: "AMAZON", categoryId: "personal-hobbies", priority: 3 },
  { id: "r6", pattern: "STARBUCKS", categoryId: "food-coffee", priority: 1 },
]);
```

Each rule has:
- **pattern**: Case-insensitive merchant name match
- **categoryId**: Target subcategory
- **priority**: Lower number = checked first (for conflict resolution)

Rules are displayed as:
```
P1  "WHOLE FOODS"  →  🍽 Groceries  [✕]
P1  "NETFLIX"      →  👤 Subscriptions  [✕]
P3  "AMAZON"       →  👤 Hobbies  [✕]
```

New rules can be added (currently via `prompt()`) and deleted inline. The rule list is
sorted by priority for display.

---

## 14. Modals

### 14.1 Add Transaction Modal

`renderAddTxnModal` (lines 1015–1200) is a full-featured form:

**Fields:**
- Date (date picker, defaults to today)
- Type (expense/income toggle)
- Merchant (text input)
- Amount + Currency (number + EUR/USD dropdown)
- Category (hierarchical select with optgroups)
- Project (optional dropdown, defaults to "None = regular spend")
- Tags (comma-separated text input)
- Notes (textarea)
- Split toggle (checkbox)

**Split mode** (when enabled) replaces the single category picker with a dynamic list
of category + amount pairs:

```jsx
// Lines 1120–1163: Split transaction UI
{form.splits.map((sp, i) => (
  <div className="form-row" key={i}>
    <select value={sp.categoryId} onChange={...}>
      {/* Category picker */}
    </select>
    <input type="number" placeholder="Amount" value={sp.amount} onChange={...} />
    {form.splits.length > 1 && <button onClick={/* remove */}>✕</button>}
  </div>
))}
<button onClick={/* add split row */}>+ Add Split</button>
```

A running total vs the entered amount is shown at the top of the split section to help
ensure splits add up correctly.

On submit, the transaction is appended to the `transactions` array:

```jsx
// Lines 1070–1085: Transaction creation
const handleSubmit = () => {
  if (!form.amount || !form.merchant) return;  // Validation
  const txn = {
    id: genId(),
    date: form.date,
    amount: parseFloat(form.amount),
    currency: form.currency,
    merchant: form.merchant,
    categoryId: form.splitEnabled ? form.splits[0]?.categoryId : form.categoryId,
    tags: form.tags ? form.tags.split(",").map(t => t.trim()).filter(Boolean) : [],
    projectId: form.projectId || null,
    type: form.type,
    splits: form.splitEnabled ? form.splits.map(s => ({
      categoryId: s.categoryId, amount: parseFloat(s.amount) || 0
    })) : null,
  };
  setTransactions(prev => [...prev, txn]);
  setShowAddTxn(false);
};
```

### 14.2 Add Project Modal

`renderAddProjectModal` (lines 1203–1259) collects: name, budget, currency, start/end dates.
On submit, creates a new project object:

```jsx
// Lines 1208–1214: Project creation
const handleSubmit = () => {
  setProjects(prev => [...prev, {
    id: genId(),
    name: form.name,
    budget: parseFloat(form.budget),
    currency: form.currency,
    startDate: form.startDate,
    endDate: form.endDate,
    status: "active",
  }]);
  setShowAddProject(false);
};
```

Both modals use a backdrop overlay with `backdrop-filter: blur(4px)` and close on
overlay click (via `onClick` on the overlay + `e.stopPropagation()` on the modal content).

---

## 15. Navigation & Routing

Navigation is a single row of buttons rendered as a tab bar:

```jsx
// Lines 1275–1288: Tab navigation
<div className="nav">
  {[
    { id: "dashboard",    label: "📊 Dashboard" },
    { id: "canispend",    label: "🚦 Can I Spend?" },
    { id: "transactions", label: "📋 Transactions" },
    { id: "trends",       label: "📈 Trends" },
    { id: "projects",     label: "✈️ Projects" },
    { id: "rules",        label: "⚙️ Rules" },
  ].map(v => (
    <button className={view === v.id ? "active" : ""}
            onClick={() => setView(v.id)}>
      {v.label}
    </button>
  ))}
</div>
```

View rendering is a simple conditional chain:

```jsx
// Lines 1290–1297: View dispatcher
{view === "dashboard" && renderDashboard()}
{view === "drill" && renderDrill()}        // Hidden nav item, triggered by click
{view === "canispend" && renderCanISpend()}
{view === "transactions" && renderTransactions()}
{view === "trends" && renderTrends()}
{view === "projects" && renderProjects()}
{view === "rules" && renderRules()}
```

Note: "drill" is not in the nav — it's only accessible by clicking a category on the dashboard.

Month navigation is shared across all views via the header selector:

```jsx
// Lines 1268–1273: Month navigation arrows
<div className="month-selector">
  <button onClick={prevMonth}>◀</button>
  <span>{monthLabel}</span>    {/* e.g., "Mar 2026" */}
  <button onClick={nextMonth}>▶</button>
</div>
```

---

## 16. End-to-End Flows

### Flow A: "Can I afford dinner tonight?"

```
1. Open app → Dashboard loads with current month
2. Quick glance: EUR Food & Dining shows 🟡 yellow dot (78% used)
3. Click "🚦 Can I Spend?" tab
4. Enter: Amount=85, Currency=EUR, Category=Food & Dining
5. System calculates:
   - Budget: €800
   - Already spent: €624
   - Remaining: €176
   - After this: €91
   - Verdict: ✅ Yes (€91 left, ~€3.80/day for 24 remaining days)
6. Decision: Go ahead, but maybe cook at home the rest of the week
```

### Flow B: "Booking Italy trip flights"

```
1. Click "✈️ Projects" tab
2. Click "+ New Project"
3. Enter: Name="Italy Trip 2026", Budget=3000, Currency=EUR
4. Project created with progress bar at 0%
5. Click "📋 Transactions" tab → "+ Add"
6. Enter: Merchant="Ryanair", Amount=450, Currency=EUR
7. Category: Transport → Flights
8. Project: Select "Italy Trip 2026"     ← THIS IS THE KEY STEP
9. Submit → transaction saved with projectId set
10. Dashboard: Food & Dining budget unchanged (flights excluded)
11. Projects view: Italy Trip shows €450/€3000 (15%)
```

### Flow C: "Is lifestyle creep happening?"

```
1. Click "📈 Trends" tab
2. View "Savings Rate Trend" chart at bottom
3. Bars show: 6 months ago 32% → 28% → 25% → 22% → 19% → 18%
4. Declining from green to yellow — lifestyle creep confirmed
5. Scroll up to "Monthly Spending Trend"
6. Identify which months spiked — EUR bars growing each month
7. Navigate to a spike month, click Dashboard, examine categories
8. Find: Personal spending up 40% → drill down → Subscriptions doubled
9. Action: Cancel unused subscriptions
```

### Flow D: "Splitting a Costco run"

```
1. Click "📋 Transactions" → "+ Add"
2. Enter: Merchant="Costco", Amount=247.50, Currency=USD
3. Check "Split across categories" checkbox
4. Split 1: Food → Groceries, Amount: 185.00
5. Click "+ Add Split"
6. Split 2: Personal → Hobbies, Amount: 62.50
7. Running total shows: 247.50 / 247.50 ✓
8. Submit → transaction saved with splits array
9. Dashboard: Food budget debited $185, Personal debited $62.50
10. Transaction table shows orange "SPLIT" badge
```

### Flow E: "Monthly review — month just ended"

```
1. Use ◀ arrow to navigate to previous month
2. Dashboard: Review all traffic lights
   - Any 🔴 red? Investigate with drill-down
   - All 🟢 green? Check if budgets are too generous
3. Click "📈 Trends" for context
4. Compare this month's bars to the same month last year (YoY chart)
5. Check savings rate — did we meet the 20% target?
6. Navigate back to current month to continue tracking
```

---

## Appendix: Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Single array for all transactions | Yes | Simpler queries, one source of truth |
| `projectId` null vs string | Yes | Minimal schema change, maximum flexibility |
| Budgets at parent level only | Yes | Avoids over-budgeting 55 subcategories |
| Dual currency side-by-side | Yes | No conversion needed, avoids FX noise |
| Traffic light at 75%/100% | Yes | Gives warning buffer before overspending |
| Tags orthogonal to categories | Yes | Enables cross-cutting analysis without hierarchy changes |
| Day-progress marker on bars | Yes | Pace indicator: spending vs time elapsed |
| `useCallback` for filters | Yes | Reusable across views without re-creating functions |
| CSS variables for theming | Yes | Single source for all colors, easy to retheme |
| Sample data on load | Yes | Instant demo without manual data entry |
