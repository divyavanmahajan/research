import { useState, useMemo, useCallback, useEffect } from "react";

// ─── DEFAULT DATA ───────────────────────────────────────────────────
const DEFAULT_CATEGORIES = [
  { id: "housing", label: "Housing", icon: "🏠", children: [
    { id: "housing-mortgage", label: "Mortgage/Rent" },
    { id: "housing-tax", label: "Property Tax" },
    { id: "housing-maint", label: "Maintenance" },
    { id: "housing-utilities", label: "Utilities" },
    { id: "housing-insurance", label: "Home Insurance" },
    { id: "housing-furnish", label: "Furnishings" },
  ]},
  { id: "transport", label: "Transport", icon: "🚗", children: [
    { id: "transport-car", label: "Car Payment" },
    { id: "transport-fuel", label: "Fuel" },
    { id: "transport-insurance", label: "Insurance" },
    { id: "transport-maint", label: "Maintenance" },
    { id: "transport-public", label: "Public Transit" },
    { id: "transport-parking", label: "Parking/Tolls" },
    { id: "transport-flights", label: "Flights" },
  ]},
  { id: "food", label: "Food & Dining", icon: "🍽", children: [
    { id: "food-grocery", label: "Groceries" },
    { id: "food-restaurant", label: "Restaurants" },
    { id: "food-coffee", label: "Coffee/Cafes" },
    { id: "food-delivery", label: "Delivery" },
    { id: "food-alcohol", label: "Alcohol" },
  ]},
  { id: "family", label: "Family & Kids", icon: "👨‍👩‍👧‍👦", children: [
    { id: "family-childcare", label: "Childcare" },
    { id: "family-school", label: "School/Tuition" },
    { id: "family-activities", label: "Activities" },
    { id: "family-clothing", label: "Clothing (Kids)" },
    { id: "family-medical", label: "Medical (Kids)" },
  ]},
  { id: "health", label: "Health", icon: "🏥", children: [
    { id: "health-insurance", label: "Insurance Premiums" },
    { id: "health-doctor", label: "Doctor/Dental" },
    { id: "health-pharmacy", label: "Pharmacy" },
    { id: "health-fitness", label: "Fitness/Gym" },
  ]},
  { id: "personal", label: "Personal", icon: "👤", children: [
    { id: "personal-clothing", label: "Clothing" },
    { id: "personal-hair", label: "Haircare" },
    { id: "personal-subs", label: "Subscriptions" },
    { id: "personal-gifts", label: "Gifts" },
    { id: "personal-hobbies", label: "Hobbies" },
  ]},
  { id: "tech", label: "Technology", icon: "📱", children: [
    { id: "tech-devices", label: "Devices" },
    { id: "tech-software", label: "Software" },
    { id: "tech-phone", label: "Phone Plans" },
  ]},
  { id: "education", label: "Education", icon: "📚", children: [
    { id: "edu-courses", label: "Courses" },
    { id: "edu-books", label: "Books" },
    { id: "edu-membership", label: "Professional Memberships" },
  ]},
  { id: "financial", label: "Financial", icon: "🏛", children: [
    { id: "fin-bankfees", label: "Bank Fees" },
    { id: "fin-investfees", label: "Investment Fees" },
    { id: "fin-interest", label: "Loan Interest" },
    { id: "fin-fx", label: "Currency Exchange" },
  ]},
  { id: "giving", label: "Giving", icon: "🎁", children: [
    { id: "giving-charity", label: "Charity" },
    { id: "giving-family", label: "Family Support" },
  ]},
  { id: "misc", label: "Miscellaneous", icon: "📦", children: [
    { id: "misc-uncat", label: "Uncategorized" },
    { id: "misc-cash", label: "Cash (Unknown)" },
  ]},
];

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

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function genId() { return Math.random().toString(36).slice(2, 10); }
function today() { return new Date().toISOString().slice(0, 10); }
function monthKey(d) { return d.slice(0, 7); }
function dayOfMonth(d) { return parseInt(d.slice(8, 10)); }
function daysInMonth(ym) {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m, 0).getDate();
}

// ─── SAMPLE TRANSACTIONS ───────────────────────────────────────────
function generateSampleData() {
  const txns = [];
  const now = new Date();
  const months = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`);
  }
  const merchants = [
    { name: "Whole Foods", cat: "food-grocery", cur: "USD", min: 40, max: 180 },
    { name: "Albert Heijn", cat: "food-grocery", cur: "EUR", min: 30, max: 120 },
    { name: "Shell Gas", cat: "transport-fuel", cur: "EUR", min: 50, max: 90 },
    { name: "Chevron", cat: "transport-fuel", cur: "USD", min: 40, max: 80 },
    { name: "Netflix", cat: "personal-subs", cur: "USD", min: 15, max: 15 },
    { name: "Spotify", cat: "personal-subs", cur: "EUR", min: 10, max: 10 },
    { name: "Restaurant La Piazza", cat: "food-restaurant", cur: "EUR", min: 40, max: 120 },
    { name: "Chipotle", cat: "food-restaurant", cur: "USD", min: 12, max: 25 },
    { name: "Amazon", cat: "personal-hobbies", cur: "USD", min: 15, max: 200 },
    { name: "Pharmacy CVS", cat: "health-pharmacy", cur: "USD", min: 8, max: 60 },
    { name: "Apotheek", cat: "health-pharmacy", cur: "EUR", min: 5, max: 40 },
    { name: "Kids Soccer Club", cat: "family-activities", cur: "EUR", min: 30, max: 30 },
    { name: "Daycare Little Stars", cat: "family-childcare", cur: "USD", min: 800, max: 800 },
    { name: "Electric Company", cat: "housing-utilities", cur: "EUR", min: 80, max: 150 },
    { name: "ConEd", cat: "housing-utilities", cur: "USD", min: 90, max: 200 },
    { name: "Starbucks", cat: "food-coffee", cur: "USD", min: 5, max: 8 },
    { name: "Gym Membership", cat: "health-fitness", cur: "EUR", min: 40, max: 40 },
  ];

  months.forEach(ym => {
    merchants.forEach(m => {
      const count = m.max === m.min ? 1 : Math.floor(Math.random() * 3) + 1;
      for (let i = 0; i < count; i++) {
        const day = Math.floor(Math.random() * 28) + 1;
        const amt = +(m.min + Math.random() * (m.max - m.min)).toFixed(2);
        txns.push({
          id: genId(), date: `${ym}-${String(day).padStart(2,"0")}`,
          amount: amt, currency: m.cur, merchant: m.name,
          categoryId: m.cat, tags: [], projectId: null, notes: "",
          type: "expense", splits: null,
        });
      }
    });
  });

  // Add some income
  months.forEach(ym => {
    txns.push({ id: genId(), date: `${ym}-01`, amount: 5500, currency: "EUR",
      merchant: "Employer EU - Salary", categoryId: null, tags: ["salary"],
      projectId: null, notes: "Monthly salary", type: "income", splits: null });
    txns.push({ id: genId(), date: `${ym}-01`, amount: 7000, currency: "USD",
      merchant: "Employer US - Salary", categoryId: null, tags: ["salary"],
      projectId: null, notes: "Monthly salary", type: "income", splits: null });
  });

  // Add a project
  const proj = { id: genId(), name: "Italy Trip 2026", budget: 3000, currency: "EUR",
    startDate: months[9]+"-01", endDate: months[10]+"-30", status: "active" };
  const projTxns = [
    { id: genId(), date: months[9]+"-05", amount: 450, currency: "EUR", merchant: "Ryanair",
      categoryId: "transport-flights", tags: ["EU"], projectId: proj.id, notes: "Flights to Rome",
      type: "expense", splits: null },
    { id: genId(), date: months[9]+"-10", amount: 680, currency: "EUR", merchant: "Hotel Roma",
      categoryId: "housing-mortgage", tags: ["EU"], projectId: proj.id, notes: "5 nights",
      type: "expense", splits: null },
    { id: genId(), date: months[10]+"-02", amount: 127.50, currency: "EUR", merchant: "Trattoria Roma",
      categoryId: "food-restaurant", tags: ["EU"], projectId: proj.id, notes: "Anniversary dinner",
      type: "expense", splits: null },
  ];

  return { transactions: [...txns, ...projTxns], projects: [proj] };
}

// ─── STYLES ─────────────────────────────────────────────────────────
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #0a0e17;
  --bg2: #111827;
  --bg3: #1a2234;
  --bg4: #243049;
  --border: #2a3654;
  --border2: #374766;
  --text: #e8ecf4;
  --text2: #94a3b8;
  --text3: #64748b;
  --green: #22c55e;
  --green-bg: rgba(34,197,94,0.1);
  --yellow: #eab308;
  --yellow-bg: rgba(234,179,8,0.1);
  --red: #ef4444;
  --red-bg: rgba(239,68,68,0.1);
  --blue: #3b82f6;
  --blue-bg: rgba(59,130,246,0.1);
  --purple: #a855f7;
  --purple-bg: rgba(168,85,247,0.1);
  --cyan: #06b6d4;
  --orange: #f97316;
  --font: 'DM Sans', sans-serif;
  --mono: 'JetBrains Mono', monospace;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: var(--bg); color: var(--text); font-family: var(--font); }

.app { max-width: 1400px; margin: 0 auto; padding: 16px; }

/* NAV */
.nav { display: flex; gap: 4px; background: var(--bg2); border-radius: 12px; padding: 4px; margin-bottom: 20px; border: 1px solid var(--border); overflow-x: auto; }
.nav button { flex: 1; min-width: max-content; padding: 10px 16px; border: none; background: transparent; color: var(--text2); font-family: var(--font); font-size: 13px; font-weight: 500; border-radius: 8px; cursor: pointer; transition: all 0.2s; white-space: nowrap; }
.nav button:hover { color: var(--text); background: var(--bg3); }
.nav button.active { background: var(--bg4); color: var(--text); box-shadow: 0 2px 8px rgba(0,0,0,0.3); }

/* HEADER */
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; flex-wrap: wrap; gap: 12px; }
.header h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }
.header h1 span { color: var(--blue); }
.month-selector { display: flex; align-items: center; gap: 8px; }
.month-selector button { background: var(--bg3); border: 1px solid var(--border); color: var(--text); width: 32px; height: 32px; border-radius: 8px; cursor: pointer; font-size: 14px; display: flex; align-items: center; justify-content: center; }
.month-selector button:hover { background: var(--bg4); }
.month-selector span { font-family: var(--mono); font-size: 14px; color: var(--text2); min-width: 90px; text-align: center; }

/* CARDS */
.card { background: var(--bg2); border: 1px solid var(--border); border-radius: 14px; padding: 20px; margin-bottom: 16px; }
.card h2 { font-size: 15px; font-weight: 600; margin-bottom: 14px; color: var(--text2); text-transform: uppercase; letter-spacing: 0.5px; }
.card h3 { font-size: 14px; font-weight: 600; margin-bottom: 10px; }

/* GRID */
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.grid4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; }
@media (max-width: 900px) { .grid2, .grid3, .grid4 { grid-template-columns: 1fr; } }

/* TRAFFIC LIGHT */
.traffic { display: flex; flex-direction: column; gap: 10px; }
.traffic-item { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: var(--bg3); border-radius: 10px; cursor: pointer; transition: all 0.15s; border: 1px solid transparent; }
.traffic-item:hover { border-color: var(--border2); background: var(--bg4); }
.traffic-icon { font-size: 20px; width: 32px; text-align: center; flex-shrink: 0; }
.traffic-info { flex: 1; min-width: 0; }
.traffic-label { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.traffic-amounts { font-family: var(--mono); font-size: 12px; color: var(--text2); }
.traffic-bar-wrap { height: 6px; background: var(--bg); border-radius: 3px; overflow: hidden; margin-top: 4px; }
.traffic-bar { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.traffic-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot-green { background: var(--green); box-shadow: 0 0 8px rgba(34,197,94,0.4); }
.dot-yellow { background: var(--yellow); box-shadow: 0 0 8px rgba(234,179,8,0.4); }
.dot-red { background: var(--red); box-shadow: 0 0 8px rgba(239,68,68,0.4); }

/* STAT BOXES */
.stat-box { background: var(--bg3); border-radius: 10px; padding: 14px; text-align: center; }
.stat-box .label { font-size: 11px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.stat-box .value { font-family: var(--mono); font-size: 20px; font-weight: 700; }
.stat-box .sub { font-size: 11px; color: var(--text3); margin-top: 4px; }
.stat-green .value { color: var(--green); }
.stat-yellow .value { color: var(--yellow); }
.stat-red .value { color: var(--red); }
.stat-blue .value { color: var(--blue); }

/* OVERALL METER */
.meter-wrap { margin-bottom: 16px; }
.meter-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }
.meter-header .pct { font-family: var(--mono); font-size: 28px; font-weight: 700; }
.meter-header .detail { font-size: 12px; color: var(--text2); }
.meter-bar-outer { height: 14px; background: var(--bg); border-radius: 7px; overflow: hidden; position: relative; }
.meter-bar-inner { height: 100%; border-radius: 7px; transition: width 0.5s ease; }
.meter-bar-marker { position: absolute; top: -4px; width: 2px; height: 22px; background: var(--text); border-radius: 1px; opacity: 0.5; }
.meter-legend { display: flex; justify-content: space-between; margin-top: 6px; font-size: 11px; color: var(--text3); }

/* TABLES */
.txn-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.txn-table th { text-align: left; padding: 8px 10px; color: var(--text3); font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
.txn-table td { padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.txn-table tr:hover td { background: var(--bg3); }
.txn-table .amt { font-family: var(--mono); font-weight: 500; text-align: right; }
.txn-table .amt.expense { color: var(--red); }
.txn-table .amt.income { color: var(--green); }
.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-right: 4px; }
.tag-project { background: var(--purple-bg); color: var(--purple); }
.tag-custom { background: var(--blue-bg); color: var(--blue); }
.tag-split { background: var(--orange); color: #000; font-size: 9px; }

/* CHART BARS */
.chart-container { display: flex; align-items: flex-end; gap: 6px; height: 180px; padding-top: 10px; }
.chart-bar-wrap { flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end; }
.chart-bar { width: 100%; border-radius: 4px 4px 0 0; transition: height 0.4s ease; min-height: 2px; position: relative; cursor: pointer; }
.chart-bar:hover { opacity: 0.85; }
.chart-bar-label { font-size: 10px; color: var(--text3); margin-top: 6px; }
.chart-bar-value { font-family: var(--mono); font-size: 9px; color: var(--text2); margin-bottom: 4px; }
.chart-stacked { display: flex; flex-direction: column-reverse; width: 100%; }

/* DUAL BAR */
.dual-bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.dual-bar-label { width: 60px; font-size: 11px; color: var(--text3); text-align: right; flex-shrink: 0; }
.dual-bar-track { flex: 1; display: flex; gap: 2px; height: 20px; }
.dual-bar-fill { height: 100%; border-radius: 3px; position: relative; transition: width 0.4s ease; cursor: pointer; }
.dual-bar-fill:hover::after { content: attr(data-tip); position: absolute; top: -28px; left: 50%; transform: translateX(-50%); background: var(--bg4); color: var(--text); padding: 2px 8px; border-radius: 4px; font-size: 10px; font-family: var(--mono); white-space: nowrap; z-index: 10; }

/* FORMS */
.form-row { display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-group label { font-size: 11px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.3px; }
.form-group input, .form-group select, .form-group textarea {
  background: var(--bg3); border: 1px solid var(--border); color: var(--text);
  padding: 8px 12px; border-radius: 8px; font-family: var(--font); font-size: 13px;
  outline: none; transition: border-color 0.2s;
}
.form-group input:focus, .form-group select:focus { border-color: var(--blue); }
.btn { padding: 8px 18px; border: none; border-radius: 8px; font-family: var(--font); font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.btn-primary { background: var(--blue); color: #fff; }
.btn-primary:hover { background: #2563eb; }
.btn-secondary { background: var(--bg3); color: var(--text); border: 1px solid var(--border); }
.btn-secondary:hover { background: var(--bg4); }
.btn-danger { background: var(--red-bg); color: var(--red); }
.btn-sm { padding: 4px 12px; font-size: 12px; }

/* MODAL */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 100; backdrop-filter: blur(4px); }
.modal { background: var(--bg2); border: 1px solid var(--border); border-radius: 16px; padding: 24px; max-width: 560px; width: 90%; max-height: 85vh; overflow-y: auto; }
.modal h2 { font-size: 18px; margin-bottom: 16px; }

/* PROJECTS */
.project-card { background: var(--bg3); border-radius: 12px; padding: 16px; border: 1px solid var(--border); }
.project-card h3 { font-size: 15px; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.project-badge { padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }
.project-active { background: var(--green-bg); color: var(--green); }
.project-completed { background: var(--blue-bg); color: var(--blue); }

/* RULES */
.rule-item { display: flex; align-items: center; gap: 10px; padding: 10px; background: var(--bg3); border-radius: 8px; margin-bottom: 6px; font-size: 13px; }
.rule-pattern { font-family: var(--mono); color: var(--cyan); flex: 1; }
.rule-arrow { color: var(--text3); }
.rule-target { color: var(--text2); }

/* MISC */
.empty { text-align: center; padding: 40px; color: var(--text3); font-size: 14px; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.flex-gap { display: flex; gap: 8px; align-items: center; }
.mt { margin-top: 12px; }
.mb { margin-bottom: 12px; }
.pill { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.scroll-x { overflow-x: auto; }
`;

// ─── HELPERS ────────────────────────────────────────────────────────
const fmt = (n, cur) => {
  const sym = cur === "EUR" ? "€" : "$";
  return `${sym}${Math.abs(n).toLocaleString("en", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
};

const fmtFull = (n, cur) => {
  const sym = cur === "EUR" ? "€" : "$";
  return `${sym}${Math.abs(n).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const pct = (a, b) => b === 0 ? 0 : Math.round((a / b) * 100);
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const trafficColor = (spent, budget) => {
  if (budget === 0) return "green";
  const r = spent / budget;
  if (r <= 0.75) return "green";
  if (r <= 1.0) return "yellow";
  return "red";
};
const colorVar = c => c === "green" ? "var(--green)" : c === "yellow" ? "var(--yellow)" : "var(--red)";

function getCatLabel(cats, id) {
  for (const g of cats) {
    if (g.id === id) return g.label;
    for (const c of g.children) {
      if (c.id === id) return `${g.icon} ${c.label}`;
    }
  }
  return id || "—";
}
function getParentCat(cats, id) {
  for (const g of cats) {
    for (const c of g.children) {
      if (c.id === id) return g.id;
    }
  }
  return id;
}
function getAllSubcatIds(cats, parentId) {
  const g = cats.find(c => c.id === parentId);
  return g ? g.children.map(c => c.id) : [parentId];
}

// ─── MAIN APP ───────────────────────────────────────────────────────
export default function FinanceTracker() {
  const [data] = useState(() => generateSampleData());
  const [transactions, setTransactions] = useState(data.transactions);
  const [projects, setProjects] = useState(data.projects);
  const [categories] = useState(DEFAULT_CATEGORIES);
  const [budgetsEUR] = useState(SAMPLE_BUDGETS_EUR);
  const [budgetsUSD] = useState(SAMPLE_BUDGETS_USD);
  const [incomeEUR] = useState(5500);
  const [incomeUSD] = useState(7000);
  const [savingsGoalPct] = useState(20);
  const [rules, setRules] = useState([
    { id: "r1", pattern: "WHOLE FOODS", categoryId: "food-grocery", priority: 1 },
    { id: "r2", pattern: "ALBERT HEIJN", categoryId: "food-grocery", priority: 1 },
    { id: "r3", pattern: "SHELL", categoryId: "transport-fuel", priority: 2 },
    { id: "r4", pattern: "NETFLIX", categoryId: "personal-subs", priority: 1 },
    { id: "r5", pattern: "AMAZON", categoryId: "personal-hobbies", priority: 3 },
    { id: "r6", pattern: "STARBUCKS", categoryId: "food-coffee", priority: 1 },
  ]);

  const [view, setView] = useState("dashboard");
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const n = new Date();
    return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,"0")}`;
  });
  const [drillCat, setDrillCat] = useState(null);
  const [showAddTxn, setShowAddTxn] = useState(false);
  const [showAddProject, setShowAddProject] = useState(false);
  const [compareYear, setCompareYear] = useState(null);

  // ── Derived ──
  const monthTxns = useMemo(() =>
    transactions.filter(t => monthKey(t.date) === selectedMonth),
    [transactions, selectedMonth]
  );

  const regularExpenses = useCallback((txns) =>
    txns.filter(t => t.type === "expense" && !t.projectId),
    []
  );

  const projectExpenses = useCallback((txns) =>
    txns.filter(t => t.type === "expense" && t.projectId),
    []
  );

  const incomes = useCallback((txns) =>
    txns.filter(t => t.type === "income"),
    []
  );

  const spendByCat = useCallback((txns, cur) => {
    const map = {};
    regularExpenses(txns).forEach(t => {
      if (t.currency !== cur) return;
      const parent = getParentCat(categories, t.categoryId);
      map[parent] = (map[parent] || 0) + t.amount;
    });
    return map;
  }, [categories, regularExpenses]);

  const totalRegularSpend = useCallback((txns, cur) =>
    regularExpenses(txns).filter(t => t.currency === cur).reduce((s, t) => s + t.amount, 0),
    [regularExpenses]
  );

  const totalIncome = useCallback((txns, cur) =>
    incomes(txns).filter(t => t.currency === cur).reduce((s, t) => s + t.amount, 0),
    [incomes]
  );

  const totalBudget = (budgets) => Object.values(budgets).reduce((s, v) => s + v, 0);

  const savingsTarget = (inc) => inc * (savingsGoalPct / 100);
  const discretionaryPool = (inc, budgets) => inc - savingsTarget(inc);

  // Month navigation
  const prevMonth = () => {
    const [y, m] = selectedMonth.split("-").map(Number);
    const d = new Date(y, m - 2, 1);
    setSelectedMonth(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`);
  };
  const nextMonth = () => {
    const [y, m] = selectedMonth.split("-").map(Number);
    const d = new Date(y, m, 1);
    setSelectedMonth(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`);
  };
  const monthLabel = selectedMonth ? `${MONTHS[parseInt(selectedMonth.split("-")[1])-1]} ${selectedMonth.split("-")[0]}` : "";

  // Day progress through month
  const dayProgress = useMemo(() => {
    const now = new Date();
    const currentYM = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}`;
    if (selectedMonth !== currentYM) return 100;
    return pct(now.getDate(), daysInMonth(selectedMonth));
  }, [selectedMonth]);

  // ── VIEWS ─────────────────────────────────────────────────────────

  // DASHBOARD
  const renderDashboard = () => {
    const eurSpend = spendByCat(monthTxns, "EUR");
    const usdSpend = spendByCat(monthTxns, "USD");
    const eurTotal = totalRegularSpend(monthTxns, "EUR");
    const usdTotal = totalRegularSpend(monthTxns, "USD");
    const eurBudgetTotal = totalBudget(budgetsEUR);
    const usdBudgetTotal = totalBudget(budgetsUSD);
    const eurPool = discretionaryPool(incomeEUR, budgetsEUR);
    const usdPool = discretionaryPool(incomeUSD, budgetsUSD);
    const eurSaved = incomeEUR - eurTotal;
    const usdSaved = incomeUSD - usdTotal;
    const eurSavingsRate = pct(eurSaved, incomeEUR);
    const usdSavingsRate = pct(usdSaved, incomeUSD);
    const overallEUR = trafficColor(eurTotal, eurBudgetTotal);
    const overallUSD = trafficColor(usdTotal, usdBudgetTotal);

    return (
      <>
        {/* Overall meters */}
        <div className="grid2 mb">
          {[{ cur: "EUR", total: eurTotal, budget: eurBudgetTotal, pool: eurPool, income: incomeEUR, saved: eurSaved, savRate: eurSavingsRate, color: overallEUR },
            { cur: "USD", total: usdTotal, budget: usdBudgetTotal, pool: usdPool, income: incomeUSD, saved: usdSaved, savRate: usdSavingsRate, color: overallUSD }
          ].map(d => (
            <div className="card" key={d.cur}>
              <div className="flex-between mb">
                <h2>{d.cur} Budget</h2>
                <span className="pill" style={{ background: d.color === "green" ? "var(--green-bg)" : d.color === "yellow" ? "var(--yellow-bg)" : "var(--red-bg)", color: colorVar(d.color) }}>
                  {d.color === "green" ? "On Track" : d.color === "yellow" ? "Watch It" : "Over Budget"}
                </span>
              </div>
              <div className="meter-wrap">
                <div className="meter-header">
                  <span className="pct" style={{ color: colorVar(d.color) }}>{pct(d.total, d.budget)}%</span>
                  <span className="detail">{fmt(d.total, d.cur)} of {fmt(d.budget, d.cur)} budget</span>
                </div>
                <div className="meter-bar-outer">
                  <div className="meter-bar-inner" style={{ width: `${clamp(pct(d.total, d.budget), 0, 100)}%`, background: colorVar(d.color) }} />
                  <div className="meter-bar-marker" style={{ left: `${dayProgress}%` }} />
                </div>
                <div className="meter-legend">
                  <span>Day {Math.round(dayProgress)}% through month</span>
                  <span>Remaining: {fmt(Math.max(0, d.budget - d.total), d.cur)}</span>
                </div>
              </div>
              <div className="grid3 mt">
                <div className={`stat-box stat-blue`}>
                  <div className="label">Income</div>
                  <div className="value">{fmt(d.income, d.cur)}</div>
                </div>
                <div className={`stat-box ${d.savRate >= savingsGoalPct ? "stat-green" : "stat-yellow"}`}>
                  <div className="label">Savings Rate</div>
                  <div className="value">{d.savRate}%</div>
                  <div className="sub">Target: {savingsGoalPct}%</div>
                </div>
                <div className={`stat-box stat-${d.color}`}>
                  <div className="label">Remaining</div>
                  <div className="value">{fmt(Math.max(0, d.budget - d.total), d.cur)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Category traffic lights */}
        <div className="grid2">
          {["EUR", "USD"].map(cur => {
            const spend = cur === "EUR" ? eurSpend : usdSpend;
            const budgets = cur === "EUR" ? budgetsEUR : budgetsUSD;
            return (
              <div className="card" key={cur}>
                <h2>{cur} Categories</h2>
                <div className="traffic">
                  {categories.map(g => {
                    const spent = spend[g.id] || 0;
                    const budget = budgets[g.id] || 0;
                    if (budget === 0 && spent === 0) return null;
                    const color = trafficColor(spent, budget);
                    const p = budget > 0 ? clamp(pct(spent, budget), 0, 100) : 0;
                    return (
                      <div className="traffic-item" key={g.id} onClick={() => { setDrillCat(g.id); setView("drill"); }}>
                        <div className="traffic-icon">{g.icon}</div>
                        <div className="traffic-info">
                          <div className="traffic-label">{g.label}</div>
                          <div className="traffic-amounts">
                            {fmt(spent, cur)} / {fmt(budget, cur)}
                            <span style={{ float: "right", color: colorVar(color) }}>{p}%</span>
                          </div>
                          <div className="traffic-bar-wrap">
                            <div className="traffic-bar" style={{ width: `${p}%`, background: colorVar(color) }} />
                          </div>
                        </div>
                        <div className={`traffic-dot dot-${color}`} />
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Project summary */}
        {projects.length > 0 && (
          <div className="card mt">
            <h2>Active Projects (excluded from budget)</h2>
            <div className="grid3">
              {projects.map(p => {
                const spent = transactions.filter(t => t.projectId === p.id).reduce((s, t) => s + t.amount, 0);
                const color = trafficColor(spent, p.budget);
                return (
                  <div className="project-card" key={p.id}>
                    <h3>✈️ {p.name} <span className={`project-badge project-${p.status}`}>{p.status}</span></h3>
                    <div className="traffic-amounts" style={{ fontFamily: "var(--mono)", fontSize: 13 }}>
                      {fmt(spent, p.currency)} / {fmt(p.budget, p.currency)}
                    </div>
                    <div className="traffic-bar-wrap" style={{ marginTop: 8 }}>
                      <div className="traffic-bar" style={{ width: `${clamp(pct(spent, p.budget), 0, 100)}%`, background: colorVar(color) }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </>
    );
  };

  // DRILL DOWN
  const renderDrill = () => {
    if (!drillCat) return <div className="empty">Select a category from the dashboard</div>;
    const cat = categories.find(c => c.id === drillCat);
    if (!cat) return null;
    const subIds = getAllSubcatIds(categories, drillCat);
    const txns = monthTxns.filter(t => t.type === "expense" && !t.projectId && subIds.includes(t.categoryId));
    const totalEUR = txns.filter(t => t.currency === "EUR").reduce((s, t) => s + t.amount, 0);
    const totalUSD = txns.filter(t => t.currency === "USD").reduce((s, t) => s + t.amount, 0);
    const budgetEUR = budgetsEUR[drillCat] || 0;
    const budgetUSD = budgetsUSD[drillCat] || 0;

    // sub-category breakdown
    const subBreakdown = {};
    txns.forEach(t => {
      const k = `${t.categoryId}-${t.currency}`;
      subBreakdown[k] = (subBreakdown[k] || 0) + t.amount;
    });

    return (
      <div className="card">
        <div className="flex-between mb">
          <h2>{cat.icon} {cat.label} — {monthLabel}</h2>
          <button className="btn btn-secondary btn-sm" onClick={() => setView("dashboard")}>← Back</button>
        </div>
        <div className="grid2 mb">
          <div className={`stat-box stat-${trafficColor(totalEUR, budgetEUR)}`}>
            <div className="label">EUR Spent / Budget</div>
            <div className="value">{fmt(totalEUR, "EUR")} / {fmt(budgetEUR, "EUR")}</div>
            <div className="sub">Remaining: {fmt(Math.max(0, budgetEUR - totalEUR), "EUR")}</div>
          </div>
          <div className={`stat-box stat-${trafficColor(totalUSD, budgetUSD)}`}>
            <div className="label">USD Spent / Budget</div>
            <div className="value">{fmt(totalUSD, "USD")} / {fmt(budgetUSD, "USD")}</div>
            <div className="sub">Remaining: {fmt(Math.max(0, budgetUSD - totalUSD), "USD")}</div>
          </div>
        </div>

        {/* Sub-category bars */}
        <h3>Subcategory Breakdown</h3>
        <div style={{ marginBottom: 16 }}>
          {cat.children.map(sub => {
            const eurAmt = subBreakdown[`${sub.id}-EUR`] || 0;
            const usdAmt = subBreakdown[`${sub.id}-USD`] || 0;
            if (eurAmt === 0 && usdAmt === 0) return null;
            const maxAmt = Math.max(totalEUR + totalUSD, 1);
            return (
              <div className="dual-bar-row" key={sub.id}>
                <div className="dual-bar-label">{sub.label}</div>
                <div className="dual-bar-track">
                  {eurAmt > 0 && <div className="dual-bar-fill" style={{ width: `${pct(eurAmt, maxAmt)}%`, background: "var(--blue)" }} data-tip={`€${eurAmt.toFixed(0)}`} />}
                  {usdAmt > 0 && <div className="dual-bar-fill" style={{ width: `${pct(usdAmt, maxAmt)}%`, background: "var(--cyan)" }} data-tip={`$${usdAmt.toFixed(0)}`} />}
                </div>
              </div>
            );
          })}
        </div>

        {/* Transactions */}
        <h3>Transactions</h3>
        <div className="scroll-x">
          <table className="txn-table">
            <thead><tr><th>Date</th><th>Merchant</th><th>Subcategory</th><th>Tags</th><th style={{textAlign:"right"}}>Amount</th></tr></thead>
            <tbody>
              {txns.sort((a,b) => b.date.localeCompare(a.date)).map(t => (
                <tr key={t.id}>
                  <td style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{t.date}</td>
                  <td>{t.merchant}</td>
                  <td style={{ color: "var(--text2)" }}>{getCatLabel(categories, t.categoryId)}</td>
                  <td>{t.tags.map(tag => <span key={tag} className="tag tag-custom">{tag}</span>)}</td>
                  <td className="amt expense">{fmtFull(t.amount, t.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // TRANSACTIONS
  const renderTransactions = () => {
    const sorted = [...monthTxns].sort((a, b) => b.date.localeCompare(a.date));
    return (
      <div className="card">
        <div className="flex-between mb">
          <h2>All Transactions — {monthLabel}</h2>
          <button className="btn btn-primary btn-sm" onClick={() => setShowAddTxn(true)}>+ Add</button>
        </div>
        <div className="scroll-x">
          <table className="txn-table">
            <thead><tr><th>Date</th><th>Merchant</th><th>Category</th><th>Tags</th><th>Project</th><th style={{textAlign:"right"}}>Amount</th></tr></thead>
            <tbody>
              {sorted.map(t => {
                const proj = t.projectId ? projects.find(p => p.id === t.projectId) : null;
                return (
                  <tr key={t.id}>
                    <td style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{t.date}</td>
                    <td>{t.merchant}</td>
                    <td style={{ color: "var(--text2)", fontSize: 12 }}>{t.type === "income" ? "💰 Income" : getCatLabel(categories, t.categoryId)}</td>
                    <td>{t.tags.map(tag => <span key={tag} className="tag tag-custom">{tag}</span>)}{t.splits && <span className="tag tag-split">SPLIT</span>}</td>
                    <td>{proj ? <span className="tag tag-project">{proj.name}</span> : "—"}</td>
                    <td className={`amt ${t.type}`}>{t.type === "expense" ? "-" : "+"}{fmtFull(t.amount, t.currency)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {sorted.length === 0 && <div className="empty">No transactions this month</div>}
      </div>
    );
  };

  // TRENDS
  const renderTrends = () => {
    const [y, m] = selectedMonth.split("-").map(Number);
    const monthKeys = [];
    for (let i = 11; i >= 0; i--) {
      const d = new Date(y, m - 1 - i, 1);
      monthKeys.push(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`);
    }

    const monthData = monthKeys.map(mk => {
      const txns = transactions.filter(t => monthKey(t.date) === mk);
      return {
        key: mk,
        label: `${MONTHS[parseInt(mk.split("-")[1])-1]}'${mk.slice(2,4)}`,
        eurSpend: totalRegularSpend(txns, "EUR"),
        usdSpend: totalRegularSpend(txns, "USD"),
        eurIncome: totalIncome(txns, "EUR"),
        usdIncome: totalIncome(txns, "USD"),
      };
    });

    const maxSpend = Math.max(...monthData.map(d => Math.max(d.eurSpend, d.usdSpend)), 1);
    const maxIncome = Math.max(...monthData.map(d => Math.max(d.eurIncome, d.usdIncome)), 1);
    const maxVal = Math.max(maxSpend, maxIncome);

    // YoY comparison
    const currentYearKey = selectedMonth.slice(0, 4);
    const prevYearKey = String(parseInt(currentYearKey) - 1);
    const yoyData = MONTHS.map((label, i) => {
      const mk1 = `${currentYearKey}-${String(i+1).padStart(2,"0")}`;
      const mk2 = `${prevYearKey}-${String(i+1).padStart(2,"0")}`;
      const txns1 = transactions.filter(t => monthKey(t.date) === mk1);
      const txns2 = transactions.filter(t => monthKey(t.date) === mk2);
      return {
        label, month: i+1,
        currEUR: totalRegularSpend(txns1, "EUR"),
        currUSD: totalRegularSpend(txns1, "USD"),
        prevEUR: totalRegularSpend(txns2, "EUR"),
        prevUSD: totalRegularSpend(txns2, "USD"),
      };
    });
    const yoyMax = Math.max(...yoyData.map(d => Math.max(d.currEUR, d.currUSD, d.prevEUR, d.prevUSD)), 1);

    return (
      <>
        {/* Monthly trend */}
        <div className="card">
          <h2>Monthly Spending Trend (12 Months)</h2>
          <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
            <span style={{ fontSize: 11, color: "var(--blue)" }}>■ EUR Spend</span>
            <span style={{ fontSize: 11, color: "var(--cyan)" }}>■ USD Spend</span>
            <span style={{ fontSize: 11, color: "var(--text3)" }}>— Budget</span>
          </div>
          <div className="chart-container">
            {monthData.map(d => (
              <div className="chart-bar-wrap" key={d.key}>
                <div className="chart-bar-value">{fmt(d.eurSpend, "EUR")}</div>
                <div style={{ display: "flex", gap: 2, alignItems: "flex-end", width: "100%", height: "100%" }}>
                  <div className="chart-bar" style={{
                    flex: 1, height: `${pct(d.eurSpend, maxVal)}%`,
                    background: "var(--blue)",
                  }} title={`EUR: ${fmt(d.eurSpend, "EUR")}`} />
                  <div className="chart-bar" style={{
                    flex: 1, height: `${pct(d.usdSpend, maxVal)}%`,
                    background: "var(--cyan)",
                  }} title={`USD: ${fmt(d.usdSpend, "USD")}`} />
                </div>
                <div className="chart-bar-label">{d.label}</div>
              </div>
            ))}
          </div>
          {/* Budget lines as reference */}
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12, fontFamily: "var(--mono)", fontSize: 11, color: "var(--text3)" }}>
            <span>EUR Budget: {fmt(totalBudget(budgetsEUR), "EUR")}/mo</span>
            <span>USD Budget: {fmt(totalBudget(budgetsUSD), "USD")}/mo</span>
          </div>
        </div>

        {/* Year over Year */}
        <div className="card">
          <h2>Year-over-Year: {currentYearKey} vs {prevYearKey}</h2>
          <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
            <span style={{ fontSize: 11, color: "var(--blue)" }}>■ {currentYearKey}</span>
            <span style={{ fontSize: 11, color: "var(--text3)" }}>■ {prevYearKey}</span>
          </div>
          <div>
            <h3 style={{ color: "var(--text2)", fontSize: 12, marginBottom: 8 }}>EUR Spending</h3>
            <div className="chart-container" style={{ height: 120 }}>
              {yoyData.map(d => (
                <div className="chart-bar-wrap" key={d.label}>
                  <div style={{ display: "flex", gap: 2, alignItems: "flex-end", width: "100%", height: "100%" }}>
                    <div className="chart-bar" style={{ flex: 1, height: `${pct(d.currEUR, yoyMax)}%`, background: "var(--blue)" }} />
                    <div className="chart-bar" style={{ flex: 1, height: `${pct(d.prevEUR, yoyMax)}%`, background: "var(--text3)", opacity: 0.4 }} />
                  </div>
                  <div className="chart-bar-label">{d.label}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ marginTop: 20 }}>
            <h3 style={{ color: "var(--text2)", fontSize: 12, marginBottom: 8 }}>USD Spending</h3>
            <div className="chart-container" style={{ height: 120 }}>
              {yoyData.map(d => (
                <div className="chart-bar-wrap" key={d.label+"u"}>
                  <div style={{ display: "flex", gap: 2, alignItems: "flex-end", width: "100%", height: "100%" }}>
                    <div className="chart-bar" style={{ flex: 1, height: `${pct(d.currUSD, yoyMax)}%`, background: "var(--cyan)" }} />
                    <div className="chart-bar" style={{ flex: 1, height: `${pct(d.prevUSD, yoyMax)}%`, background: "var(--text3)", opacity: 0.4 }} />
                  </div>
                  <div className="chart-bar-label">{d.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Savings rate trend */}
        <div className="card">
          <h2>Savings Rate Trend</h2>
          <div className="chart-container" style={{ height: 120 }}>
            {monthData.map(d => {
              const eurRate = d.eurIncome > 0 ? pct(d.eurIncome - d.eurSpend, d.eurIncome) : 0;
              const usdRate = d.usdIncome > 0 ? pct(d.usdIncome - d.usdSpend, d.usdIncome) : 0;
              const avgRate = Math.round((eurRate + usdRate) / 2);
              const c = avgRate >= savingsGoalPct ? "var(--green)" : avgRate >= 10 ? "var(--yellow)" : "var(--red)";
              return (
                <div className="chart-bar-wrap" key={d.key+"s"}>
                  <div className="chart-bar-value" style={{ color: c }}>{avgRate}%</div>
                  <div className="chart-bar" style={{ width: "100%", height: `${clamp(avgRate, 2, 100)}%`, background: c }} />
                  <div className="chart-bar-label">{d.label}</div>
                </div>
              );
            })}
          </div>
          <div style={{ textAlign: "center", marginTop: 8, fontSize: 11, color: "var(--text3)" }}>
            Target savings rate: {savingsGoalPct}%
          </div>
        </div>
      </>
    );
  };

  // PROJECTS
  const renderProjects = () => {
    return (
      <div className="card">
        <div className="flex-between mb">
          <h2>Projects & Trips</h2>
          <button className="btn btn-primary btn-sm" onClick={() => setShowAddProject(true)}>+ New Project</button>
        </div>
        {projects.length === 0 && <div className="empty">No projects yet. Create one to track trip or one-off spending separately from your regular budget.</div>}
        {projects.map(p => {
          const txns = transactions.filter(t => t.projectId === p.id).sort((a, b) => b.date.localeCompare(a.date));
          const spent = txns.reduce((s, t) => s + t.amount, 0);
          const color = trafficColor(spent, p.budget);
          return (
            <div className="project-card mb" key={p.id}>
              <h3>✈️ {p.name} <span className={`project-badge project-${p.status}`}>{p.status}</span></h3>
              <div className="grid4 mb">
                <div className="stat-box"><div className="label">Budget</div><div className="value" style={{fontSize:16}}>{fmt(p.budget, p.currency)}</div></div>
                <div className={`stat-box stat-${color}`}><div className="label">Spent</div><div className="value" style={{fontSize:16}}>{fmt(spent, p.currency)}</div></div>
                <div className="stat-box"><div className="label">Remaining</div><div className="value" style={{fontSize:16}}>{fmt(Math.max(0, p.budget - spent), p.currency)}</div></div>
                <div className="stat-box"><div className="label">Transactions</div><div className="value" style={{fontSize:16}}>{txns.length}</div></div>
              </div>
              <div className="traffic-bar-wrap mb">
                <div className="traffic-bar" style={{ width: `${clamp(pct(spent, p.budget), 0, 100)}%`, background: colorVar(color) }} />
              </div>
              {txns.length > 0 && (
                <table className="txn-table">
                  <thead><tr><th>Date</th><th>Merchant</th><th>Category</th><th style={{textAlign:"right"}}>Amount</th></tr></thead>
                  <tbody>
                    {txns.map(t => (
                      <tr key={t.id}>
                        <td style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{t.date}</td>
                        <td>{t.merchant}</td>
                        <td style={{ color: "var(--text2)", fontSize: 12 }}>{getCatLabel(categories, t.categoryId)}</td>
                        <td className="amt expense">{fmtFull(t.amount, t.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // RULES
  const renderRules = () => {
    return (
      <div className="card">
        <div className="flex-between mb">
          <h2>Auto-Categorization Rules</h2>
          <button className="btn btn-primary btn-sm" onClick={() => {
            const pattern = prompt("Merchant pattern (e.g. WALMART):");
            if (!pattern) return;
            // Simple: just add to uncategorized, user can edit
            setRules(prev => [...prev, { id: genId(), pattern: pattern.toUpperCase(), categoryId: "misc-uncat", priority: 5 }]);
          }}>+ Add Rule</button>
        </div>
        <p style={{ fontSize: 13, color: "var(--text2)", marginBottom: 16 }}>
          Rules match merchant names (case-insensitive) and auto-assign categories. Higher priority rules are checked first. You can override any auto-categorized transaction manually.
        </p>
        <div>
          {rules.sort((a,b) => a.priority - b.priority).map(r => (
            <div className="rule-item" key={r.id}>
              <span style={{ fontSize: 11, color: "var(--text3)", fontFamily: "var(--mono)" }}>P{r.priority}</span>
              <span className="rule-pattern">"{r.pattern}"</span>
              <span className="rule-arrow">→</span>
              <span className="rule-target">{getCatLabel(categories, r.categoryId)}</span>
              <button className="btn btn-danger btn-sm" onClick={() => setRules(prev => prev.filter(x => x.id !== r.id))}>✕</button>
            </div>
          ))}
        </div>
        {rules.length === 0 && <div className="empty">No rules defined. Rules are learned as you categorize transactions.</div>}
      </div>
    );
  };

  // CAN I SPEND? (quick check)
  const renderCanISpend = () => {
    const [checkAmt, setCheckAmt] = useState("");
    const [checkCur, setCheckCur] = useState("EUR");
    const [checkCat, setCheckCat] = useState("food");

    const budgets = checkCur === "EUR" ? budgetsEUR : budgetsUSD;
    const budget = budgets[checkCat] || 0;
    const spent = spendByCat(monthTxns, checkCur)[checkCat] || 0;
    const remaining = Math.max(0, budget - spent);
    const amt = parseFloat(checkAmt) || 0;
    const afterSpend = remaining - amt;
    const canSpend = afterSpend >= 0;
    const daysLeft = daysInMonth(selectedMonth) - dayOfMonth(today());
    const dailyBudgetRemaining = daysLeft > 0 ? remaining / daysLeft : remaining;

    const cat = categories.find(c => c.id === checkCat);

    return (
      <div className="card">
        <h2>Can I Spend This?</h2>
        <p style={{ fontSize: 13, color: "var(--text2)", marginBottom: 16 }}>
          Quick check before making a purchase. Enter the amount and category to see if it fits your budget.
        </p>
        <div className="form-row">
          <div className="form-group" style={{ flex: 1 }}>
            <label>Amount</label>
            <input type="number" placeholder="0.00" value={checkAmt} onChange={e => setCheckAmt(e.target.value)} style={{ fontSize: 24, fontFamily: "var(--mono)", padding: "12px 16px" }} />
          </div>
          <div className="form-group" style={{ width: 100 }}>
            <label>Currency</label>
            <select value={checkCur} onChange={e => setCheckCur(e.target.value)} style={{ fontSize: 16, padding: "12px" }}>
              <option value="EUR">EUR €</option>
              <option value="USD">USD $</option>
            </select>
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Category</label>
            <select value={checkCat} onChange={e => setCheckCat(e.target.value)} style={{ fontSize: 14, padding: "12px" }}>
              {categories.map(g => <option key={g.id} value={g.id}>{g.icon} {g.label}</option>)}
            </select>
          </div>
        </div>

        {amt > 0 && (
          <div style={{ marginTop: 20, padding: 24, borderRadius: 14, background: canSpend ? "var(--green-bg)" : "var(--red-bg)", border: `2px solid ${canSpend ? "var(--green)" : "var(--red)"}` }}>
            <div style={{ fontSize: 48, textAlign: "center", marginBottom: 8 }}>
              {canSpend ? "✅" : "🛑"}
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, textAlign: "center", color: canSpend ? "var(--green)" : "var(--red)", marginBottom: 16 }}>
              {canSpend ? "Yes, you can spend this" : "This would exceed your budget"}
            </div>
            <div className="grid3">
              <div className="stat-box">
                <div className="label">{cat?.icon} {cat?.label} Budget</div>
                <div className="value" style={{ color: "var(--text)" }}>{fmt(budget, checkCur)}</div>
              </div>
              <div className="stat-box">
                <div className="label">Already Spent</div>
                <div className="value" style={{ color: "var(--yellow)" }}>{fmt(spent, checkCur)}</div>
              </div>
              <div className={`stat-box ${canSpend ? "stat-green" : "stat-red"}`}>
                <div className="label">After This Purchase</div>
                <div className="value">{fmt(afterSpend, checkCur)}</div>
              </div>
            </div>
            <div style={{ marginTop: 16, textAlign: "center", fontSize: 13, color: "var(--text2)" }}>
              {daysLeft > 0 && canSpend && (
                <>Daily budget for remaining {daysLeft} days: {fmt(Math.max(0, afterSpend / daysLeft), checkCur)}/day</>
              )}
              {daysLeft > 0 && !canSpend && (
                <>You're already {fmt(Math.abs(afterSpend), checkCur)} over budget for {cat?.label} this month</>
              )}
            </div>
          </div>
        )}

        {amt === 0 && (
          <div className="grid2 mt">
            {["EUR", "USD"].map(cur => {
              const bud = cur === "EUR" ? budgetsEUR : budgetsUSD;
              const catBud = bud[checkCat] || 0;
              const catSpent = spendByCat(monthTxns, cur)[checkCat] || 0;
              const catRemain = Math.max(0, catBud - catSpent);
              const color = trafficColor(catSpent, catBud);
              return (
                <div key={cur} style={{ padding: 16, background: "var(--bg3)", borderRadius: 10 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>{cat?.icon} {cat?.label} — {cur}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 20, color: colorVar(color), marginBottom: 4 }}>
                    {fmt(catRemain, cur)} remaining
                  </div>
                  <div className="traffic-bar-wrap">
                    <div className="traffic-bar" style={{ width: `${clamp(pct(catSpent, catBud), 0, 100)}%`, background: colorVar(color) }} />
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 6 }}>
                    {fmt(catSpent, cur)} of {fmt(catBud, cur)} used ({pct(catSpent, catBud)}%)
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  // ADD TRANSACTION MODAL
  const renderAddTxnModal = () => {
    const [form, setForm] = useState({
      date: today(), amount: "", currency: "EUR", merchant: "",
      categoryId: "misc-uncat", tags: "", projectId: "", notes: "",
      type: "expense", splitEnabled: false, splits: [{ categoryId: "misc-uncat", amount: "" }],
    });

    const handleSubmit = () => {
      if (!form.amount || !form.merchant) return;
      const txn = {
        id: genId(), date: form.date, amount: parseFloat(form.amount),
        currency: form.currency, merchant: form.merchant,
        categoryId: form.splitEnabled ? form.splits[0]?.categoryId : form.categoryId,
        tags: form.tags ? form.tags.split(",").map(t => t.trim()).filter(Boolean) : [],
        projectId: form.projectId || null, notes: form.notes, type: form.type,
        splits: form.splitEnabled ? form.splits.map(s => ({ categoryId: s.categoryId, amount: parseFloat(s.amount) || 0 })) : null,
      };
      setTransactions(prev => [...prev, txn]);
      setShowAddTxn(false);
    };

    return (
      <div className="modal-overlay" onClick={() => setShowAddTxn(false)}>
        <div className="modal" onClick={e => e.stopPropagation()}>
          <h2>Add Transaction</h2>
          <div className="form-row">
            <div className="form-group" style={{ flex: 1 }}>
              <label>Date</label>
              <input type="date" value={form.date} onChange={e => setForm({...form, date: e.target.value})} />
            </div>
            <div className="form-group" style={{ width: 120 }}>
              <label>Type</label>
              <select value={form.type} onChange={e => setForm({...form, type: e.target.value})}>
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group" style={{ flex: 2 }}>
              <label>Merchant</label>
              <input value={form.merchant} onChange={e => setForm({...form, merchant: e.target.value})} placeholder="e.g. Whole Foods" />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Amount</label>
              <input type="number" value={form.amount} onChange={e => setForm({...form, amount: e.target.value})} placeholder="0.00" />
            </div>
            <div className="form-group" style={{ width: 90 }}>
              <label>Currency</label>
              <select value={form.currency} onChange={e => setForm({...form, currency: e.target.value})}>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </div>
          </div>

          {!form.splitEnabled ? (
            <div className="form-row">
              <div className="form-group" style={{ flex: 1 }}>
                <label>Category</label>
                <select value={form.categoryId} onChange={e => setForm({...form, categoryId: e.target.value})}>
                  {categories.map(g => (
                    <optgroup key={g.id} label={`${g.icon} ${g.label}`}>
                      {g.children.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                    </optgroup>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <div style={{ background: "var(--bg3)", padding: 12, borderRadius: 8, marginBottom: 10 }}>
              <div className="flex-between mb">
                <label style={{ fontSize: 11, color: "var(--text3)", textTransform: "uppercase" }}>Split Transaction</label>
                <span style={{ fontSize: 11, color: "var(--text3)", fontFamily: "var(--mono)" }}>
                  Total: {form.splits.reduce((s, sp) => s + (parseFloat(sp.amount) || 0), 0).toFixed(2)} / {form.amount || "0.00"}
                </span>
              </div>
              {form.splits.map((sp, i) => (
                <div className="form-row" key={i} style={{ marginBottom: 6 }}>
                  <div className="form-group" style={{ flex: 2 }}>
                    <select value={sp.categoryId} onChange={e => {
                      const newSplits = [...form.splits];
                      newSplits[i].categoryId = e.target.value;
                      setForm({...form, splits: newSplits});
                    }}>
                      {categories.map(g => (
                        <optgroup key={g.id} label={`${g.icon} ${g.label}`}>
                          {g.children.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                        </optgroup>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <input type="number" placeholder="Amount" value={sp.amount} onChange={e => {
                      const newSplits = [...form.splits];
                      newSplits[i].amount = e.target.value;
                      setForm({...form, splits: newSplits});
                    }} />
                  </div>
                  {form.splits.length > 1 && (
                    <button className="btn btn-danger btn-sm" onClick={() => {
                      setForm({...form, splits: form.splits.filter((_, j) => j !== i)});
                    }}>✕</button>
                  )}
                </div>
              ))}
              <button className="btn btn-secondary btn-sm" onClick={() => {
                setForm({...form, splits: [...form.splits, { categoryId: "misc-uncat", amount: "" }]});
              }}>+ Add Split</button>
            </div>
          )}

          <div className="form-row">
            <div className="form-group" style={{ flex: 1 }}>
              <label>Project (optional)</label>
              <select value={form.projectId} onChange={e => setForm({...form, projectId: e.target.value})}>
                <option value="">— None (regular spend) —</option>
                {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group" style={{ flex: 1 }}>
              <label>Tags (comma-separated)</label>
              <input value={form.tags} onChange={e => setForm({...form, tags: e.target.value})} placeholder="e.g. spouse, reimbursable" />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group" style={{ flex: 1 }}>
              <label>Notes</label>
              <textarea value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} rows={2} placeholder="Optional notes..." />
            </div>
          </div>

          <div className="flex-between mt">
            <label style={{ fontSize: 12, color: "var(--text2)", cursor: "pointer" }}>
              <input type="checkbox" checked={form.splitEnabled} onChange={e => setForm({...form, splitEnabled: e.target.checked})} style={{ marginRight: 6 }} />
              Split across categories
            </label>
            <div className="flex-gap">
              <button className="btn btn-secondary" onClick={() => setShowAddTxn(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSubmit}>Add Transaction</button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ADD PROJECT MODAL
  const renderAddProjectModal = () => {
    const [form, setForm] = useState({
      name: "", budget: "", currency: "EUR", startDate: today(), endDate: "", status: "active"
    });
    const handleSubmit = () => {
      if (!form.name || !form.budget) return;
      setProjects(prev => [...prev, {
        id: genId(), name: form.name, budget: parseFloat(form.budget),
        currency: form.currency, startDate: form.startDate, endDate: form.endDate, status: form.status,
      }]);
      setShowAddProject(false);
    };
    return (
      <div className="modal-overlay" onClick={() => setShowAddProject(false)}>
        <div className="modal" onClick={e => e.stopPropagation()}>
          <h2>New Project / Trip</h2>
          <p style={{ fontSize: 13, color: "var(--text2)", marginBottom: 16 }}>
            Projects are tracked separately from your regular monthly budget. Use them for trips, renovations, or any one-off spending.
          </p>
          <div className="form-row">
            <div className="form-group" style={{ flex: 1 }}>
              <label>Project Name</label>
              <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="e.g. Italy Trip 2026" />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group" style={{ flex: 1 }}>
              <label>Budget</label>
              <input type="number" value={form.budget} onChange={e => setForm({...form, budget: e.target.value})} placeholder="3000" />
            </div>
            <div className="form-group" style={{ width: 100 }}>
              <label>Currency</label>
              <select value={form.currency} onChange={e => setForm({...form, currency: e.target.value})}>
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group" style={{ flex: 1 }}>
              <label>Start Date</label>
              <input type="date" value={form.startDate} onChange={e => setForm({...form, startDate: e.target.value})} />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>End Date</label>
              <input type="date" value={form.endDate} onChange={e => setForm({...form, endDate: e.target.value})} />
            </div>
          </div>
          <div className="flex-gap mt" style={{ justifyContent: "flex-end" }}>
            <button className="btn btn-secondary" onClick={() => setShowAddProject(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSubmit}>Create Project</button>
          </div>
        </div>
      </div>
    );
  };

  // ── RENDER ─────────────────────────────────────────────────────────
  return (
    <>
      <style>{CSS}</style>
      <div className="app">
        <div className="header">
          <h1>💰 Finance<span>Flow</span></h1>
          <div className="month-selector">
            <button onClick={prevMonth}>◀</button>
            <span>{monthLabel}</span>
            <button onClick={nextMonth}>▶</button>
          </div>
        </div>

        <div className="nav">
          {[
            { id: "dashboard", label: "📊 Dashboard" },
            { id: "canispend", label: "🚦 Can I Spend?" },
            { id: "transactions", label: "📋 Transactions" },
            { id: "trends", label: "📈 Trends" },
            { id: "projects", label: "✈️ Projects" },
            { id: "rules", label: "⚙️ Rules" },
          ].map(v => (
            <button key={v.id} className={view === v.id ? "active" : ""} onClick={() => setView(v.id)}>
              {v.label}
            </button>
          ))}
        </div>

        {view === "dashboard" && renderDashboard()}
        {view === "drill" && renderDrill()}
        {view === "canispend" && renderCanISpend()}
        {view === "transactions" && renderTransactions()}
        {view === "trends" && renderTrends()}
        {view === "projects" && renderProjects()}
        {view === "rules" && renderRules()}

        {showAddTxn && renderAddTxnModal()}
        {showAddProject && renderAddProjectModal()}
      </div>
    </>
  );
}
