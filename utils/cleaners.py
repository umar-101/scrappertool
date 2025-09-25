from dateutil import parser

def clean_price(price_str):
    if not price_str:
        return None
    return int(price_str.replace("$", "").replace(",", "").strip())

def clean_size(size_str):
    if not size_str:
        return None
    return int(size_str.replace("SF", "").replace("Sq Ft", "").replace(",", "").strip())

def clean_date(date_str):
    if not date_str:
        return None
    dt = parser.parse(date_str)
    return dt.isoformat()

def clean_brokers(*brokers):
    return [b.strip() for b in brokers if b and b.strip()]
