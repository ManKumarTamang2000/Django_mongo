@echo off
echo Adding files...
git add .

echo Committing...
git commit -m "updated"

echo Pushing to GitHub...
git push origin main

echo DONE 
pause
