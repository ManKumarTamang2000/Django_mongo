@echo off
echo Adding files...
git add .

echo Committing...
git commit -m "auto update"

echo Pushing to GitHub...
git push origin main

echo DONE 
pause
