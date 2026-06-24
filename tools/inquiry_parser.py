import json
from groq import Groq

SYSTEM_PROMPT = """You are a real estate intake specialist.
Parse the buyers message and extract structured requirements.

Respond with ONLY valid JSON, no explanation:

{
  "budget_min": number or null,
  "budget_max": number or null,
  "bedrooms_min": number or null,
  "bedrooms_max": number or null,
  "neighbourhood": [list of strings],
  "property_type": [list of strings],
  "must_haves": [list of strings],
  "nice_to_haves": [list of strings],
  "timeline": "urgent" or "within 3 months" or "flexible" or "unknown",
  "buyer_profile": "relocating" or "investor" or "first time" or "upgrading" or "unknown,
  "lead_quality": number from 1 to 5,
  "lead_quality_reason": "one sentence",
  "flags": [list of concerns like "anonymous", "no_phone", "vague_budget"]
}"""

def parse_inquiry(client: Groq, buyer_name: str, message: str) -> dict:
  if not message or message.strip() == "":
    return {
      "budget_min": None,
      "budget_max": None,
      "bedrooms_min": None,
      "bedrooms_max": None,
      "neighbourhood": [],
      "property_type": [],
      "must_haves": [],
      "nice_to_haves": [],
      "timeline": "unknown",
      "buyer_profile": "unknown",
      "lead_quality": 1,
      "lead_quality_reason": "no message provided",
      "flags": ["no_message"]
    }
    
  user_prompt=f"""Buyer name: {buyer_name}
                Message: {message} 

                Parse this into the required JSON format."""

  response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
      {"role": "system", "content": SYSTEM_PROMPT},
      {"role": "user", "content": user_prompt}
    ],
    temperature=0.1,
    max_tokens=800
  )
  
  raw = response.choices[0].message.content.strip()
  
  if raw.startswith("```"):
    raw = raw.split("```")[1]
    if raw.startswith("json"):
      raw = raw[4:]
      
  parsed = json.loads(raw)
  return parsed