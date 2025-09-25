DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "password",
    "database": "auctions_db"
}

SCRAPE_SETTINGS = {
    "loopnet": {"url": "https://www.loopnet.com/search/commercial-real-estate/usa/auctions/"},
    "crexi": {"url": "https://www.crexi.com/properties/Auctions?pageSize=60"},
    "rmi": {"url": "https://rimarketplace.com/commercial/search/lt=auction"}
}
