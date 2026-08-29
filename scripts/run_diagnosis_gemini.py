"""
run_diagnosis_gemini.py — feeds every case in data/cases.csv to Google's
Gemini model (free tier, no credit card required) using the same NetSage AI
system prompt, and saves results to data/ai_results.json — same file, same
schema, that the website already reads. This is a free alternative to
run_diagnosis.py (which uses the paid Anthropic API).

Setup:
    1. Get a free key at https://aistudio.google.com (Get API key -> default
       Gemini project). No credit card required.
    2. Set it as an environment variable:
       export GOOGLE_API_KEY="AIzaSy..."        (macOS/Linux/VS Code bash terminal)
       $env:GOOGLE_API_KEY="AIzaSy..."           (Windows PowerShell)

Usage:
    python3 scripts/run_diagnosis_gemini.py                 # run every case
    python3 scripts/run_diagnosis_gemini.py C001 C010        # run only specific case IDs
    python3 scripts/run_diagnosis_gemini.py --overwrite      # re-run cases that already have a result

No third-party packages required — uses only Python's standard library.
"""
import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error

MODEL = "gemini-2.0-flash"
API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

SYSTEM_PROMPT = """You are NetSage AI, a troubleshooting assistant for junior network engineers working in Cisco Packet Tracer labs. You are shown a SYMPTOM, a TOPOLOGY NOTE, and SHOW-COMMAND OUTPUT. Propose the most likely root cause using ONLY the evidence given.

Rules:
1. Never invent evidence not present in the show-command output.
2. If evidence is insufficient, say so and set confidence to "low".
3. Always name the OSI layer most responsible for the symptom.
4. Always propose exactly one concrete next command.
5. fix_steps must be reversible, non-destructive lab actions.
6. This is a DRAFT. A human reviewer will Accept, Edit, or Reject it. Do not claim the issue is resolved.
7. Respond with ONLY a single JSON object, no prose, no markdown fences, no explanation before or after.

Schema: {"root_cause":string,"confidence":"low"|"medium"|"high","evidence":string,"osi_layer":string,"next_command":string,"fix_steps":[string]}"""


def call_gemini(api_key, user_message, max_retries=3):
    url = API_URL_TEMPLATE.format(model=MODEL, key=api_key)
    body = json.dumps({
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {"temperature": 0.2},
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )

    last_err = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                clean = text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean)
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')[:300]}"
            if e.code == 429:  # rate limited — back off and retry
                time.sleep(3 * (attempt + 1))
                continue
            break
        except Exception as e:
            last_err = str(e)
            time.sleep(1)
    return {"error": last_err or "Unknown error calling the API"}


def main():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: Set the GOOGLE_API_KEY environment variable first.")
        print('  export GOOGLE_API_KEY="AIzaSy..."   (Linux/macOS/bash)')
        print('  $env:GOOGLE_API_KEY="AIzaSy..."      (Windows PowerShell)')
        sys.exit(1)

    args = sys.argv[1:]
    overwrite = "--overwrite" in args
    only_ids = {a for a in args if not a.startswith("--")}

    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    csv_path = os.path.join(base, "data", "cases.csv")
    out_path = os.path.join(base, "data", "ai_results.json")

    results = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            try:
                results = json.load(f)
            except json.JSONDecodeError:
                results = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if only_ids:
        rows = [r for r in rows if r["case_id"] in only_ids]

    print(f"Running diagnosis for {len(rows)} case(s) using Gemini (free tier)...\n")
    for i, row in enumerate(rows, 1):
        cid = row["case_id"]
        if cid in results and not overwrite:
            print(f"[{i}/{len(rows)}] {cid} — already has a result, skipping (use --overwrite to redo)")
            continue

        user_message = (
            f"SYMPTOM: {row['symptom']}\n"
            f"TOPOLOGY NOTE: {row['topology_note']}\n"
            f"SHOW OUTPUT:\n{row['show_output']}"
        )
        print(f"[{i}/{len(rows)}] {cid} — calling Gemini...")
        result = call_gemini(api_key, user_message)
        results[cid] = result

        if "error" in result:
            print(f"    ERROR: {result['error']}")
        else:
            print(f"    root_cause: {result.get('root_cause','')[:90]}")
            print(f"    confidence: {result.get('confidence','')}")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        time.sleep(1)  # free tier has per-minute rate limits — be polite

    print(f"\nDone. Results saved to {out_path}")
    print("Refresh index.html in your browser to see the AI diagnoses.")


if __name__ == "__main__":
    main()