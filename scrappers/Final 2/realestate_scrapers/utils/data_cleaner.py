"""
Data cleaning utilities for real estate scrapers
"""
import re
import time
from datetime import datetime
from typing import Union, Optional


def clean_text(text: str) -> str:
    """
    Clean and normalize text by removing extra whitespace and special characters
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text string
    """
    if not text:
        return ''
    
    # Remove extra whitespace and normalize
    cleaned = re.sub(r'\s+', ' ', str(text).strip())
    return cleaned


def parse_currency(currency_str: Union[str, int, float]) -> float:
    """
    Parse currency string to float value
    
    Args:
        currency_str: Currency string or number
        
    Returns:
        Float value of currency
    """
    if not currency_str:
        return 0.0
    
    if isinstance(currency_str, (int, float)):
        return float(currency_str)
    
    # Remove currency symbols and commas
    cleaned = re.sub(r'[^\d.,]', '', str(currency_str))
    
    # Handle different decimal separators
    if ',' in cleaned and '.' in cleaned:
        # Assume comma is thousands separator
        cleaned = cleaned.replace(',', '')
    elif ',' in cleaned and '.' not in cleaned:
        # Check if comma is decimal separator (European format)
        parts = cleaned.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            cleaned = cleaned.replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def format_date(date_str: Union[str, datetime]) -> str:
    """
    Format date string to ISO format
    
    Args:
        date_str: Date string or datetime object
        
    Returns:
        ISO formatted date string or empty string if invalid
    """
    if not date_str:
        return ''
    
    if isinstance(date_str, datetime):
        return date_str.isoformat()
    
    # Try to parse common date formats
    date_formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
        '%B %d, %Y',
        '%b %d, %Y',
        '%d %B %Y',
        '%d %b %Y'
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(str(date_str).strip(), fmt)
            return parsed_date.isoformat()
        except ValueError:
            continue
    
    # If no format matches, return original string cleaned
    return clean_text(str(date_str))


def extract_building_size(asset_info: list) -> float:
    """
    Extract building size from asset information
    
    Args:
        asset_info: List of asset information dictionaries
        
    Returns:
        Building size as float or 0.0 if not found
    """
    if not asset_info or not isinstance(asset_info, list):
        return 0.0
    
    size_keywords = [
        'building_size', 'buildingSize', 'size', 'area', 'sqft', 'sf',
        'gross_leasable_area', 'grossLeasableArea', 'totalArea', 'total_area'
    ]
    
    for item in asset_info:
        if not isinstance(item, dict):
            continue
            
        # Check for size-related fields
        for key, value in item.items():
            if any(keyword.lower() in key.lower() for keyword in size_keywords):
                try:
                    size = parse_currency(value)
                    if size > 0:
                        return size
                except:
                    continue
                    
        # Check for numeric values that might be sizes
        for key, value in item.items():
            if isinstance(value, (int, float)) and value > 100:  # Reasonable minimum size
                return float(value)
    
    return 0.0


def sleep(seconds: float) -> None:
    """
    Sleep for specified number of seconds
    
    Args:
        seconds: Number of seconds to sleep
    """
    time.sleep(seconds)