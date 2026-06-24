import json
import pandas as pd
from groq import Groq

_MLS_DF_CACHE = None

def load_mls(csv_path: str) -> pd.DataFrame:
  #csv ek bar load krenge baar baar nahi
  global _MLS_DF_CACHE
  if _MLS_DF_CACHE is not None:
    return _MLS_DF_CACHE
  
  df = pd.read_csv(csv_path)
  
  # Column names clean karo
  df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
  
  for col in ["price", "bedrooms", "bathrooms", "sqft", "year_built", "days_on_market"]:
    if col in df.columns:
      df[col] = pd.to_numeric(df[col], errors="coerce")
      
  for status_col in ["listing_status", "status"]:
    if status_col in df.columns:
      df = df[df[status_col].isin(["Active", "Pending"])].copy()
      break
    
  df = df.reset_index(drop=True)
  _MLS_DF_CACHE = df
  return df


def _hard_filter(df: pd.DataFrame, requirements: dict) -> pd.DataFrame:
  filtered = df.copy()
  
  budget_max = requirements.get("budget_max")
  budget_min = requirements.get("budget_min")
  bedrooms_min = requirements.get("bedrooms_min")
  bathrooms_min = requirements.get("bathrooms_min")
  neighborhoods = requirements.get("neighbourhood", [])
  
  #budget filter - 15% buffer diya hai kyunki buyers aksar thoda idhar udhar adjust kr lete hai
  if budget_max:
    filtered = filtered[filtered["price"] <= budget_max * 1.5]
  if budget_min:
    filtered = filtered[filtered["price"] >= budget_min * 0.85]
  #bedrooms - given toh hona hi chahiye
  if bedrooms_min:
    filtered = filtered[filtered["bedrooms"] >= bedrooms_min]
    
  #Bathrooms - 0.5 ka buffer
  if bathrooms_min:
    filtered = filtered[filtered["bathrooms"] >= bathrooms_min-1]
    
  #Neighbourhood filter - Assuming neighbourhood buyer ko exact chahiye
  if neighborhoods:
    pattern = "|".join(neighborhoods)
    for col in ["neighborhood", "neighbourhood", "city", "area"]:
      if col in filtered.columns:
        mask = filtered[col].str.contains(pattern, case=False, na=False)
        if mask.sum() > 0:
          filtered = filtered[mask]
          break
  
  return filtered

def _format_for_llm(df: pd.DataFrame) -> str:
    if "days_on_market" in df.columns:
        df = df.sort_values("days_on_market", na_position="last")

    df = df.head(12)    # ← if ke bahar
    lines = []

    for _, row in df.iterrows():
        listing_id = row.get("listing_id", row.get("mls_number", "N/A"))
        address    = row.get("address", "N/A")
        hood       = row.get("neighborhood", row.get("city", "N/A"))  # typo fix
        price      = row.get("price", 0)
        beds       = row.get("bedrooms", "?")
        baths      = row.get("bathrooms", "?")
        sqft       = row.get("sqft", "?")
        yr         = row.get("year_built", "?")
        ptype      = row.get("property_type", row.get("property_t", "?"))
        features   = str(row.get("features", row.get("description", "")))[:150]
        status     = row.get("listing_status", row.get("status", "?"))
        dom        = row.get("days_on_market", "?")

        lines.append(
            f"ID:{listing_id} | {address}, {hood} | ${price:,.0f} | "
            f"{beds}bd/{baths}ba | {sqft}sqft | Built {yr} | {ptype} | "  # beds fix
            f"{status} | {dom} days | Features: {features}"
        )

    return "\n".join(lines)    # ← loop ke bahar

RANK_PROMPT = """You are a real estate agent's assistant.
Pick the TOP 3-5 best matching listings and explain why each fits.

Respond only with valid JSON:

{
  "matches":[
    {
      "listing_id": "MLS-XXXX",
      "address": "full address",
      "neighborhood": "area name",
      "price": number,
      "bedrooms": number,
      "bathrooms": number,
      "sqft": number,
      "match_score": number from 1 to 10,
      "why_it_fits": "2-3 sentences",
      "caveats": "any concerns or null"
    }
  ],
  "matching_note": "1-2 sentences on overall inventory situation"
}"""

def match_listings(client: Groq, csv_path: str, requirements: dict, buyer_name: str) -> dict:
  df = load_mls(csv_path)
  
  #Pandas se filter karo
  filtered = _hard_filter(df, requirements)
  
  relaxed = False
  if filtered.empty:
    filtered = df.copy()
    relaxed = True
    
  listings_text = _format_for_llm(filtered)
  
  budget_max = requirements.get("budget_max", 0) or 0
  budget_min = requirements.get("budget_min", 0) or 0
  budget_str = f"${budget_min:,.0f}-{budget_max:,.0f}" if budget_max else "Not specified"
  
  user_prompt = f"""Buyer: {buyer_name}
Budget: {budget_str}
Bedrooms: {requirements.get('bedrooms_min', '?')}+
Neighborhoods: {', '.join(requirements.get('neighborhoods', [])) or 'No preference'}
Must-haves: {', '.join(requirements.get('must_haves', [])) or 'None'}
{"NOTE: No hard-filter matches — showing broader inventory." if relaxed else ""}

Listings:
{listings_text}

Pick best 3-5 matches."""

  response = client.chat.completions.create(
    model = "llama-3.3-70b-versatile",
    messages = [
      {"role": "system", "content": RANK_PROMPT},
      {"role": "user", "content": user_prompt}
    ],
    temperature = 0.2,
    max_tokens = 1500
  )
  
  raw = response.choices[0].message.content.strip()
  if raw.startswith("```"):
    raw = raw.split("```")[1]
    if raw.startswith("json"):
      raw = raw[4:]
      
  result = json.loads(raw)
  result["filters_relaxed"] = relaxed
  result["total_after_filter"] = len(filtered)
  return result
  
