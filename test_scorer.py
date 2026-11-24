import json
from scorer import score_job

# A dummy CV (we will use your real one in the app)
cv = "BSc Statistics, 2024. Skills: Python, pandas, SQL, Power BI. Projects: sales dashboard in Power BI; data cleaning in pandas; SQL queries on a Kaggle dataset."

# A dummy South African Junior JD
jd = """Junior Data Analyst — Sandton
Requirements: 0-2 years experience. SQL, Excel, Power BI. Python advantageous.
Build dashboards, clean data, support reporting team."""

print("Sending request to Groq... (this might take 2-5 seconds)")
result = score_job(cv, jd)

print("\n--- SCORING RESULT ---")
print(json.dumps(result, indent=2))