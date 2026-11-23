# legal_rules.py
# JUSTO's rule book.
# This file knows nothing about Flask or the database. Its only job is to
# answer one question: "May an LC1 court lawfully hear this matter?"
# Keeping the rules here makes them easy to read and easy to change.

# The most a village (LC1) or parish (LC2) court may award in a civil claim.
# 2,000,000 Ugandan shillings is the statutory ceiling.
LC_MONETARY_LIMIT_UGX = 2_000_000

# Section 8 of the Local Council Courts Act, 2006:
# a bench needs at least 5 members, and at least 2 of them must be women.
QUORUM_MIN_MEMBERS = 5
QUORUM_MIN_WOMEN = 2

# Matters an LC1 court is NOT allowed to hear.
# For each one we store: a friendly label, where the citizen must go instead,
# and a plain-English reason we can show on screen.
PROHIBITED_CATEGORIES = {
    "criminal": {
        "label": "Criminal offence (assault, theft, etc.)",
        "referral": "Uganda Police Force, then the Magistrate's Court",
        "reason": "LC courts only handle civil and customary matters, not criminal prosecutions.",
    },
    "registered_land": {
        "label": "Registered land title dispute",
        "referral": "Chief Magistrate's Court / High Court Land Division",
        "reason": "LC courts may mediate customary boundaries, but cannot decide registered land ownership.",
    },
    "divorce_custody": {
        "label": "Statutory divorce or child custody order",
        "referral": "Family and Children Court / Chief Magistrate's Court",
        "reason": "Ending a statutory marriage or ordering custody is outside LC1 power.",
    },
}

# Matters an LC1 court IS allowed to hear.
ALLOWED_CATEGORIES = {
    "minor_debt": "Minor debt / breach of contract",
    "customary_land": "Customary land boundary / trespass",
    "mediation": "Family / neighbourhood mediation",
    "property_damage": "Damage to property / livestock trespass",
}


def category_label(category):
    """Turn a category key into text a person can read. Unknown keys pass through."""
    if category in ALLOWED_CATEGORIES:
        return ALLOWED_CATEGORIES[category]
    if category in PROHIBITED_CATEGORIES:
        return PROHIBITED_CATEGORIES[category]["label"]
    return category


def validate_jurisdiction(
    category,
    claim_amount_ugx=0,
    quorum_present=QUORUM_MIN_MEMBERS,
    women_present=QUORUM_MIN_WOMEN,
):
    """
    Check one dispute against the Act. Returns a simple dictionary:
      is_valid             - True only if LC1 may hear it with this bench
      status               - a short machine-readable result
      issues               - list of problems found (empty when valid)
      recommended_referral - where to send the matter, or how to fix the bench
    """
    issues = []
    referral = None

    # 1. Wrong kind of case? Send it to the correct court or agency.
    if category in PROHIBITED_CATEGORIES:
        rule = PROHIBITED_CATEGORIES[category]
        issues.append("Wrong court: " + rule["reason"])
        referral = rule["referral"]

    # 2. Is the claim worth more than LC1 is allowed to award?
    if claim_amount_ugx > LC_MONETARY_LIMIT_UGX:
        issues.append(
            "Money limit: UGX {:,} is above the LC limit of UGX {:,}.".format(
                claim_amount_ugx, LC_MONETARY_LIMIT_UGX
            )
        )
        if referral is None:
            referral = "Chief Magistrate's Court (Small Claims Registry)"

    # 3. Is the bench lawful? If not, the ruling would be invalid.
    if quorum_present < QUORUM_MIN_MEMBERS or women_present < QUORUM_MIN_WOMEN:
        issues.append(
            "Quorum: {} members recorded ({} women). The law requires at least {} "
            "members including {} women.".format(
                quorum_present, women_present, QUORUM_MIN_MEMBERS, QUORUM_MIN_WOMEN
            )
        )
        if referral is None:
            referral = "Adjourn until a lawful bench sits (5 members, at least 2 women)."

    if issues:
        return {
            "is_valid": False,
            "status": "OUT_OF_JURISDICTION_OR_QUORUM",
            "issues": issues,
            "recommended_referral": referral,
        }

    return {
        "is_valid": True,
        "status": "VALID_FOR_LC_HEARING",
        "issues": [],
        "recommended_referral": None,
    }


# Short answers to the questions citizens ask most often.
# The "keywords" are matched against the question text in lower case.
LEGAL_ANSWERS = [
    {
        "keywords": ["quorum", "members", "women", "bench", "committee", "valid"],
        "answer": (
            "Section 8 of the Local Council Courts Act, 2006 says an LC1 or LC2 bench "
            "must have at least 5 members, including at least 2 women. A ruling made "
            "without that quorum is invalid."
        ),
    },
    {
        "keywords": ["appeal", "14 days", "lc2", "magistrate", "dissatisfied"],
        "answer": (
            "You have 14 days from the date of judgment to appeal from LC1 to the Parish "
            "(LC2) Court, and then to the Chief Magistrate's Court. Ask the Secretary for "
            "your certified record and verification code."
        ),
    },
    {
        "keywords": ["fee", "fees", "cost", "pay", "receipt", "money"],
        "answer": (
            "Official LC court fees are small and regulated (about UGX 2,000 at LC1). "
            "You must be given an official receipt. Demand a JUSTO SMS receipt for every payment."
        ),
    },
    {
        "keywords": ["police", "criminal", "theft", "assault", "divorce", "custody", "title"],
        "answer": (
            "Criminal matters go to the Uganda Police Force and Magistrate's Court; registered "
            "land titles go to the Chief Magistrate's Court; statutory divorce and custody go "
            "to the Family and Children Court. An LC1 court must refer these matters out."
        ),
    },
    {
        "keywords": ["limit", "amount", "million", "above", "2,000,000", "2000000"],
        "answer": (
            "An LC1 court may award up to UGX 2,000,000 in a civil claim. A larger claim must "
            "be taken to the Chief Magistrate's Court."
        ),
    },
    {
        "keywords": ["lost", "altered", "verify", "record", "hash", "code"],
        "answer": (
            "Every JUSTO case has a 12-character verification code printed on its record. "
            "Use the Verify a Record tab in the citizen app, or dial *384*2026#, to check it."
        ),
    },
]


def answer_legal_question(question):
    """Return a short legal-guide answer for a citizen's question."""
    text = (question or "").lower().strip()
    for item in LEGAL_ANSWERS:
        if any(keyword in text for keyword in item["keywords"]):
            return item["answer"]
    return (
        "Under the Local Council Courts Act, 2006 an LC1 court needs a quorum of at least "
        "5 members including 2 women, may award up to UGX 2,000,000, and must keep a written "
        "record so you can appeal within 14 days."
    )
