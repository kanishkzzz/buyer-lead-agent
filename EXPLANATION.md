# Written Explanation — Buyer Lead Intake Agent
**Candidate:** Kanishk  
**Role:** AI Product Engineer — AgentMira  
**Submission Date:** June 24, 2026

---

## 1. Overall Approach and Design Decisions

### What I Built

A multi-step Buyer Lead Intake Agent that processes incoming buyer inquiries and produces structured Lead Briefs for real estate agents. The agent takes a free-text buyer message, matches it against ~300 Miami MLS listings, and generates a Markdown brief the realtor can read before their first call.

### Architecture — Why 3 Separate Tools

The core design decision was to break the pipeline into three distinct tools instead of making one large LLM call with everything in a single prompt.

**Tool 1 — `inquiry_parser`:** Extracts structured requirements from the buyer's free-text message. Budget, bedrooms, neighborhoods, must-haves, timeline, buyer profile, and a lead quality score (1–5). This is a pure NLP task — LLMs are excellent at understanding intent from messy human language, so this is the right place for an LLM call.

**Tool 2 — `mls_matcher`:** Two-stage matching. First, pandas hard-filters the 300 listings using numeric comparisons (budget ±15%, minimum bedrooms, minimum bathrooms). Then the filtered candidates go to the LLM for ranking and reasoning. The key tradeoff here: LLMs are unreliable at math. Asking an LLM "is $689,000 within a $700,000 budget?" introduces hallucination risk. Pandas does that correctly every time. The LLM then handles what it's actually good at — reasoning about soft preferences like "gym in building," "good school district," or "investor-friendly."

**Tool 3 — `lead_analyst`:** Receives outputs from both prior tools and produces realtor-facing intelligence — urgency level, concerns before outreach, suggested contact channel, and qualifying questions. This tool runs last because it needs full context: what the buyer wants AND what inventory is available before it can say "call within 2 hours" vs "send an email."

This sequential flow is what makes it an agent rather than a single LLM call. Each tool's output feeds the next one, and the final synthesis prompt has the complete picture before generating the brief.

### Key Tradeoffs

**No vector database:** With ~300 listings, all filtered candidates fit comfortably in a single LLM context window after pandas pre-filtering. Adding ChromaDB or FAISS would introduce setup complexity, embedding costs, and an additional failure point — with no meaningful quality improvement at this data scale. At 10,000+ listings, semantic search would become necessary.

**Markdown output over JSON:** The brief is what the realtor reads on their phone. Markdown renders cleanly in any email client, Notion, or browser. Raw JSON is also saved alongside every brief for programmatic use or debugging.

**15% budget buffer in filtering:** Real buyers flex. A buyer who says "$700K max" will often consider $740K for the right property. The buffer surfaces near-misses that the realtor can present as stretch options, rather than silently eliminating them.

**Groq + llama-3.3-70b-versatile:** Free tier, fast inference (~2–3 seconds per call), and reliable structured JSON output. No cost barrier for running all 12 leads.

**Error isolation per lead:** Each lead is wrapped in a try/except block in `main.py`. If one lead fails, the remaining 11 continue processing. A single bad JSON response from the LLM should not crash the entire batch.

---

## 2. Walkthrough of the 12 Lead Briefs

### LEAD-2026-001 — Marcus Thompson
Clear, high-intent lead. Relocating to Miami for a tech job — this signals a firm deadline and genuine purchase intent. Budget ($600K–$800K) is well-defined, neighborhoods (Brickell/Downtown) are specific, and must-haves (gym, city-view balcony) are actionable filters. Agent flagged as HOT — relocation buyers move fast and will work with whoever responds first. 4 matching condos found in budget range.

### LEAD-2026-002 — Patricia and David Chen
Family of four moving from Boston. Strong lead — 4 bedrooms, pool as non-negotiable, school district matters (kids in elementary school). Budget up to $2.3M with stretch. The "pool is non-negotiable" flag was caught and surfaced as a hard filter note. Agent correctly identified this as HOT — family relocation with a clear checklist is easy to work with. 5 matches found in Coral Gables/Pinecrest area.

### LEAD-2026-003 — Anonymous (form not filled)
Most interesting edge case in the batch. Buyer did not fill the form — anonymous name, no phone number, but left a message. Two problems flagged: (1) $250K budget for a 4-bedroom in Miami is unrealistic — median Miami home price is well above this. (2) No phone means email-only outreach. Agent correctly surfaced both concerns in the "Before You Call" section and suggested email acknowledgment rather than a call. Only 1 match found, which itself signals the budget problem clearly.

### LEAD-2026-004 — Sofia Reyes
Investor profile — looking for rental income properties, not a personal home. Budget not explicitly stated in message. Parser extracted minimal budget info, flagged as `vague_budget`. Agent correctly identified this as a different buyer type (investor vs. end-user) and suggested the realtor ask about target cap rate and preferred property type before showing anything. Warm urgency — investor leads need more qualification before they're actionable.

### LEAD-2026-005 — Robert Klein
Luxury segment — budget $950K–$1.25M, no bedroom count specified. 116 listings passed hard filter because bedrooms_min was null, giving the LLM a wide candidate pool. Agent ranked top 5 by feature match. Flagged that without a bedroom preference, the realtor should ask this as their first qualifying question before scheduling viewings.

### LEAD-2026-006 — Aaron Cooper
3-bedroom requirement, budget up to $850K. Budget_min was null (buyer only gave a max), which the agent handled gracefully. 22 listings passed filter, 5 ranked. HOT urgency — message tone suggested active search. Realtor talking points included mentioning specific neighborhoods that fit the profile.

### LEAD-2026-007 — Elena Vasquez
Unique situation — Elena is buying for her elderly parents, not for herself. This context matters for the realtor: the actual decision-makers may not be on the call. Agent caught this and flagged it as a concern — "buyer is purchasing on behalf of parents; confirm their involvement in viewings." Warm urgency because the parents' needs (accessibility, ground floor, no stairs) need verification before matching.

### LEAD-2026-008 — Jennifer Walsh
High-quality lead — 5/5 quality score. Budget $1.2M–$1.4M, 4+ bedrooms, specific about wanting a home office and good school district. 9 listings passed hard filter, 5 matched well. HOT urgency. The specificity of requirements made this the easiest brief to generate — clear buyer, clear needs, good inventory match.

### LEAD-2026-009 — Luis Hernandez
Budget up to $750K, 2+ bedrooms. Budget_min was null. Only 5 listings passed hard filter, 3 matched well — tighter inventory at this price point in the requested neighborhoods. Agent correctly noted the limited inventory in matching_note and suggested the realtor set expectations on availability before the first call.

### LEAD-2026-010 — Karen O'Brien
Highest-value lead in the batch — budget up to $8M, 5+ bedrooms. Ultra-luxury segment. Only 6 listings passed hard filter at this price point, which is expected — the top end of any market has limited inventory. HOT urgency — an $8M buyer getting a slow response is an expensive miss. Agent flagged: call immediately, this is a priority lead.

### LEAD-2026-011 — Priya Sharma
Budget up to $400K, 1+ bedroom. First-time buyer profile. 41 listings passed filter — good availability at this price point. Agent correctly identified this as a first-time buyer and added qualifying questions around mortgage pre-approval, which is critical before showing properties. HOT urgency because of the competitive market at this price range.

### LEAD-2026-012 — Michael Reeves
Budget $500K–$900K, no bedroom count specified. 119 listings passed hard filter — wide range because both budget and bedrooms were broad. Agent ranked top 5 and flagged that the realtor should ask for bedroom preference before scheduling anything. HOT urgency based on message tone.

---

## 3. How I Used AI Coding Tools

I used Claude throughout this build as a thinking partner and debugging aid, not as a code generator.

My approach was deliberate: before asking Claude anything, I would try to reason through the problem myself — what function needs to exist, what inputs it takes, what it should return. Only when I got stuck on a logical issue, a syntax error I couldn't trace, or a design decision I was unsure about would I bring Claude in.

Specifically, Claude helped me in three ways during this build:

**Logic validation:** When I was designing the two-stage matching approach (pandas filter → LLM rank), I was unsure whether to do all filtering in the LLM or split it. I explained my thinking to Claude and asked if the reasoning was sound. Claude confirmed the split was the right call and explained why LLMs are unreliable at numeric comparisons — which strengthened my understanding of when to use each tool.

**Debugging:** When errors appeared in the terminal (the `name 'bed' is not defined` error, the `NoneType.__format__` crash), I would look at the traceback myself first and try to identify the root cause before asking for help. Claude helped me confirm my diagnosis and pointed out a second instance of the same bug in a different file I had missed.

**Syntax and Python patterns:** Coming from a JavaScript/MERN background, some Python-specific patterns (pandas DataFrame operations, f-string formatting with None values, module-level caching with a global variable) were unfamiliar. Claude explained the pattern and the reasoning behind it, which I then applied myself.

What I did not use Claude for: writing functions wholesale, generating prompts I didn't understand, or copying solutions without understanding them first. Every line in this codebase I can explain because I either wrote it myself or understood it before it went in.

---

## 4. What I Would Build Next

**Webhook intake endpoint:** Right now the agent runs as a batch script. The real version needs a FastAPI endpoint that accepts a POST request when a lead comes in through a website form and triggers the pipeline in real time — generating and delivering the brief within 30 seconds of the buyer submitting.

**Automated first-touch draft:** After generating the Lead Brief, the agent should also draft a personalized outreach email or text for the realtor to send in one click. The realtor reviews, edits if needed, and sends — cutting their response time from hours to minutes.

**Lead memory and CRM sync:** If the same buyer reaches out again through a different channel, the agent currently treats them as a new lead. A simple database layer (PostgreSQL or Supabase) to store lead history and match returning buyers would make follow-ups significantly smarter.

**Richer MLS matching with embeddings:** At 300 listings, pandas + LLM context works fine. At 10,000+ listings, a vector database (ChromaDB or Pinecone) with embeddings on listing descriptions would enable semantic search — matching "quiet neighborhood good for families" against listing text in a way that keyword filtering cannot.

**Realtor feedback loop:** Let the realtor mark which matched properties the buyer actually liked. Feed that signal back to improve ranking over time — essentially a lightweight learning loop on top of the matching logic.

**n8n automation layer:** Connect the webhook to n8n to handle routing — send the brief via email to the realtor, log the lead to a Google Sheet, and trigger a Slack notification for hot leads, all without additional code.
