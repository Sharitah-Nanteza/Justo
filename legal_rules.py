# legal_rules.py

# Statutory monetary ceiling for general civil matters under LC Courts Act (2,000,000 UGX / 100 currency points)
LC_MONETARY_LIMIT_UGX = 2_000_000

# Categories explicitly outside LC1/LC2 civil jurisdiction
PROHIBITED_CATEGORIES = {
    "criminal_felony": {
        "label": "Criminal Offence / Assault / Theft",
        "referral": "Uganda Police Force (Criminal Investigations Department) & Magistrate's Court",
        "reason": "Under the Local Council Courts Act, 2006, LC courts only handle specified civil and customary matters—not criminal prosecutions."
    },
    "registered_land_title": {
        "label": "Registered Land Title Dispute",
        "referral": "Chief Magistrate's Court / High Court Land Division",
        "reason": "LC1/LC2 courts may mediate customary land boundary matters, but disputes over registered land titles fall outside LC jurisdiction."
    },
    "divorce_statutory": {
        "label": "Statutory Marriage Divorce / Child Custody Order",
        "referral": "Chief Magistrate's Court / Family & Children Court",
        "reason": "Dissolution of statutory marriages and formal custody orders must be handled by a Magistrate's Court."
    }
}

ALLOWED_CATEGORIES = {
    "minor_debt": "Minor Debt / Breach of Contract",
    "customary_land_boundary": "Customary Land Boundary / Trespass",
    "domestic_mediation": "Domestic / Neighborhood Peace Mediation",
    "chattel_damage": "Damage to Property / Livestock Trespass"
}


def validate_jurisdiction(category: str, claim_amount_ugx: int, quorum_present: int, women_present: int):
    """
    Validates whether an LC1/LC2 court has lawful jurisdiction and valid quorum to hear a matter.
    Returns a structured verdict dict.
    """
    issues = []
    referral_target = None

    if category in PROHIBITED_CATEGORIES:
        rule = PROHIBITED_CATEGORIES[category]
        issues.append(f"Subject-Matter Bar: {rule['reason']}")
        referral_target = rule["referral"]

    if claim_amount_ugx > LC_MONETARY_LIMIT_UGX:
        issues.append(
            f"Monetary Ceiling Exceeded: Claim of UGX {claim_amount_ugx:,} exceeds the statutory LC limit of UGX {LC_MONETARY_LIMIT_UGX:,}."
        )
        referral_target = referral_target or "Chief Magistrate's Court (Small Claims / Civil Registry)"

    if quorum_present < 5 or women_present < 2:
        issues.append(
            f"Invalid Quorum: Recorded {quorum_present} members ({women_present} women). Section 8 of the Local Council Courts Act requires at least 5 members, including at least 2 women."
        )

    if issues:
        return {
            "is_valid": False,
            "status": "OUT_OF_JURISDICTION_OR_QUORUM",
            "issues": issues,
            "recommended_referral": referral_target or "Adjourn until lawful quorum (5 members, min. 2 women) is constituted."
        }

    return {
        "is_valid": True,
        "status": "VALID_FOR_LC_HEARING",
        "issues": [],
        "recommended_referral": None
    }


LEGAL_FAQ = [
    {
        "keywords": ["quorum", "members", "women", "committee", "abakiise"],
        "answer": (
            "Under Section 8 of the Local Council Courts Act, 2006, the quorum of a village (LC1) or parish (LC2) court "
            "is 5 members, and at least 2 of those members MUST be women. Any ruling made without this quorum is legally invalid."
        )
    },
    {
        "keywords": ["appeal", "appeals", "dissatisfied", "lc2", "magistrate", "14 days", "okujulira"],
        "answer": (
            "Under Section 32 of the Local Council Courts Act, a party dissatisfied with an LC1 judgment has 14 days from the date "
            "of judgment to file an appeal to the Parish (LC2) Court, and subsequently to the Chief Magistrate's Court using the certified record."
        )
    },
    {
        "keywords": ["fee", "fees", "money", "cost", "pay", "ssente", "shillings"],
        "answer": (
            "Official LC court filing fees are regulated under the Local Council Courts Regulations (nominal statutory fees, typically UGX 1,000–5,000 depending on court level). "
            "Every payment must be issued an official receipt; arbitrary charges are unlawful."
        )
    },
    {
        "keywords": ["summons", "refuse", "absent", "attend", "witness"],
        "answer": (
            "Under the Local Council Courts Act, if a respondent duly served with summons fails to appear without reasonable cause, "
            "the court may issue a fresh summons or proceed to hear the complainant's evidence ex parte after verifying proof of service."
        )
    },
    {
        "keywords": ["limit", "amount", "million", "land", "criminal", "theft"],
        "answer": (
            "LC1/LC2 courts handle civil disputes (debts, contracts, property damage) up to UGX 2,000,000 (100 currency points) and customary land/marriage matters. "
            "Criminal offences and registered land title disputes must be referred to Police or the Chief Magistrate's Court."
        )
    }
]


def answer_legal_question(question: str) -> str:
    q = question.lower().strip()
    for item in LEGAL_FAQ:
        if any(kw in q for kw in item["keywords"]):
            return item["answer"]
    return (
        "Under the Local Council Courts Act, 2006, LC1 and LC2 courts must ensure: (1) a quorum of at least 5 members including 2 women, "
        "(2) civil claims within UGX 2,000,000, (3) fair hearing for both parties, and (4) written judgment records enabling appeal within 14 days."
    )