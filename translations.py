# translations.py
# All the words the phone (USSD) service and SMS messages use.
# Africa's Talking expects a reply starting with CON (more input needed)
# or END (session finished), so every string below starts that way.
# Add a new language by copying one block and giving it a new number key.

# The first screen: choose a language. This one is shared because the
# citizen has not chosen a language yet.
USSD_WELCOME = (
    "CON Welcome to JUSTO - Access to Justice\n"
    "Choose language / Londa Olulimi:\n"
    "1. English\n"
    "2. Luganda\n"
    "3. Runyankole-Rukiga\n"
    "4. Swahili\n"
    "5. Luo (Acholi)"
)


USSD_STRINGS = {
    "1": {  # English
        "lang_name": "English",
        "main_menu": (
            "CON JUSTO - Grassroots Justice\n"
            "1. Check Case Status\n"
            "2. Official LC Court Fees\n"
            "3. How to Appeal (14 Days)\n"
            "4. Court Quorum Rule"
        ),
        "enter_case_id": "CON Enter your Case ID (e.g. JST-2026-001):",
        "case_not_found": "END Case not found. Visit your LC1 Secretary for your receipt code.",
        "case_status": (
            "END JUSTO Case: {case_id}\n"
            "Court: {court}\n"
            "Parties: {a} vs {b}\n"
            "Status: {status}\n"
            "Hearing: {hearing}\n"
            "Verify code: {hash}"
        ),
        "fees_info": (
            "END Official LC Fees:\n"
            "- LC1 filing: UGX 2,000\n"
            "- LC2 appeal: UGX 5,000\n"
            "Demand an official receipt for every payment."
        ),
        "appeal_info": (
            "END Appeal Guide:\n"
            "You have 14 days from judgment to appeal from LC1 to LC2, then to the "
            "Chief Magistrate's Court. Quote your verification code."
        ),
        "quorum_info": (
            "END Quorum Rule:\n"
            "An LC1/LC2 hearing is valid only when at least 5 members sit, "
            "including at least 2 women."
        ),
        "invalid_option": "END Invalid option. Please dial *384*2026# again.",
        "goodbye": "END Thank you for using JUSTO.",
    },
    "2": {  # Luganda
        "lang_name": "Luganda",
        "main_menu": (
            "CON JUSTO - Obwenkanya mu Kyalo\n"
            "1. Kebera omusango gwo\n"
            "2. Ebisale bya Kooti ya LC\n"
            "3. Engeri y'okujulira (ennaku 14)\n"
            "4. Etteeka ly'Abakiise ba Kooti"
        ),
        "enter_case_id": "CON Yingiza ennamba y'omusango gwo (nga JST-2026-001):",
        "case_not_found": "END Omusango tegutuuze. Buuza Omuwandiisi wa LC1 okukuwa koodi.",
        "case_status": (
            "END Omusango gwa JUSTO: {case_id}\n"
            "Kooti: {court}\n"
            "Abalwanyi: {a} ne {b}\n"
            "Embeera: {status}\n"
            "Ekuungana: {hearing}\n"
            "Koodi: {hash}"
        ),
        "fees_info": (
            "END Ebisale bya LC:\n"
            "- Okuwaaba ku LC1: UGX 2,000\n"
            "- Okujulira ku LC2: UGX 5,000\n"
            "Saba risiiti ya SMS buli lukya."
        ),
        "appeal_info": (
            "END Okujulira:\n"
            "Olina ennaku 14 okuva ku kusalwa kw'omusango okujulira ku LC2, "
            "n'oluvanyuma eri Omulamuzi. Twala koodi yo eya JUSTO."
        ),
        "quorum_info": (
            "END Etteeka ly'Abakiise:\n"
            "Kooti ya LC1/LC2 etuula mu mateeka nga eriko abakiise abatakka wansi wa 5, "
            "nga kuliko abakyala 2."
        ),
        "invalid_option": "END Ekika kino si kituufu. Yeeyambula *384*2026#.",
        "goodbye": "END Webale okukozesa JUSTO.",
    },
    "3": {  # Runyankole-Rukiga
        "lang_name": "Runyankole-Rukiga",
        "main_menu": (
            "CON JUSTO - Oburinganiza omu Kyaro\n"
            "1. Reeba embeera y'omushango\n"
            "2. Ebisale bya Kooti ya LC\n"
            "3. Okujurira (ebiro 14)\n"
            "4. Ebiragiro by'Abakiise ba Kooti"
        ),
        "enter_case_id": "CON Handiika enamba y'omushango (nk'ekyokureeberaho JST-2026-001):",
        "case_not_found": "END Omushango tiyaboneka. Buuza Omuhandiiki wa LC1.",
        "case_status": (
            "END Omushango gwa JUSTO: {case_id}\n"
            "Kooti: {court}\n"
            "Abashubuzi: {a} na {b}\n"
            "Embeera: {status}\n"
            "Ebiro by'okuigwa: {hearing}\n"
            "Koodi: {hash}"
        ),
        "fees_info": (
            "END Ebisale bya LC:\n"
            "- Okutwara omushango LC1: UGX 2,000\n"
            "- Okujurira LC2: UGX 5,000\n"
            "Shaba risiiti ya SMS ya JUSTO."
        ),
        "appeal_info": (
            "END Okujurira:\n"
            "Oine ebiro 14 kuruga aha kusharamu kw'omushango okujurira ahari LC2, "
            "ninga ahari Omuramuzi. Tokwerwa koodi ya JUSTO."
        ),
        "quorum_info": (
            "END Ebiragiro by'Abakiise:\n"
            "Kooti ya LC1/LC2 neija omu biragiro ku erimu abakiise 5 kandi harimu abakazi 2."
        ),
        "invalid_option": "END Ekicweka eki tikirikwa. Subizamu *384*2026#.",
        "goodbye": "END Webale kukoresa JUSTO.",
    },
    "4": {  # Swahili
        "lang_name": "Swahili",
        "main_menu": (
            "CON JUSTO - Haki Mashinani\n"
            "1. Angalia hali ya kesi\n"
            "2. Ada rasmi za Mahakama ya LC\n"
            "3. Jinsi ya kukata rufaa (siku 14)\n"
            "4. Sheria ya akidi ya mahakama"
        ),
        "enter_case_id": "CON Weka Namba ya Kesi ya JUSTO (mfano JST-2026-001):",
        "case_not_found": "END Namba ya kesi haijapatikana. Wasiliana na Katibu wa LC1.",
        "case_status": (
            "END Kesi ya JUSTO: {case_id}\n"
            "Mahakama: {court}\n"
            "Wahusika: {a} dhidi ya {b}\n"
            "Hali: {status}\n"
            "Sikio: {hearing}\n"
            "Kodi: {hash}"
        ),
        "fees_info": (
            "END Ada za LC:\n"
            "- Kufungua kesi LC1: UGX 2,000\n"
            "- Rufaa LC2: UGX 5,000\n"
            "Dai risiti rasmi kwa kila malipo."
        ),
        "appeal_info": (
            "END Mwongozo wa Rufaa:\n"
            "Una siku 14 baada ya hukumu kukata rufaa kwenda LC2, kisha kwa "
            "Mahakama ya Hakimu. Nukuu kodi yako ya JUSTO."
        ),
        "quorum_info": (
            "END Sheria ya Akidi:\n"
            "Kikao cha LC1/LC2 ni halali tu kikiwa na wajumbe wasiopungua 5, "
            "wakiwemo wanawake angalau 2."
        ),
        "invalid_option": "END Chaguo si sahihi. Pigia tena *384*2026#.",
        "goodbye": "END Asante kwa kutumia JUSTO.",
    },
    "5": {  # Luo / Acholi
        "lang_name": "Luo (Acholi)",
        "main_menu": (
            "CON JUSTO - Ngol Matir i Gang\n"
            "1. Nen kit ma koppi tye kwede\n"
            "2. Wel lim me Kot pa LC\n"
            "3. Kit me cwalo kop i Kot Malo (nino 14)\n"
            "4. Cik pa Ludito Kot"
        ),
        "enter_case_id": "CON Ket namba me koppi (calo JST-2026-001):",
        "case_not_found": "END Namba me koppe pe ononge. Penyo Karan pa LC1.",
        "case_status": (
            "END Kop pa JUSTO: {case_id}\n"
            "Kot: {court}\n"
            "Ludwol: {a} ki {b}\n"
            "Kit: {status}\n"
            "Nino me winyo: {hearing}\n"
            "Koodi: {hash}"
        ),
        "fees_info": (
            "END Wel lim me Kot pa LC:\n"
            "- Cako kop i LC1: UGX 2,000\n"
            "- Cwalo kop i LC2: UGX 5,000\n"
            "Kway waraga SMS pa JUSTO."
        ),
        "appeal_info": (
            "END Kit me Cwalo Kop Malo:\n"
            "Itye ki nino 14 me cwalo koppi i LC2, ka odoko ci bot Jangol-kop madit. "
            "Ket koodi ni me JUSTO."
        ),
        "quorum_info": (
            "END Cik pa Ludito Kot:\n"
            "Kot pa LC1/LC2 myero obed ki ludito 5, ki mon ma pe gikwo 2."
        ),
        "invalid_option": "END Lacwec ada pe. Cwale kendo *384*2026#.",
        "goodbye": "END Apwoyo ki JUSTO.",
    },
}


# SMS text used by the court terminal and the citizen app.
# Using templates here keeps every message consistent and easy to translate.
SMS_TEMPLATES = {
    "case_receipt": (
        "JUSTO receipt: Case {case_id} ({complainant}) was registered. "
        "Hearing: {hearing}. Verify code: {code}. Dial *384*2026# to track."
    ),
    "referral_notice": (
        "JUSTO notice: Case {case_id} cannot be heard at LC1. "
        "Referral: {referral}. Ref: {code}."
    ),
    "status_update": (
        "JUSTO LC1 update: Case {case_id} is now {status}. "
        "Verify code: {code}. Dial *384*2026# to track."
    ),
    "court_reply": "JUSTO court reply ({case_id}): {body}",
}
