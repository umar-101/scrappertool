import csv
import os
from django.core.management.base import BaseCommand
from api.models import LoopNetProperty, MarketPlaceProperty, OtherSourceProperty

# Base project dir (points to backend/)
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
CSV_DIR = os.path.join(BASE_DIR, "csv_files")  # folder where CSVs are stored


class Command(BaseCommand):
    help = "Import or update scraped CSVs into database (LoopNet, MarketPlace, Crexi)"

    def handle(self, *args, **options):
        self.import_loopnet()
        self.import_marketplace()
        self.import_crexi()

    def import_loopnet(self):
        loopnet_path = os.path.join(CSV_DIR, "loopnet.csv")
        if not os.path.exists(loopnet_path):
            self.stdout.write(self.style.WARNING("LoopNet CSV not found. Skipping..."))
            return

        with open(loopnet_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            created_count, updated_count = 0, 0
            for row in reader:
                obj, created = LoopNetProperty.objects.update_or_create(
                    property_url=row.get("Property URL"),
                    defaults={
                        "property_name": row.get("Property Name"),
                        "address": row.get("Address"),
                        "bidding_starts": row.get("Bidding Starts"),
                        "bidding_ends": row.get("Bidding Ends"),
                        "starting_bid": row.get("Starting Bid"),
                        "current_bid": row.get("Current Bid"),
                        "bid_increment": row.get("Bid Increment"),
                        "reserve_status": row.get("Reserve Status"),
                        "property_type": row.get("Property Type"),
                        "year_built": row.get("Year Built"),
                        "broker1": row.get("Broker 1"),
                        "broker2": row.get("Broker 2"),
                        "broker3": row.get("Broker 3"),
                        "total_building_size": row.get("Total Building Size"),
                        "building_size": row.get("Building Size"),
                        "source": row.get("Source"),
                        "scraped_at": row.get("Scraped At"),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ LoopNet: {created_count} new, {updated_count} updated"
            )
        )

    def import_marketplace(self):
        marketplace_path = os.path.join(CSV_DIR, "rmi.csv")
        if not os.path.exists(marketplace_path):
            self.stdout.write(self.style.WARNING("MarketPlace CSV not found. Skipping..."))
            return

        with open(marketplace_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            created_count, updated_count = 0, 0
            for row in reader:
                obj, created = MarketPlaceProperty.objects.update_or_create(
                    property_url=row.get("property_url"),
                    defaults={
                        "property_name": row.get("propertyName"),
                        "address": row.get("address"),
                        "asset_type": row.get("assetType"),
                        "auction_status": row.get("auctionStatus"),
                        "bid_increment": row.get("bidIncrement"),
                        "bidding_ends": row.get("biddingEnds"),
                        "bidding_starts": row.get("biddingStarts"),
                        "broker1": row.get("broker1"),
                        "broker2": row.get("broker2"),
                        "broker3": row.get("broker3"),
                        "building_size": row.get("buildingSize"),
                        "current_bid": row.get("currentBid"),
                        "date_added": row.get("dateAdded"),
                        "minimum_bid": row.get("minimumBid"),
                        "property_type": row.get("propertyType"),
                        "registered_bidders": row.get("registeredBidders"),
                        "reserve_status": row.get("reserveMet"),
                        "size": row.get("size"),
                        "source": row.get("source"),
                        "starting_bid": row.get("startingBid"),
                        "units": row.get("units"),
                        "year_built": row.get("yearBuilt"),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ MarketPlace: {created_count} new, {updated_count} updated"
            )
        )

    def import_crexi(self):
        crexi_path = os.path.join(CSV_DIR, "crexi.csv")
        if not os.path.exists(crexi_path):
            self.stdout.write(self.style.WARNING("Crexi CSV not found. Skipping..."))
            return

        with open(crexi_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            created_count, updated_count = 0, 0
            for row in reader:
                obj, created = OtherSourceProperty.objects.update_or_create(
                    property_url=row.get("property_url"),
                    defaults={
                        "property_name": row.get("propertyName"),
                        "address": row.get("address"),
                        "asset_type": row.get("assetType"),
                        "auction_status": row.get("auctionStatus"),
                        "bid_increment": row.get("bidIncrement"),
                        "bidding_ends": row.get("biddingEnds"),
                        "bidding_starts": row.get("biddingStarts"),
                        "broker1": row.get("broker1"),
                        "broker2": row.get("broker2"),
                        "broker3": row.get("broker3"),
                        "building_size": row.get("buildingSize"),
                        "current_bid": row.get("currentBid"),
                        "date_added": row.get("dateAdded"),
                        "minimum_bid": row.get("minimumBid"),
                        "property_type": row.get("propertyType"),
                        "registered_bidders": row.get("registeredBidders"),
                        "reserve_status": row.get("reserveMet"),
                        "size": row.get("size"),
                        "source": row.get("source") or "Crexi",
                        "starting_bid": row.get("startingBid"),
                        "units": row.get("units"),
                        "year_built": row.get("yearBuilt"),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Crexi: {created_count} new, {updated_count} updated"
            )
        )
