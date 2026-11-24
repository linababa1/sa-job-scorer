import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Check if the key is loaded
if not os.getenv("LLM_API_KEY") or "your-" in os.getenv("LLM_API_KEY"):
    print("ERROR: You need to put a real API key in the .env file!")
    exit()

client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"), 
    base_url=os.getenv("LLM_BASE_URL") or None
)

print("Sending request to the LLM...")
try:
    r = client.chat.completions.create(
        model=os.getenv("LLM_MODEL"),
        messages=[{"role": "user", "content": 'Reply with only this JSON: {"ok": true}'}],
        response_format={"type": "json_object"},
    )
    print("SUCCESS! The LLM replied:")
    print(r.choices[0].message.content)
except Exception as e:
    print(f"\nFAILED. Error message:\n{e}")