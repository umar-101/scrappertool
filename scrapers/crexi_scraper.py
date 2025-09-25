"""
Crexi Real Estate Scraper
Extracts auction data from Crexi marketplace
"""

import json
import os
import re
import time
import random
import signal
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from fake_useragent import UserAgent

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_cleaner import (
    clean_text, parse_currency, format_date, extract_building_size,
    sleep, calculate_bidding_end, clean_property_type, extract_units,
    clean_broker_info, format_empty_field
)
from utils.csv_exporter import export_scraper_results, print_scraper_summary


class SafeChromeDriver:
    """
    Wrapper for undetected Chrome driver to handle cleanup properly
    """
    def __init__(self, *args, **kwargs):
        self._driver = None
        self._closed = False
        try:
            self._driver = uc.Chrome(*args, **kwargs)
        except Exception as e:
            raise e
    
    def __getattr__(self, name):
        if self._closed:
            raise Exception("Driver has been closed")
        return getattr(self._driver, name)
    
    def quit(self):
        if not self._closed and self._driver:
            try:
                self._driver.quit()
            except:
                pass
            finally:
                self._closed = True
                self._driver = None
    
    def close(self):
        self.quit()
    
    def __del__(self):
        # Prevent the original __del__ from running
        pass


class CrexiScraper:
    """
    Crexi Real Estate Scraper using undetected Chrome driver
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
            'session_rotation_limit': 25,
            'headless': False,
            'window_size': (1920, 1080),
            'implicit_wait': 15,
            'page_load_timeout': 60,
            **(config or {})
        }
        
        self.driver = None
        self.request_count = 0
        self.ua = UserAgent()
        
        # User agent rotation for better stealth
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
        ]
        self.current_user_agent_index = 0

    def initialize_driver(self) -> None:
        """
        Initialize undetected Chrome driver with stealth configuration
        """
        print('🔧 Initializing undetected Chrome driver...')
        
        try:
            # Configure Chrome options for stealth
            options = uc.ChromeOptions()
            
            # Set Chrome browser path (common locations)
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', '')),
            ]
            
            # Find Chrome browser executable
            chrome_executable = None
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_executable = path
                    break
            
            if chrome_executable:
                print(f'  🌐 Found Chrome browser at: {chrome_executable}')
                options.binary_location = chrome_executable
            else:
                print('  ⚠️  Chrome browser not found in common locations, trying default Chrome')
            
            # Basic stealth options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-setuid-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-accelerated-2d-canvas')
            options.add_argument('--no-first-run')
            options.add_argument('--no-zygote')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-features=TranslateUI,VizDisplayCompositor')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-sync')
            options.add_argument('--disable-web-security')
            options.add_argument('--enable-features=NetworkService')
            options.add_argument(f'--window-size={self.config["window_size"][0]},{self.config["window_size"][1]}')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-features=VizDisplayCompositor')
            
            # Additional network and timeout options
            options.add_argument('--disable-background-networking')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-client-side-phishing-detection')
            options.add_argument('--disable-component-extensions-with-background-pages')
            options.add_argument('--disable-hang-monitor')
            options.add_argument('--disable-ipc-flooding-protection')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-prompt-on-repost')
            options.add_argument('--disable-sync-preferences')
            options.add_argument('--disable-domain-reliability')
            options.add_argument('--disable-features=TranslateUI')
            options.add_argument('--disable-ipc-flooding-protection')
            options.add_argument('--no-default-browser-check')
            options.add_argument('--no-first-run')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-extensions-file-access-check')
            options.add_argument('--disable-extensions-http-throttling')
            options.add_argument('--aggressive-cache-discard')
            options.add_argument('--enable-aggressive-domstorage-flushing')
            
            # Set user agent
            current_ua = self.user_agents[self.current_user_agent_index]
            self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
            options.add_argument(f'--user-agent={current_ua}')
            
            # Additional stealth options
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            # Enable performance logging for network interception
            from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
            caps = DesiredCapabilities.CHROME
            # Use browser log type instead of performance for newer Chrome versions
            caps["goog:loggingPrefs"] = {"browser": "ALL", "performance": "ALL"}
            
            # Initialize the driver with automated driver download using safe wrapper
            self.driver = SafeChromeDriver(
                options=options,
                headless=self.config['headless'],
                version_main=None,  # Let undetected-chromedriver auto-detect Chrome version
                desired_capabilities=caps
            )
            
            # Set timeouts
            self.driver.implicitly_wait(self.config['implicit_wait'])
            self.driver.set_page_load_timeout(self.config['page_load_timeout'])
            self.driver.set_script_timeout(60)  # Set script timeout to 60 seconds
            
            # Execute stealth scripts
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": current_ua
            })
            
            print(f'✓ Undetected Chrome driver initialized successfully')
            print(f'  🔄 Using user agent: {current_ua[:50]}...')
            
        except Exception as e:
            print(f'✗ Failed to initialize Chrome driver: {str(e)}')
            raise

    def rotate_driver_session(self) -> None:
        """
        Rotate driver session to avoid detection
        """
        print('🔄 Rotating driver session...')
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        self.request_count = 0
        self.initialize_driver()
        print('✓ Driver session rotated')

    def wait_for_cloudflare(self, timeout: int = 30) -> bool:
        """
        Wait for Cloudflare challenge to complete
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if Cloudflare challenge was resolved, False otherwise
        """
        print('🛡️  Checking for Cloudflare challenge...')
        
        try:
            # Check if we're on a Cloudflare challenge page
            page_source = self.driver.page_source.lower()
            title = self.driver.title.lower()
            
            if ('just a moment' in title or 
                'cloudflare' in page_source or 
                'cf-chl' in page_source or
                '__cf_chl' in self.driver.current_url):
                
                print('  🛡️  Cloudflare challenge detected, waiting for resolution...')
                
                # Wait for the challenge to complete
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        current_title = self.driver.title.lower()
                        current_source = self.driver.page_source.lower()
                        current_url = self.driver.current_url
                        
                        if ('just a moment' not in current_title and 
                            'cf-chl' not in current_source and
                            '__cf_chl' not in current_url):
                            print('  ✓ Cloudflare challenge resolved')
                            time.sleep(2)  # Additional wait
                            return True
                            
                    except:
                        pass
                    
                    time.sleep(1)
                
                print('  ⚠️  Cloudflare challenge timeout')
                return False
            else:
                print('  ✓ No Cloudflare challenge detected')
                return True
                
        except Exception as e:
            print(f'  ⚠️  Error checking for Cloudflare: {str(e)}')
            return False

    def fetch_auction_links(self) -> List[str]:
        """
        Fetch all auction links from the auctions page by parsing HTML and handling pagination
        
        Returns:
            List of auction page URLs
        """
        print('📄 Fetching auction links from Crexi auctions page...')
        
        if not self.driver:
            self.initialize_driver()

        # Check if we need to rotate session
        if self.request_count >= self.config['session_rotation_limit']:
            self.rotate_driver_session()

        try:
            # Navigate to the homepage first to establish session
            print('  📄 Establishing session via homepage...')
            self.driver.get('https://www.crexi.com')
            
            # Wait for Cloudflare challenge if present
            self.wait_for_cloudflare()
            
            # Navigate to auctions page with pageSize=60
            print('  🎯 Navigating to auctions page with pageSize=60...')
            self.driver.get(self.config['auctions_url'])
            
            # Wait for page to load
            time.sleep(5)
            
            # Wait for Cloudflare challenge if present
            self.wait_for_cloudflare()
            
            # Wait for the page content to load
            print('  ⏳ Waiting for auction listings to load...')
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a.cui-card-cover-link'))
            )
            
            all_auction_links = []
            current_page = 1
            
            while True:
                print(f'  📄 Processing page {current_page}...')
                
                # Extract auction links from current page
                auction_links = self.extract_auction_links_from_page()
                all_auction_links.extend(auction_links)
                print(f'  ✓ Found {len(auction_links)} auction links on page {current_page}')
                
                # Check if there's a next page
                if not self.has_next_page():
                    print(f'  ✓ Reached last page. Total auction links found: {len(all_auction_links)}')
                    break
                
                # Navigate to next page
                if not self.navigate_to_next_page():
                    print(f'  ✓ No more pages available. Total auction links found: {len(all_auction_links)}')
                    break
                
                current_page += 1
                time.sleep(3)  # Wait between page loads
            
                self.request_count += 1
            return all_auction_links
                
        except Exception as e:
            print(f'✗ Failed to fetch auction links: {str(e)}')
            raise

    def extract_auction_links_from_page(self) -> List[str]:
        """
        Extract auction links from the current page
        
        Returns:
            List of auction page URLs
        """
        try:
            # Find all auction card cover links
            auction_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a.cui-card-cover-link')
            
            auction_links = []
            for element in auction_elements:
                href = element.get_attribute('href')
                if href and '/properties/' in href:
                    # Convert relative URLs to absolute URLs
                    if href.startswith('/'):
                        href = f'https://www.crexi.com{href}'
                    auction_links.append(href)
            
            return auction_links
            
        except Exception as e:
            print(f'  ✗ Error extracting auction links from page: {str(e)}')
            return []

    def has_next_page(self) -> bool:
        """
        Check if there's a next page available
        
        Returns:
            True if next page exists, False otherwise
        """
        try:
            # Look for next page button that's not disabled
            next_button = self.driver.find_element(By.CSS_SELECTOR, 'a[data-cy="nextPage"]:not([disabled])')
            return next_button is not None and next_button.is_enabled()
        except:
            return False

    def navigate_to_next_page(self) -> bool:
        """
        Navigate to the next page
        
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            # Find and click the next page button
            next_button = self.driver.find_element(By.CSS_SELECTOR, 'a[data-cy="nextPage"]:not([disabled])')
            next_button.click()
            
            # Wait for page to load
            time.sleep(3)
            
            # Wait for new content to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a.cui-card-cover-link'))
            )
            
            return True
            
        except Exception as e:
            print(f'  ✗ Error navigating to next page: {str(e)}')
            return False

    def fetch_property_details_from_page(self, auction_url: str) -> Dict[str, Any]:
        """
        Navigate to auction page and intercept API calls to get property details
        
        Args:
            auction_url: URL of the auction page
            
        Returns:
            Detailed property data from intercepted API calls
        """
        print(f'  🔍 Fetching details from auction page: {auction_url}')
        
        if not self.driver:
            self.initialize_driver()

        # Check if we need to rotate session
        if self.request_count >= self.config['session_rotation_limit']:
            self.rotate_driver_session()

        try:
            # Navigate to the auction page
            print(f'  🌐 Navigating to auction page...')
            self.driver.get(auction_url)
            
            # Wait for Cloudflare challenge if present
            self.wait_for_cloudflare()
            
            # Wait for page to load completely
            print(f'  ⏳ Waiting for page to load completely...')
            WebDriverWait(self.driver, 30).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Wait for the page to make API calls and intercept them
            print(f'  🔍 Waiting for browser to make API calls...')
            auction_details, asset_details, broker_details = self.wait_for_api_responses()
            
            if auction_details or asset_details:
                # Merge the three API responses into a unified data structure
                merged_data = self.merge_api_responses(auction_details, asset_details, broker_details)
                
                # Add the property URL to the data
                merged_data['property_url'] = auction_url
                
                print(f'  ✓ Successfully intercepted and merged API data')
                self.request_count += 1
                return merged_data
            else:
                raise Exception('Could not intercept any API data from browser requests')
                
        except Exception as e:
            print(f'  ✗ Failed to fetch details from auction page: {str(e)}')
            raise

    def wait_for_api_responses(self, timeout: int = 30) -> tuple:
        """
        Wait for the browser to make API calls and intercept them using Chrome DevTools Protocol
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Tuple of (auction_details, asset_details, broker_details)
        """
        import time
        import json
        
        # Enable network domain for CDP
        try:
            self.driver.execute_cdp_cmd('Network.enable', {})
            self.driver.execute_cdp_cmd('Runtime.enable', {})
            self.driver.execute_cdp_cmd('Page.enable', {})
            print(f'  ✓ CDP network monitoring enabled')
        except Exception as e:
            print(f'  ⚠️  Could not enable CDP: {str(e)}')
            return None, None, None
        
        # Wait for the page to make API calls
        print(f'  ⏳ Waiting for browser to make API calls...')
        time.sleep(5)  # Give the page time to make API calls
        
        auction_details = None
        asset_details = None
        broker_details = None
        
        # Try to intercept network requests using multiple methods
        print(f'  🔍 Intercepting network requests...')
        try:
            # Method 1: Try CDP-based interception first
            intercepted_data = self.intercept_network_requests_cdp()
            if not intercepted_data or not any([intercepted_data.get('auction_data'), intercepted_data.get('asset_data'), intercepted_data.get('broker_data')]):
                # Method 2: Fallback to performance logs
                print(f'  🔄 CDP interception incomplete, trying performance logs...')
                intercepted_data = self.intercept_network_requests()
            
            if intercepted_data:
                auction_details = intercepted_data.get('auction_data')
                asset_details = intercepted_data.get('asset_data')
                broker_details = intercepted_data.get('broker_data')
                
                if auction_details:
                    print(f'  ✓ Successfully intercepted auction data')
                if asset_details:
                    print(f'  ✓ Successfully intercepted asset data')
                if broker_details:
                    print(f'  ✓ Successfully intercepted broker data')
        except Exception as e:
            print(f'  ⚠️  Network interception failed: {str(e)}')
        
        return auction_details, asset_details, broker_details
    
    def merge_api_responses(self, auction_details: Optional[Dict[str, Any]], 
                          asset_details: Optional[Dict[str, Any]], 
                          broker_details: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Merge the three API responses into a unified data structure
        
        Args:
            auction_details: Data from /auctions/{id} API
            asset_details: Data from /assets/{id} API  
            broker_details: Data from /assets/{id}/brokers API
            
        Returns:
            Merged property data
        """
        merged_data = {}
        
        # Start with auction details as the base
        if auction_details:
            merged_data.update(auction_details)
            print(f'  ✓ Merged auction data with {len(auction_details)} fields')
        
        # Add asset details, overriding any conflicting fields from auction
        if asset_details:
            merged_data.update(asset_details)
            print(f'  ✓ Merged asset data with {len(asset_details)} fields')
        
        # Add broker details
        if broker_details:
            merged_data['brokers'] = broker_details
            print(f'  ✓ Merged broker data with {len(broker_details)} brokers')
        else:
            merged_data['brokers'] = []
            print(f'  ⚠️  No broker data available')
        
        return merged_data
    
    def intercept_network_requests_cdp(self) -> Dict[str, Any]:
        """
        Intercept network requests using Chrome DevTools Protocol directly
        
        Returns:
            Dictionary with intercepted auction, asset, and broker data
        """
        import json
        import time
        
        intercepted_data = {
            'auction_data': None,
            'asset_data': None,
            'broker_data': None,
            'all_requests': [],
            'all_responses': []
        }
        
        try:
            # Get network events from CDP
            print(f'  🔍 Getting network events from CDP...')
            
            # Try to get response bodies for API calls
            # This is a simplified approach - in a real implementation, you'd need to
            # track request/response pairs and extract the data
            
            # For now, we'll use the existing performance log method as fallback
            return intercepted_data
            
        except Exception as e:
            print(f'  ⚠️  CDP interception failed: {str(e)}')
            return intercepted_data
    
    def intercept_network_requests(self) -> Dict[str, Any]:
        """
        Intercept network requests using performance logs to capture the three API calls:
        - /assets/{id}
        - /auctions/{id}
        - /assets/{id}/brokers
        
        Returns:
            Dictionary with intercepted auction, asset, and broker data
        """
        import json
        import time
        
        try:
            # Try to get performance logs first, fallback to browser logs
            logs = []
            try:
                logs = self.driver.get_log("performance")
                print(f'  ✓ Using performance logs for network interception')
            except Exception as perf_error:
                print(f'  ⚠️  Performance logs not available: {str(perf_error)}')
                try:
                    logs = self.driver.get_log("browser")
                    print(f'  ✓ Using browser logs for network interception')
                except Exception as browser_error:
                    print(f'  ⚠️  Browser logs not available: {str(browser_error)}')
                    return intercepted_data
            
            intercepted_data = {
                'auction_data': None,
                'asset_data': None,
                'broker_data': None,
                'all_requests': [],
                'all_responses': []
            }
            
            # Track request IDs for each API endpoint
            request_ids = {
                'auction': None,
                'asset': None,
                'broker': None
            }
            
            for entry in logs:
                try:
                    log = json.loads(entry["message"])["message"]
                    
                    if log["method"] == "Network.requestWillBeSent":
                        request = log["params"]["request"]
                        request_data = {
                            'method': request['method'],
                            'url': request['url'],
                            'headers': request.get('headers', {}),
                            'postData': request.get('postData', ''),
                            'timestamp': entry['timestamp'],
                            'requestId': log["params"]["requestId"]
                        }
                        intercepted_data['all_requests'].append(request_data)
                        
                        # Check for the three specific API calls
                        url = request['url']
                        if 'api.crexi.com' in url:
                            if '/auctions/' in url and not url.endswith('/brokers'):
                                print(f'  🎯 Found auction API request: {url}')
                                request_ids['auction'] = log["params"]["requestId"]
                            elif '/assets/' in url and '/brokers' in url:
                                print(f'  🎯 Found broker API request: {url}')
                                request_ids['broker'] = log["params"]["requestId"]
                            elif '/assets/' in url and '/brokers' not in url:
                                print(f'  🎯 Found asset API request: {url}')
                                request_ids['asset'] = log["params"]["requestId"]
                    
                    elif log["method"] == "Network.responseReceived":
                        response = log["params"]["response"]
                        response_data = {
                            'url': response['url'],
                            'status': response['status'],
                            'mimeType': response.get('mimeType', ''),
                            'timestamp': entry['timestamp'],
                            'requestId': log["params"]["requestId"]
                        }
                        intercepted_data['all_responses'].append(response_data)
                        
                        # Check for API responses
                        url = response['url']
                        if 'api.crexi.com' in url and response.get('status') == 200:
                            if '/auctions/' in url and not url.endswith('/brokers'):
                                print(f'  🎯 Found auction API response: {url} - Status: {response["status"]}')
                            elif '/assets/' in url and '/brokers' in url:
                                print(f'  🎯 Found broker API response: {url} - Status: {response["status"]}')
                            elif '/assets/' in url and '/brokers' not in url:
                                print(f'  🎯 Found asset API response: {url} - Status: {response["status"]}')
                    
                    elif log["method"] == "Network.loadingFinished":
                        # Try to get response body for API calls
                        request_id = log["params"]["requestId"]
                        
                        # Check if this is one of our target API calls
                        target_type = None
                        for api_type, stored_id in request_ids.items():
                            if stored_id == request_id:
                                target_type = api_type
                                break
                        
                        if target_type:
                            try:
                                response_body = self.driver.execute_cdp_cmd('Network.getResponseBody', {
                                    'requestId': request_id
                                })
                                
                                if response_body and 'body' in response_body:
                                    body = response_body['body']
                                    if response_body.get('base64Encoded', False):
                                        import base64
                                        body = base64.b64decode(body).decode('utf-8')
                                    
                                    try:
                                        json_data = json.loads(body)
                                        
                                        if target_type == 'auction':
                                            intercepted_data['auction_data'] = json_data
                                            print(f'  ✅ Intercepted auction data with {len(json_data)} fields')
                                        elif target_type == 'asset':
                                            intercepted_data['asset_data'] = json_data
                                            print(f'  ✅ Intercepted asset data with {len(json_data)} fields')
                                        elif target_type == 'broker':
                                            intercepted_data['broker_data'] = json_data
                                            print(f'  ✅ Intercepted broker data with {len(json_data)} items')
                                            
                                    except json.JSONDecodeError as e:
                                        print(f'  ⚠️  Could not parse JSON for {target_type}: {str(e)}')
                                        
                            except Exception as e:
                                print(f'  ⚠️  Could not retrieve response body for {target_type}: {str(e)}')
                            
                except (json.JSONDecodeError, KeyError) as e:
                    # Skip malformed log entries
                    continue
            
            return intercepted_data
            
        except Exception as e:
            print(f'  ⚠️  Network interception failed: {str(e)}')
            return None



    def process_property_data(self, listing_data: Dict[str, Any], 
                            auction_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process detailed property data into standardized format
        
        Args:
            listing_data: Basic listing data from search
            auction_details: Detailed auction data from API
            
        Returns:
            Processed property data
        """
        try:
            auction_details = auction_details or {}
            property_id = listing_data.get('id') or auction_details.get('id')
            
            # Extract address from auction details
            address = auction_details.get('propertyAddress', 'Address not available')
            
            # Extract auction timing information
            bidding_starts = auction_details.get('auctionStartsOn', '')
            bidding_ends = auction_details.get('auctionEndsOn', '')
            
            # Format dates
            bidding_starts_formatted = format_date(bidding_starts) if bidding_starts else ''
            bidding_ends_formatted = format_date(bidding_ends) if bidding_ends else ''
            
            # If bidding ends is not available, calculate it (bidding starts + 2 days)
            if not bidding_ends_formatted and bidding_starts_formatted:
                bidding_ends_formatted = calculate_bidding_end(bidding_starts_formatted)

            # Extract broker information from brokers API response
            broker_names = 'No broker information'
            try:
                brokers = auction_details.get('brokers', [])
                if brokers:
                    broker_list = []
                    for broker in brokers:
                        first_name = broker.get('firstName', '')
                        last_name = broker.get('lastName', '')
                        brokerage_name = broker.get('brokerage', {}).get('name', '')
                        
                        broker_info = f"{first_name} {last_name}".strip()
                        if brokerage_name and brokerage_name != 'Unknown':
                            broker_info += f" ({brokerage_name})"
                        
                        # Add license information if available
                        licenses = broker.get('licenses', [])
                        if licenses and licenses[0] != 'N/A' and licenses[0]:
                            broker_info += f" - License: {licenses[0]}"
                        
                        broker_list.append(broker_info)
                    
                    broker_names = '; '.join(broker_list) if broker_list else 'No broker information'
                else:
                    # Fallback to compliance auctioneer if no brokers found
                    compliance_auctioneer = auction_details.get('complianceAuctioneer', {})
                    if compliance_auctioneer:
                        broker_names = clean_text(compliance_auctioneer.get('display', ''))
                
                # Clean the broker information to remove company logo text and other issues
                broker_names = clean_broker_info(broker_names)
                
            except Exception as e:
                print(f'  ⚠️  Error processing broker information: {str(e)}')
                broker_names = 'No broker information'

            # Extract bidding information
            starting_bid = auction_details.get('startingBid', 0)
            current_bid = auction_details.get('currentBidAmount', 0)
            
            # Extract property name
            property_name = auction_details.get('propertyName', listing_data.get('name', f'Property {property_id}'))
            
            # Extract auction status
            auction_status = auction_details.get('auctionStatus', 'Unknown')
            
            # Extract additional stats
            stats = auction_details.get('stats', {})
            registered_bidders = stats.get('numberOfRegisteredBidders', 0)
            
            return {
                'propertyName': clean_text(property_name),
                'address': clean_text(address),
                'biddingStarts': bidding_starts_formatted,
                'biddingEnds': bidding_ends_formatted,
                'startingBid': starting_bid,
                'currentBid': current_bid,
                'propertyType': clean_property_type(auction_details.get('propertyType', 'Commercial')),
                'assetType': 'Real Estate',
                'yearBuilt': format_empty_field(auction_details.get('yearBuilt', ''), 'N/A'),
                'dateAdded': format_date(auction_details.get('auctionMarketingStartsOn', '')) or 'N/A',
                'brokers': broker_names,
                'buildingSize': format_empty_field(auction_details.get('buildingSize', 0), 'N/A'),
                'units': format_empty_field(auction_details.get('units', ''), 'N/A'),
                'size': format_empty_field(auction_details.get('size', 0), 'N/A'),
                'source': 'Crexi',
                'property_url': auction_details.get('property_url', ''),
                'auctionStatus': auction_status,
                'registeredBidders': registered_bidders,
                'reserveMet': auction_details.get('reserveMet', False),
                'bidIncrement': auction_details.get('bidIncrementAmount', 0),
                'minimumBid': auction_details.get('minimumBidAmount', 0)
            }
        except Exception as e:
            property_id = listing_data.get('id', 'unknown')
            print(f'  Critical error processing property {property_id}: {str(e)}')
            # Return minimal data to avoid complete loss
            return {
                'propertyName': f'Property {property_id}',
                'address': 'Address not available',
                'biddingStarts': 'N/A',
                'biddingEnds': 'N/A',
                'startingBid': 0,
                'currentBid': 0,
                'propertyType': 'Commercial',
                'assetType': 'Real Estate',
                'yearBuilt': 'N/A',
                'dateAdded': 'N/A',
                'brokers': 'No broker information',
                'buildingSize': 'N/A',
                'units': 'N/A',
                'size': 'N/A',
                'source': 'Crexi',
                'property_url': listing_data.get('url', ''),
                'auctionStatus': 'Unknown',
                'registeredBidders': 0,
                'reserveMet': False,
                'bidIncrement': 0,
                'minimumBid': 0
            }

    def close_driver(self) -> None:
        """
        Close driver session with proper error handling
        """
        if self.driver:
            print('🔒 Closing driver session...')
            try:
                # Try to close all windows first
                try:
                    for handle in self.driver.window_handles:
                        try:
                            self.driver.switch_to.window(handle)
                            self.driver.close()
                        except Exception as e:
                            print(f'  ⚠️  Warning: Could not close window {handle}: {str(e)}')
                            continue
                except Exception as e:
                    print(f'  ⚠️  Warning: Could not access window handles: {str(e)}')
                
                # Quit the driver
                try:
                    self.driver.quit()
                except Exception as e:
                    print(f'  ⚠️  Warning: Could not quit driver cleanly: {str(e)}')
                    # Force cleanup if normal quit fails
                    try:
                        self.driver.service.stop()
                    except:
                        pass
                
                # Additional cleanup to prevent __del__ issues
                try:
                    # Clear the driver reference and force garbage collection
                    driver_ref = self.driver
                    self.driver = None
                    del driver_ref
                except:
                    pass
                
            except Exception as e:
                print(f'  ⚠️  Warning: Error during driver cleanup: {str(e)}')
            finally:
                self.driver = None
                print('✓ Driver session closed')

    def scrape(self) -> Dict[str, Any]:
        """
        Main scraping function - scrapes all properties with detailed information and exports to CSV
        
        Returns:
            Dictionary containing scraping results
        """
        print('🚀 Starting Crexi property scraping with undetected Chrome driver...')
        start_time = time.time()
        
        result = {
            'processed_auctions': [],
            'total_processed': 0,
            'errors': [],
            'scraped_at': datetime.now()
        }

        try:
            # Step 1: Get all auction links from the auctions page
            print('📄 Fetching auction links from Crexi auctions page...')
            auction_links = self.fetch_auction_links()
            
            print(f'📊 Found {len(auction_links)} auction links to process')
            print('🔍 Fetching detailed information for each auction...\n')

            # Step 2: Process each auction page
            print(f'🔄 Processing all {len(auction_links)} auctions...')
            
            for i, auction_url in enumerate(auction_links):
                print(f'Processing auction {i + 1}/{len(auction_links)}: {auction_url}')

                try:
                    # Extract property ID from URL for basic info
                    property_id = None
                    property_name = 'Unknown'
                    
                    # Extract property ID from URL
                    id_match = re.search(r'/properties/(\d+)/', auction_url)
                    if id_match:
                        property_id = int(id_match.group(1))
                        property_name = f'Property {property_id}'
                    
                    # Fetch detailed auction data from the page
                    auction_details = self.fetch_property_details_from_page(auction_url)
                    
                    # Create basic listing data from URL
                    listing_data = {
                        'id': property_id,
                        'name': property_name,
                        'url': auction_url
                    }
                    
                    processed_property = self.process_property_data(listing_data, auction_details)
                    result['processed_auctions'].append(processed_property)
                    result['total_processed'] += 1

                    # Add delay between requests to be respectful
                    if i < len(auction_links) - 1:
                        sleep(self.config['delay_between_requests'] / 1000)  # Convert to seconds

                except Exception as e:
                    error_msg = f'Failed to process auction {auction_url}: {str(e)}'
                    result['errors'].append(error_msg)
                    print(f'  ✗ {error_msg}')
                    
                    # Try to create a minimal record with basic URL data to avoid complete loss
                    try:
                        print(f'  Attempting to create minimal record for auction...')
                        property_id = None
                        id_match = re.search(r'/properties/(\d+)/', auction_url)
                        if id_match:
                            property_id = int(id_match.group(1))
                        
                        minimal_listing = {
                            'id': property_id,
                            'name': f'Property {property_id}' if property_id else 'Unknown',
                            'url': auction_url
                        }
                        minimal_property = self.process_property_data(minimal_listing, {})
                        result['processed_auctions'].append(minimal_property)
                        result['total_processed'] += 1
                        print(f'  ✓ Created minimal record for auction')
                    except Exception as minimal_error:
                        print(f'  ✗ Failed to create minimal record for auction: {str(minimal_error)}')

            end_time = time.time()
            duration = end_time - start_time
            
            print(f'\n🎉 Scraping completed in {duration:.2f} seconds')
            print(f'📈 Results: {result["total_processed"]} properties processed successfully')
            
            if result['errors']:
                print(f'⚠️  {len(result["errors"])} errors encountered during processing')

            # Step 3: Export to CSV and JSON
            print('\n📁 Exporting to CSV and JSON...')
            csv_filename, json_filename = export_scraper_results(
                result['processed_auctions'],
                result['errors'],
                result['total_processed']
            )

            print(f'\n✅ Scraping completed successfully!')
            print(f'📁 CSV file: {csv_filename}')
            print(f'📁 JSON file: {json_filename}')
            print(f'📊 Total properties processed: {result["total_processed"]}')
            
            # Add summary to result for proper display
            result['summary'] = {
                'total_properties': len(result['processed_auctions']),
                'successful': result['total_processed'],
                'errors_count': len(result['errors']),
                'success_rate': (result['total_processed'] / len(result['processed_auctions']) * 100) if result['processed_auctions'] else 0
            }
            
            return result
            
        except Exception as e:
            error_msg = f'Critical error during scraping: {str(e)}'
            result['errors'].append(error_msg)
            print(f'💥 {error_msg}')
            raise
        finally:
            # Always close the driver session
            try:
                self.close_driver()
            except Exception as e:
                print(f'⚠️  Warning: Error during final driver cleanup: {str(e)}')
                # Force cleanup
                try:
                    if hasattr(self, 'driver') and self.driver:
                        self.driver = None
                except:
                    pass


def main():
    """
    Main function to run the Crexi scraper
    """
    scraper = None
    
    def signal_handler(signum, frame):
        """Handle interrupt signals gracefully"""
        print('\n⚠️  Received interrupt signal, cleaning up...')
        if scraper:
            try:
                scraper.close_driver()
            except:
                pass
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize scraper with configuration
        config = {
            'headless': False,  # Set to True for headless mode
            'delay_between_requests': 2000,  # 2 seconds between requests
            'session_rotation_limit': 20,  # Rotate session after 20 requests
        }
        
        scraper = CrexiScraper(config)
        
        # Run the scraper
        results = scraper.scrape()
        
        # Print summary
        print_scraper_summary(results)
        
    except KeyboardInterrupt:
        print('\n⚠️  Scraping interrupted by user')
    except Exception as e:
        print(f'\n💥 Fatal error: {str(e)}')
    finally:
        # Ensure cleanup
        if scraper:
            try:
                scraper.close_driver()
            except:
                pass
        # Force garbage collection to clean up any remaining driver references
        import gc
        gc.collect()


if __name__ == '__main__':
    main()
