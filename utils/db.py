import psycopg2
from config import DB_CONFIG
from datetime import datetime

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def upsert_listing(record):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id SERIAL PRIMARY KEY,
            site TEXT,
            url TEXT UNIQUE,
            property_name TEXT,
            address TEXT,
            property_type TEXT,
            year_built INT,
            brokers TEXT[],
            start_bid BIGINT,
            current_bid BIGINT,
            bid_increment BIGINT,
            bidding_starts TIMESTAMP,
            bidding_ends TIMESTAMP,
            status TEXT,
            size BIGINT,
            last_seen TIMESTAMP
        );
    """)
    cur.execute("""
        INSERT INTO listings (site, url, property_name, address, property_type, year_built, brokers,
                              start_bid, current_bid, bid_increment, bidding_starts, bidding_ends,
                              status, size, last_seen)
        VALUES (%(site)s, %(url)s, %(property_name)s, %(address)s, %(property_type)s, %(year_built)s, %(brokers)s,
                %(start_bid)s, %(current_bid)s, %(bid_increment)s, %(bidding_starts)s, %(bidding_ends)s,
                %(status)s, %(size)s, %(last_seen)s)
        ON CONFLICT (url) DO UPDATE
        SET current_bid = EXCLUDED.current_bid,
            status = EXCLUDED.status,
            last_seen = EXCLUDED.last_seen;
    """, {**record, "last_seen": datetime.utcnow()})
    conn.commit()
    cur.close()
    conn.close()
