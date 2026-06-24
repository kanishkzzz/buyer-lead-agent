import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from groq import Groq

from agent.orchestrator import run_agent

# .env file se GROQ_API_KEY load karo
load_dotenv()


def get_client() -> Groq:
    """Groq client banao — API key check karo pehle"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY nahi mili.")
        print(".env file mein apni key daalo.")
        sys.exit(1)
    return Groq(api_key=api_key)


def slugify(name: str) -> str:
    """
    Buyer name ko safe filename mein convert karo
    Example: "Marcus Thompson" → "marcus_thompson"
    """
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\s]", "", name)   # special chars hata do
    name = re.sub(r"\s+", "_", name)            # spaces ko underscore karo
    return name[:40]                             # max 40 chars


def save_outputs(result: dict, output_dir: Path) -> None:
    """
    Har lead ke liye 2 files save karo:
      1. .md  — Lead Brief (submission ke liye)
      2. .json — Raw data  (debugging ke liye)
    """
    lead_id  = result["lead_id"]
    slug     = slugify(result["buyer_name"])
    basename = f"{lead_id}_{slug}"

    # ── Markdown Brief ─────────────────────────────
    md_path = output_dir / f"{basename}.md"
    md_path.write_text(result["brief_markdown"], encoding="utf-8")

    # ── Raw JSON ───────────────────────────────────
    json_path = output_dir / f"{basename}.json"
    json_data = {
        "lead_id":      result["lead_id"],
        "buyer_name":   result["buyer_name"],
        "status":       result["status"],
        "requirements": result["requirements"],
        "matches":      result["matches"],
        "analysis":     result["analysis"],
    }
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    print(f"  Saved → {md_path.name}")
    print(f"  Saved → {json_path.name}")


def generate_summary(results: list, output_dir: Path) -> None:
    """
    Saare 12 leads ka ek page summary banao.
    Realtor isko pehle dekhe — triage ke liye.
    """
    urgency_emoji = {"hot": "🔴", "warm": "🟡", "cold": "🟢"}

    lines = [
        "# AgentMira — Lead Intake Summary",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        f"**Total leads:** {len(results)}",
        f"**Successful:** {sum(1 for r in results if r['status'] == 'success')}",
        "",
        "---",
        "",
        "| Lead | Buyer | Urgency | Budget | Beds | Quality |",
        "|------|-------|---------|--------|------|---------|",
    ]

    for r in results:
        req      = r.get("requirements", {})
        analysis = r.get("analysis", {})
        urgency  = analysis.get("urgency", "warm")
        emoji    = urgency_emoji.get(urgency, "🟡")

        # Budget string banao
        bmax = req.get("budget_max", 0) or 0
        bmin = req.get("budget_min", 0) or 0
        if bmax:
            budget_str = f"${bmin//1000}K–${bmax//1000}K"
        else:
            budget_str = "Unknown"

        lines.append(
            f"| {r['lead_id']} "
            f"| {r['buyer_name'][:20]} "
            f"| {emoji} {urgency.title()} "
            f"| {budget_str} "
            f"| {req.get('bedrooms_min', '?')}+ "
            f"| {req.get('lead_quality', '?')}/5 |"
        )

    # Hot leads alag section mein dikhao
    lines += ["", "---", "", "## 🔴 Hot Leads — Act Now", ""]
    hot = [r for r in results if r.get("analysis", {}).get("urgency") == "hot"]

    if hot:
        for r in hot:
            action = r.get("analysis", {}).get("suggested_next_action", "")
            lines.append(f"**{r['buyer_name']}** ({r['lead_id']})")
            lines.append(f"→ {action}")
            lines.append("")
    else:
        lines.append("*No hot leads in this batch.*")

    summary_path = output_dir / "summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Summary saved → summary.md")


def main():
    # ── Paths setup ────────────────────────────────────────────
    base_dir   = Path(__file__).parent
    data_dir   = base_dir / "data"
    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)   # output folder nahi hai toh banao

    inquiries_path = data_dir / "sample_buyer_inquiries.json"
    mls_path       = data_dir / "miami_mls_listings.csv"

    # ── Data files check karo ──────────────────────────────────
    if not inquiries_path.exists():
        print(f"ERROR: {inquiries_path} nahi mili.")
        print("data/ folder mein apni JSON file daalo.")
        sys.exit(1)

    if not mls_path.exists():
        print(f"ERROR: {mls_path} nahi mili.")
        print("data/ folder mein apni CSV file daalo.")
        sys.exit(1)

    # ── Leads load karo ───────────────────────────────────────
    with open(inquiries_path, encoding="utf-8") as f:
        leads = json.load(f)

    # ── Start ─────────────────────────────────────────────────
    print(f"\nAgentMira — Buyer Lead Intake Agent")
    print(f"=====================================")
    print(f"Leads found   : {len(leads)}")
    print(f"MLS data      : {mls_path.name}")
    print(f"Output folder : {output_dir}")
    print(f"Started at    : {datetime.now().strftime('%H:%M:%S')}")

    client  = get_client()
    results = []

    # ── Har lead process karo ─────────────────────────────────
    for i, lead in enumerate(leads, 1):
        print(f"\nLead {i}/{len(leads)}")

        try:
            result = run_agent(client, str(mls_path), lead)
            results.append(result)
            save_outputs(result, output_dir)

        except Exception as e:
            # Ek lead fail ho toh poora program mat roko
            print(f"  ✗ Error on {lead.get('lead_id')}: {e}")
            results.append({
                "lead_id":        lead.get("lead_id", f"LEAD-{i}"),
                "buyer_name":     lead.get("buyer_name", "Unknown"),
                "status":         "error",
                "brief_markdown": f"# Error\n\n{str(e)}",
                "requirements":   {},
                "matches":        {},
                "analysis":       {}
            })

    # ── Summary ─────────────────────────────────────────
    generate_summary(results, output_dir)

    # ── Done ──────────────────────────────────────────────────
    success = sum(1 for r in results if r["status"] == "success")
    print(f"\n{'='*55}")
    print(f"  Done! {success}/{len(leads)} leads processed.")
    print(f"  Briefs saved in: output/")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()