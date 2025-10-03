    """
PropertyData class for real estate scraper data structure
"""
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class PropertyData:
    """
    Standardized property data structure for real estate scrapers
    """
    property_url: str = ''
    property_name: str = ''
    address: str = ''
    bidding_starts: str = ''
    bidding_ends: str = ''
    starting_bid: float = 0.0
    current_bid: float = 0.0
    property_type: str = ''
    asset_type: str = ''
    year_built: str = ''
    date_added: str = ''
    broker1: str = ''
    broker2: str = ''
    broker3: str = ''
    building_size: float = 0.0
    units: str = ''
    size: float = 0.0
    source: str = ''
    auction_status: str = ''
    registered_bidders: int = 0
    reserve_met: bool = False
    bid_increment: float = 0.0
    minimum_bid: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert PropertyData to dictionary for CSV export
        
        Returns:
            Dictionary representation of property data
        """
        return {
            'property_url': self.property_url,
            'propertyName': self.property_name,
            'address': self.address,
            'biddingStarts': self.bidding_starts,
            'biddingEnds': self.bidding_ends,
            'startingBid': self.starting_bid,
            'currentBid': self.current_bid,
            'propertyType': self.property_type,
            'assetType': self.asset_type,
            'yearBuilt': self.year_built,
            'dateAdded': self.date_added,
            'broker1': self.broker1,
            'broker2': self.broker2,
            'broker3': self.broker3,
            'buildingSize': self.building_size,
            'units': self.units,
            'size': self.size,
            'source': self.source,
            'auctionStatus': self.auction_status,
            'registeredBidders': self.registered_bidders,
            'reserveMet': self.reserve_met,
            'bidIncrement': self.bid_increment,
            'minimumBid': self.minimum_bid
        }