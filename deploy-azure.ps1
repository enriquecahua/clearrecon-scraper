# Azure Deployment Script for ClearRecon Scraper
# Run this in PowerShell with Azure CLI installed

# Variables - CHANGE THESE VALUES
$RESOURCE_GROUP = "clearrecon-rg"
$APP_NAME = "clearrecon-scraper"
$LOCATION = "East US"
$SKU = "B1"  # Basic tier - sufficient for this app

Write-Host "🚀 Starting Azure deployment for ClearRecon Scraper..." -ForegroundColor Green

# Step 1: Login to Azure (if not already logged in)
Write-Host "📝 Logging into Azure..." -ForegroundColor Yellow
az login

# Step 2: Create Resource Group
Write-Host "📁 Creating resource group: $RESOURCE_GROUP" -ForegroundColor Yellow
az group create --name $RESOURCE_GROUP --location $LOCATION

# Step 3: Create App Service Plan
Write-Host "⚙️ Creating App Service Plan..." -ForegroundColor Yellow
az appservice plan create `
    --name "$APP_NAME-plan" `
    --resource-group $RESOURCE_GROUP `
    --sku $SKU `
    --is-linux

# Step 4: Create Web App with Container
Write-Host "🌐 Creating Web App..." -ForegroundColor Yellow
az webapp create `
    --resource-group $RESOURCE_GROUP `
    --plan "$APP_NAME-plan" `
    --name $APP_NAME `
    --deployment-container-image-name "mcr.microsoft.com/appsvc/staticsite:latest"

# Step 5: Configure GitHub deployment
Write-Host "🔗 Setting up GitHub deployment..." -ForegroundColor Yellow
Write-Host "⚠️ You'll need to configure GitHub deployment manually in the Azure portal" -ForegroundColor Red
Write-Host "Repository: https://github.com/enriquecahua/clearrecon-scraper" -ForegroundColor Cyan

# Step 6: Set environment variables
Write-Host "Setting environment variables..." -ForegroundColor Yellow
Write-Host "You need to set these environment variables in Azure portal:" -ForegroundColor Red
Write-Host "SENDER_EMAIL=clearreconinfo@gmail.com" -ForegroundColor Cyan
Write-Host "SENDER_PASSWORD=qzxonqftvoqlfepe" -ForegroundColor Cyan
Write-Host "SMTP_SERVER=smtp.gmail.com" -ForegroundColor Cyan
Write-Host "SMTP_PORT=587" -ForegroundColor Cyan
Write-Host "PORT=8000" -ForegroundColor Cyan

# Get the app URL
$APP_URL = az webapp show --resource-group $RESOURCE_GROUP --name $APP_NAME --query "defaultHostName" --output tsv
Write-Host "✅ Deployment script complete!" -ForegroundColor Green
Write-Host "🌐 Your app will be available at: https://$APP_URL" -ForegroundColor Green
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to Azure Portal > App Services > $APP_NAME" -ForegroundColor White
Write-Host "2. Configure GitHub deployment" -ForegroundColor White
Write-Host "3. Set environment variables" -ForegroundColor White
Write-Host "4. Test the deployment" -ForegroundColor White
