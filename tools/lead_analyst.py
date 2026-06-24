import json
from groq import Groq

SYSTEM_PROMPT = """You are a senior real estate agent coach.
Given a buyer lead and matched_listings, give actionable advice to the realtor.

Be direct and practical. Realtor in busy and reads this on their phone.

Respond with ONLY valid JSON, no explanation:

{
  "urgency": "hot" or "warm" or "cold",
  "urgency_reason": "one sentence why",
  "realtor_talking_points": [
    "2-4 specific things to mention or ask in the first call"
  ],
  "concerns_before_outreach": [
    "things to be aware of before calling"
  ],
  "suggested_next_action": "one clear specific action",
  "outreach_channel": "call" or "email" or "text",
  "outreach_reason": "why this channel fits this buyer",
  "pre_qual_questions": [
    "1-3 questions to ask to qualify this lead"
  ]
}"""

def analyse_lead(
    client: Groq,
    buyer_name: str,
    buyer_email: str,
    buyer_phone: str,
    channel: str,
    received_at: str,
    original_message: str,
    requirements: dict,
    matches: dict
) -> dict:

    match_summary = ""
    if matches.get("matches"):
        top3 = matches["matches"][:3]
        match_summary = "\n".join(
            f"- {m.get('address')} | ${m.get('price', 0):,.0f} | "
            f"Score: {m.get('match_score')}/10 | {m.get('why_it_fits', '')[:80]}"
            for m in top3
        )
    else:
        match_summary = "No strong matches found in current inventory."

    flags = requirements.get("flags", [])
    is_anonymous = (
        "anonymous" in flags
        or not buyer_name
        or "anonymous" in buyer_name.lower()
    )
    has_phone = bool(buyer_phone and buyer_phone.strip())

    user_prompt = f"""Buyer: {buyer_name} ({'anonymous' if is_anonymous else 'identified'})
Contact: {'Phone available' if has_phone else 'NO PHONE - email only'} | {buyer_email or 'no email'}
Channel: {channel} | Received: {received_at}

What they wrote:
"{original_message[:400]}"

Their needs:
- Budget: ${requirements.get('budget_min') or 0:,.0f} - ${requirements.get('budget_max') or 0:,.0f}
- Beds: {requirements.get('bedrooms_min', '?')}+ | Baths: {requirements.get('bathrooms_min', '?')}+
- Neighborhoods: {', '.join(requirements.get('neighborhoods', [])) or 'flexible'}
- Must-haves: {', '.join(requirements.get('must_haves', [])) or 'none'}
- Timeline: {requirements.get('timeline', 'unknown')}
- Buyer type: {requirements.get('buyer_profile', 'unknown')}
- Lead quality score: {requirements.get('lead_quality', '?')}/5
- Flags: {', '.join(flags) if flags else 'none'}

Top matched properties:
{match_summary}

Inventory note: {matches.get('matching_note', '')}

Assess this lead and advise the realtor."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=800
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    # ── Yeh fallback add karo ──────────────────────────────────
    try:
        result = json.loads(raw)
        return result
    except json.JSONDecodeError:
        # JSON parse fail hua toh safe default return karo
        return {
            "urgency": "warm",
            "urgency_reason": "Could not parse analysis — review manually.",
            "realtor_talking_points": ["Review lead manually"],
            "concerns_before_outreach": ["Analysis parsing failed"],
            "suggested_next_action": "Review lead manually and follow up within 24 hours.",
            "outreach_channel": "email",
            "outreach_reason": "Default fallback.",
            "pre_qual_questions": ["What is your timeline?", "Are you pre-approved?"]
        }
  
  