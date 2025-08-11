# Azure Deployment Guide - ClearRecon Scraper

This guide provides multiple methods to deploy your ClearRecon scraper to Azure.

## 🚀 Method 1: Azure App Service with GitHub (Recommended)

### Prerequisites
- Azure account with active subscription
- Azure CLI installed or use Azure Cloud Shell

### Step 1: Run the Deployment Script

Execute the PowerShell script I created:
```powershell
.\deploy-azure.ps1
```

### Step 2: Configure GitHub Deployment in Azure Portal

1. **Go to Azure Portal** → App Services → `clearrecon-scraper`
2. **Deployment Center** → Source: GitHub
3. **Authorize GitHub** and select:
   - Organization: `enriquecahua`
   - Repository: `clearrecon-scraper`
   - Branch: `main`
4. **Build Provider**: GitHub Actions
5. **Save** the configuration

### Step 3: Set Environment Variables

In Azure Portal → App Services → `clearrecon-scraper` → Configuration:

```
SENDER_EMAIL = clearreconinfo@gmail.com
SENDER_PASSWORD = qzxonqftvoqlfepe
SMTP_SERVER = smtp.gmail.com
SMTP_PORT = 587
PORT = 8000
WEBSITES_PORT = 8000
```

### Step 4: Configure Container Settings

1. **Container Settings** → Single Container
2. **Image Source**: Docker Hub or other registry
3. **Image**: `python:3.11-slim` (will be overridden by Dockerfile)
4. **Startup Command**: Leave empty (uses Dockerfile CMD)

---

## 🐳 Method 2: Azure Container Instances

### Step 1: Build and Push to Azure Container Registry

```bash
# Create Azure Container Registry
az acr create --resource-group clearrecon-rg --name clearreconacr --sku Basic

# Build and push image
az acr build --registry clearreconacr --image clearrecon-scraper .
```

### Step 2: Deploy to Container Instances

```bash
# Deploy container
az container create \
  --resource-group clearrecon-rg \
  --name clearrecon-scraper \
  --image clearreconacr.azurecr.io/clearrecon-scraper \
  --ports 8000 \
  --environment-variables \
    SENDER_EMAIL=clearreconinfo@gmail.com \
    SENDER_PASSWORD=qzxonqftvoqlfepe \
    SMTP_SERVER=smtp.gmail.com \
    SMTP_PORT=587 \
    PORT=8000
```

---

## 🌐 Method 3: Manual Azure Portal Deployment

### Step 1: Create Resources in Azure Portal

1. **Create Resource Group**: `clearrecon-rg`
2. **Create App Service Plan**: Linux, B1 Basic
3. **Create Web App**: Container-based

### Step 2: Configure Deployment

1. **Deployment Center** → GitHub
2. Connect to your repository: `https://github.com/enriquecahua/clearrecon-scraper`
3. **Branch**: `main`
4. **Build Provider**: GitHub Actions

### Step 3: Environment Variables

Add these in Configuration → Application Settings:
- `SENDER_EMAIL`: `clearreconinfo@gmail.com`
- `SENDER_PASSWORD`: `qzxonqftvoqlfepe`
- `SMTP_SERVER`: `smtp.gmail.com`
- `SMTP_PORT`: `587`
- `PORT`: `8000`
- `WEBSITES_PORT`: `8000`

---

## 🔧 Troubleshooting

### Common Issues

1. **Container won't start**
   - Check Application Logs in Azure Portal
   - Verify environment variables are set
   - Ensure PORT and WEBSITES_PORT match

2. **Email not working**
   - Verify Gmail app password is correct
   - Check SMTP settings in environment variables
   - Test email functionality locally first

3. **Scraping fails**
   - Chrome/Selenium may need additional configuration in Azure
   - Check container logs for ChromeDriver errors
   - Verify the Dockerfile Chrome installation

### Monitoring

1. **Application Insights**: Enable for monitoring
2. **Log Stream**: View real-time logs
3. **Metrics**: Monitor CPU, memory usage
4. **Alerts**: Set up alerts for failures

---

## 📊 Expected Costs

- **App Service B1**: ~$13/month
- **Container Instances**: ~$10-20/month (depending on usage)
- **Storage**: Minimal cost for logs

---

## 🎯 Post-Deployment Checklist

- [ ] App starts successfully
- [ ] Web interface loads at your Azure URL
- [ ] Scraping functionality works
- [ ] Email sending works with test filter
- [ ] CSV download works
- [ ] All endpoints respond correctly

---

## 🔗 Useful Azure CLI Commands

```bash
# View app logs
az webapp log tail --name clearrecon-scraper --resource-group clearrecon-rg

# Restart app
az webapp restart --name clearrecon-scraper --resource-group clearrecon-rg

# View app settings
az webapp config appsettings list --name clearrecon-scraper --resource-group clearrecon-rg

# Scale app
az appservice plan update --name clearrecon-scraper-plan --resource-group clearrecon-rg --sku S1
```

---

## 🎉 Success!

Once deployed, your ClearRecon scraper will be available at:
`https://clearrecon-scraper.azurewebsites.net`

The application will have all the same functionality as your local version:
- Selenium-based scraping of 654+ foreclosure listings
- Web interface with city/date filtering
- Email functionality with CSV attachments
- Automatic daily data refresh at 2 AM
