# segnalazioni/services.py
import re, hashlib

# 1. Stopwords estese: prefissi stradali, articoli e preposizioni articolate
STOPWORDS_VIA = re.compile(
    r'^(via|viale|v\.le|piazza|piaz|p\.zza|p\.za|corso|c\.so|largo|l\.go|vicolo|vcl|strada|str\.da)\s+'
    r'|^(della|dello|degli|delle|del|dell|dei|di|da|in|su|per|con)\s+',
    re.IGNORECASE
)

# Nomi propri comuni da saltare per prediligere il cognome della via
NOMI_PROPRI_COMUNI = {'alessandro', 'tullio', 'camillo', 'giuseppe', 'giovanni', 'luigi', 'francesco', 'mario'}

CONSONANTI = ['b', 'c', 'd', 'f', 'g', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'z']
VOCALI = ['a', 'e', 'i', 'o', 'u']

def generate_strict_fantasy_suffix(seed: str | None) -> str:
    """
    Genera SEMPRE un nome di fantasia di 4 lettere nello schema CVCV (es. rofi, pleo, kima, sobo).
    Evita combinazioni illeggibili come 'eeee', 'eeaa' o stringhe puramente esadecimali.
    """
    seed_str = str(seed or "tree_default_seed").strip()

    # Hash MD5 per generare un valore intero deterministico
    hash_val = int(hashlib.md5(seed_str.encode('utf-8')).hexdigest(), 16)

    # Schema CVCV (Consonante - Vocale - Consonante - Vocale)
    c1 = CONSONANTI[hash_val % len(CONSONANTI)]
    v1 = VOCALI[(hash_val >> 4) % len(VOCALI)]
    c2 = CONSONANTI[(hash_val >> 8) % len(CONSONANTI)]
    v2 = VOCALI[(hash_val >> 12) % len(VOCALI)]

    return f"{c1}{v1}{c2}{v2}"


def extract_street_keyword(address: str | None) -> str:
    """Estrae la parola chiave piu significativa dell'indirizzo."""
    if not address or not str(address).strip():
        return "anon"

    # Prendi solo la parte dell'indirizzo prima del civico e della citta
    addr_clean = address.split(',')[0].strip()

    # Rimuovi prefissi stradali e articoli (ripetutamente se necessario)
    previous = ""
    while previous != addr_clean:
        previous = addr_clean
        addr_clean = STOPWORDS_VIA.sub('', addr_clean).strip()

    # Separa le parole rimanenti
    parole = [p for p in re.findall(r'[a-zA-Z]+', addr_clean.lower()) if len(p) > 1]

    if not parole:
        return "albe"

    # Se ci sono piu parole e la prima e un nome proprio comune, prendiamo il cognome (es. Lamarmora)
    if len(parole) > 1 and parole[0] in NOMI_PROPRI_COMUNI:
        parola_chiave = parole[1]
    else:
        parola_chiave = parole[0]

    return parola_chiave[:4].ljust(4, 'a')


def build_report_code(address: str | None, image_id: str | None) -> str:
    """Funzione principale di generazione del codice xxxx-yyyy."""
    street_prefix = extract_street_keyword(address)
    fantasy_suffix = generate_strict_fantasy_suffix(image_id)
    return f"{street_prefix}-{fantasy_suffix}"
