from fastapi import FastAPI, Request, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import io
import glob
from datetime import datetime, date, timedelta
import csv
import re
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import tempfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="ClearRecon CA Scraper - Enhanced Selenium Version")

# Ensure directories exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("csv_data", exist_ok=True)
os.makedirs("debug", exist_ok=True)

templates = Jinja2Templates(directory="templates")

# Global variables for caching
latest_csv_path = None
all_cities = []

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page with comprehensive scraper interface."""
    return templates.TemplateResponse("index_full.html", {
        "request": request,
        "default_start": date.today().strftime("%Y-%m-%d"),
        "default_end": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    })

@app.post("/scrape_all")
async def scrape_all_listings():
    """Scrape all listings using enhanced Selenium with pagination handling."""
    try:
        print("Starting enhanced Selenium scrape for ALL listings...")
        
        csv_path = scrape_clearrecon_selenium_enhanced()
        
        if csv_path and os.path.exists(csv_path):
            global latest_csv_path, all_cities
            latest_csv_path = csv_path
            
            # Extract all unique cities
            all_cities = extract_cities_from_csv(csv_path)
            
            # Get row count
            with open(csv_path, 'r', encoding='utf-8') as f:
                row_count = sum(1 for line in csv.DictReader(f))
            
            return JSONResponse({
                "success": True,
                "message": f"Successfully scraped {row_count} listings",
                "csv_path": csv_path,
                "cities_found": len(all_cities),
                "cities": all_cities[:10]  # Show first 10 cities
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "Failed to create CSV file"
            })
            
    except Exception as e:
        print(f"Scrape error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.post("/filter")
async def filter_listings(
    city: str = Form("all"),
    start_date: str = Form(...),
    end_date: str = Form(...),
    email: str = Form("")
):
    """Filter listings from CSV by city and date range."""
    try:
        latest_csv_path = get_latest_csv_path()
        
        if not latest_csv_path or not os.path.exists(latest_csv_path):
            return JSONResponse({
                "success": False,
                "error": "No CSV data available. Please scrape all listings first."
            })
        
        # Load and filter CSV data using basic CSV handling
        results = []
        total_count = 0
        
        with open(latest_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            for row in reader:
                total_count += 1
                
                # Filter by city (case insensitive, exact match or substring)
                if city and city != "all":
                    row_city = row.get('city', '').strip()
                    if not row_city:
                        continue
                    
                    # Normalize both cities for comparison
                    normalized_filter_city = city.lower().title()
                    normalized_row_city = row_city.lower().title()
                    
                    # Try exact match first, then substring match
                    if (normalized_filter_city != normalized_row_city and 
                        normalized_filter_city.lower() not in normalized_row_city.lower()):
                        continue
                
                # Filter by date range if date exists
                if row.get('date'):
                    try:
                        # Try to parse various date formats
                        date_str = row['date']
                        row_date = None
                        
                        # Try different date formats
                        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y']:
                            try:
                                row_date = datetime.strptime(date_str, fmt).date()
                                break
                            except ValueError:
                                continue
                        
                        if row_date and (row_date < start_dt or row_date > end_dt):
                            continue
                    except:
                        pass  # Include if date parsing fails
                
                results.append(row)
        
        # Send email if email address is provided
        email_sent = False
        if email and email.strip() and results:
            filter_info = {
                "city": city if city != "all" else "All Cities",
                "start_date": start_date,
                "end_date": end_date
            }
            email_sent = send_filtered_results_email(email.strip(), results, filter_info)
        
        return JSONResponse({
            "success": True,
            "results": results,
            "count": len(results),
            "total_available": total_count,
            "email_sent": email_sent,
            "email_message": "Filtered results sent to your email!" if email_sent else ("Email not sent - check configuration" if email and email.strip() else "")
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@app.get("/csv")
async def view_csv():
    """View the latest CSV file as plain text."""
    try:
        latest_csv = get_latest_csv_path()
        if not latest_csv:
            return {"status": "error", "message": "No CSV file found. Please run a scrape first."}
        
        with open(latest_csv, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return Response(content=content, media_type="text/plain")
    except Exception as e:
        return {"status": "error", "message": f"Error reading CSV: {str(e)}"}

@app.get("/csvdata")
async def download_csv():
    """Download the latest CSV file."""
    try:
        latest_csv = get_latest_csv_path()
        if not latest_csv:
            return {"status": "error", "message": "No CSV file found. Please run a scrape first."}
        
        # Read the file content
        with open(latest_csv, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create a file-like object in memory
        file_like = io.StringIO(content)
        
        # Return as a downloadable file
        return StreamingResponse(
            iter([file_like.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=foreclosure_listings_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    except Exception as e:
        return {"status": "error", "message": f"Error preparing CSV for download: {str(e)}"}

@app.get("/cities")
async def get_cities():
    """Get all available cities from the latest CSV."""
    latest_csv_path = get_latest_csv_path()
    
    if not latest_csv_path or not os.path.exists(latest_csv_path):
        return JSONResponse({"cities": []})
    
    cities = await extract_cities_from_csv(latest_csv_path)
    return JSONResponse({"cities": cities})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "scraper_type": "enhanced_selenium",
        "csv_files": len(glob.glob("csv_data/*.csv")),
        "latest_csv": get_latest_csv_path() is not None
    })

@app.get("/diagnostics")
async def run_diagnostics():
    """Run comprehensive diagnostics to identify CSV creation issues."""
    try:
        # Import diagnostics here to avoid startup issues
        from azure_diagnostics import AzureDiagnostics
        
        diagnostics = AzureDiagnostics()
        results = diagnostics.run_all_tests()
        
        # Calculate summary
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['status'])
        failed_tests = total_tests - passed_tests
        
        return JSONResponse({
            "success": True,
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%"
            },
            "results": results,
            "recommendation": "All tests passed - issue may be in scraping logic" if failed_tests == 0 else "Some tests failed - check failed tests for root cause"
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": f"Diagnostics failed: {str(e)}",
            "recommendation": "Check server logs for detailed error information"
        })

def scrape_clearrecon_selenium_enhanced() -> str:
    """Enhanced Selenium scraper with comprehensive pagination handling for all 666+ listings."""
    
    # Configure Chrome options for Azure deployment
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")  # Required for Azure
    chrome_options.add_argument("--disable-dev-shm-usage")  # Required for Azure
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    
    try:
        print("Step 1: Initializing Chrome WebDriver...")
        # Use webdriver-manager for automatic ChromeDriver setup with Azure Linux fix
        chromedriver_path = ChromeDriverManager().install()
        print(f"ChromeDriver downloaded to: {chromedriver_path}")
        
        # Fix for Azure Linux: ensure we're using the actual chromedriver binary
        if chromedriver_path.endswith('THIRD_PARTY_NOTICES.chromedriver'):
            # Find the actual chromedriver binary in the same directory
            driver_dir = os.path.dirname(chromedriver_path)
            actual_driver = os.path.join(driver_dir, 'chromedriver')
            if os.path.exists(actual_driver):
                chromedriver_path = actual_driver
                print(f"Using actual ChromeDriver binary: {chromedriver_path}")
            else:
                # Try alternative names
                for name in ['chromedriver-linux64', 'chromedriver_linux64']:
                    alt_path = os.path.join(driver_dir, name)
                    if os.path.exists(alt_path):
                        chromedriver_path = alt_path
                        print(f"Using alternative ChromeDriver: {chromedriver_path}")
                        break
        
        # Make sure the driver is executable
        import stat
        os.chmod(chromedriver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        
        print("Step 2: Navigating to ClearRecon...")
        driver.get("https://clearrecon-ca.com/california-listings/")
        
        print("Step 3: Checking for disclaimer...")
        # Enhanced disclaimer handling
        disclaimer_selectors = [
            "//a[contains(text(), 'Agree')]",
            "//button[contains(text(), 'Agree')]",
            "//input[@value='Agree']",
            "//a[contains(text(), 'Accept')]",
            "//button[contains(text(), 'Accept')]",
            "//input[@value='Accept']"
        ]
        
        disclaimer_accepted = False
        for selector in disclaimer_selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                print(f"Found disclaimer element: {selector}")
                
                # Scroll element into view
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(1)
                
                # Try multiple click strategies
                try:
                    element.click()
                except:
                    try:
                        driver.execute_script("arguments[0].click();", element)
                    except:
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(driver).move_to_element(element).click().perform()
                
                print("Disclaimer accepted!")
                disclaimer_accepted = True
                
                # Wait for page to reload after accepting disclaimer
                time.sleep(5)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                break
                
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Could not handle disclaimer with selector {selector}: {e}")
                continue
        
        if not disclaimer_accepted:
            print("No disclaimer found or already accepted")
        
        print("Step 4: Enhanced pagination handling to get ALL listings...")
        all_listings = []
        page_count = 1
        max_pages = 50  # Safety limit to get all ~666 listings
        
        while page_count <= max_pages:
            print(f"Processing page {page_count}...")
            
            # Wait for page to load completely
            time.sleep(3)
            
            # Scroll to load all content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Extract listings from current page
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            page_listings = extract_all_listings_selenium(soup, driver, page_count)
            
            print(f"Page {page_count}: Found {len(page_listings)} listings")
            all_listings.extend(page_listings)
            
            # Look for next page
            next_found = False
            next_selectors = [
                "//a[contains(text(), 'Next')]",
                "//button[contains(text(), 'Next')]",
                "//a[contains(@class, 'next')]",
                "//button[contains(@class, 'next')]",
                "//a[contains(text(), '>')]",
                "//button[contains(text(), '>')]",
                "//a[contains(@title, 'Next')]",
                "//button[contains(@title, 'Next')]"
            ]
            
            for next_selector in next_selectors:
                try:
                    next_elements = driver.find_elements(By.XPATH, next_selector)
                    for next_element in next_elements:
                        if next_element.is_displayed() and next_element.is_enabled():
                            print(f"Found next page button: {next_selector}")
                            
                            # Scroll element into view
                            driver.execute_script("arguments[0].scrollIntoView(true);", next_element)
                            time.sleep(1)
                            
                            # Try multiple click strategies
                            try:
                                next_element.click()
                            except:
                                try:
                                    driver.execute_script("arguments[0].click();", next_element)
                                except:
                                    from selenium.webdriver.common.action_chains import ActionChains
                                    ActionChains(driver).move_to_element(next_element).click().perform()
                            
                            print(f"Successfully navigated to page {page_count + 1}")
                            time.sleep(5)  # Wait for page to load
                            page_count += 1
                            next_found = True
                            break
                            
                except (NoSuchElementException, TimeoutException):
                    continue
                
                if next_found:
                    break
            
            if not next_found:
                print(f"No more pages found after page {page_count}")
                break
        
        print(f"Total listings extracted from {page_count} pages: {len(all_listings)}")
        
        # Deduplicate listings by TS Number (case-insensitive)
        unique_listings = {}
        for listing in all_listings:
            ts_num = listing.get("ts_number", "").strip()
            if ts_num:  # Only keep listings with a TS Number
                # Use lowercase for case-insensitive comparison
                unique_listings[ts_num.lower()] = listing
        
        print(f"Found {len(all_listings)} total listings, {len(unique_listings)} unique by TS Number")
        
        # Save to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"csv_data/clearrecon_listings_enhanced_{timestamp}.csv"
        
        save_to_csv(list(unique_listings.values()), csv_path)
        print(f"Saved {len(unique_listings)} unique listings to {csv_path}")
        
        return csv_path
        
    except Exception as e:
        print(f"Enhanced Selenium scraping error: {e}")
        return None
        
    finally:
        if driver:
            driver.quit()

def extract_all_listings_selenium(soup: BeautifulSoup, driver, page_num: int) -> List[Dict]:
    """Extract all listings from the Selenium-loaded page."""
    listings = []
    
    try:
        # Strategy 1: Table-based extraction
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables on page {page_num}")
        
        for table_index, table in enumerate(tables):
            rows = table.find_all('tr')
            if len(rows) > 1:  # Has header and data rows
                headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
                print(f"Table {table_index + 1}: {len(rows)} rows, Headers: {headers}")
                
                for row_index, row in enumerate(rows[1:], 1):  # Skip header
                    cells = row.find_all(['td', 'th'])
                    cell_data = [cell.get_text(strip=True) for cell in cells]
                    
                    if any(cell_data):  # Skip empty rows
                        listing = parse_listing_data_enhanced(cell_data, headers)
                        listing["row_index"] = row_index
                        listing["table_index"] = table_index + 1
                        listing["page_number"] = page_num
                        listings.append(listing)
        
        # Strategy 2: Div-based extraction if no tables
        if not listings:
            print(f"No table data found on page {page_num}, trying div extraction...")
            divs = soup.find_all('div', class_=re.compile(r'listing|property|auction|item'))
            
            for div_index, div in enumerate(divs):
                text = div.get_text(strip=True)
                if len(text) > 50:  # Meaningful content
                    listing = parse_listing_data_enhanced([text], [])
                    listing["row_index"] = div_index + 1
                    listing["table_index"] = 0
                    listing["page_number"] = page_num
                    listing["source"] = "div extraction"
                    listings.append(listing)
        
        print(f"Page {page_num}: Extracted {len(listings)} listings")
        return listings
        
    except Exception as e:
        print(f"Extraction error on page {page_num}: {e}")
        return []

def parse_listing_data_enhanced(cell_data: List[str], headers: List[str]) -> Dict:
    """Enhanced parsing with comprehensive city extraction and CSV structure."""
    listing = {
        "ts_number": "",  # Add TS Number field
        "address": "",
        "city": "",
        "county": "",
        "date": "",
        "price": "",
        "details": "",
        "status": "",
        "raw_data": "",
        "row_index": "",
        "table_index": "",
        "page_number": ""
    }
    
    # Combine all cell data for analysis
    combined_text = " ".join(cell_data).strip()
    listing["raw_data"] = combined_text
    
    # Enhanced city extraction with comprehensive CA city patterns
    city_patterns = [
        # Major CA cities (comprehensive list)
        r'\b(Los Angeles|San Francisco|San Diego|Sacramento|Oakland|Fresno|Long Beach|Bakersfield|Anaheim|Riverside|Santa Ana|Stockton|Irvine|Chula Vista|Fremont|San Bernardino|Modesto|Fontana|Oxnard|Moreno Valley|Huntington Beach|Glendale|Santa Clarita|Garden Grove|Oceanside|Rancho Cucamonga|Santa Rosa|Ontario|Lancaster|Elk Grove|Corona|Palmdale|Salinas|Pomona|Hayward|Escondido|Torrance|Sunnyvale|Orange|Fullerton|Pasadena|Thousand Oaks|Visalia|Simi Valley|Concord|Roseville|Rocklin|Victorville|Santa Clara|Vallejo|Berkeley|El Monte|Downey|Costa Mesa|Inglewood|Carlsbad|San Buenaventura|Fairfield|West Covina|Murrieta|Richmond|Norwalk|Antioch|Temecula|Burbank|Daly City|Rialto|Santa Maria|El Cajon|San Mateo|Clovis|Compton|Jurupa Valley|Vista|South Gate|Mission Viejo|Vacaville|Carson|Hesperia|Santa Monica|Westminster|Redding|Santa Barbara|Chico|Newport Beach|San Leandro|San Marcos|Whittier|Hawthorne|Citrus Heights|Tracy|Alhambra|Livermore|Buena Park|Lakewood|Merced|Hemet|Chino|Menifee|Lake Forest|Napa|Redwood City|Bellflower|Indio|Tustin|Baldwin Park|Chino Hills|Mountain View|Alameda|Upland|Folsom|San Ramon|Pleasanton|Union City|Perris|Manteca|Lynwood|Apple Valley|Redlands|Turlock|Milpitas|Redondo Beach|Rancho Cordova|Yorba Linda|Palo Alto|Davis|Camarillo|Walnut Creek|Pittsburg|South San Francisco|Yuba City|San Clemente|Laguna Niguel|Pico Rivera|Montebello|Lodi|Madera|Santa Cruz|La Habra|Encinitas|Monterey Park|Tulare|Cupertino|Gardena|National City|Petaluma|Huntington Park|San Rafael|Porterville|Hanford|Waterford|Delano|Diamond Bar|Glendora|Cerritos|Azusa|Rancho Palos Verdes|Fountain Valley|Placentia|Monrovia|Santee|Eastvale|Rosemead|San Gabriel|Gilroy|Stanton|Paramount|Brea|Covina|San Bruno|Arcadia|Culver City|Benicia|Colton|Beaumont|Morgan Hill|San Luis Obispo|Los Altos|Brentwood|Aliso Viejo|La Mesa|West Sacramento|Agoura Hills|La Mirada|Rowland Heights|Cypress|Newark|Desert Hot Springs|Duarte|Lomita|Barstow|Adelanto|Twentynine Palms|Yucca Valley|Joshua Tree|Ridgecrest|California City|Tehachapi|Mojave)\b',
        
        # Pattern: City, CA or City, California
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+CA\b',
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+California\b',
        
        # Pattern: Address in City format
        r'(?:in|at|located in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        
        # Pattern: City name before zip code
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\d{5}(?:-\d{4})?\b'
    ]
    
    for pattern in city_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            city_name = match.group(1).strip()
            # Clean up city name
            city_name = re.sub(r'[,\.]$', '', city_name)  # Remove trailing comma/period
            listing["city"] = city_name.title()  # Proper case
            break
    
    # Enhanced address extraction
    address_patterns = [
        r'\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Way|Lane|Ln|Circle|Cir|Court|Ct|Place|Pl)\b',
        r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Way|Lane|Ln|Circle|Cir|Court|Ct|Place|Pl)',
        r'\d+\s+[A-Za-z0-9\s\-]+(?=,|\s+[A-Z][a-z]+,?\s+CA)'
    ]
    
    for pattern in address_patterns:
        address_match = re.search(pattern, combined_text, re.IGNORECASE)
        if address_match:
            listing["address"] = address_match.group().strip()
            break
    
    # Extract price
    price_pattern = r'\$[\d,]+(?:\.\d{2})?'
    price_match = re.search(price_pattern, combined_text)
    if price_match:
        listing["price"] = price_match.group().strip()
    
    # Extract date with multiple formats
    date_patterns = [
        r'\b\d{1,2}/\d{1,2}/\d{4}\b',
        r'\b\d{4}-\d{1,2}-\d{1,2}\b',
        r'\b\d{1,2}-\d{1,2}-\d{4}\b'
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, combined_text)
        if date_match:
            listing["date"] = date_match.group().strip()
            break
    
    # Extract TS Number (Trustee Sale Number)
    # First, look for the TS Number pattern in the beginning of the text
    ts_patterns = [
        # Format: 123456-CA
        r'^\s*(\d{5,}-[A-Z]{2})\b',
        # Format: TS# 12345 or TS 12345-CA
        r'TS[#\s]*\s*([A-Z0-9-]{5,})',
        # Format: TRUSTEE SALE #12345 or TRUSTEE'S SALE #12345-CA
        r'TRUSTEE[\'S]*\s*SALE[\s-]*#?[\s-]*([A-Z0-9-]{5,})',
        # Format: Sale #12345 or Sale #12345-CA
        r'Sale[\s-]*#?[\s-]*([A-Z0-9-]{5,})',
        # Look for any 5+ digit number followed by -CA or -AZ
        r'\b(\d{5,}-[A-Z]{2})\b',
        # Look for any 5+ digit number that might be a TS Number
        r'\b(\d{5,})\b'
    ]
    
    # First try to find TS Number in the raw data
    for pattern in ts_patterns:
        ts_match = re.search(pattern, combined_text, re.IGNORECASE)
        if ts_match:
            # Get the first non-None group
            ts_num = next((g for g in ts_match.groups() if g), '').strip().upper()
            # Clean up the TS Number
            ts_num = re.sub(r'[^A-Z0-9-]', '', ts_num)  # Remove any non-alphanumeric characters except hyphens
            # Ensure TS Number is at least 5 characters (e.g., 12345 or 123-CA)
            if len(ts_num) >= 5:
                # If it's just numbers, add -CA suffix if not present
                if ts_num.isdigit() and len(ts_num) >= 5 and not ts_num.endswith(('-CA', '-AZ')):
                    ts_num = f"{ts_num}-CA"
                listing["ts_number"] = ts_num
                print(f"Extracted TS Number: {ts_num} from text")
                break
    
    # If still no TS Number, try to extract from the raw data field if it exists
    if "ts_number" not in listing and "raw_data" in listing and listing["raw_data"]:
        for pattern in ts_patterns:
            ts_match = re.search(pattern, listing["raw_data"], re.IGNORECASE)
            if ts_match:
                ts_num = next((g for g in ts_match.groups() if g), '').strip().upper()
                ts_num = re.sub(r'[^A-Z0-9-]', '', ts_num)
                if len(ts_num) >= 5:
                    if ts_num.isdigit() and len(ts_num) >= 5 and not ts_num.endswith(('-CA', '-AZ')):
                        ts_num = f"{ts_num}-CA"
                    listing["ts_number"] = ts_num
                    print(f"Extracted TS Number from raw_data: {ts_num}")
                    break
    
    # Use remaining text as details
    listing["details"] = combined_text[:1000]  # Increased limit for more details
    
    return listing

async def save_to_csv(listings: List[Dict], csv_path: str):
    """Save listings to CSV file with proper structure and deduplication by TS Number."""
    if not listings:
        return
    
    # Deduplicate listings by TS Number (case-insensitive)
    unique_listings = {}
    for listing in listings:
        ts_num = listing.get("ts_number", "").strip().upper()
        if ts_num:  # Only keep listings with a TS Number
            unique_listings[ts_num] = listing
    
    print(f"Saving {len(unique_listings)} unique listings (from {len(listings)} total)")
    
    # Ensure all listings have the same keys
    all_keys = set()
    for listing in unique_listings.values():
        all_keys.update(listing.keys())
    
    # Ensure consistent field order
    field_order = ["ts_number", "address", "city", "county", "date", "price", "details", "status"]
    fieldnames = [f for f in field_order if f in all_keys]
    fieldnames.extend(sorted(f for f in all_keys if f not in field_order))
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        
        for listing in unique_listings.values():
            # Ensure all fields are present and properly formatted
            row = {key: str(listing.get(key, '')).strip() for key in fieldnames}
            writer.writerow(row)

def send_filtered_results_email(email_address: str, filtered_results: List[Dict], filter_info: Dict) -> bool:
    """Send filtered results as CSV attachment via email (Azure compatible)."""
    try:
        # Email configuration (use environment variables for Azure)
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        sender_email = os.environ.get("SENDER_EMAIL", "")
        sender_password = os.environ.get("SENDER_PASSWORD", "")
        
        if not sender_email or not sender_password:
            print("Email configuration missing. Set SENDER_EMAIL and SENDER_PASSWORD environment variables.")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email_address
        msg['Subject'] = f"ClearRecon Filtered Listings - {len(filtered_results)} Results"
        
        # Email body
        body = f"""
Hello,

Your filtered ClearRecon California foreclosure listings are attached.

Filter Details:
- City: {filter_info.get('city', 'All Cities')}
- Date Range: {filter_info.get('start_date', 'N/A')} to {filter_info.get('end_date', 'N/A')}
- Results Found: {len(filtered_results)} listings

The results are attached as a CSV file for easy viewing in Excel or other spreadsheet applications.

Best regards,
ClearRecon Scraper System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Create CSV attachment
        if filtered_results:
            # Create temporary CSV file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='', encoding='utf-8') as temp_file:
                fieldnames = filtered_results[0].keys()
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(filtered_results)
                temp_filename = temp_file.name
            
            # Attach CSV file
            with open(temp_filename, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"clearrecon_filtered_{timestamp}.csv"
            
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}',
            )
            
            msg.attach(part)
            
            # Clean up temp file
            os.unlink(temp_filename)
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, email_address, text)
        server.quit()
        
        print(f"Email sent successfully to {email_address}")
        return True
        
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def get_latest_csv_path() -> Optional[str]:
    """Get the path to the most recent CSV file."""
    csv_files = glob.glob("csv_data/*.csv")
    if not csv_files:
        return None
    return max(csv_files, key=os.path.getctime)

def extract_cities_from_csv(csv_path: str) -> List[str]:
    """Extract all unique cities from the CSV file with proper capitalization."""
    try:
        cities = set()
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                city = row.get('city', '').strip()
                if city and len(city) > 0:
                    # Normalize city name: lowercase first, then title case
                    normalized_city = city.lower().title()
                    cities.add(normalized_city)
        return sorted(list(cities))
    except Exception as e:
        print(f"Error extracting cities: {e}")
        return []

def run_test_scraper():
    """Run the scraper in test mode."""
    print("Starting test scraper...")
    try:
        result = scrape_clearrecon_selenium_enhanced()
        if result and "listings" in result:
            print(f"\nSuccessfully scraped {len(result['listings'])} listings")
            print(f"CSV saved to: {result.get('csv_path', 'Unknown')}")
            
            # Show sample data
            if result['listings']:
                print("\nSample listing:")
                sample = result['listings'][0]
                for key, value in sample.items():
                    if key != 'raw_data':  # Skip raw data as it's too long
                        print(f"{key}: {value}")
        return result
    except Exception as e:
        print(f"Error running scraper: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def quick_test():
    """Run a quick test of the scraper directly with detailed error reporting."""
    print("=== Starting Quick Test ===")
    print("This will test if Selenium and Chrome WebDriver are working properly.")
    
    try:
        print("\n1. Testing Python imports...")
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        print("✅ Selenium imports successful")
        
        print("\n2. Checking Chrome WebDriver...")
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        # Print Python and package versions
        import sys
        print(f"Python version: {sys.version}")
        print(f"Selenium version: {webdriver.__version__}")
        
        # Setup Chrome options
        print("\n3. Configuring Chrome options...")
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Try to initialize Chrome WebDriver
        print("\n4. Initializing Chrome WebDriver...")
        try:
            # First try with webdriver-manager
            print("Attempting to use webdriver-manager...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ Chrome WebDriver initialized successfully")
        except Exception as e:
            print(f"⚠️ webdriver-manager approach failed: {str(e)}")
            print("Falling back to system ChromeDriver...")
            try:
                driver = webdriver.Chrome(options=chrome_options)
                print("✅ Chrome WebDriver (system) initialized successfully")
            except Exception as e2:
                print(f"❌ Both WebDriver initialization methods failed")
                print(f"First error: {str(e)}")
                print(f"Second error: {str(e2)}")
                print("\nTroubleshooting steps:")
                print("1. Make sure Google Chrome is installed")
                print("2. Try running: pip install --upgrade webdriver-manager")
                print("3. Make sure Chrome and ChromeDriver versions are compatible")
                return
        
        # Test page load
        print("\n5. Testing page load...")
        try:
            test_url = "https://www.google.com"
            print(f"Loading {test_url}...")
            driver.get(test_url)
            print(f"✅ Page loaded successfully")
            print(f"Page title: {driver.title}")
        except Exception as e:
            print(f"❌ Page load failed: {str(e)}")
        
        # Clean up
        print("\n6. Cleaning up...")
        try:
            driver.quit()
            print("✅ WebDriver closed successfully")
        except:
            print("⚠️ Could not close WebDriver properly")
        
        print("\n=== Quick Test Completed ===")
        
    except Exception as e:
        print(f"\n❌ Error during quick test: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting steps:")
        print("1. Make sure all required packages are installed:")
        print("   pip install selenium webdriver-manager")
        print("2. Make sure Google Chrome is installed")
        print("3. Check if Chrome and ChromeDriver versions are compatible")

if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        run_test_scraper()
    elif "--quick" in sys.argv:
        quick_test()
    else:
        import uvicorn
        port = int(os.environ.get("PORT", 8089))
        uvicorn.run(app, host="0.0.0.0", port=port)
