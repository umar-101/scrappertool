# Real Estate Scrapers

A collection of web scrapers for extracting real estate auction data from various platforms using `nodriver` for undetectable browser automation.

## 🏗️ Project Structure

```
realestate_scrapers/
├── scrapers/
│   ├── crexi_scraper.py      # Crexi auction scraper
│   ├── loopnet_scraper.py    # LoopNet auction scraper
│   └── rmi_scraper.py        # RMI auction scraper
├── utils/
│   ├── csv_exporter.py       # CSV export utilities
│   └── data_cleaner.py       # Data cleaning utilities
├── main.py                   # Main scraper service
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Poetry configuration
└── README.md                # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Chrome browser installed
- Poetry (recommended) or pip

### Installation

#### Option 1: Using Poetry (Recommended)

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

#### Option 2: Using pip

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 📊 Available Scrapers

### 1. Crexi Scraper

Extracts auction data from Crexi marketplace with network request interception.

**Features:**
- ✅ Network request interception for API data
- ✅ Automatic pagination handling
- ✅ CSV export with timestamp
- ✅ Retry logic with 3 attempts
- ✅ Fast processing (30s max per attempt)
- ✅ Headless mode support

**Run Crexi Scraper:**
```bash
python scrapers/crexi_scraper.py
```

**Output:**
- CSV file: `crexi_auctions_YYYY-MM-DD_HH-MM-SS.csv`
- Extracts: Property details, auction info, broker information

### 2. LoopNet Scraper

Extracts auction data from LoopNet marketplace.

**Features:**
- ✅ Automatic pagination handling
- ✅ CSV export with timestamp
- ✅ Headless mode support
- ✅ Optimized for speed

**Run LoopNet Scraper:**
```bash
python scrapers/loopnet_scraper.py
```

**Output:**
- CSV file: `loopnet_auctions_YYYY-MM-DD_HH-MM-SS.csv`
- Extracts: Property details, auction info, broker information

### 3. RMI Scraper

Extracts auction data from RMI marketplace.

**Run RMI Scraper:**
```bash
python scrapers/rmi_scraper.py
```

## 🔧 Configuration

### Browser Settings

All scrapers support headless mode for faster execution:

```python
# In scraper files, you can modify:
config = {
    'headless': True,  # Set to False to see browser window
    'delay_between_requests': 500,  # Milliseconds between requests
}
```

### Scraper Limits

- **Crexi Scraper**: Limited to first 10 auctions for testing
- **LoopNet Scraper**: Processes all available auctions
- **RMI Scraper**: Processes all available auctions

## 📁 Output Data

### CSV Export Format

All scrapers export data to CSV files with the following fields:

| Field | Description |
|-------|-------------|
| `propertyName` | Name of the property |
| `address` | Full property address |
| `biddingStarts` | Auction start date/time |
| `biddingEnds` | Auction end date/time |
| `startingBid` | Starting bid amount |
| `propertyType` | Type of property (Commercial, etc.) |
| `yearBuilt` | Year the property was built |
| `broker1`, `broker2`, `broker3` | Broker contact information |
| `buildingSize` | Size of the building |
| `property_url` | Direct link to the property |
| `source` | Data source (Crexi, LoopNet, RMI) |

### Sample Output

```csv
propertyName,address,biddingStarts,biddingEnds,startingBid,propertyType,broker1,broker2,broker3,property_url,source
"Former School","110 Pearl St, Oscoda, Iosco County, MI 48750","2025-10-06T16:00:00Z","2025-10-08T16:00:00Z",1.0,Commercial,"Gordon Hyde","Alexsis Wolfson",N/A,https://www.crexi.com/properties/2138610/michigan-former-school,Crexi
```

## 🛠️ Advanced Usage

### Running All Scrapers

```bash
# Run the main service (all scrapers)
python main.py
```

### Custom Configuration

You can modify scraper behavior by editing the configuration in each scraper file:

```python
# Example: Modify Crexi scraper limits
test_auction_links = auction_links[:20]  # Process first 20 instead of 10
```

### Debug Mode

To see browser windows and debug output:

```python
# Set headless=False in scraper configuration
config = {
    'headless': False,
    'delay_between_requests': 1000,
}
```

## 🔍 Troubleshooting

### Common Issues

1. **Chrome not found**
   - Ensure Chrome browser is installed
   - Update Chrome to latest version

2. **Network timeouts**
   - Check internet connection
   - Increase delay between requests

3. **No data extracted**
   - Verify website structure hasn't changed
   - Check for anti-bot measures

4. **Browser crashes**
   - Reduce concurrent requests
   - Increase delay between requests

### Performance Optimization

- **Headless mode**: Set `headless=True` for faster execution
- **Reduce delays**: Lower `delay_between_requests` for faster scraping
- **Limit auctions**: Process fewer auctions for testing

## 📋 Dependencies

### Core Dependencies

- `nodriver` - Undetectable browser automation
- `beautifulsoup4` - HTML parsing
- `asyncio` - Asynchronous programming
- `pandas` - Data manipulation (optional)

### Full Requirements

See `requirements.txt` for complete dependency list.
