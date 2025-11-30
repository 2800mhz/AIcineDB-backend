@echo off
echo 🎬 Vimeo Batch Analysis Starting... 

echo [1/5] Analyzing vimeo. com/1012529319
curl -X POST "http://localhost:8000/api/analyze" -H "Content-Type: application/json" -d "{\"url\": \"https://vimeo. com/1012529319\", \"priority\": 5}"
echo. 

echo [2/5] Analyzing vimeo.com/1004202323
curl -X POST "http://localhost:8000/api/analyze" -H "Content-Type: application/json" -d "{\"url\": \"https://vimeo.com/1004202323\", \"priority\": 5}"
echo. 

echo [3/5] Analyzing vimeo.com/1119004215
curl -X POST "http://localhost:8000/api/analyze" -H "Content-Type: application/json" -d "{\"url\": \"https://vimeo. com/1119004215\", \"priority\": 5}"
echo.

echo [4/5] Analyzing vimeo.com/845983169
curl -X POST "http://localhost:8000/api/analyze" -H "Content-Type: application/json" -d "{\"url\": \"https://vimeo.com/845983169\", \"priority\": 5}"
echo. 

echo [5/5] Analyzing vimeo.com/994780900
curl -X POST "http://localhost:8000/api/analyze" -H "Content-Type: application/json" -d "{\"url\": \"https://vimeo. com/994780900\", \"priority\": 5}"
echo.

echo ✅ All jobs submitted!  Check progress at http://localhost:8000/api/jobs
pause