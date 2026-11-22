# app.py
import hashlib
import os
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from legal_rules import (
    ALLOWED_CATEGORIES,
    PROHIBITED_CATEGORIES,
    answer_legal_question,
    validate_jurisdiction,
)
from translations import USSD_STRINGS

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "justo.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_verification_hash(case_id: str, complainant: str, respondent: str, created_at: str) -> str:
    raw = f"{case_id}|{complainant}|{respondent}|{created_at}|JUSTO-JLOS-2026"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()


def send_sms_notification(phone: str, message: str):
    """
    Sends SMS via Africa's Talking if credentials are configured, otherwise logs cleanly for demo.
    """
    at_username = os.getenv("AT_USERNAME")
    at_api_key = os.getenv("AT_API_KEY")
    if at_username and at_api_key and phone:
        try:
            import africastalking
            africastalking.initialize(at_username, at_api_key)
            sms = africastalking.SMS
            sms.send(message, [phone])
            return {"sent": True, "provider": "AfricasTalking"}
        except Exception as exc:
            return {"sent": False, "error": str(exc)}
    print(f"[JUSTO SMS GATEWAY -> {phone}]: {message}")
    return {"sent": True, "provider": "SimulatedGateway", "preview": message}


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            village_court TEXT NOT NULL,
            complainant_name TEXT NOT NULL,
            complainant_phone TEXT NOT NULL,
            respondent_name TEXT NOT NULL,
            respondent_phone TEXT NOT NULL,
            category TEXT NOT NULL,
            category_label TEXT NOT NULL,
            claim_amount_ugx INTEGER DEFAULT 0,
            quorum_present INTEGER DEFAULT 5,
            women_present INTEGER DEFAULT 2,
            summary TEXT,
            hearing_date TEXT,
            status TEXT NOT NULL,
            jurisdiction_valid INTEGER NOT NULL,
            referral_note TEXT,
            ruling_notes TEXT,
            verification_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # Seed realistic Ugandan LC1 cases if database is empty
    cur.execute("SELECT COUNT(*) FROM cases")
    if cur.fetchone()[0] == 0:
        seed_cases = [
            (
                "JST-2026-001",
                "Ntinda II Village LC1 Court, Nakawa",
                "Namukasa Sarah",
                "+256772100201",
                "Okello Patrick",
                "+256701300401",
                "customary_land_boundary",
                "Customary Land Boundary / Trespass",
                450000,
                6,
                3,
                "Dispute over 2-meter boundary hedge encroachment between adjacent plots.",
                "2026-11-27 10:00",
                "HEARING_SCHEDULED",
                1,
                "",
                "Site inspection scheduled with village elders and both parties.",
                "2026-11-22T09:15:00"
            ),
            (
                "JST-2026-002",
                "Kisenyi I Village LC1 Court, Central",
                "Mugisha Emmanuel",
                "+256782550112",
                "Ssempijja Bosco",
                "+256752880990",
                "minor_debt",
                "Minor Debt / Breach of Contract",
                850000,
                5,
                2,
                "Unpaid balance for wholesale maize supply delivered in October 2026.",
                "2026-11-20 14:00",
                "RESOLVED_CONSENT",
                1,
                "",
                "Consent judgment: Respondent to pay UGX 850,000 in two installments by 15 Dec 2026.",
                "2026-11-18T11:30:00"
            )
        ]
        for sc in seed_cases:
            v_hash = generate_verification_hash(sc[0], sc[2], sc[4], sc[17])
            cur.execute(
                """
                INSERT INTO cases (
                    case_id, village_court, complainant_name, complainant_phone,
                    respondent_name, respondent_phone, category, category_label,
                    claim_amount_ugx, quorum_present, women_present, summary,
                    hearing_date, status, jurisdiction_valid, referral_note,
                    ruling_notes, verification_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*sc[:17], v_hash, sc[17])
            )

    conn.commit()
    conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/meta", methods=["GET"])
def get_meta():
    return jsonify({
        "allowed_categories": ALLOWED_CATEGORIES,
        "prohibited_categories": {k: v["label"] for k, v in PROHIBITED_CATEGORIES.items()},
        "monetary_limit_ugx": 2_000_000
    })


@app.route("/api/cases", methods=["GET"])
def list_cases():
    conn = get_db()
    rows = conn.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/cases", methods=["POST"])
def create_case():
    data = request.get_json(force=True)
    category = data.get("category", "minor_debt")
    claim_amount = int(data.get("claim_amount_ugx", 0) or 0)
    quorum_present = int(data.get("quorum_present", 5) or 5)
    women_present = int(data.get("women_present", 2) or 2)

    verdict = validate_jurisdiction(category, claim_amount, quorum_present, women_present)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM cases")
    next_num = cur.fetchone()[0] + 1
    case_id = data.get("case_id") or f"JST-2026-{next_num:03d}"

    created_at = data.get("created_at") or datetime.now().isoformat(timespec="seconds")
    complainant_name = data.get("complainant_name", "").strip()
    respondent_name = data.get("respondent_name", "").strip()
    complainant_phone = data.get("complainant_phone", "").strip()
    respondent_phone = data.get("respondent_phone", "").strip()

    if category in ALLOWED_CATEGORIES:
        category_label = ALLOWED_CATEGORIES[category]
    elif category in PROHIBITED_CATEGORIES:
        category_label = PROHIBITED_CATEGORIES[category]["label"]
    else:
        category_label = category

    status = "HEARING_SCHEDULED" if verdict["is_valid"] else "REFERRED_OUT_OF_JURISDICTION"
    referral_note = "; ".join(verdict["issues"]) if not verdict["is_valid"] else ""
    v_hash = generate_verification_hash(case_id, complainant_name, respondent_name, created_at)

    cur.execute(
        """
        INSERT OR REPLACE INTO cases (
            case_id, village_court, complainant_name, complainant_phone,
            respondent_name, respondent_phone, category, category_label,
            claim_amount_ugx, quorum_present, women_present, summary,
            hearing_date, status, jurisdiction_valid, referral_note,
            ruling_notes, verification_hash, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            data.get("village_court", "Naguru I Village LC1 Court"),
            complainant_name,
            complainant_phone,
            respondent_name,
            respondent_phone,
            category,
            category_label,
            claim_amount,
            quorum_present,
            women_present,
            data.get("summary", ""),
            data.get("hearing_date", "2026-11-28 10:00"),
            status,
            1 if verdict["is_valid"] else 0,
            referral_note,
            data.get("ruling_notes", ""),
            v_hash,
            created_at,
        ),
    )
    conn.commit()
    saved = dict(conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone())
    conn.close()

    # Trigger instant SMS receipt / referral alert
    if verdict["is_valid"]:
        sms_msg = (
            f"JUSTO LC1 Receipt: Case {case_id} logged ({complainant_name} vs {respondent_name}). "
            f"Hearing: {saved['hearing_date']}. Verify code: {v_hash}. Dial *384*2026# to track."
        )
    else:
        sms_msg = (
            f"JUSTO Notice ({case_id}): Matter exceeds LC1 jurisdiction/quorum. "
            f"Referred to: {verdict['recommended_referral']}. Ref: {v_hash}."
        )

    sms_status = send_sms_notification(complainant_phone, sms_msg)

    return jsonify({
        "case": saved,
        "jurisdiction_verdict": verdict,
        "sms_status": sms_status
    }), 201


@app.route("/api/cases/<case_id>/resolve", methods=["POST"])
def resolve_case(case_id):
    data = request.get_json(force=True)
    ruling_notes = data.get("ruling_notes", "").strip()
    new_status = data.get("status", "RESOLVED_CONSENT")

    conn = get_db()
    conn.execute(
        "UPDATE cases SET ruling_notes = ?, status = ? WHERE case_id = ?",
        (ruling_notes, new_status, case_id)
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    conn.close()

    if not updated:
        return jsonify({"error": "Case not found"}), 404

    return jsonify({"case": dict(updated)})


@app.route("/api/cases/sync", methods=["POST"])
def sync_offline_cases():
    """
    Receives a batch of offline-created cases from the browser's localStorage and syncs them to SQLite.
    """
    payload = request.get_json(force=True)
    offline_cases = payload.get("cases", [])
    synced_ids = []

    for item in offline_cases:
        with app.test_request_context(json=item):
            resp, _ = create_case()
            synced_ids.append(resp.get_json()["case"]["case_id"])

    return jsonify({"synced_count": len(synced_ids), "synced_ids": synced_ids})


@app.route("/api/legal-guide", methods=["POST"])
def legal_guide():
    data = request.get_json(force=True)
    question = data.get("question", "")
    answer = answer_legal_question(question)
    return jsonify({
        "question": question,
        "answer": answer,
        "source": "Local Council Courts Act, 2006 (Laws of Uganda)"
    })


@app.route("/ussd", methods=["POST"])
def ussd_callback():
    """
    Africa's Talking USSD Webhook supporting 5 Ugandan languages:
    1: English, 2: Luganda, 3: Runyankole-Rukiga, 4: Swahili, 5: Luo (Acholi)
    """
    session_id = request.values.get("sessionId", "")
    phone_number = request.values.get("phoneNumber", "")
    text = request.values.get("text", "").strip()

    parts = text.split("*") if text else []

    # Step 0: Language Selection
    if len(parts) == 0:
        response = (
            "CON Welcome to JUSTO (Access to Justice)\n"
            "Select Language / Londa Olulimi:\n"
            "1. English\n"
            "2. Luganda\n"
            "3. Runyankole-Rukiga\n"
            "4. Swahili\n"
            "5. Luo (Acholi)"
        )
        return response, 200, {"Content-Type": "text/plain"}

    lang_choice = parts[0]
    if lang_choice not in USSD_STRINGS:
        return "END Invalid language selection. Please dial again.", 200, {"Content-Type": "text/plain"}

    strings = USSD_STRINGS[lang_choice]

    # Step 1: Main Menu in chosen language
    if len(parts) == 1:
        return strings["main_menu"], 200, {"Content-Type": "text/plain"}

    menu_choice = parts[1]

    # Step 2: Handle Menu Choice
    if len(parts) == 2:
        if menu_choice == "1":
            return strings["enter_case_id"], 200, {"Content-Type": "text/plain"}
        elif menu_choice == "2":
            return strings["fees_info"], 200, {"Content-Type": "text/plain"}
        elif menu_choice == "3":
            return strings["appeal_info"], 200, {"Content-Type": "text/plain"}
        elif menu_choice == "4":
            return strings["quorum_info"], 200, {"Content-Type": "text/plain"}
        else:
            return "END Invalid option.", 200, {"Content-Type": "text/plain"}

    # Step 3: Case Status Lookup by Case ID
    if len(parts) == 3 and menu_choice == "1":
        lookup_id = parts[2].strip().upper()
        conn = get_db()
        row = conn.execute("SELECT * FROM cases WHERE UPPER(case_id) = ?", (lookup_id,)).fetchone()
        conn.close()

        if not row:
            return strings["case_not_found"], 200, {"Content-Type": "text/plain"}

        case = dict(row)
        response = (
            f"END JUSTO Case: {case['case_id']}\n"
            f"Court: {case['village_court']}\n"
            f"Parties: {case['complainant_name']} vs {case['respondent_name']}\n"
            f"Status: {case['status']}\n"
            f"Hearing: {case['hearing_date']}\n"
            f"Verify Code: {case['verification_hash']}"
        )
        return response, 200, {"Content-Type": "text/plain"}

    return "END Thank you for using JUSTO.", 200, {"Content-Type": "text/plain"}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)