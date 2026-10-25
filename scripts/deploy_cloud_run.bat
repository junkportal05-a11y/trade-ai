@echo off
REM ==============================================================================
REM APEXTRADE AI — One-Click Google Cloud Run Deployment (Windows Batch)
REM ==============================================================================
REM Prerequisites:
REM   1. Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install
REM   2. Run: gcloud auth login && gcloud auth application-default login
REM   3. Create a GCP project: gcloud projects create YOUR_PROJECT_ID
REM   4. Enable billing on the project
REM   5. Set project: gcloud config set project YOUR_PROJECT_ID
REM ==============================================================================

echo.
echo ==============================================================================
echo APEXTRADE AI — Google Cloud Run Deployment
echo ==============================================================================
echo.

REM Check if gcloud is available
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: gcloud CLI not found. Please install Google Cloud SDK first.
    echo Visit: https://cloud.google.com/sdk/docs/install
    exit /b 1
)

REM Get project ID from config or prompt
for /f "tokens=*" %%a in ('gcloud config get-value project 2^>nul') do set PROJECT_ID=%%a
if "%PROJECT_ID%"=="" (
    set /p PROJECT_ID="Enter your GCP Project ID: "
    if "%PROJECT_ID%"=="" (
        echo ERROR: Project ID is required.
        exit /b 1
    )
    gcloud config set project %PROJECT_ID%
)

echo.
echo Deploying to project: %PROJECT_ID%
echo Region: us-central1
echo Service: apextrade-backend
echo.

REM Deploy to Cloud Run (Free Tier optimized)
gcloud run deploy apextrade-backend ^
  --source . ^
  --platform managed ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --memory 512Mi ^
  --cpu 1 ^
  --min-instances 0 ^
  --max-instances 2 ^
  --set-env-vars ENVIRONMENT=production ^
  --timeout 300 ^
  --concurrency 80

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Deployment failed. Check the output above for details.
    exit /b 1
)

echo.
echo ==============================================================================
echo DEPLOYMENT SUCCESSFUL!
echo ==============================================================================
echo.
echo Your backend is now live at:
for /f "tokens=*" %%u in ('gcloud run services describe apextrade-backend --region=us-central1 --format="value(status.url)" 2^>nul') do set SERVICE_URL=%%u
if not "%SERVICE_URL%"=="" (
    echo   %SERVICE_URL%
) else (
    echo   Run: gcloud run services describe apextrade-backend --region=us-central1 --format="value(status.url)"
)
echo.
echo Next steps:
echo 1. Set required environment variables in Cloud Run console:
echo    - DATABASE_URL (Supabase/Neon PostgreSQL)
echo    - GEMINI_API_KEY (Google AI Studio)
echo    - REDIS_URL or UPSTASH_REDIS_URL (Upstash)
echo    - SENTRY_DSN (optional, Sentry.io)
echo    - JWT_SECRET, FERNET_KEYS, ADMIN_KEY (generate secure values)
echo 2. Update frontend .env with VITE_API_URL=%SERVICE_URL%
echo 3. Deploy frontend to Vercel/Netlify
echo.
pause