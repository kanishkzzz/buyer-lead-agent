# AgentMira — Buyer Lead Intake Agent
> Case Study Submission | AI Product Engineer | DTU Campus Recruitment 2025–26

A multi-step AI agent that processes incoming buyer inquiries and produces structured Lead Briefs for real estate agents. The agent parses free-text buyer messages, matches them against ~300 Miami MLS listings, and generates a Markdown brief the realtor can read before their first call.

---

## How It Works

```
Buyer Inquiry (free-text message)
        │
        ▼
[Tool 1] inquiry_parser
  LLM extracts: budget, bedrooms, neighborhoods,
  must-haves, buyer profile, lead quality score (1–5)
        │
        ▼
[Tool 2] mls_matcher
  Pandas hard-filters 300 MLS listings (budget ±15%, beds, baths)
  LLM ranks top 3–5 matches with reasoning
        │
        ▼
[Tool 3] lead_analyst
  LLM assesses urgency, flags concerns,
  suggests outreach channel + qualifying questions
        │
        ▼
[Synthesis] Final LLM call
  Combines all tool outputs → formatted Lead Brief
        │
        ▼
Lead Brief (Markdown) saved to output/
```

Each tool's output feeds into the next — this is what makes it an agent, not a single LLM call.

---

## Project Structure

```
buyer-lead-agent/
├── agent/
│   └── orchestrator.py        ← Calls all 3 tools, synthesises final brief
├── tools/
│   ├── inquiry_parser.py      ← Tool 1: parse free-text buyer message
│   ├── mls_matcher.py         ← Tool 2: filter + rank MLS listings
│   └── lead_analyst.py        ← Tool 3: assess lead, advise realtor
├── data/
│   ├── miami_mls_listings.csv
│   └── sample_buyer_inquiries.json
├── output/
│   ├── summary.md                        ← Triage view of all 12 leads
│   ├── LEAD-2026-001_marcus_thompson.md  ← One brief per inquiry
│   └── ...
├── main.py                    ← Entry point
├── requirements.txt
├── EXPLANATION.md             ← Full written explanation
└── .env.example
```

---

## Setup & Run

### 1. Clone the repository
```bash
git clone https://github.com/kanishkzzz/buyer-lead-agent.git
cd buyer-lead-agent
```

### 2. Create a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your API key
```bash
cp .env.example .env
# Open .env and paste your Groq API key
# Get a free key at: https://console.groq.com
```

### 5. Add data files
Place both files in the `/data` directory:
```
data/
├── miami_mls_listings.csv
└── sample_buyer_inquiries.json
```

### 6. Run the agent
```bash
python main.py
```

---

## Output

For each of the 12 buyer inquiries, the agent generates:

- **`.md` file** — The Lead Brief (primary deliverable for the realtor)
- **`.json` file** — Raw structured data from all 3 tools (for debugging)
- **`summary.md`** — One-page triage view of all leads with urgency and budget

### Sample Lead Brief Output
```
# Lead Brief — Marcus Thompson
Received: 2026-06-19 via website_form
Contact: 305-555-0142 | marcus@email.com
Urgency: 🔴 Hot

## What They're Looking For
Relocating to Miami for a new tech job. Looking for a 2–3 bedroom
condo in Brickell or Downtown with a gym and city-view balcony.
Budget clearly defined at ~$700K...

## Top Matching Properties
### 1. 1200 Brickell Ave #1804 — $689,000
- Why it fits: 2BR/2BA in Brickell, building gym confirmed...
- Watch out: Listed as Pending — confirm availability

## Suggested Next Action
Call within 2 hours — relocation buyer with a firm job start date.
```

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python | Best ecosystem for AI/LLM work |
| LLM | llama-3.3-70b-versatile | Free, fast, reliable JSON output |
| LLM Provider | Groq API | Zero cost, ~2s inference per call |
| Data filtering | Pandas | Math comparisons — more reliable than LLM |
| Output format | Markdown | Readable on phone and laptop |

---

## Key Design Decisions

**Pandas filtering before LLM ranking** — Hard constraints (budget, bedrooms) are filtered in pandas with a 15% buffer. LLMs are unreliable at numeric comparisons. The LLM then ranks survivors on soft criteria like features and neighborhood fit.

**No vector database** — 300 listings fit in a single LLM context window after pandas pre-filtering. ChromaDB would add complexity with no quality gain at this scale.

**3 separate tools instead of 1 prompt** — Each tool has a distinct role. Separation makes each step independently testable and debuggable. It also lets each LLM call have a focused system prompt rather than one giant prompt trying to do everything.

**Error isolation per lead** — Each lead is wrapped in try/except so one failure doesn't crash the full batch of 12.

---

## Results

```
Total leads processed : 12/12
Hot leads             : 9
Warm leads            : 2
Cold leads            : 0
Avg brief length      : ~2,800 chars
```
