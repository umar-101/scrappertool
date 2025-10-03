"""
CSV and JSON export utilities for real estate scrapers
"""
import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any


def export_to_csv(data: List[Dict[str, Any]], filename: str) -> None:
    """
    Export data to CSV file
    
    Args:
        data: List of dictionaries to export
        filename: Output filename
    """
    if not data:
        print("No data to export")
        return
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    # Get all unique keys from all records
    all_keys = set()
    for record in data:
        all_keys.update(record.keys())
    
    fieldnames = sorted(list(all_keys))
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"CSV exported to: {filename}")


def save_to_json(data: Dict[str, Any], filename: str) -> None:
    """
    Save data to JSON file
    
    Args:
        data: Dictionary to save
        filename: Output filename
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, ensure_ascii=False, default=str)
    
    print(f"JSON exported to: {filename}")