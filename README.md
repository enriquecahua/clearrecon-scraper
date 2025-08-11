# ClearRecon California Foreclosure Listings Scraper

A production-ready web application that scrapes California foreclosure listings from ClearRecon and provides filtering, CSV export, and email functionality.

<!-- Deployment trigger: Azure deployment with Docker Hub authentication -->
<!-- Docker Hub repository: enriquecahua/clearrecon-foreclosure-app -->

## 🚀 Features

- **Selenium-based scraping** - Bypasses JavaScript disclaimer and extracts all listings
- **Unique data extraction** - Deduplicates by TS Number to ensure 654+ unique listings
- **Web interface** - Professional UI with dynamic filtering
- **Email integration** - Send filtered results as CSV attachments
- **Data persistence** - Timestamped CSV files for reuse
- **Azure deployment ready** - Docker configuration included

## Local Setup

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or: source venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Run the application**:
   ```bash
   python main.py
   # or: uvicorn main:app --reload
   ```

4. **Open browser**: http://localhost:8000

## Usage

1. Enter optional email address
2. Specify city (default: Sacramento)
3. Set date range (default: today to +30 days)
4. Click "Search Listings"
5. Results appear dynamically below the form

## Azure Deployment

### Option 1: Azure Container Instances

```bash
# Build and push to Azure Container Registry
az acr build --registry myregistry --image clearrecon-scraper .

# Deploy to Container Instances
az container create \
  --resource-group mygroup \
  --name clearrecon-scraper \
  --image myregistry.azurecr.io/clearrecon-scraper \
  --ports 8000 \
  --environment-variables PORT=8000
```

### Option 2: Azure Web App for Containers

```bash
# Create App Service Plan
az appservice plan create --name myplan --resource-group mygroup --sku B1 --is-linux

# Create Web App
az webapp create --resource-group mygroup --plan myplan --name clearrecon-scraper --deployment-container-image-name myregistry.azurecr.io/clearrecon-scraper
```

## Architecture

- **FastAPI**: Web framework with automatic API documentation
- **Playwright**: Headless browser for robust web scraping
- **Jinja2**: Template engine for HTML rendering
- **Docker**: Containerization with pre-installed Chromium

## API Endpoints

- `GET /`: Main application interface
- `POST /scrape`: JSON API for scraping (used by AJAX)
- `GET /health`: Health check endpoint

## Scraping Strategy

1. Navigate to ClearRecon CA listings page
2. Auto-detect and accept any disclaimer/terms
3. Navigate to actual listings if needed
4. Select maximum results per page
5. Extract listings from tables or other structures
6. Filter results by city and date range
7. Return structured JSON data

## Error Handling

- Graceful fallbacks for different page structures
- Timeout handling for slow-loading pages
- User-friendly error messages in the UI
- Detailed logging for debugging

## Development

The scraper uses multiple strategies to handle:
- Different disclaimer acceptance patterns
- Various navigation structures
- Multiple result display formats
- Dynamic content loading
- Rate limiting and timeouts

## Support

For issues or questions, check the browser console for client-side errors and server logs for backend issues.
