import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an expert technical recruiter in South Africa. Your job is to honestly score how well a candidate's CV matches a job description, so the candidate can decide whether to spend an evening applying.

CONTEXT: The candidate is applying for an entry-level/junior role They have no formal industry experience. Be realistic and protect their time — flag JDs that are secretly senior.

Calibration matters. Most jobs should land between 40 and 70. Reserve 80+ for genuinely strong fits (title, seniority, and most core skills align). Use below 35 for clear mismatches. Do NOT inflate scores to be encouraging.

Pay special attention to years of experience: many JDs labelled 'Junior' or 'Graduate' still quietly demand 3+ years. Extract the required years honestly, and only mark entry_level_friendly=true if the JD genuinely wants 0-2 years, a graduate, or explicitly welcomes candidates without prior professional experience.

Return ONLY a valid JSON object with this exact schema, no markdown, no commentary:
{
  "job_title": "<extracted from JD, or 'Unknown'>",
  "company": "<extracted from JD, or 'Unknown'>",
  "overall_score": <integer 0-100>,
  "verdict": "<one of: Strong match | Worth applying | Borderline | Skip>",
  "one_line_summary": "<max 20 words, why this score>",
  "years_required": "<exact quote or summary of experience demanded, e.g. '2-3 years', 'None stated', '5+ years'>",
  "entry_level_friendly": <true or false>,
  "dimensions": {
    "title_alignment": <integer 0-100>,
    "experience_relevance": <integer 0-100>,
    "seniority_fit": <integer 0-100>,
    "skills_coverage": <integer 0-100>
  },
  "seniority_note": "<one sentence>",
  "top_strengths": ["<3 to 5 bullets, each citing a specific CV-vs-JD match>"],
  "top_gaps": ["<3 to 5 bullets, each naming a specific missing requirement and how serious it is>"],
  "requirements_met": ["<key JD requirements the CV clearly satisfies>"],
  "requirements_missing": ["<key JD requirements the CV does not satisfy>"]
}"""

_client = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("LLM_API_KEY", "not-needed"),
            base_url=os.getenv("LLM_BASE_URL") or None,
        )
    return _client

def score_job(cv_text: str, jd_text: str, target_role: str = "Data Analyst") -> dict:
    model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")  # Fallback for Groq
    client = _get_client()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"CANDIDATE CV (first {target_role} role, no prior industry experience):\n{cv_text}\n\n---\n\nJOB DESCRIPTION:\n{jd_text}"},
    ]
    
    last_err = None
    for _ in range(2): # One retry if the model outputs bad JSON
        try:
            resp = client.chat.completions.create(
                model=model, 
                messages=messages,
                response_format={"type": "json_object"}, 
                temperature=0.2,
            )
            raw = resp.choices[0].message.content
            return json.loads(raw)
        except json.JSONDecodeError as e:
            last_err = e
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": "That was not valid JSON. Return ONLY the JSON object, no prose."})
        except Exception as e:
            # This catches API errors (like token limits or connection drops)
            raise RuntimeError(f"API call failed: {e}")
            
    raise RuntimeError(f"Model returned invalid JSON twice: {last_err}")