// finance/utilities/finance-helpers.js
// Template utility functions for financial calculations

/**
 * Format number as currency
 * @param {number} amount - The amount to format
 * @param {string} currency - Currency code (default: 'USD')
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
}

/**
 * Calculate percentage change
 * @param {number} oldValue - Previous value
 * @param {number} newValue - Current value
 * @returns {number} Percentage change (rounded to 2 decimals)
 */
function calculatePercentageChange(oldValue, newValue) {
  if (oldValue === 0) return 0;
  return Number(((newValue - oldValue) / oldValue * 100).toFixed(2));
}

/**
 * Calculate compound interest
 * @param {number} principal - Initial amount
 * @param {number} rate - Annual interest rate (as percentage)
 * @param {number} years - Number of years
 * @param {number} compounds - Times interest is compounded per year (default: 12 for monthly)
 * @returns {number} Final amount
 */
function calculateCompoundInterest(principal, rate, years, compounds = 12) {
  const amount = principal * Math.pow((1 + rate / 100 / compounds), compounds * years);
  return Number(amount.toFixed(2));
}

/**
 * Calculate monthly payment for loan
 * @param {number} principal - Loan amount
 * @param {number} annualRate - Annual interest rate (as percentage)
 * @param {number} months - Number of months to repay
 * @returns {number} Monthly payment amount
 */
function calculateMonthlyPayment(principal, annualRate, months) {
  const monthlyRate = annualRate / 100 / 12;
  if (monthlyRate === 0) return principal / months;
  
  const payment = principal * 
    (monthlyRate * Math.pow(1 + monthlyRate, months)) / 
    (Math.pow(1 + monthlyRate, months) - 1);
  
  return Number(payment.toFixed(2));
}

/**
 * Calculate ROI (Return on Investment)
 * @param {number} invested - Initial investment amount
 * @param {number} gained - Gain from investment
 * @returns {number} ROI as percentage
 */
function calculateROI(invested, gained) {
  if (invested === 0) return 0;
  return Number(((gained / invested) * 100).toFixed(2));
}

/**
 * Calculate expense ratio
 * @param {number} expenses - Total expenses
 * @param {number} income - Total income
 * @returns {number} Expense ratio as percentage
 */
function calculateExpenseRatio(expenses, income) {
  if (income === 0) return 0;
  return Number(((expenses / income) * 100).toFixed(2));
}

/**
 * Calculate savings rate
 * @param {number} savings - Amount saved
 * @param {number} income - Total income
 * @returns {number} Savings rate as percentage
 */
function calculateSavingsRate(savings, income) {
  if (income === 0) return 0;
  return Number(((savings / income) * 100).toFixed(2));
}

/**
 * Round to nearest currency value
 * @param {number} amount - Amount to round
 * @param {number} nearest - Round to nearest value (default: 0.01 for cents)
 * @returns {number} Rounded amount
 */
function roundCurrency(amount, nearest = 0.01) {
  return Math.round(amount / nearest) * nearest;
}

// Export all functions
module.exports = {
  formatCurrency,
  calculatePercentageChange,
  calculateCompoundInterest,
  calculateMonthlyPayment,
  calculateROI,
  calculateExpenseRatio,
  calculateSavingsRate,
  roundCurrency
};

// Example usage (uncomment to test):
/*
console.log(formatCurrency(1234.56));
// Output: $1,234.56

console.log(calculatePercentageChange(100, 150));
// Output: 50

console.log(calculateCompoundInterest(1000, 5, 10, 12));
// Output: 1644.72

console.log(calculateMonthlyPayment(200000, 4.5, 360));
// Output: 1013.37

console.log(calculateROI(10000, 2500));
// Output: 25

console.log(calculateSavingsRate(5000, 20000));
// Output: 25
*/
