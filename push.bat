@echo off
echo Adding files...
git add .

echo Committing...
git commit -m "Integrated embeddings and updated chatbot settings and migrations"

echo Pushing to GitHub...
git push origin main

echo DONE
pause
