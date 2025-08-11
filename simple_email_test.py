#!/usr/bin/env python3
"""
Simple email test - modify the credentials below and run
"""
import os
import requests

# MODIFY THESE CREDENTIALS FOR TESTING
SENDER_EMAIL = "your-email@gmail.com"  # Replace with your Gmail
SENDER_PASSWORD = "your-app-password"   # Replace with your Gmail app password
TEST_EMAIL = "recipient@example.com"    # Replace with email to receive test

def test_email():
    """Test email functionality with hardcoded credentials"""
    
    # Set environment variables
    os.environ["SENDER_EMAIL"] = SENDER_EMAIL
    os.environ["SENDER_PASSWORD"] = SENDER_PASSWORD
    os.environ["SMTP_SERVER"] = "smtp.gmail.com"
    os.environ["SMTP_PORT"] = "587"
    
    print("Testing email functionality...")
    print(f"Sender: {SENDER_EMAIL}")
    print(f"Recipient: {TEST_EMAIL}")
    
    # Test filter request with email
    filter_data = {
        "city": "all",
        "start_date": "2025-01-01", 
        "end_date": "2025-12-31",
        "email": TEST_EMAIL
    }
    
    try:
        response = requests.post("http://localhost:8090/filter", data=filter_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"SUCCESS: Filter completed")
            print(f"Results found: {result.get('count', 0)}")
            print(f"Email sent: {result.get('email_sent', False)}")
            print(f"Message: {result.get('email_message', 'No message')}")
            
            if result.get('email_sent'):
                print(f"EMAIL SENT! Check {TEST_EMAIL} for CSV attachment")
            else:
                print("Email not sent - check credentials and configuration")
                
        else:
            print(f"ERROR: Request failed with status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    if SENDER_EMAIL == "your-email@gmail.com":
        print("ERROR: Please modify the credentials in this script first!")
        print("Update SENDER_EMAIL, SENDER_PASSWORD, and TEST_EMAIL")
    else:
        test_email()
