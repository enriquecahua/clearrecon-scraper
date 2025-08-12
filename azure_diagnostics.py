#!/usr/bin/env python3
"""
Azure Diagnostics for ClearRecon Scraper
Tests to identify why CSV generation is failing in Azure environment
"""

import os
import sys
import csv
import tempfile
import glob
from datetime import datetime
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

class AzureDiagnostics:
    def __init__(self):
        self.results = []
        self.test_count = 0
        self.passed_count = 0
        
    def log_test(self, test_name, status, message="", details=""):
        """Log test result"""
        self.test_count += 1
        if status:
            self.passed_count += 1
            status_str = "✅ PASS"
        else:
            status_str = "❌ FAIL"
            
        result = f"{status_str} - {test_name}: {message}"
        if details:
            result += f"\n    Details: {details}"
            
        print(result)
        self.results.append({
            'test': test_name,
            'status': status,
            'message': message,
            'details': details
        })
        
    def test_environment_info(self):
        """Test 1: Environment Information"""
        try:
            cwd = os.getcwd()
            python_version = sys.version
            platform = sys.platform
            
            # Check if running in Azure
            is_azure = any([
                os.environ.get('WEBSITE_SITE_NAME'),
                os.environ.get('APPSETTING_WEBSITE_SITE_NAME'),
                os.environ.get('WEBSITE_INSTANCE_ID')
            ])
            
            details = f"CWD: {cwd}, Python: {python_version[:20]}, Platform: {platform}, Azure: {is_azure}"
            self.log_test("Environment Info", True, "Environment detected", details)
            
        except Exception as e:
            self.log_test("Environment Info", False, f"Error: {e}")
            
    def test_file_permissions(self):
        """Test 2: File System Permissions"""
        try:
            # Test current directory write permissions
            test_file = "test_write_permissions.txt"
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            
            self.log_test("Current Dir Write", True, "Can write to current directory")
            
        except Exception as e:
            self.log_test("Current Dir Write", False, f"Cannot write to current dir: {e}")
            
        try:
            # Test csv_data directory creation and write
            csv_dir = "csv_data"
            os.makedirs(csv_dir, exist_ok=True)
            
            test_csv = os.path.join(csv_dir, "test_permissions.csv")
            with open(test_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['test', 'data'])
            
            # Verify file exists and has content
            if os.path.exists(test_csv) and os.path.getsize(test_csv) > 0:
                os.remove(test_csv)
                self.log_test("CSV Dir Write", True, f"Can write CSV files to {csv_dir}")
            else:
                self.log_test("CSV Dir Write", False, "CSV file not created or empty")
                
        except Exception as e:
            self.log_test("CSV Dir Write", False, f"Cannot write to csv_data: {e}")
            
    def test_temp_directory(self):
        """Test 3: Temporary Directory Access"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
                temp_file.write("test,data\n1,2\n")
                temp_filename = temp_file.name
                
            # Verify temp file
            if os.path.exists(temp_filename) and os.path.getsize(temp_filename) > 0:
                os.unlink(temp_filename)
                self.log_test("Temp File Access", True, "Can create temporary files")
            else:
                self.log_test("Temp File Access", False, "Temp file not accessible")
                
        except Exception as e:
            self.log_test("Temp File Access", False, f"Temp file error: {e}")
            
    def test_chrome_installation(self):
        """Test 4: Chrome Browser Installation"""
        try:
            # Check if Chrome is installed
            chrome_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium-browser',
                '/opt/google/chrome/chrome'
            ]
            
            chrome_found = False
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_found = True
                    self.log_test("Chrome Installation", True, f"Chrome found at {path}")
                    break
                    
            if not chrome_found:
                self.log_test("Chrome Installation", False, "Chrome not found in standard paths")
                
        except Exception as e:
            self.log_test("Chrome Installation", False, f"Chrome check error: {e}")
            
    def test_chromedriver_setup(self):
        """Test 5: ChromeDriver Setup"""
        try:
            # Test ChromeDriver installation
            driver_path = ChromeDriverManager().install()
            if os.path.exists(driver_path):
                self.log_test("ChromeDriver Setup", True, f"ChromeDriver installed at {driver_path}")
            else:
                self.log_test("ChromeDriver Setup", False, "ChromeDriver not found")
                
        except Exception as e:
            self.log_test("ChromeDriver Setup", False, f"ChromeDriver error: {e}")
            
    def test_selenium_basic(self):
        """Test 6: Basic Selenium Functionality"""
        driver = None
        try:
            # Configure Chrome for Azure
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Initialize WebDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # Test basic navigation
            driver.get("https://www.google.com")
            title = driver.title
            
            if "Google" in title:
                self.log_test("Selenium Basic", True, f"Successfully loaded Google: {title}")
            else:
                self.log_test("Selenium Basic", False, f"Unexpected title: {title}")
                
        except Exception as e:
            self.log_test("Selenium Basic", False, f"Selenium error: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                    
    def test_clearrecon_access(self):
        """Test 7: ClearRecon Website Access"""
        driver = None
        try:
            # Configure Chrome for Azure
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Initialize WebDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # Test ClearRecon access
            driver.get("https://clearrecon-ca.com/california-listings/")
            time.sleep(5)  # Wait for page load
            
            page_source = driver.page_source
            title = driver.title
            
            if "clearrecon" in title.lower() or "california" in title.lower():
                self.log_test("ClearRecon Access", True, f"Successfully accessed ClearRecon: {title}")
                
                # Check for disclaimer
                if "agree" in page_source.lower() or "disclaimer" in page_source.lower():
                    self.log_test("Disclaimer Detection", True, "Disclaimer detected on page")
                else:
                    self.log_test("Disclaimer Detection", False, "No disclaimer found")
                    
            else:
                self.log_test("ClearRecon Access", False, f"Unexpected page: {title}")
                
        except Exception as e:
            self.log_test("ClearRecon Access", False, f"ClearRecon access error: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                    
    def test_network_connectivity(self):
        """Test 8: Network Connectivity"""
        try:
            # Test basic HTTP request
            response = requests.get("https://www.google.com", timeout=10)
            if response.status_code == 200:
                self.log_test("Network Basic", True, f"HTTP request successful: {response.status_code}")
            else:
                self.log_test("Network Basic", False, f"HTTP request failed: {response.status_code}")
                
            # Test ClearRecon connectivity
            response = requests.get("https://clearrecon-ca.com/california-listings/", timeout=15)
            if response.status_code == 200:
                self.log_test("ClearRecon Network", True, f"ClearRecon accessible: {response.status_code}")
            else:
                self.log_test("ClearRecon Network", False, f"ClearRecon not accessible: {response.status_code}")
                
        except Exception as e:
            self.log_test("Network Connectivity", False, f"Network error: {e}")
            
    def test_csv_creation_simulation(self):
        """Test 9: CSV Creation Simulation"""
        try:
            # Simulate the exact CSV creation process
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_dir = "csv_data"
            os.makedirs(csv_dir, exist_ok=True)
            
            csv_path = os.path.join(csv_dir, f"test_clearrecon_listings_{timestamp}.csv")
            
            # Create test data similar to scraper output
            test_data = [
                {
                    'ts_number': 'TEST-123-CA',
                    'address': '123 Test St',
                    'city': 'Test City',
                    'date': '01/01/2024',
                    'price': '$100,000'
                },
                {
                    'ts_number': 'TEST-456-CA',
                    'address': '456 Sample Ave',
                    'city': 'Sample City',
                    'date': '01/02/2024',
                    'price': '$200,000'
                }
            ]
            
            # Write CSV using same method as scraper
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                if test_data:
                    fieldnames = test_data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                    writer.writeheader()
                    writer.writerows(test_data)
            
            # Verify file creation
            if os.path.exists(csv_path):
                file_size = os.path.getsize(csv_path)
                if file_size > 0:
                    self.log_test("CSV Creation Sim", True, f"CSV created successfully: {file_size} bytes")
                    # Clean up
                    os.remove(csv_path)
                else:
                    self.log_test("CSV Creation Sim", False, "CSV file created but empty")
            else:
                self.log_test("CSV Creation Sim", False, "CSV file not created")
                
        except Exception as e:
            self.log_test("CSV Creation Sim", False, f"CSV creation error: {e}")
            
    def run_all_tests(self):
        """Run all diagnostic tests"""
        print("🔍 Starting Azure Diagnostics for ClearRecon Scraper")
        print("=" * 60)
        
        # Run all tests
        self.test_environment_info()
        self.test_file_permissions()
        self.test_temp_directory()
        self.test_chrome_installation()
        self.test_chromedriver_setup()
        self.test_selenium_basic()
        self.test_clearrecon_access()
        self.test_network_connectivity()
        self.test_csv_creation_simulation()
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.passed_count}/{self.test_count} tests passed")
        
        if self.passed_count == self.test_count:
            print("🎉 All tests passed! The issue may be in the scraping logic itself.")
        else:
            print("⚠️  Some tests failed. These may be the root cause of CSV generation issues.")
            
        return self.results

def main():
    """Main function to run diagnostics"""
    diagnostics = AzureDiagnostics()
    results = diagnostics.run_all_tests()
    
    # Save results to file for later analysis
    try:
        with open('azure_diagnostics_results.txt', 'w') as f:
            f.write(f"Azure Diagnostics Results - {datetime.now()}\n")
            f.write("=" * 60 + "\n")
            for result in results:
                status = "PASS" if result['status'] else "FAIL"
                f.write(f"{status} - {result['test']}: {result['message']}\n")
                if result['details']:
                    f.write(f"    Details: {result['details']}\n")
        print(f"\n📝 Results saved to azure_diagnostics_results.txt")
    except Exception as e:
        print(f"⚠️  Could not save results file: {e}")

if __name__ == "__main__":
    main()
