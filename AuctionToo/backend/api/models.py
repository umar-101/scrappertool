from django.db import models


class BaseProperty(models.Model):
    # common normalized fields
    property_url = models.TextField(blank=True, null=True)
    property_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    bidding_starts = models.CharField(max_length=100, blank=True, null=True)
    bidding_ends = models.CharField(max_length=100, blank=True, null=True)
    starting_bid = models.CharField(max_length=100, blank=True, null=True)
    current_bid = models.CharField(max_length=100, blank=True, null=True)
    bid_increment = models.CharField(max_length=100, blank=True, null=True)
    reserve_status = models.CharField(max_length=100, blank=True, null=True)  # reserveMet / reserveNotMet
    auction_status = models.CharField(max_length=100, blank=True, null=True)  # ongoing / closed etc.
    asset_type = models.CharField(max_length=100, blank=True, null=True)
    property_type = models.CharField(max_length=100, blank=True, null=True)
    year_built = models.CharField(max_length=50, blank=True, null=True)

    broker1 = models.CharField(max_length=255, blank=True, null=True)
    broker2 = models.CharField(max_length=255, blank=True, null=True)
    broker3 = models.CharField(max_length=255, blank=True, null=True)

    building_size = models.CharField(max_length=100, blank=True, null=True)
    total_building_size = models.CharField(max_length=100, blank=True, null=True)
    size = models.CharField(max_length=100, blank=True, null=True)
    units = models.CharField(max_length=50, blank=True, null=True)

    registered_bidders = models.CharField(max_length=100, blank=True, null=True)
    minimum_bid = models.CharField(max_length=100, blank=True, null=True)

    source = models.CharField(max_length=100, blank=True, null=True)
    scraped_at = models.CharField(max_length=100, blank=True, null=True)
    date_added = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        abstract = True  # ensures we don't create a table for this


class LoopNetProperty(BaseProperty):
    def __str__(self):
        return self.property_name if self.property_name else "Unnamed LoopNet Property"


class MarketPlaceProperty(BaseProperty):
    def __str__(self):
        return self.property_name if self.property_name else "Unnamed MarketPlace Property"


class OtherSourceProperty(BaseProperty):
    def __str__(self):
        return self.property_name if self.property_name else "Unnamed Other Source Property"
