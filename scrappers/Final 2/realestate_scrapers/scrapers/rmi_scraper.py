"""
RMI Marketplace Scraper
Scrapes auction data from RMI Marketplace using HTTP requests
"""

import requests
import time
import json
import asyncio
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.property_data import PropertyData
from utils.data_cleaner import clean_text, parse_currency, format_date, extract_building_size
from utils.csv_exporter import export_to_csv


class RMIScraper:
    """
    RMI Marketplace scraper using HTTP requests
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the RMI scraper
        
        Args:
            config: Configuration dictionary
        """
        self.config = {
            'base_url': 'https://api.rimarketplace.com/api',
            'limit': 60,
            'max_retries': 3,
            'retry_delay': 1000,
            'delay_between_requests': 500,
            'timeout': 30,
            'verbose': False,
            **(config or {})
        }
        
        # Token management
        self.current_token = None
        self.token_expiry = None
        
        # Request configurations
        self.search_headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'dnt': '1',
            'origin': 'https://rimarketplace.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://rimarketplace.com/',
            'sec-ch-ua': '"Not=A?Brand";v="24", "Chromium";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
        }
        
        self.detail_headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'dnt': '1',
            'origin': 'https://rimarketplace.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://rimarketplace.com/',
            'sec-ch-ua': '"Not=A?Brand";v="24", "Chromium";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
        }
        
        self.auth_headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'content-length': '0',
            'dnt': '1',
            'origin': 'https://rimarketplace.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://rimarketplace.com/',
            'sec-ch-ua': '"Not=A?Brand";v="24", "Chromium";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
        }
    
    def log(self, message: str) -> None:
        """Log message if verbose mode is enabled"""
        if self.config.get('verbose', False):
            print(message)
    
    def generate_auction_url_slug(self, property_name: str) -> str:
        """
        Generate a URL-friendly slug from property name
        
        Args:
            property_name: The property name
            
        Returns:
            URL-friendly slug
        """
        if not property_name:
            return ''
        
        # Convert to lowercase and replace spaces with hyphens
        slug = property_name.lower()
        # Remove special characters and keep only alphanumeric, spaces, and hyphens
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        # Replace multiple spaces/hyphens with single hyphen
        slug = re.sub(r'[\s-]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        return slug
    
    def authenticate(self) -> str:
        """
        Authenticate and get a fresh JWT token
        
        Returns:
            The JWT token
        """
        try:
            self.log('🔐 Authenticating with RI Marketplace API...')
            
            response = requests.post(
                f'{self.config["base_url"]}/authenticate',
                headers=self.auth_headers,
                timeout=self.config['timeout']
            )
            response.raise_for_status()
            
            data = response.json()
            if data and not data.get('error') and data.get('results', {}).get('token'):
                self.current_token = data['results']['token']
                self.token_expiry = time.time() + data['results']['expiresIn']
                
                self.log(f'✓ Successfully authenticated - token expires in {data["results"]["expiresIn"]} seconds')
                return self.current_token
            else:
                raise Exception(f"Authentication failed: {data.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f'✗ Authentication failed: {str(e)}')
            raise Exception(f"Failed to authenticate: {str(e)}")
    
    def get_valid_token(self) -> str:
        """
        Get current valid token, refreshing if necessary
        
        Returns:
            The JWT token
        """
        # Check if we have a valid token that hasn't expired
        if self.current_token and self.token_expiry and time.time() < self.token_expiry:
            return self.current_token
        
        # Token is expired or doesn't exist, get a new one
        return self.authenticate()
    
    def fetch_page(self, page: int) -> Dict[str, Any]:
        """
        Fetch a single page of auctions with retry logic
        
        Args:
            page: Page number to fetch
            
        Returns:
            API response data
        """
        url = f'{self.config["base_url"]}/search?legend=auction&limit={self.config["limit"]}&page={page}&sortOrder=ASC'
        
        for attempt in range(1, self.config['max_retries'] + 1):
            try:
                self.log(f'Fetching page {page} (attempt {attempt}/{self.config["max_retries"]})')
                
                # Get fresh token for each request
                token = self.get_valid_token()
                
                headers = {
                    **self.search_headers,
                    'authorization': f'Bearer {token}'
                }
                
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.config['timeout']
                )
                response.raise_for_status()
                
                data = response.json()
                if data and not data.get('error'):
                    self.log(f'✓ Successfully fetched page {page} - {len(data.get("data", {}).get("property", []))} auctions')
                    return data
                else:
                    raise Exception(f"API returned error: {data.get('message', 'Unknown error')}")
                    
            except Exception as e:
                self.log(f'✗ Attempt {attempt} failed for page {page}: {str(e)}')
                
                if attempt == self.config['max_retries']:
                    raise Exception(f"Failed to fetch page {page} after {self.config['max_retries']} attempts: {str(e)}")
                
                time.sleep(self.config['retry_delay'] * attempt / 1000)
    
    def fetch_auction_details(self, property_id: int) -> Dict[str, Any]:
        """
        Fetch detailed auction data for a specific property
        
        Args:
            property_id: Property ID to fetch details for
            
        Returns:
            Detailed auction data
        """
        data = {
            "propertyId": str(property_id),
            "userId": "",
            "isCmsUrl": False
        }
        
        for attempt in range(1, self.config['max_retries'] + 1):
            try:
                self.log(f'  Fetching details for property {property_id} (attempt {attempt}/{self.config["max_retries"]})')
                
                # Get fresh token for each request
                token = self.get_valid_token()
                
                headers = {
                    **self.detail_headers,
                    'authorization': f'Bearer {token}'
                }
                
                response = requests.post(
                    f'{self.config["base_url"]}/auction',
                    headers=headers,
                    json=data,
                    timeout=self.config['timeout']
                )
                response.raise_for_status()
                
                result = response.json()
                if result and not result.get('error'):
                    self.log(f'  ✓ Successfully fetched details for property {property_id}')
                    return result
                else:
                    raise Exception(f"API returned error: {result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                self.log(f'  ✗ Attempt {attempt} failed for property {property_id}: {str(e)}')
                
                if attempt == self.config['max_retries']:
                    raise Exception(f"Failed to fetch details for property {property_id} after {self.config['max_retries']} attempts: {str(e)}")
                
                time.sleep(self.config['retry_delay'] * attempt / 1000)
    
    def process_auction_data(self, auction: Dict[str, Any], details: Dict[str, Any]) -> PropertyData:
        """
        Process detailed auction data into standardized format
        
        Args:
            auction: Basic auction data
            details: Detailed auction data
            
        Returns:
            Processed PropertyData object
        """
        try:
            info = details.get('data', {}).get('propertyList', [{}])[0].get('information', {})
            brokers = details.get('data', {}).get('listedBrokers', [])
            asset_info = details.get('data', {}).get('propertyList', [{}])[0].get('asset_info', [])
            
            # Extract up to 3 brokers with error handling
            broker1 = ''
            broker2 = ''
            broker3 = ''
            try:
                broker_list = brokers[:3]
                if len(broker_list) > 0 and broker_list[0] and broker_list[0].get('name'):
                    broker1 = clean_text(broker_list[0]['name'])
                if len(broker_list) > 1 and broker_list[1] and broker_list[1].get('name'):
                    broker2 = clean_text(broker_list[1]['name'])
                if len(broker_list) > 2 and broker_list[2] and broker_list[2].get('name'):
                    broker3 = clean_text(broker_list[2]['name'])
            except Exception as e:
                self.log(f'  Warning: Error processing brokers for auction {auction.get("propertyId")}: {str(e)}')
            
            # Extract building size with multiple fallbacks
            building_size = 0
            try:
                building_size = extract_building_size(asset_info)
                if building_size == 0:
                    # Try alternative sources
                    building_size = (
                        parse_currency(info.get('office_grossLeasableArea')) or
                        parse_currency(info.get('retail_grossLeasableArea')) or
                        parse_currency(info.get('industrial_grossLeasableArea')) or
                        parse_currency(info.get('multifamily_grossLeasableArea')) or
                        parse_currency(info.get('grossLeasableArea')) or
                        0
                    )
            except Exception as e:
                self.log(f'  Warning: Error extracting building size for auction {auction.get("propertyId")}: {str(e)}')
                building_size = 0
            
            # Build address
            address_parts = [
                info.get('propertyAddress', ''),
                info.get('propertyCity', auction.get('propertyCity', '')),
                info.get('propertyState', auction.get('stateName', '')),
                info.get('propertyZip', '')
            ]
            address = clean_text(' '.join(filter(None, address_parts))) or 'Address not available'
            
            # Generate property name and auction URL
            property_name = clean_text(info.get('propertyName') or auction.get('propertyName') or 'Unknown Property')
            property_id = auction.get('propertyId', '')
            url_slug = self.generate_auction_url_slug(property_name)
            auction_url = f"https://rimarketplace.com/auction/{property_id}/{url_slug}" if property_id and url_slug else f"https://rimarketplace.com/property/{property_id}"
            
            return PropertyData(
                property_url=auction_url,
                property_name=property_name,
                address=address,
                bidding_starts=format_date(info.get('startBidding') or auction.get('auctionStartDate')) or '',
                bidding_ends=format_date(info.get('endBidding') or auction.get('auctionEndDate')) or '',
                starting_bid=parse_currency(info.get('start_bid') or auction.get('start_bid')) or 0.0,
                current_bid=parse_currency(info.get('current_bid') or auction.get('current_bid')) or 0.0,
                property_type=clean_text(info.get('property_type_name') or auction.get('property_type_name') or 'Unknown'),
                asset_type=clean_text(info.get('asset_type_name') or 'Real Estate'),
                year_built=clean_text(info.get('yearBuilt') or '') or '',
                date_added='',  # Not available in RMI
                broker1=broker1,
                broker2=broker2,
                broker3=broker3,
                building_size=building_size or 0.0,
                units='',  # Not available in RMI
                size=0.0,  # Not available in RMI
                source='RMI',
                auction_status='',  # Not available in RMI
                registered_bidders=0,  # Not available in RMI
                reserve_met=False,  # Not available in RMI
                bid_increment=0.0,  # Not available in RMI
                minimum_bid=0.0  # Not available in RMI
            )
            
        except Exception as e:
            self.log(f'  Critical error processing auction {auction.get("propertyId")}: {str(e)}')
            # Return minimal data to avoid complete loss
            property_name = clean_text(auction.get('propertyName') or 'Unknown Property')
            property_id = auction.get('propertyId', '')
            url_slug = self.generate_auction_url_slug(property_name)
            auction_url = f"https://rimarketplace.com/auction/{property_id}/{url_slug}" if property_id and url_slug else f"https://rimarketplace.com/property/{property_id}"
            
            return PropertyData(
                property_url=auction_url,
                property_name=property_name,
                address=clean_text(f"{auction.get('propertyCity', '')} {auction.get('stateName', '')}".strip()) or 'Address not available',
                bidding_starts=format_date(auction.get('auctionStartDate')) or '',
                bidding_ends=format_date(auction.get('auctionEndDate')) or '',
                starting_bid=parse_currency(auction.get('start_bid')) or 0.0,
                current_bid=parse_currency(auction.get('current_bid')) or 0.0,
                property_type=clean_text(auction.get('property_type_name') or 'Unknown'),
                asset_type='Real Estate',
                year_built='',
                date_added='',
                broker1='',
                broker2='',
                broker3='',
                building_size=0.0,
                units='',
                size=0.0,
                source='RMI',
                auction_status='',
                registered_bidders=0,
                reserve_met=False,
                bid_increment=0.0,
                minimum_bid=0.0
            )
    
    def scrape_all_auctions(self) -> Dict[str, Any]:
        """
        Scrape all auctions from all pages (basic data only)
        
        Returns:
            Dictionary with auctions, total count, pages scraped, and errors
        """
        auctions = []
        total_count = 0
        pages_scraped = 0
        errors = []
        
        try:
            # First, get the first page to determine total pages
            first_page = self.fetch_page(1)
            
            total_count = first_page.get('data', {}).get('count', 0)
            pages_scraped = 1
            auctions.extend(first_page.get('data', {}).get('property', []))
            
            # If there are more pages, fetch them
            total_pages = first_page.get('data', {}).get('pages', 1)
            if total_pages > 1:
                for page in range(2, total_pages + 1):
                    try:
                        page_data = self.fetch_page(page)
                        auctions.extend(page_data.get('data', {}).get('property', []))
                        pages_scraped += 1
                    except Exception as e:
                        error = f"Failed to fetch page {page}: {str(e)}"
                        errors.append(error)
            
            return {
                'auctions': auctions,
                'total_count': total_count,
                'pages_scraped': pages_scraped,
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"Critical error during basic scraping: {str(e)}"
            errors.append(error_msg)
            raise Exception(error_msg)
    
    def scrape(self) -> List[PropertyData]:
        """
        Main scraping function - scrapes all auctions with detailed information
        
        Returns:
            List of PropertyData objects
        """
        print('🚀 Starting RI Marketplace auction scraping...')
        start_time = time.time()
        
        processed_auctions = []
        errors = []
        
        try:
            # Step 1: Get all basic auction data
            print('📄 Fetching all auction listings...')
            basic_result = self.scrape_all_auctions()
            errors.extend(basic_result['errors'])
            
            auctions = basic_result['auctions']
            print(f'📊 Found {len(auctions)} auctions to process')
            print('🔍 Fetching detailed information for each auction...\n')
            
            # Step 2: Process each auction with detailed data
            for i, auction in enumerate(auctions):
                print(f'Processing auction {i + 1}/{len(auctions)}: {auction.get("propertyName", "Unknown")}')
                
                try:
                    details = self.fetch_auction_details(auction['propertyId'])
                    processed_auction = self.process_auction_data(auction, details)
                    processed_auctions.append(processed_auction)
                    
                    # Add delay between requests to be respectful
                    if i < len(auctions) - 1:
                        time.sleep(self.config['delay_between_requests'] / 1000)
                        
                except Exception as e:
                    error_msg = f"Failed to process auction {auction.get('propertyId')} ({auction.get('propertyName', 'Unknown')}): {str(e)}"
                    errors.append(error_msg)
                    print(f'  ✗ {error_msg}')
                    
                    # Try to create a minimal record with basic data to avoid complete loss
                    try:
                        print(f'  Attempting to create minimal record for auction {auction.get("propertyId")}...')
                        minimal_auction = self.process_auction_data(auction, {'data': {}})
                        processed_auctions.append(minimal_auction)
                        print(f'  ✓ Created minimal record for auction {auction.get("propertyId")}')
                    except Exception as minimal_error:
                        print(f'  ✗ Failed to create minimal record for auction {auction.get("propertyId")}: {str(minimal_error)}')
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f'\n🎉 Scraping completed in {duration:.2f} seconds')
            print(f'📈 Results: {len(processed_auctions)} auctions processed successfully')
            
            if errors:
                print(f'⚠️  {len(errors)} errors encountered during processing')
            
            return processed_auctions
            
        except Exception as e:
            error_msg = f"Critical error during scraping: {str(e)}"
            errors.append(error_msg)
            print(f'💥 {error_msg}')
            raise Exception(error_msg)
    
    def cleanup(self):
        """Cleanup resources"""
        # No browser to cleanup for HTTP-based scraper
        pass


def main():
    """
    Main function to run the RMI scraper
    """
    try:
        # Initialize scraper
        scraper = RMIScraper()
        
        # Run scraping
        property_data_objects = scraper.scrape()
        
        if property_data_objects:
            # Convert PropertyData objects to dictionaries for CSV export
            property_data_dicts = [prop.to_dict() for prop in property_data_objects]
            
            # Export to CSV
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            csv_filename = f"rmi_auctions_{timestamp}.csv"
            export_to_csv(property_data_dicts, csv_filename)
            
            print(f"\n🎉 RMI scraping completed successfully!")
            print(f"📊 Processed {len(property_data_objects)} auctions")
            print(f"📁 Data exported to: {csv_filename}")
            
            # Show sample data
            if property_data_dicts:
                print(f'\n📋 Sample extracted data from first auction:')
                sample_data = property_data_dicts[0]
                for key, value in sample_data.items():
                    print(f'  {key}: {value}')
        else:
            print("⚠️ No auction data was scraped")
            
    except Exception as e:
        print(f"💥 Error running RMI scraper: {str(e)}")
    finally:
        # Cleanup
        try:
            scraper.cleanup()
        except:
            pass


if __name__ == "__main__":
    main()
