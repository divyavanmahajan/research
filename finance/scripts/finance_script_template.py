#!/usr/bin/env python3
# finance/scripts/data_processor.py
# Template script for processing financial data

import csv
import json
from datetime import datetime
from typing import List, Dict

def load_csv(filepath: str) -> List[Dict]:
    """Load CSV file and return as list of dictionaries."""
    data = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = [row for row in reader]
        print(f"✓ Loaded {len(data)} records from {filepath}")
        return data
    except FileNotFoundError:
        print(f"✗ Error: File not found - {filepath}")
        return []

def process_transactions(transactions: List[Dict]) -> Dict:
    """
    Process financial transactions and return summary statistics.
    
    Args:
        transactions: List of transaction dictionaries with 'amount' and 'type' keys
    
    Returns:
        Dictionary with summary statistics
    """
    if not transactions:
        return {"error": "No transactions to process"}
    
    total_income = sum(float(t.get('amount', 0)) for t in transactions if t.get('type') == 'income')
    total_expenses = sum(float(t.get('amount', 0)) for t in transactions if t.get('type') == 'expense')
    net = total_income - total_expenses
    
    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_balance": round(net, 2),
        "transaction_count": len(transactions),
        "processed_at": datetime.now().isoformat()
    }

def save_json(data: Dict, filepath: str) -> bool:
    """Save data to JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved results to {filepath}")
        return True
    except Exception as e:
        print(f"✗ Error saving file: {e}")
        return False

def main():
    """Main execution function."""
    print("=" * 50)
    print("Financial Data Processor")
    print("=" * 50)
    
    # Example usage
    csv_file = "data/transactions.csv"
    json_output = "data/summary.json"
    
    # Load and process
    transactions = load_csv(csv_file)
    summary = process_transactions(transactions)
    
    # Save results
    save_json(summary, json_output)
    
    # Display results
    print("\nSummary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    main()
