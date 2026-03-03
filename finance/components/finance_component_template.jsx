// finance/components/FinanceDashboard.jsx
// Template React component for finance metrics dashboard

import React, { useState } from 'react';

const FinanceDashboard = () => {
  const [data, setData] = useState({
    totalBalance: 0,
    monthlyExpense: 0,
    savings: 0,
    investments: 0
  });

  return (
    <div className="p-8 bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
      <h1 className="text-4xl font-bold text-gray-800 mb-8">Finance Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Metric Card Template */}
        <MetricCard label="Total Balance" value={`$${data.totalBalance.toLocaleString()}`} />
        <MetricCard label="Monthly Expense" value={`$${data.monthlyExpense.toLocaleString()}`} />
        <MetricCard label="Savings" value={`$${data.savings.toLocaleString()}`} />
        <MetricCard label="Investments" value={`$${data.investments.toLocaleString()}`} />
      </div>
    </div>
  );
};

// Reusable metric card component
const MetricCard = ({ label, value }) => (
  <div className="bg-white rounded-lg shadow-md p-6">
    <p className="text-gray-600 text-sm font-semibold mb-2">{label}</p>
    <p className="text-2xl font-bold text-indigo-600">{value}</p>
  </div>
);

export default FinanceDashboard;
