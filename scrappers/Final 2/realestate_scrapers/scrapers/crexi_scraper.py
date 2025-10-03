"""
Crexi Real Estate Scraper
Extracts auction data from Crexi marketplace using nodriver with network request interception
"""

import nodriver as uc
import asyncio
import re
import json
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from nodriver import cdp

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utilities
from utils.csv_exporter import export_to_csv


class RequestMonitor:
    """Monitor network requests to capture API responses"""
    
    def __init__(self):
        self.requests = []
        self.last_request = None
        self.lock = asyncio.Lock()

    async def listen(self, page):
        """Start listening for network requests"""
        async def handler(evt):
            async with self.lock:
                if evt.response.encoded_data_length > 0 and 'api.crexi.com' in evt.response.url:
                    self.requests.append([evt.response.url, evt.request_id])
                    self.last_request = time.time()

        page.add_handler(cdp.network.ResponseReceived, handler)

    async def receive(self, page):
        """Get the response bodies for captured requests"""
        responses = []
        retries = 0
        max_retries = 3

        # Wait for requests to complete
        while True:
            if self.last_request is None or retries > max_retries:
                break

            if time.time() - self.last_request <= 2:
                retries += 1
                await asyncio.sleep(2)
                continue
            else:
                break

        await page

        # Get response bodies
        async with self.lock:
            for request in self.requests:
                try:
                    res = await page.send(cdp.network.get_response_body(request[1]))
                    if res is None:
                        continue
                    
                    # Decode response body if it's base64 encoded
                    body = res[0]
                    if res[1]:  # If base64 encoded
                        import base64
                        body = base64.b64decode(body).decode('utf-8')
                    
                    # Parse JSON if possible
                    try:
                        json_data = json.loads(body)
                        responses.append({
                            'url': request[0],
                            'data': json_data
                        })
                    except json.JSONDecodeError:
                        pass
                        
                except Exception:
                    pass

        return responses


class CrexiScraper:
    """
    Crexi Real Estate Scraper using nodriver to avoid detection
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the scraper with configuration
        
        Args:
            config: Configuration dictionary
        """
        self.config = {
            'base_url': 'https://www.crexi.com',
            'auctions_url': 'https://www.crexi.com/properties/Auctions?pageSize=60',
            'max_retries': 3,
            'retry_delay': 2000,
            'delay_between_requests': 1000,
            'headless': True,
            'window_size': (1920, 1080),
            **(config or {})
        }
        
        self.browser = None
        self.all_auction_links = []
        self.api_responses = {}  # Store intercepted API responses
        self.monitor = RequestMonitor()  # Network request monitor

    async def start_browser(self):
        """Start browser with minimal configuration"""
        print('🔧 Starting nodriver browser...')
        self.browser = await uc.start()
        print('✓ Browser started successfully')
        
    async def close_browser(self):
        """Close browser"""
        try:
            if self.browser:
                await self.browser.stop()
                self.browser = None
                print('✓ Browser closed successfully')
            else:
                print("🔒 No browser session to close")
        except Exception as e:
            print(f"⚠️ Error closing browser: {e}")
            # Force cleanup
            self.browser = None

    async def handle_security_check(self, page):
        """Handle security checks and redirects"""
        # Skip security checks for speed
        pass

    async def wait_for_content_load(self, page, max_retries=3):
        """Wait for JavaScript content to load with retry logic"""
        for attempt in range(max_retries):
            print(f"⏳ Loading content (attempt {attempt + 1}/{max_retries})...")
            
            max_wait = 30  # Maximum wait time in seconds
            wait_time = 0
            
            while wait_time < max_wait:
                try:
                    content = await page.get_content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    auction_elements = soup.find_all('a', class_='cui-card-cover-link')
                    
                    if auction_elements:
                        print(f"✅ Found {len(auction_elements)} auction links")
                        return True
                        
                except Exception as e:
                    print(f"⚠️ Error checking content: {e}")
                    
                await asyncio.sleep(2)
                wait_time += 2
                
            print(f"⚠️ Attempt {attempt + 1} failed, retrying...")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
            
        print("❌ All attempts failed")
        return False

    async def setup_network_interception(self, page):
        """Setup network request interception to capture API responses"""
        try:
            # Enable Network domain first
            await page.send(cdp.network.enable())
            
            # Start monitoring network requests
            await self.monitor.listen(page)
            
        except Exception as e:
            pass

    async def wait_for_required_api_responses(self, page, property_id: str, max_retries=3) -> List[Dict]:
        """
        Wait for all three required API responses to be captured with retry logic
        
        Args:
            page: The page object
            property_id: The property ID to wait for
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of captured API responses
        """
        required_endpoints = [
            f'/assets/{property_id}',
            f'/auctions/{property_id}',
            f'/assets/{property_id}/brokers'
        ]
        
        for attempt in range(max_retries):
            print(f"  🎯 Capturing API responses (attempt {attempt + 1}/{max_retries})...")
            
            captured_endpoints = set()
            max_wait_time = 30  # 30 seconds per attempt
            wait_time = 0
            
            while wait_time < max_wait_time:
                api_responses = await self.monitor.receive(page)
                
                if not isinstance(api_responses, list):
                    api_responses = []
                
                # Check which endpoints we have captured
                for response in api_responses:
                    if isinstance(response, dict):
                        url = response.get('url', '')
                        for endpoint in required_endpoints:
                            if endpoint in url:
                                captured_endpoints.add(endpoint)
                
                # Check if we have all required endpoints
                if len(captured_endpoints) >= 3:
                    print(f"  ✅ Captured all 3 required API responses!")
                    return api_responses
                
                await asyncio.sleep(2)
                wait_time += 2
            
            print(f"  ⚠️ Attempt {attempt + 1} failed ({len(captured_endpoints)}/3 endpoints)")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
        
        print(f"  ❌ Failed to capture all endpoints after {max_retries} attempts")
        return []

    def extract_property_id_from_url(self, url: str) -> Optional[str]:
        """Extract property ID from API URL"""
        try:
            # Match patterns like /assets/2139723 or /auctions/2139723
            match = re.search(r'/(?:assets|auctions)/(\d+)', url)
            if match:
                return match.group(1)
        except:
            pass
        return None

    async def fetch_auction_links(self) -> List[str]:
        """
        Fetch all auction links from the auctions page with pagination handling
        
        Returns:
            List of auction page URLs
        """
        print('📄 Fetching auction links from Crexi auctions page...')
        
        if not self.browser:
            await self.start_browser()

        try:
            # Navigate to the homepage first to establish session
            print('  📄 Establishing session via homepage...')
            page = await self.browser.get('https://www.crexi.com')
            await self.handle_security_check(page)
            
            # Navigate to auctions page with pageSize=60
            print('  🎯 Navigating to auctions page with pageSize=60...')
            page = await self.browser.get(self.config['auctions_url'])
            await self.handle_security_check(page)
            
            # Wait for JavaScript content to load
            await self.wait_for_content_load(page)
            
            all_auction_links = []
            current_page = 1
            
            while True:
                print(f'  📄 Processing page {current_page}...')
                
                # Extract auction links from current page
                auction_links = await self.extract_auction_links_from_page(page)
                all_auction_links.extend(auction_links)
                print(f'  ✓ Found {len(auction_links)} auction links on page {current_page}')
                
                # Check if there's a next page
                if not await self.has_next_page(page):
                    print(f'  ✓ Reached last page. Total auction links found: {len(all_auction_links)}')
                    break
                
                # Navigate to next page
                page = await self.navigate_to_next_page(page)
                if not page:
                    print(f'  ✓ No more pages available. Total auction links found: {len(all_auction_links)}')
                    break
                
                # Wait for content to load on new page
                await self.wait_for_content_load(page)
                
                current_page += 1
                await asyncio.sleep(3)  # Wait between page loads
            
            return all_auction_links
                
        except Exception as e:
            print(f'✗ Failed to fetch auction links: {str(e)}')
            raise

    async def extract_auction_links_from_page(self, page) -> List[str]:
        """
        Extract auction links from the current page
        
        Returns:
            List of auction page URLs
        """
        try:
            # Get page content and parse with BeautifulSoup
            content = await page.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all auction card cover links
            auction_elements = soup.find_all('a', class_='cui-card-cover-link')
            
            auction_links = []
            for element in auction_elements:
                href = element.get('href')
                if href and '/properties/' in href:
                    # Convert relative URLs to absolute URLs
                    if href.startswith('/'):
                        href = f'https://www.crexi.com{href}'
                    auction_links.append(href)
            
            return auction_links
            
        except Exception as e:
            print(f'  ✗ Error extracting auction links from page: {str(e)}')
            return []

    async def has_next_page(self, page) -> bool:
        """
        Check if there's a next page available
        
        Returns:
            True if next page exists, False otherwise
        """
        try:
            # Get page content and parse with BeautifulSoup
            content = await page.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for next page button that's not disabled
            next_button = soup.find('a', {'data-cy': 'nextPage'})
            if next_button and not next_button.get('disabled'):
                return True
            return False
        except:
            return False

    async def navigate_to_next_page(self, page):
        """
        Navigate to the next page
        
        Returns:
            New page object if navigation successful, None otherwise
        """
        try:
            # Get page content and parse with BeautifulSoup
            content = await page.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find and click the next page button
            next_button = soup.find('a', {'data-cy': 'nextPage'})
            if next_button and not next_button.get('disabled'):
                # Get the href and navigate to it
                href = next_button.get('href')
                if href:
                    if href.startswith('/'):
                        href = f'https://www.crexi.com{href}'
                    new_page = await self.browser.get(href)
                    await self.handle_security_check(new_page)
                    return new_page
            
            return None
            
        except Exception as e:
            print(f'  ✗ Error navigating to next page: {str(e)}')
            return None

    async def extract_property_data_from_api(self, auction_url: str) -> Dict[str, Any]:
        """
        Extract property data by visiting the auction page and capturing API responses
        
        Args:
            auction_url: URL of the auction page
            
        Returns:
            Dictionary containing extracted property data
        """
        try:
            # Setup network interception BEFORE navigating to the page
            await self.setup_network_interception(self.browser.main_tab)
            
            # Navigate to the auction page
            page = await self.browser.get(auction_url)
            
            # Extract property ID from URL
            property_id = self.extract_property_id_from_auction_url(auction_url)
            if not property_id:
                return {}
            
            # Wait for all three required API responses with retry logic
            api_responses = await self.wait_for_required_api_responses(page, property_id)
            
            if not api_responses:
                return {}
            
            # Process the captured API responses
            asset_data = {}
            auction_data = {}
            brokers_data = {}
            
            for response in api_responses:
                url = response.get('url', '')
                data = response.get('data', {})
                
                if f'/assets/{property_id}' in url and '/brokers' not in url:
                    asset_data = data
                elif f'/auctions/{property_id}' in url:
                    auction_data = data
                elif f'/assets/{property_id}/brokers' in url:
                    brokers_data = data
            
            # Process the data
            property_data = self.process_api_data(asset_data, auction_data, brokers_data, auction_url)
            return property_data
            
        except Exception as e:
            return {}

    def extract_property_id_from_auction_url(self, url: str) -> Optional[str]:
        """Extract property ID from auction URL"""
        try:
            match = re.search(r'/properties/(\d+)/', url)
            if match:
                return match.group(1)
        except:
            pass
        return None

    def process_api_data(self, asset_data: Dict, auction_data: Dict, brokers_data: Dict, auction_url: str) -> Dict[str, Any]:
        """
        Process API data into standardized format
        
        Args:
            asset_data: Asset API response data
            auction_data: Auction API response data  
            brokers_data: Brokers API response data
            auction_url: Original auction URL
            
        Returns:
            Processed property data
        """
        try:
            # Extract basic information from auction data
            property_name = 'Unknown Property'
            address = 'Address not available'
            auction_starts = ''
            auction_ends = ''
            
            if auction_data and isinstance(auction_data, dict):
                property_name = auction_data.get('propertyName', 'Unknown Property')
                address = auction_data.get('propertyAddress', 'Address not available')
                
                # Extract auction timing
                auction_starts = auction_data.get('auctionStartsOn', '')
                auction_ends = auction_data.get('auctionEndsOn', '')
            
            # Calculate bidding ends if not provided (bidding starts + 2 days)
            if not auction_ends and auction_starts:
                try:
                    from datetime import datetime, timedelta
                    start_date = datetime.fromisoformat(auction_starts.replace('Z', '+00:00'))
                    end_date = start_date + timedelta(days=2)
                    auction_ends = end_date.isoformat().replace('+00:00', 'Z')
                except:
                    pass
            
            # Extract property details from asset data
            property_type = 'Commercial'  # Default
            year_built = 'N/A'
            building_size = 'N/A'
            
            if asset_data and isinstance(asset_data, dict):
                # Get property type
                types = asset_data.get('types', [])
                if types:
                    property_type = ', '.join(types)
                
                # Get year built
                year_built = asset_data.get('details', {}).get('Year Built', 'N/A')
                
                # Get building size
                building_size = asset_data.get('details', {}).get('Square Footage', 'N/A')
            
            # Extract broker information
            brokers = []
            if brokers_data and isinstance(brokers_data, list):
                for broker in brokers_data[:3]:  # Limit to 3 brokers
                    broker_name = f"{broker.get('firstName', '')} {broker.get('lastName', '')}".strip()
                    if broker_name:
                        brokers.append(broker_name)
            
            # Format broker names
            broker_1 = brokers[0] if len(brokers) > 0 else 'N/A'
            broker_2 = brokers[1] if len(brokers) > 1 else 'N/A'
            broker_3 = brokers[2] if len(brokers) > 2 else 'N/A'
            
            return {
                'propertyName': property_name,
                'address': address,
                'biddingStarts': auction_starts,
                'biddingEnds': auction_ends,
                'startingBid': auction_data.get('startingBid', 0),
                'currentBid': auction_data.get('currentBid', 0),
                'propertyType': property_type,
                'assetType': 'Real Estate',
                'yearBuilt': year_built,
                'dateAdded': auction_data.get('auctionMarketingStartsOn', 'N/A'),
                'broker1': broker_1,
                'broker2': broker_2,
                'broker3': broker_3,
                'buildingSize': building_size,
                'units': 'N/A',  # Not available in API
                'size': building_size,
                'source': 'Crexi',
                'property_url': auction_url,
                'auctionStatus': auction_data.get('auctionStatus', 'Unknown'),
                'registeredBidders': auction_data.get('stats', {}).get('numberOfRegisteredBidders', 0),
                'reserveMet': auction_data.get('reserveMet', False),
                'bidIncrement': auction_data.get('bidIncrementAmount', 0),
                'minimumBid': auction_data.get('minimumBidAmount', 0)
            }
            
        except Exception as e:
            print(f'  ⚠️ Error processing API data: {str(e)}')
            return {
                'propertyName': 'Error processing property',
                'address': 'Address not available',
                'biddingStarts': '',
                'biddingEnds': '',
                'startingBid': 0,
                'currentBid': 0,
                'propertyType': 'Commercial',
                'assetType': 'Real Estate',
                'yearBuilt': 'N/A',
                'dateAdded': 'N/A',
                'broker1': 'N/A',
                'broker2': 'N/A',
                'broker3': 'N/A',
                'buildingSize': 'N/A',
                'units': 'N/A',
                'size': 'N/A',
                'source': 'Crexi',
                'property_url': auction_url,
                'auctionStatus': 'Unknown',
                'registeredBidders': 0,
                'reserveMet': False,
                'bidIncrement': 0,
                'minimumBid': 0
            }

    async def scrape_links(self) -> List[str]:
        """
        Main method to scrape all auction links from Crexi
        
        Returns:
            List of all auction URLs found
        """
        print('🚀 Starting Crexi auction link scraping with nodriver...')
        
        try:
            # Fetch all auction links
            auction_links = await self.fetch_auction_links()
            
            print(f'✅ Successfully found {len(auction_links)} auction links')
            return auction_links
            
        except Exception as e:
            print(f'❌ Error during link scraping: {str(e)}')
            raise
        # Note: Don't close browser here as we need it for data extraction

    async def test_single_auction_data_extraction(self, auction_url: str) -> Dict[str, Any]:
        """
        Test data extraction for a single auction URL
        
        Args:
            auction_url: URL of the auction to test
        
        Returns:
            Extracted property data
        """
        print(f'🧪 Testing data extraction for: {auction_url}')
        
        if not self.browser:
            await self.start_browser()
        
        try:
            # Extract property data from the auction page
            property_data = await self.extract_property_data_from_api(auction_url)
            
            print(f'✅ Successfully extracted data for test auction')
            return property_data

        except Exception as e:
            print(f'❌ Error during test data extraction: {str(e)}')
            return {}
        finally:
            # Close browser when done
            if self.browser:
                await self.close_browser()


async def main():
    """
    Main function to run the Crexi scraper
    """
    scraper = None
    
    try:
        # Initialize scraper with configuration
        config = {
            'headless': True,  # Set to True for headless mode
            'delay_between_requests': 500, 
        }
        
        scraper = CrexiScraper(config)
        
        # Run the scraper to get all auction links
        auction_links = await scraper.scrape_links()
        
        print(f'\n✅ Successfully scraped {len(auction_links)} auction links')
        print('📋 Links found:')

        
        # Extract data from first 10 auction links for testing
        if auction_links:
            test_auction_links = auction_links[:10]
            print(f'\n🔍 Starting data extraction from {len(test_auction_links)} auctions...')
            all_property_data = []
            
            # Process each auction link
            for i, auction_url in enumerate(test_auction_links):
                print(f'📄 Processing auction {i+1}/{len(test_auction_links)}...')
                
                try:
                    # Extract property data from this auction
                    property_data = await scraper.extract_property_data_from_api(auction_url)
                    
                    if property_data:
                        all_property_data.append(property_data)
                        print(f'  ✅ Success')
                    else:
                        print(f'  ❌ Failed')
                    
                except Exception as e:
                    print(f'  ❌ Error: {str(e)}')
                    continue
            
            print(f'\n🎉 Data extraction completed!')
            print(f'📊 Successfully extracted data from {len(all_property_data)}/{len(auction_links)} auctions')
            
            # Export data to CSV
            if all_property_data:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                csv_filename = f"crexi_auctions_{timestamp}.csv"
                export_to_csv(all_property_data, csv_filename)
                print(f"📊 Data exported to: {csv_filename}")
                
                # Show sample data
                print(f'\n📋 Sample extracted data from first auction:')
                sample_data = all_property_data[0]
                for key, value in sample_data.items():
                    print(f'  {key}: {value}')
            else:
                print("⚠️ No data to export")
            
            return all_property_data
        else:
            print(f'⚠️ No auction links found to process')
            return []
        
    except KeyboardInterrupt:
        print('\n⚠️  Scraping interrupted by user')
    except Exception as e:
        print(f'\n💥 Fatal error: {str(e)}')
    finally:
        # Ensure cleanup
        if scraper:
            try:
                print('🔒 Closing browser session...')
                await scraper.close_browser()
            except Exception as e:
                print(f'⚠️  Warning: Error during final browser cleanup: {str(e)}')


if __name__ == '__main__':
    asyncio.run(main())
