import nodriver as uc
import asyncio
import re
import json
import csv
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup

class LoopNetScraper:
    """Simple LoopNet scraper using nodriver to avoid detection"""
    
    def __init__(self):
        self.browser = None
        self.base_url = 'https://www.loopnet.com/search/commercial-real-estate/usa/auctions/'
        self.all_urls = []
        
    async def start_browser(self):
        """Start browser with minimal configuration"""
        self.browser = await uc.start(headless=False)
        
    async def close_browser(self):
        """Close browser"""
        try:
            if self.browser:
                await self.browser.stop()
                self.browser = None
        except Exception as e:
            print(f"⚠️ Error closing browser: {e}")
            
    async def wait_for_element_with_retry(self, page, selector=None, content_check=None, timeout=30, max_retries=3, retry_delay=2):
        """
        Generic function to wait for elements or content with retry logic
        
        Args:
            page: Browser page object
            selector: CSS selector to wait for (optional)
            content_check: Function that takes page content and returns True if condition is met (optional)
            timeout: Maximum wait time per attempt in seconds
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            
        Returns:
            True if element/content found, False otherwise
        """
        for retry in range(max_retries):
            print(f"🔍 Attempt {retry + 1}/{max_retries} - Waiting for element/content...")
            
            wait_time = 0
            while wait_time < timeout:
                try:
                    # Check for CSS selector if provided
                    if selector:
                        elements = await page.select_all(selector)
                        if elements:
                            print(f"✅ Found element with selector: {selector}")
                            return True
                    
                    # Check for custom content condition if provided
                    if content_check:
                        content = await page.get_content()
                        if content_check(content):
                            print("✅ Content condition met")
                            return True
                    
                    # If both selector and content_check are None, just wait for page load
                    if not selector and not content_check:
                        content = await page.get_content()
                        if len(content) > 1000:  # Basic page load check
                            print("✅ Page loaded")
                            return True
                            
                except Exception as e:
                    print(f"⚠️ Error during wait check: {e}")
                    
                await asyncio.sleep(1)
                wait_time += 1
            
            # If this wasn't the last retry, reload the page and try again
            if retry < max_retries - 1:
                print(f"⏳ Timeout reached. Retrying page load in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                try:
                    await page.reload()
                    await asyncio.sleep(2)  # Give page time to start loading
                except Exception as e:
                    print(f"⚠️ Error reloading page: {e}")
            else:
                print(f"❌ All {max_retries} attempts failed")
                
        return False

    async def handle_security_check(self, page):
        """Handle security checks and redirects"""
        print("🔒 Checking for security measures...")
        
        # Wait for page to load completely with retry logic
        def security_check(content):
            return 'challenge' not in content.lower() and 'security' not in content.lower() and len(content) > 1000
        
        success = await self.wait_for_element_with_retry(
            page, 
            content_check=security_check,
            timeout=10,
            max_retries=2
        )
        
        if success:
            print("✅ Security check passed")
        else:
            print("⚠️ Security check may have issues, proceeding anyway...")
        
    async def wait_for_pagination(self, page):
        """Wait for pagination to load on main page with retry logic"""
        print("⏳ Waiting for pagination to load...")
        
        # Define pagination check function
        def pagination_check(content):
            soup = BeautifulSoup(content, 'html.parser')
            pagination_elements = soup.find_all(class_='total-results-paging-digits')
            page_links = soup.find_all('a', {'data-pg': True})
            return len(pagination_elements) > 0 or len(page_links) > 0
        
        # Use retry logic for pagination loading
        success = await self.wait_for_element_with_retry(
            page,
            selector='.total-results-paging-digits, a[data-pg]',
            content_check=pagination_check,
            timeout=30,
            max_retries=3
        )
        
        if success:
            print("✅ Pagination loaded successfully")
        else:
            print("⚠️ Pagination timeout after retries, proceeding with current page")
            
        return success
        
    async def extract_pagination_info(self, page):
        """Extract pagination information from the page"""
        print("📄 Extracting pagination info...")
        
        content = await page.get_content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for total results text
        total_results_element = soup.find(class_='total-results-paging-digits')
        total_results_text = total_results_element.get_text().strip() if total_results_element else ''
        
        if total_results_text:
            # Parse pagination text like "1-20 of 150"
            match = re.search(r'(\d+)-(\d+)\s+of\s+(\d+)', total_results_text)
            if match:
                total_results = int(match.group(3))
                items_per_page = int(match.group(2)) - int(match.group(1)) + 1
                total_pages = (total_results + items_per_page - 1) // items_per_page
                
                print(f"📊 Found {total_results} total results, {items_per_page} per page, {total_pages} total pages")
                return total_pages
        
        # Fallback: look for page links
        page_links = soup.find_all('a', {'data-pg': True})
        if page_links:
            max_page = 1
            for link in page_links:
                page_num = int(link.get('data-pg', 0))
                if page_num > max_page:
                    max_page = page_num
            
            print(f"📊 Found {max_page} pages from pagination links")
            return max_page
                
        print("📊 No pagination found, assuming single page")
        return 1
        
    async def extract_urls_from_listings_schema(self, page):
        """Extract URLs from listings schema JSON in HTML with retry logic"""
        print("🔗 Extracting URLs from listings schema...")
        
        # Define schema check function
        def schema_check(content):
            soup = BeautifulSoup(content, 'html.parser')
            schema_script = soup.find('script', {'id': 'listings-schema'})
            return schema_script is not None and schema_script.get_text().strip()
        
        # Wait for schema to load with retry logic
        success = await self.wait_for_element_with_retry(
            page,
            selector='script#listings-schema',
            content_check=schema_check,
            timeout=30,
            max_retries=3
        )
        
        if not success:
            print('⚠️ No script tag with id="listings-schema" found after retries')
            return []
        
        content = await page.get_content()
        soup = BeautifulSoup(content, 'html.parser')
        schema_script = soup.find('script', {'id': 'listings-schema'})
        
        if not schema_script:
            print('No script tag with id="listings-schema" found')
            return []
        
        json_content = schema_script.get_text()
        if not json_content:
            print('No JSON content found in listings-schema script tag')
            return []
        
        try:
            listings_data = json.loads(json_content)
            urls = []
            
            if (listings_data.get('mainEntity') and 
                listings_data['mainEntity'].get('itemListElement')):
                
                for item in listings_data['mainEntity']['itemListElement']:
                    if item.get('url'):
                        urls.append(item['url'])
            
            print(f"📋 Found {len(urls)} URLs from JSON schema")
            return urls
            
        except Exception as e:
            print(f'Error extracting URLs from listings schema: {e}')
            return []
        
    async def collect_all_urls(self):
        """Collect all auction URLs from all pages"""
        print("🚀 Starting URL collection...")
        
        await self.start_browser()
        page = await self.browser.get(self.base_url)
        
        # Handle security checks
        await self.handle_security_check(page)
        
        # Wait for pagination to load
        await self.wait_for_pagination(page)
        
        # Get pagination info
        total_pages = await self.extract_pagination_info(page)
        
        # Extract URLs from first page
        first_page_urls = await self.extract_urls_from_listings_schema(page)
        self.all_urls.extend(first_page_urls)
        print(f"📄 Page 1: Found {len(first_page_urls)} URLs")
        
        # Extract URLs from remaining pages
        for page_num in range(2, total_pages + 1):
            max_page_retries = 3
            page_retry_count = 0
            page_success = False
            
            while page_retry_count < max_page_retries and not page_success:
                try:
                    print(f"📄 Fetching page {page_num}/{total_pages} (attempt {page_retry_count + 1}/{max_page_retries})...")
                    
                    page_url = f"{self.base_url}{page_num}/"
                    page = await self.browser.get(page_url)
                    
                    # Handle security for each page
                    await self.handle_security_check(page)
                    
                    page_urls = await self.extract_urls_from_listings_schema(page)
                    
                    if page_urls:  # Only consider successful if URLs found
                        self.all_urls.extend(page_urls)
                        print(f"📄 Page {page_num}: Found {len(page_urls)} URLs")
                        page_success = True
                    else:
                        print(f"⚠️ No URLs found on page {page_num}, retrying...")
                        page_retry_count += 1
                        if page_retry_count < max_page_retries:
                            await asyncio.sleep(2)  # Wait before retry
                    
                except Exception as e:
                    print(f"❌ Error fetching page {page_num} (attempt {page_retry_count + 1}): {e}")
                    page_retry_count += 1
                    if page_retry_count < max_page_retries:
                        await asyncio.sleep(2)  # Wait before retry
            
            if not page_success:
                print(f"❌ Failed to fetch page {page_num} after {max_page_retries} attempts")
            
            # Small delay between pages
            await asyncio.sleep(1)
                
        # Remove duplicates
        unique_urls = list(set(self.all_urls))
        print(f"✅ Total unique URLs collected: {len(unique_urls)}")
        
        return unique_urls
        
    def _extract_angular_data(self, script_text: str, constant_name: str) -> Dict[str, Any]:
        """Extract data from Angular constant JavaScript"""
        try:
            # Look for the pattern after the constant name
            start_idx = script_text.find(f'"{constant_name}"')
            
            if start_idx != -1:
                # Find the opening brace after the constant name
                brace_start = script_text.find('{', start_idx)
                
                if brace_start != -1:
                    # Count braces to find the matching closing brace
                    brace_count = 0
                    for i, char in enumerate(script_text[brace_start:], brace_start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = script_text[brace_start:i+1]
                                return json.loads(json_str)
        except Exception as e:
            print(f'Error extracting Angular data for {constant_name}: {e}')
        
        return {}
    
    def _parse_net_date(self, net_date_str: str) -> str:
        """Parse .NET date format like /Date(1758556800000-0400)/"""
        try:
            if not net_date_str:
                return ''
            
            match = re.search(r'/Date\((\d+)([+-]\d{4})?\)/', net_date_str)
            if match:
                timestamp = int(match.group(1))
                dt = datetime.fromtimestamp(timestamp / 1000)
                return dt.isoformat()
        except Exception as e:
            print(f'Error parsing .NET date {net_date_str}: {e}')
        
        return ''
        
    async def extract_property_data(self, page):
        """Extract property data from individual auction page with retry logic"""
        print("🏠 Extracting property data...")
        
        # Define content check function for auction pages
        def auction_content_check(content):
            return ('auction' in content.lower() or 'bid' in content.lower()) and len(content) > 5000
        
        # Wait for auction content to load with retry logic
        success = await self.wait_for_element_with_retry(
            page,
            content_check=auction_content_check,
            timeout=30,
            max_retries=3
        )
        
        if not success:
            print("⚠️ Auction content not found after retries, extracting available data...")
        
        content = await page.get_content()
        soup = BeautifulSoup(content, 'html.parser')
        
        property_data = {
            'property_name': '',
            'address': '',
            'bidding_starts': '',
            'bidding_ends': '',
            'starting_bid': '',
            'current_bid': '',
            'bid_increment': '',
            'reserve_status': '',
            'property_type': '',
            'year_built': '',
            'broker_1': '',
            'broker_2': '',
            'broker_3': '',
            'total_building_size': '',
            'building_size': '',
            'auction_url': '',
            'scraped_at': datetime.now().isoformat()
        }
        
        try:
            # Debug: Check if this is a valid auction page
            if 'auction' not in content.lower() and 'bid' not in content.lower():
                print("No auction-related content found in HTML")
                return property_data
            
            print(f"🔍 Extracting data from page (length: {len(content)} chars)")
            
            # 1. Extract from Angular JavaScript modules
            scripts = soup.find_all('script')
            
            # Extract auction banner state
            auction_found = False
            for script in scripts:
                script_text = script.get_text()
                if 'auctionBannerState' in script_text:
                    print("Found auctionBannerState script")
                    auction_data = self._extract_angular_data(script_text, 'auctionBannerState')
                    if auction_data and 'Auction' in auction_data:
                        auction = auction_data['Auction']
                        
                        property_data['starting_bid'] = auction.get('StartingBid', '')
                        property_data['current_bid'] = auction.get('CurrentBid', '')
                        property_data['bid_increment'] = auction.get('CurrentBidIncrement', '')
                        property_data['bidding_starts'] = self._parse_net_date(auction.get('StartTime', ''))
                        property_data['bidding_ends'] = self._parse_net_date(auction.get('EndTime', ''))
                        
                        # Reserve status
                        if auction.get('IsReserveMet'):
                            property_data['reserve_status'] = 'Reserve Met'
                        elif auction.get('IsReserveNextBid'):
                            property_data['reserve_status'] = 'Next Bid Meets Reserve'
                        else:
                            property_data['reserve_status'] = 'Reserve Not Met'
                        
                        auction_found = True
                        break
            
            # Extract listing profile state
            listing_found = False
            for script in scripts:
                script_text = script.get_text()
                if 'listingProfileState' in script_text:
                    listing_data = self._extract_angular_data(script_text, 'listingProfileState')
                    if listing_data:
                        property_data['property_type'] = listing_data.get('CategoryTitle', '')
                        listing_found = True
                    break
            
            # 2. Extract from JSON-LD schema
            json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
            
            json_ld_found = False
            for json_ld_script in json_ld_scripts:
                try:
                    json_data = json.loads(json_ld_script.get_text())
                    
                    # Look for RealEstateListing type
                    if json_data.get('@type') == 'RealEstateListing':
                        json_ld_found = True
                        
                        # Property name
                        if 'name' in json_data:
                            property_data['property_name'] = json_data['name']
                        
                        # Address from description
                        if 'description' in json_data:
                            desc = json_data['description']
                            # Extract address pattern like "293 Patriot Way, Rochester, NY 14624"
                            address_match = re.search(r'(\d+\s+[^,]+,\s*[^,]+,\s*[A-Z]{2}\s+\d+)', desc)
                            if address_match:
                                property_data['address'] = address_match.group(1)
                        
                        # Brokers - extract names only, max 3
                        if 'provider' in json_data:
                            brokers = []
                            for provider in json_data['provider']:
                                if provider.get('@type') == 'RealEstateAgent':
                                    broker_name = provider.get('name', '').strip()
                                    if broker_name and len(brokers) < 3:
                                        brokers.append(broker_name)
                            
                            # Assign to broker columns
                            for i, broker in enumerate(brokers):
                                if i < 3:
                                    property_data[f'broker_{i+1}'] = broker
                        break
                        
                except json.JSONDecodeError:
                    continue
            
            # 3. Extract from HTML content (building size and year built)
            
            # Building size - look for patterns like "43,750 square foot"
            building_size_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*square\s*foot', content, re.IGNORECASE)
            if building_size_match:
                property_data['building_size'] = building_size_match.group(1).replace(',', '')
                property_data['total_building_size'] = property_data['building_size']
            else:
                # Alternative: Look for "Floor Size" in additionalProperty
                floor_size_match = re.search(r'"Floor Size"[^}]*"value":\s*"([^"]+)"', content)
                if floor_size_match:
                    size_text = floor_size_match.group(1)
                    # Extract numbers from "6,000 SF" format
                    size_numbers = re.search(r'(\d{1,3}(?:,\d{3})*)', size_text)
                    if size_numbers:
                        property_data['building_size'] = size_numbers.group(1).replace(',', '')
                        property_data['total_building_size'] = property_data['building_size']
                        print(f"📏 Extracted building size: {property_data['building_size']}")
            
            # Year built - look for patterns like "Built in 1969"
            year_built_match = re.search(r'Built\s+in\s+(\d{4})', content, re.IGNORECASE)
            if year_built_match:
                property_data['year_built'] = year_built_match.group(1)
                print(f"🏗️ Extracted year built: {property_data['year_built']}")
            else:
                # Alternative year built pattern - look in feature grids
                year_built_elements = soup.find_all('td', {'data-fact-type': 'YearBuiltRenovated'})
                for element in year_built_elements:
                    text = element.get_text().strip()
                    if text and re.match(r'\d{4}', text):
                        property_data['year_built'] = text.split('/')[0]  # Take first year if multiple
                        print(f"🏗️ Extracted year built from element: {property_data['year_built']}")
                        break
                
                # Additional method: Look for "Year Built" fact-name div
                if not property_data['year_built']:
                    fact_divs = soup.find_all('div', class_='fact-name')
                    for div in fact_divs:
                        if 'Year Built' in div.get_text():
                            # Look for the corresponding value in the next sibling or parent
                            parent = div.parent
                            if parent:
                                # Look for year pattern in the parent element
                                year_match = re.search(r'(\d{4})', parent.get_text())
                                if year_match:
                                    property_data['year_built'] = year_match.group(1)
                                    print(f"🏗️ Extracted year built from fact-name: {property_data['year_built']}")
                                    break
                
                # Additional method: Look for feature-grid structure
                if not property_data['year_built']:
                    year_built_rows = soup.find_all('tr', class_='feature-grid__row')
                    for row in year_built_rows:
                        title_cell = row.find('td', {'data-fact-type': 'YearBuilt'})
                        if title_cell and 'Year Built' in title_cell.get_text():
                            data_cell = row.find('td', class_='feature-grid__data')
                            if data_cell:
                                year_text = data_cell.get_text().strip()
                                year_match = re.search(r'(\d{4})', year_text)
                                if year_match:
                                    property_data['year_built'] = year_match.group(1)
                                    print(f"🏗️ Extracted year built from feature-grid: {property_data['year_built']}")
                                    break
            
            # 4. Fallback: Extract from title tag if property name not found
            if not property_data['property_name']:
                title_tag = soup.find('title')
                if title_tag:
                    property_data['property_name'] = title_tag.get_text().strip()
            
            # 5. Fallback: Extract address from title if not found
            if not property_data['address']:
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text()
                    # Look for address pattern in title
                    address_match = re.search(r'(\d+\s+[^,]+,\s*[^,]+,\s*[A-Z]{2}\s+\d+)', title_text)
                    if address_match:
                        property_data['address'] = address_match.group(1)
            
            # 6. Additional fallback: Try to extract any visible text content
            if not property_data['property_name'] and not property_data['address']:
                # Look for h1 or main heading
                main_heading = soup.find('h1')
                if main_heading:
                    property_data['property_name'] = main_heading.get_text().strip()
                
                # Look for any text that might be an address
                all_text = soup.get_text()
                address_patterns = [
                    r'(\d+\s+[^,]+,\s*[^,]+,\s*[A-Z]{2}\s+\d+)',
                    r'(\d+\s+[^,]+,\s*[^,]+,\s*[A-Z]{2})',
                    r'(\d+\s+[^,]+,\s*[A-Z]{2}\s+\d+)'
                ]
                
                for pattern in address_patterns:
                    address_match = re.search(pattern, all_text)
                    if address_match:
                        property_data['address'] = address_match.group(1)
                        break
            
        except Exception as e:
            print(f"⚠️ Error extracting property data: {e}")
        
        # Debug: Show what was extracted
        print(f"📊 Extracted data summary:")
        print(f"   Property: {property_data['property_name']}")
        print(f"   Address: {property_data['address']}")
        print(f"   Building Size: {property_data['building_size']}")
        print(f"   Year Built: {property_data['year_built']}")
        print(f"   Starting Bid: {property_data['starting_bid']}")
        print(f"   Property Type: {property_data['property_type']}")
            
        return property_data
        
    async def scrape_all_properties(self, urls):
        """Scrape all properties with retry logic"""
        print(f"🏠 Scraping {len(urls)} properties")
        
        results = []
        
        for i, url in enumerate(urls):
            max_property_retries = 3
            property_retry_count = 0
            property_success = False
            
            while property_retry_count < max_property_retries and not property_success:
                try:
                    retry_suffix = f" (attempt {property_retry_count + 1}/{max_property_retries})" if property_retry_count > 0 else ""
                    print(f"📄 Scraping {i+1}/{len(urls)}{retry_suffix}")
                    
                    page = await self.browser.get(url)
                    await self.handle_security_check(page)
                    
                    property_data = await self.extract_property_data(page)
                    property_data['auction_url'] = url
                    
                    # Check if we got meaningful data (at least property name or address)
                    if property_data.get('property_name') or property_data.get('address'):
                        results.append(property_data)
                        property_success = True
                        print(f"✅ Successfully scraped property: {property_data.get('property_name', 'Unknown')}")
                    else:
                        print(f"⚠️ No meaningful data extracted from {url}, retrying...")
                        property_retry_count += 1
                        if property_retry_count < max_property_retries:
                            await asyncio.sleep(2)  # Wait before retry
                    
                except Exception as e:
                    print(f"❌ Error scraping {url} (attempt {property_retry_count + 1}): {e}")
                    property_retry_count += 1
                    if property_retry_count < max_property_retries:
                        await asyncio.sleep(2)  # Wait before retry
            
            # If all retries failed, add error entry
            if not property_success:
                print(f"❌ Failed to scrape {url} after {max_property_retries} attempts")
                results.append({
                    'auction_url': url,
                    'error': f'Failed after {max_property_retries} attempts',
                    'scraped_at': datetime.now().isoformat()
                })
            
            # Small delay between properties
            await asyncio.sleep(1)
                
        return results
    
    def process_auction_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process LoopNet property data into standardized format for CSV export
        
        Args:
            raw_data: Raw property data from LoopNet
            
        Returns:
            Processed auction data with standardized column names
        """
        try:
            # Clean and format the data
            def clean_text(text):
                if not text:
                    return ''
                return str(text).strip()
            
            def parse_currency(value):
                if not value:
                    return 0
                try:
                    # Remove currency symbols and commas
                    cleaned = str(value).replace('$', '').replace(',', '').replace(' ', '')
                    return float(cleaned) if cleaned else 0
                except:
                    return 0
            
            def format_date(date_str):
                if not date_str:
                    return ''
                try:
                    # If it's already in ISO format, return as is
                    if 'T' in str(date_str):
                        return str(date_str)
                    return str(date_str)
                except:
                    return ''
            
            return {
                'Property URL': raw_data.get('auction_url', ''),
                'Property Name': clean_text(raw_data.get('property_name', '')),
                'Address': clean_text(raw_data.get('address', '')),
                'Bidding Starts': format_date(raw_data.get('bidding_starts', '')),
                'Bidding Ends': format_date(raw_data.get('bidding_ends', '')),
                'Starting Bid': parse_currency(raw_data.get('starting_bid', 0)),
                'Current Bid': parse_currency(raw_data.get('current_bid', 0)),
                'Bid Increment': parse_currency(raw_data.get('bid_increment', 0)),
                'Reserve Status': clean_text(raw_data.get('reserve_status', '')),
                'Property Type': clean_text(raw_data.get('property_type', '')),
                'Year Built': clean_text(raw_data.get('year_built', '')),
                'Broker 1': clean_text(raw_data.get('broker_1', '')),
                'Broker 2': clean_text(raw_data.get('broker_2', '')),
                'Broker 3': clean_text(raw_data.get('broker_3', '')),
                'Total Building Size': clean_text(raw_data.get('total_building_size', '')),
                'Building Size': clean_text(raw_data.get('building_size', '')),
                'Source': 'LoopNet',
                'Scraped At': raw_data.get('scraped_at', '')
            }
            
        except Exception as e:
            print(f"⚠️ Error processing auction data: {e}")
            # Return minimal data to avoid complete loss
            return {
                'Property URL': raw_data.get('auction_url', ''),
                'Property Name': clean_text(raw_data.get('property_name', '')),
                'Address': clean_text(raw_data.get('address', '')),
                'Bidding Starts': '',
                'Bidding Ends': '',
                'Starting Bid': 0,
                'Current Bid': 0,
                'Bid Increment': 0,
                'Reserve Status': '',
                'Property Type': '',
                'Year Built': '',
                'Broker 1': '',
                'Broker 2': '',
                'Broker 3': '',
                'Total Building Size': '',
                'Building Size': '',
                'Source': 'LoopNet',
                'Scraped At': raw_data.get('scraped_at', '')
            }
        
    async def scrape(self):
        """Main scraping function"""
        print("🚀 Starting LoopNet scraper...")
        
        try:
            # Step 1: Collect all URLs
            urls = await self.collect_all_urls()
            
            if not urls:
                print("❌ No URLs found")
                return []
                
            # Step 2: Scrape all properties
            raw_results = await self.scrape_all_properties(urls)
            
            # Step 3: Process and clean data for CSV export
            print("🧹 Processing and cleaning data...")
            processed_results = []
            for i, raw_data in enumerate(raw_results):
                print(f"Processing property {i + 1}/{len(raw_results)}: {raw_data.get('property_name', raw_data.get('auction_url', ''))}")
                
                try:
                    if 'error' not in raw_data:
                        processed_auction = self.process_auction_data(raw_data)
                        processed_results.append(processed_auction)
                    else:
                        print(f"  ✗ Skipping property with error: {raw_data.get('error', 'Unknown error')}")
                        
                except Exception as error:
                    print(f"  ✗ Error processing property: {error}")
            
            print(f"✅ Scraping completed! Processed {len(processed_results)} properties")
            return processed_results
            
        except Exception as e:
            print(f"💥 Scraping failed: {e}")
            return []
        finally:
            try:
                await self.close_browser()
            except Exception as e:
                print(f"⚠️ Error in cleanup: {e}")

async def main():
    scraper = LoopNetScraper()
    results = await scraper.scrape()
    
    # Save results to CSV file
    if results:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f'loopnet_auctions_{timestamp}.csv'
        
        # Define CSV columns in the specified order
        fieldnames = [
            'Property URL',
            'Property Name', 
            'Address',
            'Bidding Starts',
            'Bidding Ends',
            'Starting Bid',
            'Current Bid',
            'Bid Increment',
            'Reserve Status',
            'Property Type',
            'Year Built',
            'Broker 1',
            'Broker 2', 
            'Broker 3',
            'Total Building Size',
            'Building Size',
            'Source',
            'Scraped At'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
            
        print(f"💾 Results saved to {filename}")
        print(f"📊 Total properties exported: {len(results)}")
    else:
        print("❌ No results to save")

if __name__ == '__main__':
    # since asyncio.run never worked (for me)
    uc.loop().run_until_complete(main())
