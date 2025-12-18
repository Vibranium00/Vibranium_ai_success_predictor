import os
import io
import re
import json
import tempfile
import requests
from datetime import datetime
from textwrap import wrap
from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth
import markdown
import pathlib



# -------------------------------------------------------
# APP INIT
# -------------------------------------------------------
app = Flask(__name__, static_folder=".", template_folder=".")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
CORS(app, supports_credentials=True)

from flask import send_from_directory


# -------------------------------------------------------
# FIREBASE INIT
# -------------------------------------------------------
db = None
firebase_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")

if firebase_json:
    try:
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write(firebase_json)

        cred = credentials.Certificate(path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase initialized")
    except Exception as e:
        print("❌ Firebase init error:", e)
else:
    print("⚠️ FIREBASE_CREDENTIALS_JSON not set")

# -------------------------------------------------------
# GEMINI CONFIG (2.5 FLASH)
# -------------------------------------------------------
GEMINI_API_KEYS_STR = os.environ.get("GEMINI_API_KEYS", "")
GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEYS_STR.split(",") if k.strip()]

# 🔧 FIX: define the actual key used
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else None

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1/models/"
    "gemini-2.5-flash:generateContent"
)

print(f"✅ Gemini keys loaded: {len(GEMINI_API_KEYS)}")

# -------------------------------------------------------
# SESSION HELPERS
# -------------------------------------------------------
def login_user(uid, email, name=None, picture=None):
    session["uid"] = uid
    session["email"] = email
    session["name"] = name
    session["picture"] = picture


def logout_user():
    session.clear()


def is_logged_in():
    return "uid" in session

# -------------------------------------------------------
# AUTH ROUTES
# -------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        token = request.json.get("token")
        decoded = firebase_auth.verify_id_token(token)

        login_user(
            decoded["uid"],
            decoded.get("email"),
            decoded.get("name"),
            decoded.get("picture"),
        )

        if db:
            db.collection("users").document(decoded["uid"]).set(
                {
                    "email": decoded.get("email"),
                    "name": decoded.get("name"),
                    "picture": decoded.get("picture"),
                    "last_login": datetime.utcnow(),
                },
                merge=True,
            )

        return jsonify({"ok": True})

    except Exception as e:
        print("❌ Login error:", e)
        return jsonify({"error": "Login failed"}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    logout_user()
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me():
    if not is_logged_in():
        return jsonify({"authenticated": False})

    return jsonify(
        {
            "authenticated": True,
            "id": session["uid"],
            "email": session.get("email"),
            "name": session.get("name"),
            "picture": session.get("picture"),
        }
    )

# -------------------------------------------------------
# ANALYZE
# -------------------------------------------------------
@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    if not is_logged_in():
        return jsonify({"error": "Login required"}), 401

    if not db:
        return jsonify({"error": "Database not ready"}), 500

    if not GEMINI_API_KEY:
        return jsonify({"error": "Gemini API key missing"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    name = data.get("name")
    pitch = data.get("pitch", "")
    description = data.get("description")
    industry = data.get("industry", "")
    stage = data.get("stage", "")
    competition = data.get("competition", "")
    team_size = data.get("teamSize", "")
    mode = data.get("mode", "fast")

    if not name or not description:
        return jsonify({"error": "Missing input"}), 400

    doc_ref = db.collection("analyses").document()
    doc_id = doc_ref.id

    doc_ref.set(
        {
            "user_id": session["uid"],
            "name": name,
            "pitch": pitch,
            "description": description,
            "industry": industry,
            "stage": stage,
            "competition": competition,
            "team_size": team_size,
            "mode": mode,
            "status": "processing",
            "created_at": datetime.utcnow(),
        }
    )
#=================PROMT SEND TO GEMINI FOR ANALYSIS===============#
    try:
        prompt = f"""
Write like a real startup mentor or early-stage investor,not like an academic report.

Think aloud while evaluating.
Acknowledge uncertainty where information is missing.
Use slightly informal but professional language.
Vary sentence length.

Do not sound like a template.

You are a senior venture capitalist ,startup analyst,and former startup founder.

You have evaluated 1000+ early-stage startupsfor accelerators,angel investors, and VC firms.

You are analytical, realistic, and honest.
You do not exaggerate.
You clearly explain assumptions and risks.

Your goal is to help founders understand 
how investors would judge their startup.

Context:
This is an AI-powered startup evaluation.
The startup may be early-stage with limited data.

You must:
- Make reasonable assumptions
- Penalize missing or unclear information
- Avoid hype or generic advice

Startup Information:

Startup Name: {name}
Industry / Vertical: {industry}
Startup Stage: {stage}
Team Size: {team_size}

One-line Pitch:
{pitch}

Problem & Solution Description:
{description}

Evaluation Rules:
1. All scores must be between 0 and 100.
2. Every score must have a short justification (1–2 lines).
3. If data is missing or unclear, reduce the score.
4. Do not repeat the same text across sections.
5. Be critical but constructive.
6. Assume this is an early-stage startup unless stated otherwise.
7. Clearly mention assumptions when making judgments.

STRICT OUTPUT FORMAT (follow exactly):

## Overall Startup Score
Score: XX / 100
Short explanation (2–3 lines).

---

## Score Breakdown
| Factor | Score | Reason |
|------|------|--------|
| Market Demand | XX | |
| Competition | XX | |
| Business Model | XX | |
| Team Strength | XX | |
| Technical Feasibility | XX | |
| Monetization Potential | XX | |
| Risk & Regulation | XX | |

---

## Key Strengths
- Strength 1
- Strength 2
- Strength 3

---

## Key Weaknesses
- Weakness 1
- Weakness 2
- Weakness 3

---

## Actionable Improvements (Priority Order)
1. Improvement with clear action
2. Improvement with clear action
3. Improvement with clear action

---

## 90-Day Execution Roadmap
- Month 1:
- Month 2:
- Month 3:

---

## Investor Red Flags
- Red flag 1
- Red flag 2
- Red flag 3

---

## Suggested KPIs to Track
- KPI 1
- KPI 2
- KPI 3

---

## Confidence Level
Low / Medium / High
Explain why.

---

## Disclaimer
This assessment is based on limited inputs, so treat it as directional guidance rather than a final investment decision.
"""
        if mode == "fast":
            prompt += "\nFocus on high-level feasibility. Keep answers concise."
        else:
            prompt += "\nGo deep. Be critical. Assume investor-level scrutiny."

        
#===================================================================================================#

        r = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            },
            timeout=30,
        )

        gem = r.json()
        result_text = (
            gem["candidates"][0]["content"]["parts"][0]["text"]
            if "candidates" in gem
            else "No response"
        )

        doc_ref.set(
            {
                "status": "done",
                "completed_at": datetime.utcnow(),
                "result": result_text,
            },
            merge=True,
        )

    except Exception as e:
        print("❌ Gemini error:", e)
        doc_ref.set(
            {"status": "failed", "error": str(e)},
            merge=True,
        )
        return jsonify({"error": "Gemini failed"}), 500

    return jsonify({"ok": True, "id": doc_id})

# -------------------------------------------------------
# HISTORY
# -------------------------------------------------------
@app.route("/api/history")
def api_history():
    if not is_logged_in() or not db:
        return jsonify({"items": []})

    q = (
        db.collection("analyses")
        .where("user_id", "==", session["uid"])
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(50)
    )

    items = []
    for d in q.stream():
        x = d.to_dict()
        x["id"] = d.id
        items.append(x)

    return jsonify({"items": items})

# -------------------------------------------------------
# REPORT JSON
# -------------------------------------------------------
@app.route("/api/report/<docid>")
def api_report(docid):
    if not is_logged_in() or not db:
        return jsonify({"error": "Unauthorized"}), 401

    doc = db.collection("analyses").document(docid).get()
    if not doc.exists:
        return jsonify({"error": "Not found"}), 404

    data = doc.to_dict()
    data["id"] = docid
    return jsonify(data)

# -------------------------------------------------------
# MARKDOWN CLEANER
# -------------------------------------------------------
def clean_markdown(text):
    if not text:
        return ""
        text = re.sub(r"#+\s*", "", text)
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"\*", "", text)
        text = re.sub(r"---+", "", text)
    return text
# -------------------------------------------------------
# GEMINI OUTPUT PARSER (FOR HTML → PDF)
# -------------------------------------------------------

def parse_overall_score(text):
    m = re.search(r"Score:\s*(\d+)", text)
    return m.group(1) if m else "N/A"


def parse_scores(text):
    scores = []
    for line in text.split("\n"):
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2 and parts[1].isdigit():
                scores.append({
                    "factor": parts[0],
                    "score": int(parts[1])
                })
    return scores


def extract_list(section, text):
    block = re.search(section + r"(.*?)(\n\n|$)", text, re.S)
    if not block:
        return []

    items = []
    for line in block.group(1).split("\n"):
        line = line.strip()

        # match bullets, numbers, Month labels (with optional indentation)
        if re.match(r"^(-|\*|•|\d+\.|Month\s+\d+:)", line):
            clean = re.sub(r"^(-|\*|•|\d+\.|Month\s+\d+:)\s*", "", line).strip()

            # 🔴 SKIP EMPTY CONTENT (THIS FIXES THE ISSUE)
            if not clean:
                continue

            html = markdown.markdown(clean, extensions=["extra"]).strip()

            # 🔴 SKIP EMPTY HTML
            if html and html != "<p></p>":
                items.append(html)

    return items
    




    #FEEDBACK
    # -------------------------------------------------------
# FEEDBACK
# -------------------------------------------------------
@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    if not is_logged_in() or not db:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    feedback = {
        "user_id": session["uid"],
        "analysis_id": data.get("analysis_id"),
        "rating": int(data.get("rating", 0)),
        "helpful": bool(data.get("helpful")),
        "comment": data.get("comment", ""),
        "created_at": datetime.utcnow(),
    }

    db.collection("feedback").add(feedback)

    return jsonify({"ok": True})

# -------------------------------------------------------
# PDF (PREMIUM HTML → PDF USING WEASYPRINT)
# -------------------------------------------------------
@app.route("/api/pdf/<docid>")
def api_pdf(docid):
    if not is_logged_in():
        return "Unauthorized", 401

    # ✅ Lazy import (prevents Gunicorn crash)
    from weasyprint import HTML

    doc = db.collection("analyses").document(docid).get()
    if not doc.exists:
        return "Not found", 404

    data = doc.to_dict()
    text = data.get("result", "")

    html = render_template(
        "report_pdf.html",
        name=data.get("name"),
        industry=data.get("industry"),
        pitch=data.get("pitch"),
        description=data.get("description"),
        stage=data.get("stage"),
        competition=data.get("competition"),
        team_size=data.get("team_size"),
        mode=data.get("mode"),
        overall_score=parse_overall_score(text),
        scores=parse_scores(text),
        strengths=extract_list("Key Strengths", text),
        weaknesses=extract_list("Key Weaknesses", text),
        improvements=extract_list("Actionable Improvements (Priority Order)",text),
        roadmap=extract_list("90-Day Execution Roadmap",text),
        red_flags=extract_list("Investor Red Flags", text),
        kpis=extract_list("Suggested KPIs to Track", text),
        
    )

    BASE_DIR = pathlib.Path(__file__).resolve().parent

    pdf = HTML(
        string=html,
        base_url=str(BASE_DIR)
    ).write_pdf()



    return pdf, 200, {
        "Content-Type": "application/pdf",
        "Content-Disposition": f'attachment; filename="analysis_{docid}.pdf"',
    }




# -------------------------------------------------------
# RUN
# -------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
@app.route("/")
def home():
    return send_from_directory(".", "index.html")
@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)
