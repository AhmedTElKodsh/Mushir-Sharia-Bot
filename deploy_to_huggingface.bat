@echo off
REM Deploy Mushir Sharia Bot to Hugging Face Space
REM Usage: deploy_to_huggingface.bat

echo ============================================================
echo Deploying Mushir Sharia Bot to Hugging Face Space
echo ============================================================
echo.

REM Check if HF_TOKEN is set
if "%HF_TOKEN%"=="" (
    echo ERROR: HF_TOKEN environment variable is not set
    echo.
    echo Please set your Hugging Face token:
    echo   set HF_TOKEN=your_token_here
    echo.
    echo Or get it from: https://huggingface.co/settings/tokens
    exit /b 1
)

echo Step 1: Checking git status...
git status

echo.
echo Step 2: Adding HuggingFace remote (if not exists)...
git remote add huggingface https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot 2>nul
if errorlevel 1 (
    echo Remote already exists, updating URL...
    git remote set-url huggingface https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot
)

echo.
echo Step 3: Verifying remotes...
git remote -v

echo.
echo Step 4: Pushing to HuggingFace Space...
echo Using token authentication...
git push https://AElKodsh:%HF_TOKEN%@huggingface.co/spaces/AElKodsh/mushir-sharia-bot main --force

if errorlevel 1 (
    echo.
    echo ERROR: Push to HuggingFace failed
    echo.
    echo Troubleshooting:
    echo 1. Verify your HF_TOKEN is valid
    echo 2. Check you have write access to the Space
    echo 3. Try: git push huggingface main --force
    exit /b 1
)

echo.
echo ============================================================
echo ✅ Deployment successful!
echo ============================================================
echo.
echo Your Space is updating at:
echo https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot
echo.
echo Check build logs:
echo https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot?logs=container
echo.
echo Note: It may take 2-5 minutes for the Space to rebuild and restart.
echo ============================================================
