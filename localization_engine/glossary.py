"""Small transparent glossary used for offline smoke tests.

This is not a replacement for IndicTrans2. It exists so the repo can be
exercised on machines where the gated model or large dependencies are not yet
available.
"""

from __future__ import annotations

import re


ELECTRICIAN_GLOSSARIES: dict[str, dict[str, str]] = {
    "hin_Deva": {
        "ac supply": "एसी आपूर्ति",
        "ammeter": "अमीटर",
        "apprentice": "प्रशिक्षु",
        "cable": "केबल",
        "capacitor": "संधारित्र",
        "circuit breaker": "सर्किट ब्रेकर",
        "conduit": "कंड्यूट",
        "control panel": "नियंत्रण पैनल",
        "copper conductor": "तांबा चालक",
        "earthing": "अर्थिंग",
        "electric shock": "बिजली का झटका",
        "electrical load": "विद्युत भार",
        "fuse": "फ्यूज",
        "insulation": "इन्सुलेशन",
        "junction box": "जंक्शन बॉक्स",
        "leakage current": "लीकेज करंट",
        "live wire": "लाइव तार",
        "main switch": "मुख्य स्विच",
        "megger": "मेगर",
        "motor winding": "मोटर वाइंडिंग",
        "neutral wire": "न्यूट्रल तार",
        "phase tester": "फेज टेस्टर",
        "protective device": "सुरक्षा उपकरण",
        "resistance": "प्रतिरोध",
        "safety shoes": "सुरक्षा जूते",
        "single phase": "सिंगल फेज",
        "switch board": "स्विच बोर्ड",
        "terminal block": "टर्मिनल ब्लॉक",
        "three phase": "थ्री फेज",
        "voltage": "वोल्टेज",
        "voltmeter": "वोल्टमीटर",
        "wire stripper": "वायर स्ट्रिपर",
    },
    "gom_Deva": {
        "circuit breaker": "सर्किट ब्रेकर",
        "earthing": "अर्थिंग",
        "fuse": "फ्यूज",
        "insulation": "इन्सुलेशन",
        "voltage": "वोल्टेज",
    },
    "mai_Deva": {
        "circuit breaker": "सर्किट ब्रेकर",
        "earthing": "अर्थिंग",
        "fuse": "फ्यूज",
        "insulation": "इन्सुलेशन",
        "voltage": "वोल्टेज",
    },
    "doi_Deva": {
        "circuit breaker": "सर्किट ब्रेकर",
        "earthing": "अर्थिंग",
        "fuse": "फ्यूज",
        "insulation": "इन्सुलेशन",
        "voltage": "वोल्टेज",
    },
}


def glossary_translate(text: str, target_lang: str) -> str:
    """Return a deterministic glossary-substitution translation hint."""

    glossary = ELECTRICIAN_GLOSSARIES.get(target_lang, {})
    translated = text
    for english, target in sorted(glossary.items(), key=lambda item: len(item[0]), reverse=True):
        translated = re.sub(rf"\b{re.escape(english)}\b", target, translated, flags=re.IGNORECASE)
    return f"[fallback:{target_lang}] {translated}"
