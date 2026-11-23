# app.py
# JUSTO - digital infrastructure for Ugandan Local Council (LC1) courts.
# This file has three jobs:
#   1. create and fill the SQLite database,
#   2. decide what happens when a dispute is registered,
#   3. provide the web addresses (routes) used by the demo.
# Step (a) builds the database, the rules and the case API. Screens come later.

import hashlib
import os
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template, request
from flask_cors import CORS

from legal_rules import (
    ALLOWED_CATEGORIES,
    LC_MONETARY_LIMIT_UGX,
    PROHIBITED_CATEGORIES,
    QUORUM_MIN_MEMBERS,
    QUORUM_MIN_WOMEN,
    answer_legal_question,
    category_label,
    validate_jurisdiction,
)
from translations import SMS_TEMPLATES, USSD_STRINGS, USSD_WELCOME


# ---------------------------------------------------------------------------
# Settings and small helpers
# ---------------------------------------------------------------------------

def load_dotenv_if_available():
    """Load a .env file with python-dotenv when that package is installed."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def read_env_file():
    """Backup .env reader, so the app still works without python-dotenv."""
    path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


load_dotenv_if_available()
read_env_file()

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "justo.db")

# A fixed salt makes the verification code repeatable for the same case details.
VERIFICATION_SALT = "JUSTO-LC1-2026"


def as_int(value, default=0):
    """Convert form/JSON text to a whole number without crashing on bad input."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_db():
    """Open a database connection whose rows behave like dictionaries."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def generate_verification_hash(case_id, complainant, respondent, created_at):
    """Make a deterministic 12-character SHA-256 code for a case record."""
    raw = "|".join(
        [case_id, complainant, respondent, created_at, VERIFICATION_SALT]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()


def send_sms_notification(phone, message):
    """
    Send an SMS through Africa's Talking when real credentials are present.
    Otherwise just print the message to the console - the demo never fails
    because of a missing SMS account.
    """
    username = os.getenv("AT_USERNAME", "").strip()
    api_key = os.getenv("AT_API_KEY", "").strip()
    configured = (
        username
        and api_key
        and "your_" not in api_key
        and "placeholder" not in api_key
    )

    if configured:
        try:
            import africastalking

            africastalking.initialize(username, api_key)
            response = africastalking.SMS.send(message, [phone])
            print("[JUSTO SMS via Africa's Talking -> {}]: {}".format(phone, response))
            return {
                "sent": True,
                "provider": "AfricaTalking",
                "response": str(response),
            }
        except Exception as error:
            print("[JUSTO SMS failed, using console fallback]:", error)

    print("[JUSTO SMS -> {}]: {}".format(phone or "no phone", message))
    return {"sent": True, "provider": "ConsoleFallback", "preview": message}


# ---------------------------------------------------------------------------
# Demo data so the court terminal and citizen app are never empty
# ---------------------------------------------------------------------------

SEED_CASES = [
    {
        "case_id": "JST-2026-001",
        "village_court": "Ntinda II Village LC1 Court, Nakawa",
        "complainant_name": "Namukasa Sarah",
        "complainant_phone": "+256772100201",
        "respondent_name": "Okello Patrick",
        "respondent_phone": "+256701300401",
        "category": "customary_land",
        "claim_amount_ugx": 450000,
        "quorum_present": 6,
        "women_present": 3,
        "summary": "A hedge was planted two metres inside the complainant's plot.",
        "hearing_date": "2026-11-27 10:00",
        "ruling_notes": "Site visit with two elders scheduled.",
        "created_at": "2026-11-22T09:15:00",
        "final_status": "HEARING_SCHEDULED",
    },
    {
        "case_id": "JST-2026-002",
        "village_court": "Kisenyi I Village LC1 Court, Central",
        "complainant_name": "Mugisha Emmanuel",
        "complainant_phone": "+256782550112",
        "respondent_name": "Ssempijja Bosco",
        "respondent_phone": "+256752880990",
        "category": "minor_debt",
        "claim_amount_ugx": 850000,
        "quorum_present": 5,
        "women_present": 2,
        "summary": "Unpaid balance for a wholesale maize delivery in October.",
        "hearing_date": "2026-11-20 14:00",
        "ruling_notes": "Consent judgment: pay UGX 850,000 in two instalments by 15 December 2026.",
        "created_at": "2026-11-18T11:30:00",
        "final_status": "RESOLVED_CONSENT",
    },
    {
        "case_id": "JST-2026-003",
        "village_court": "Naguru I Village LC1 Court, Nakawa",
        "complainant_name": "Achieng Grace",
        "complainant_phone": "+256774110889",
        "respondent_name": "Kabuye Daniel",
        "respondent_phone": "+256703442118",
        "category": "registered_land",
        "claim_amount_ugx": 12000000,
        "quorum_present": 5,
        "women_present": 2,
        "summary": "Ownership dispute over a plot that has a registered title deed.",
        "hearing_date": "",
        "ruling_notes": "",
        "created_at": "2026-11-21T08:40:00",
        "final_status": "REFERRED_OUT_OF_JURISDICTION",
    },
]

SEED_MESSAGES = [
    (
        "JST-2026-001",
        "CITIZEN",
        "Namukasa Sarah",
        "Good morning, should I bring my two boundary witnesses on Thursday?",
        "2026-11-23T09:10:00",
    ),
    (
        "JST-2026-001",
        "COURT",
        "LC1 Secretary (Ntinda II)",
        "Yes, please come at 10:00 AM with both witnesses. Official filing fee is UGX 2,000.",
        "2026-11-23T09:25:00",
    ),
]


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def init_db():
    """Create the two tables and add the seed data on a brand-new database."""
    connection = get_db()
    cursor = connection.cursor()

    cursor.execute(
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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            sender_role TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # Only seed when empty, so normal app restarts never duplicate data.
    cursor.execute("SELECT COUNT(*) FROM cases")
    if cursor.fetchone()[0] == 0:
        for item in SEED_CASES:
            verdict = validate_jurisdiction(
                item["category"],
                item["claim_amount_ugx"],
                item["quorum_present"],
                item["women_present"],
            )
            status = item.get("final_status") or (
                "HEARING_SCHEDULED" if verdict["is_valid"] else "REFERRED_OUT_OF_JURISDICTION"
            )
            referral_note = "; ".join(verdict["issues"]) if not verdict["is_valid"] else ""
            code = generate_verification_hash(
                item["case_id"],
                item["complainant_name"],
                item["respondent_name"],
                item["created_at"],
            )
            cursor.execute(
                """
                INSERT INTO cases (
                    case_id, village_court, complainant_name, complainant_phone,
                    respondent_name, respondent_phone, category, category_label,
                    claim_amount_ugx, quorum_present, women_present, summary,
                    hearing_date, status, jurisdiction_valid, referral_note,
                    ruling_notes, verification_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["case_id"],
                    item["village_court"],
                    item["complainant_name"],
                    item["complainant_phone"],
                    item["respondent_name"],
                    item["respondent_phone"],
                    item["category"],
                    category_label(item["category"]),
                    item["claim_amount_ugx"],
                    item["quorum_present"],
                    item["women_present"],
                    item["summary"],
                    item["hearing_date"],
                    status,
                    1 if verdict["is_valid"] else 0,
                    referral_note,
                    item["ruling_notes"],
                    code,
                    item["created_at"],
                ),
            )

    cursor.execute("SELECT COUNT(*) FROM messages")
    if cursor.fetchone()[0] == 0:
        for message in SEED_MESSAGES:
            cursor.execute(
                """
                INSERT INTO messages (case_id, sender_role, sender_name, body, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                message,
            )

    connection.commit()
    connection.close()


def save_case_record(data):
    """
    Register one dispute. Used by the Secretary form, the citizen app and
    offline sync. Returns the saved case, the rule check and the SMS result.
    """
    claim = as_int(data.get("claim_amount_ugx"), 0)
    quorum = as_int(data.get("quorum_present"), QUORUM_MIN_MEMBERS)
    women = as_int(data.get("women_present"), QUORUM_MIN_WOMEN)
    category = data.get("category", "minor_debt")

    verdict = validate_jurisdiction(category, claim, quorum, women)

    connection = get_db()
    cursor = connection.cursor()

    # Next number in the JST-2026-xxx series. We use the highest number
    # already stored rather than the row count, so deleting a case can never
    # cause a duplicate Case ID later.
    rows = cursor.execute("SELECT case_id FROM cases").fetchall()
    used_numbers = []
    for row in rows:
        pieces = row["case_id"].split("-")
        if len(pieces) == 3 and pieces[0] == "JST" and pieces[2].isdigit():
            used_numbers.append(int(pieces[2]))
    next_number = max(used_numbers) + 1 if used_numbers else 1
    case_id = data.get("case_id") or "JST-2026-{:03d}".format(next_number)
    created_at = data.get("created_at") or datetime.now().isoformat(timespec="seconds")

    complainant = (data.get("complainant_name") or "").strip()
    respondent = (data.get("respondent_name") or "").strip()
    phone = (data.get("complainant_phone") or "").strip()

    status = (
        "HEARING_SCHEDULED"
        if verdict["is_valid"]
        else "REFERRED_OUT_OF_JURISDICTION"
    )
    referral_note = "; ".join(verdict["issues"]) if not verdict["is_valid"] else ""
    code = generate_verification_hash(case_id, complainant, respondent, created_at)

    cursor.execute(
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
            data.get("village_court") or "Village LC1 Court",
            complainant,
            phone,
            (data.get("respondent_name") or "").strip(),
            (data.get("respondent_phone") or "").strip(),
            category,
            category_label(category),
            claim,
            quorum,
            women,
            data.get("summary", ""),
            data.get("hearing_date", ""),
            status,
            1 if verdict["is_valid"] else 0,
            referral_note,
            data.get("ruling_notes", ""),
            code,
            created_at,
        ),
    )
    connection.commit()
    saved = dict(
        connection.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    )
    connection.close()

    if verdict["is_valid"]:
        sms_text = SMS_TEMPLATES["case_receipt"].format(
            case_id=case_id,
            complainant=complainant,
            hearing=saved["hearing_date"],
            code=code,
        )
    else:
        sms_text = SMS_TEMPLATES["referral_notice"].format(
            case_id=case_id,
            referral=verdict["recommended_referral"],
            code=code,
        )

    sms_status = send_sms_notification(phone, sms_text)
    return saved, verdict, sms_status


# Create the database as soon as the app starts (works for Flask and servers).
init_db()


# ---------------------------------------------------------------------------
# API routes for step (a): the rules and the case records
# ---------------------------------------------------------------------------

@app.route("/api/meta", methods=["GET"])
def api_meta():
    """Give the front end all the statutory numbers it needs to draw guardrails."""
    return jsonify(
        {
            "allowed_categories": ALLOWED_CATEGORIES,
            "prohibited_categories": PROHIBITED_CATEGORIES,
            "monetary_limit_ugx": LC_MONETARY_LIMIT_UGX,
            "quorum_min_members": QUORUM_MIN_MEMBERS,
            "quorum_min_women": QUORUM_MIN_WOMEN,
            "statuses": [
                "HEARING_SCHEDULED",
                "RESOLVED_CONSENT",
                "REFERRED_OUT_OF_JURISDICTION",
                "APPEALED_TO_LC2",
            ],
            "governing_law": "Local Council Courts Act, 2006 (Laws of Uganda)",
        }
    )


@app.route("/api/cases", methods=["GET"])
def list_cases():
    """Return every case, newest first."""
    connection = get_db()
    rows = connection.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()
    connection.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/cases/<case_id>", methods=["GET"])
def get_case(case_id):
    """Return one case, or a 404 if the ID is unknown."""
    connection = get_db()
    row = connection.execute(
        "SELECT * FROM cases WHERE UPPER(case_id) = ?", (case_id.strip().upper(),)
    ).fetchone()
    connection.close()
    if row is None:
        return jsonify({"error": "Case not found"}), 404
    return jsonify(dict(row))


@app.route("/api/cases", methods=["POST"])
def create_case():
    """Register a new dispute and show the rule check and SMS result."""
    data = request.get_json(force=True)
    saved, verdict, sms_status = save_case_record(data)
    return (
        jsonify(
            {"case": saved, "jurisdiction_verdict": verdict, "sms_status": sms_status}
        ),
        201,
    )


# ---------------------------------------------------------------------------
# Web pages for the shared court terminal (Secretary + Chairperson)
# ---------------------------------------------------------------------------

@app.route("/")
def root():
    """The court device always opens on the court terminal."""
    return redirect("/court")


@app.route("/court")
def court_terminal():
    """One page, two tabs: Secretary intake and Chairperson bench/rulings."""
    return render_template("court.html")


@app.route("/citizen")
def citizen_app():
    """Phone-style citizen app, meant to be opened in a separate window."""
    return render_template("citizen.html")


@app.route("/api/cases/<case_id>/resolve", methods=["POST"])
def resolve_case(case_id):
    """
    Save the Chairperson's ruling or status change.
    The quorum check is repeated here on the server: a browser can be tricked,
    but an invalid bench must never produce a binding ruling.
    """
    data = request.get_json(force=True)
    new_status = (data.get("status") or "RESOLVED_CONSENT").strip()
    ruling_notes = (data.get("ruling_notes") or "").strip()

    connection = get_db()
    existing = connection.execute(
        "SELECT * FROM cases WHERE UPPER(case_id) = ?", (case_id.strip().upper(),)
    ).fetchone()
    if existing is None:
        connection.close()
        return jsonify({"error": "Case not found"}), 404

    members = as_int(data.get("quorum_present"), existing["quorum_present"])
    women = as_int(data.get("women_present"), existing["women_present"])

    # A hearing or a decision is invalid without a lawful bench.
    if new_status in ["HEARING_SCHEDULED", "RESOLVED_CONSENT"]:
        if members < QUORUM_MIN_MEMBERS or women < QUORUM_MIN_WOMEN:
            connection.close()
            return (
                jsonify(
                    {
                        "error": (
                            "Section 8 quorum violation: at least {} members including {} "
                            "women are required for a binding ruling. Recorded {} total, "
                            "{} women. The ruling was NOT saved.".format(
                                QUORUM_MIN_MEMBERS, QUORUM_MIN_WOMEN, members, women
                            )
                        )
                    }
                ),
                400,
            )

    connection.execute(
        """
        UPDATE cases
        SET ruling_notes = ?, status = ?, quorum_present = ?, women_present = ?
        WHERE case_id = ?
        """,
        (ruling_notes, new_status, members, women, existing["case_id"]),
    )
    connection.commit()
    updated = dict(
        connection.execute(
            "SELECT * FROM cases WHERE case_id = ?", (existing["case_id"],)
        ).fetchone()
    )
    connection.close()

    sms_text = SMS_TEMPLATES["status_update"].format(
        case_id=updated["case_id"],
        status=updated["status"],
        code=updated["verification_hash"],
    )
    send_sms_notification(updated["complainant_phone"], sms_text)
    return jsonify({"case": updated})


@app.route("/api/cases/sync", methods=["POST"])
def sync_offline_cases():
    """Upload cases the Secretary registered while offline."""
    data = request.get_json(force=True)
    queued = data.get("cases", [])
    synced_ids = []
    for item in queued:
        saved, _, _ = save_case_record(item)
        synced_ids.append(saved["case_id"])
    return jsonify({"synced_count": len(synced_ids), "synced_ids": synced_ids})


@app.route("/api/messages", methods=["GET"])
def get_messages():
    """Return the citizen/court message thread, newest last (or recent overall)."""
    case_id = request.args.get("case_id", "").strip().upper()
    connection = get_db()
    if case_id:
        rows = connection.execute(
            "SELECT * FROM messages WHERE UPPER(case_id) = ? ORDER BY id ASC",
            (case_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM messages ORDER BY id DESC LIMIT 50"
        ).fetchall()
        rows = list(reversed(rows))
    connection.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/messages", methods=["POST"])
def post_message():
    """Store a message. A court reply also sends an SMS alert to the citizen."""
    data = request.get_json(force=True)
    case_id = (data.get("case_id") or "GENERAL").strip().upper()
    role = (data.get("sender_role") or "CITIZEN").strip().upper()
    sender_name = (data.get("sender_name") or "Citizen").strip()
    body = (data.get("body") or "").strip()

    if not body:
        return jsonify({"error": "Message body is required"}), 400

    created_at = datetime.now().isoformat(timespec="seconds")
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO messages (case_id, sender_role, sender_name, body, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (case_id, role, sender_name, body, created_at),
    )
    connection.commit()
    message_id = cursor.lastrowid
    saved = dict(
        connection.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    )

    if role == "COURT" and case_id != "GENERAL":
        case_row = connection.execute(
            "SELECT complainant_phone FROM cases WHERE UPPER(case_id) = ?", (case_id,)
        ).fetchone()
        if case_row and case_row["complainant_phone"]:
            send_sms_notification(
                case_row["complainant_phone"],
                SMS_TEMPLATES["court_reply"].format(case_id=case_id, body=body[:120]),
            )

    connection.close()
    return jsonify({"message": saved}), 201


@app.route("/api/verify/<case_id>", methods=["GET"])
def verify_case(case_id):
    """Check a printed record against the database and its verification code."""
    provided_hash = request.args.get("hash", "").strip().upper()
    connection = get_db()
    row = connection.execute(
        "SELECT * FROM cases WHERE UPPER(case_id) = ?", (case_id.strip().upper(),)
    ).fetchone()
    connection.close()

    if row is None:
        return jsonify({"found": False, "message": "No case found with that Case ID."}), 404

    case = dict(row)
    expected_hash = generate_verification_hash(
        case["case_id"],
        case["complainant_name"],
        case["respondent_name"],
        case["created_at"],
    )
    return jsonify(
        {
            "found": True,
            "case": case,
            "record_intact": case["verification_hash"].upper() == expected_hash.upper(),
            "hash_checked": bool(provided_hash),
            "hash_matches": (
                (provided_hash == case["verification_hash"].upper())
                if provided_hash
                else None
            ),
        }
    )


# ---------------------------------------------------------------------------
# Legal guide and the Africa's Talking USSD webhook
# ---------------------------------------------------------------------------

@app.route("/api/legal-guide", methods=["POST"])
def legal_guide():
    """Answer a citizen's plain-language legal question from the Act."""
    data = request.get_json(force=True) if request.data else {}
    question = data.get("question", "")
    return jsonify(
        {
            "question": question,
            "answer": answer_legal_question(question),
            "source": "Local Council Courts Act, 2006 (Laws of Uganda)",
        }
    )


# Plain text with an explicit UTF-8 charset, because several menus contain
# Luganda, Runyankole, Swahili and Acholi characters.
TEXT_HEADERS = {"Content-Type": "text/plain; charset=utf-8"}


def ussd_reply(text):
    """Wrap every USSD reply the way Africa's Talking expects it."""
    return text, 200, TEXT_HEADERS


@app.route("/ussd", methods=["POST"])
def ussd_callback():
    """
    Africa's Talking USSD webhook for *384*2026#.

    Africa's Talking posts form fields, so we read request.values. The
    JSON fallback lets our own simulator and simple tests call the same
    endpoint. `text` holds the choices so far, joined by *:
       ""            -> first screen (choose language)
       "2"           -> Luganda main menu
       "2*1"         -> ask that citizen for a Case ID
       "2*1*JST-..." -> show that case's status
    """
    def field(name, default=""):
        value = request.values.get(name)
        if value is None and request.is_json:
            value = (request.get_json(silent=True) or {}).get(name)
        return str(value or default).strip()

    text = field("text")
    language_key = field("sessionId", "DEMO")  # kept for sandbox logging
    phone_number = field("phoneNumber", "")
    print("[JUSTO USSD session={} phone={} text={!r}]".format(
        language_key, phone_number, text
    ))

    parts = text.split("*") if text else []

    # No choice yet: show the language picker.
    if not parts or parts[0] == "":
        return ussd_reply(USSD_WELCOME)

    language = parts[0]
    if language not in USSD_STRINGS:
        return ussd_reply("END Invalid language selection. Please dial *384*2026# again.")

    strings = USSD_STRINGS[language]

    # Language chosen, but no menu option yet.
    if len(parts) == 1:
        return ussd_reply(strings["main_menu"])

    option = parts[1]

    if len(parts) == 2:
        if option == "1":
            return ussd_reply(strings["enter_case_id"])
        if option == "2":
            return ussd_reply(strings["fees_info"])
        if option == "3":
            return ussd_reply(strings["appeal_info"])
        if option == "4":
            return ussd_reply(strings["quorum_info"])
        return ussd_reply(strings["invalid_option"])

    # Option 1 with a Case ID typed in.
    if len(parts) == 3 and option == "1":
        lookup_id = parts[2].strip().upper()
        connection = get_db()
        row = connection.execute(
            "SELECT * FROM cases WHERE UPPER(case_id) = ?", (lookup_id,)
        ).fetchone()
        connection.close()
        if row is None:
            return ussd_reply(strings["case_not_found"])
        case = dict(row)
        return ussd_reply(
            strings["case_status"].format(
                case_id=case["case_id"],
                court=case["village_court"],
                a=case["complainant_name"],
                b=case["respondent_name"],
                status=case["status"],
                hearing=case["hearing_date"] or "-",
                hash=case["verification_hash"],
            )
        )

    return ussd_reply(strings["goodbye"])


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
