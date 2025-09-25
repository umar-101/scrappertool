from scrapers.loopnet import scrape_loopnet
from utils.db import upsert_listing

def main():
    # Scrape LoopNet auctions
    loopnet_listings = scrape_loopnet()

    # Insert each listing into the database
    for listing in loopnet_listings:
        upsert_listing(listing)

    print(f"Scraped and stored {len(loopnet_listings)} listings from LoopNet!")


if __name__ == "__main__":
    main()
