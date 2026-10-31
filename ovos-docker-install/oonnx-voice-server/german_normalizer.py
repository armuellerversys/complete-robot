import re
from num2words import num2words

# Custom vocabulary and smart home terminology dictionary
# Add any project terms, room names, or acronyms here.
# Keys are regular expression patterns (case-insensitive search).
CUSTOM_VOCABULARY = {
    r"\bPi\b": "Pii",                      # Ensures proper pronunciation of "Pi"
    r"\bOllama\b": "Ohlama",
    r"\bDocker\b": "Docker",
    r"\bAPI\b": "A P I",
    r"\bWohnzimmer\b": "Wohnzimmer",
    r"\bKüche\b": "Küche",
    r"\bSchlafzimmer\b": "Schlafzimmer",
    r"\bHeizung\b": "Heizung",
    r"\bTemperatur\b": "Temperatur",
}

# Common German TTS abbreviation replacement dictionary
ABBREVIATIONS = {
    r"\bz\.\s*B\.\b": "zum Beispiel",
    r"\bd\.\s*h\.\b": "das heißt",
    r"\bca\.\b": "circa",
    r"\bHr\.\b": "Herr",
    r"\bFr\.\b": "Frau",
    r"\bDr\.\b": "Doktor",
    r"\bProf\.\b": "Professor",
    r"\bStk\.\b": "Stück",
    r"\bsog\.\b": "sogenannte",
}

def normalize_german_text(text: str) -> str:
    """Normalizes German text for TTS, expanding custom vocabulary, abbreviations, numbers, and units."""
    if not text:
        return text

    # 1. Expand Custom Vocabulary (Smart Home terms, technical jargon)
    for pattern, replacement in CUSTOM_VOCABULARY.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # 2. Expand standard abbreviations
    for pattern, replacement in ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # 3. Currency: "3,50 €" -> "drei Euro fünfzig Cent"
    def _replace_currency(match):
        euros = int(match.group(1))
        cents = match.group(3)
        euro_str = num2words(euros, lang='de') + " Euro"
        if cents and int(cents) > 0:
            cent_str = num2words(int(cents), lang='de') + " Cent"
            return f"{euro_str} {cent_str}"
        return euro_str

    text = re.sub(r'(\d+)(,(\d{1,2}))?\s*€', _replace_currency, text)

    # 4. Time: "18:30 Uhr" -> "achtzehn Uhr dreißig"
    def _replace_time(match):
        hours = int(match.group(1))
        minutes = int(match.group(2))
        hours_str = num2words(hours, lang='de')
        if minutes > 0:
            minutes_str = num2words(minutes, lang='de')
            return f"{hours_str} Uhr {minutes_str}"
        return f"{hours_str} Uhr"

    text = re.sub(r'\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\s*(Uhr)?\b', _replace_time, text)

    # 5. Units: "1,5 kg" -> "eins komma fünf Kilogramm"
    units_map = {
        'kg': 'Kilogramm', 'g': 'Gramm', 'km': 'Kilometer', 
        'm': 'Meter', 'cm': 'Zentimeter', 'l': 'Liter', 'min': 'Minuten'
    }
    for unit, full_word in units_map.items():
        def _replace_unit(m):
            num = m.group(1).replace(',', ' komma ')
            return f"{num} {full_word}"
        text = re.sub(rf'\b(\d+(?:,\d+)?)\s*{unit}\b', _replace_unit, text, flags=re.IGNORECASE)

    # 6. Decimals: "1,5" -> "eins komma fünf"
    def _replace_decimals(match):
        whole = num2words(int(match.group(1)), lang='de')
        dec = num2words(int(match.group(2)), lang='de')
        return f"{whole} komma {dec}"

    text = re.sub(r'\b(\d+),(\d+)\b', _replace_decimals, text)

    # 7. Integers: "42" -> "zweiundvierzig"
    def _replace_integers(match):
        return num2words(int(match.group(0)), lang='de')

    text = re.sub(r'\b\d+\b', _replace_integers, text)

    return text