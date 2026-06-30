"""Team names (Spanish as in CSV) -> ISO 3166-1 alpha-2 for flags (flagcdn.com / emoji)."""

TEAM_FLAGS: dict[str, str] = {
    "México": "mx",
    "Mexico": "mx",
    "Sudáfrica": "za",
    "Sudafrica": "za",
    "Corea": "kr",
    "Republica Checa": "cz",
    "República Checa": "cz",
    "Canadá": "ca",
    "Canada": "ca",
    "Bosnia y Herzegovina": "ba",
    "USA": "us",
    "Paraguay": "py",
    "Qatar": "qa",
    "Suiza": "ch",
    "Brasil": "br",
    "Marruecos": "ma",
    "Haití": "ht",
    "Haiti": "ht",
    "Escocia": "gb-sct",
    "Australia": "au",
    "Turquía": "tr",
    "Turquia": "tr",
    "Alemania": "de",
    "Curazao": "cw",
    "Holanda": "nl",
    "Japón": "jp",
    "Japon": "jp",
    "Costa de Marfil": "ci",
    "Ecuador": "ec",
    "Suecia": "se",
    "Túnez": "tn",
    "Tunez": "tn",
    "España": "es",
    "Espana": "es",
    "Cabo Verde": "cv",
    "Bélgica": "be",
    "Belgica": "be",
    "Egipto": "eg",
    "Arabia Saudita": "sa",
    "Uruguay": "uy",
    "Irán": "ir",
    "Iran": "ir",
    "Nueva Zelanda": "nz",
    "Francia": "fr",
    "Senegal": "sn",
    "Iraq": "iq",
    "Irak": "iq",
    "Noruega": "no",
    "Argentina": "ar",
    "Argelia": "dz",
    "Austria": "at",
    "Jordania": "jo",
    "Portugal": "pt",
    "Congo": "cg",
    "Inglaterra": "gb-eng",
    "Croacia": "hr",
    "Ghana": "gh",
    "Panamá": "pa",
    "Panama": "pa",
    "Uzbekistán": "uz",
    "Uzbekistan": "uz",
    "Colombia": "co",
    # Placeholders
    "16vos Por Definir": "",
    "8vos Por Definir": "",
    "4tos Por Definir": "",
    "Semi Por Definir": "",
    "Final Por Definir": "",
    "3ero Por Definir": "",
    "Por Definir": "",
}

# Kickoff schedule for WC 2026 (UTC, naive — always interpret as UTC in API/UI).
# Full group stage (1–72) aligned to FIFA 2026 calendar + venue time zones (EDT=UTC-4, CDT=UTC-5,
# PDT=UTC-7, Mexico City/Guadalajara/Monterrey typically UTC-6 in June).
# Quiniela home/away order may swap vs FIFA listing; times follow the fixture pair.
# Knockout 73+ placeholders until teams known (R32 from ~28 Jun). Bump SCHEDULE_REVISION on edits.
SCHEDULE_REVISION = 4

MATCH_KICKOFFS_UTC: dict[int, str] = {
    # ── Matchday 1 ───────────────────────────────────────
    1: "2026-06-11T19:00:00",   # México–Sudáfrica (Ciudad de México)
    2: "2026-06-12T02:00:00",   # Corea–República Checa (Guadalajara; late 11 Jun local)
    3: "2026-06-12T19:00:00",   # Canadá–Bosnia (Toronto)
    4: "2026-06-13T01:00:00",   # USA–Paraguay (Los Ángeles)
    5: "2026-06-13T22:00:00",   # Qatar–Suiza (Santa Clara)
    6: "2026-06-13T19:00:00",   # Brasil–Marruecos (Nueva York / NJ)
    7: "2026-06-13T16:00:00",   # Haití–Escocia (Boston)
    8: "2026-06-14T02:00:00",   # Australia–Turquía (Vancouver)
    9: "2026-06-14T19:00:00",   # Alemania–Curazao (Houston)
    10: "2026-06-14T22:00:00",  # Holanda–Japón (Dallas)
    11: "2026-06-14T16:00:00",  # Costa de Marfil–Ecuador (Filadelfia)
    12: "2026-06-15T01:00:00",  # Suecia–Túnez (Monterrey)
    13: "2026-06-15T19:00:00",  # España–Cabo Verde (Atlanta)
    14: "2026-06-15T22:00:00",  # Bélgica–Egipto (Seattle)
    15: "2026-06-15T16:00:00",  # Arabia Saudita–Uruguay (Miami)
    16: "2026-06-16T02:00:00",  # Irán–Nueva Zelanda (Los Ángeles)
    17: "2026-06-16T19:00:00",  # Francia–Senegal (Nueva York / NJ)
    18: "2026-06-16T16:00:00",  # Iraq–Noruega (Boston)
    19: "2026-06-16T22:00:00",  # Argentina–Argelia (Kansas City)
    20: "2026-06-17T02:00:00",  # Austria–Jordania (Santa Clara)
    21: "2026-06-17T19:00:00",  # Portugal–Congo (Houston)
    22: "2026-06-17T22:00:00",  # Inglaterra–Croacia (Dallas)
    23: "2026-06-17T16:00:00",  # Ghana–Panamá (Toronto)
    24: "2026-06-17T19:00:00",  # Uzbekistán–Colombia (Ciudad de México)
    # ── Matchday 2 ───────────────────────────────────────
    25: "2026-06-18T16:00:00",  # Sudáfrica–República Checa (Atlanta; Group A MD2)
    26: "2026-06-18T19:00:00",  # Bosnia–Suiza (Los Ángeles; Group B)
    27: "2026-06-18T22:00:00",  # Canadá–Qatar (Vancouver)
    28: "2026-06-19T01:00:00",  # México–Corea (Guadalajara)
    29: "2026-06-19T22:00:00",  # USA–Australia (Seattle)
    30: "2026-06-19T16:00:00",  # Marruecos–Escocia (Boston; Group C)
    31: "2026-06-19T19:00:00",  # Brasil–Haití (Filadelfia)
    32: "2026-06-20T02:00:00",  # Paraguay–Turquía (Santa Clara; Group D)
    33: "2026-06-20T17:00:00",  # Holanda–Suecia (Houston; Group F)
    34: "2026-06-20T19:00:00",  # Alemania–Costa de Marfil (Toronto; Group E)
    35: "2026-06-20T22:00:00",  # Curazao–Ecuador (Kansas City)
    36: "2026-06-21T01:00:00",  # Japón–Túnez (Monterrey)
    37: "2026-06-21T16:00:00",  # España–Arabia Saudita (Atlanta 12:00 ET)
    38: "2026-06-21T19:00:00",  # Bélgica–Irán (Los Ángeles; Group G)
    39: "2026-06-21T22:00:00",  # Cabo Verde–Uruguay (Miami 18:00 ET)
    40: "2026-06-22T01:00:00",  # Egipto–Nueva Zelanda (Vancouver)
    41: "2026-06-22T17:00:00",  # Argentina–Austria (Dallas; Group J)
    42: "2026-06-22T21:00:00",  # Francia–Iraq (Filadelfia; Group I)
    43: "2026-06-23T00:00:00",  # Senegal–Noruega (Nueva York / NJ)
    44: "2026-06-23T03:00:00",  # Argelia–Jordania (Santa Clara; Group J)
    45: "2026-06-23T17:00:00",  # Portugal–Uzbekistán (Houston; Group K)
    46: "2026-06-23T20:00:00",  # Inglaterra–Ghana (Boston; Group L)
    47: "2026-06-23T23:00:00",  # Croacia–Panamá (Toronto)
    48: "2026-06-24T02:00:00",  # Congo–Colombia (Guadalajara; Group K)
    # ── Matchday 3 (final group games; groups finish same day in pairs) ──
    49: "2026-06-24T19:00:00",  # Bosnia–Qatar (Seattle; Group B)
    50: "2026-06-24T19:00:00",  # Suiza–Canadá (Vancouver; Group B)
    51: "2026-06-24T22:00:00",  # Marruecos–Haití (Atlanta; Group C)
    52: "2026-06-24T22:00:00",  # Escocia–Brasil (Miami; Group C)
    53: "2026-06-25T01:00:00",  # Sudáfrica–Corea (Monterrey; Group A)
    54: "2026-06-25T01:00:00",  # República Checa–México (Ciudad de México; Group A)
    55: "2026-06-25T20:00:00",  # Curazao–Costa de Marfil (Filadelfia; Group E)
    56: "2026-06-25T20:00:00",  # Ecuador–Alemania (Nueva York / NJ; Group E)
    57: "2026-06-25T20:00:00",  # Japón–Suecia (Dallas; Group F)
    58: "2026-06-25T20:00:00",  # Túnez–Holanda (Kansas City; Group F)
    59: "2026-06-25T20:00:00",  # Paraguay–Australia (Santa Clara; Group D)
    60: "2026-06-25T20:00:00",  # Turquía–USA (Los Ángeles; Group D)
    61: "2026-06-26T16:00:00",  # Senegal–Iraq (Toronto; Group I)
    62: "2026-06-26T16:00:00",  # Noruega–Francia (Boston; Group I)
    63: "2026-06-26T19:00:00",  # Cabo Verde–Arabia Saudita (Houston; Group H)
    64: "2026-06-26T19:00:00",  # Uruguay–España (Guadalajara; Group H)
    65: "2026-06-26T22:00:00",  # Egipto–Irán (Seattle; Group G)
    66: "2026-06-26T22:00:00",  # Nueva Zelanda–Bélgica (Vancouver; Group G)
    67: "2026-06-27T19:00:00",  # Croacia–Ghana (Filadelfia; Group L)
    68: "2026-06-27T19:00:00",  # Panamá–Inglaterra (Nueva York / NJ; Group L)
    69: "2026-06-27T22:00:00",  # Congo–Uzbekistán (Atlanta; Group K)
    70: "2026-06-27T22:00:00",  # Colombia–Portugal (Miami; Group K)
    71: "2026-06-27T22:00:00",  # Argelia–Austria (Kansas City; Group J)
    72: "2026-06-27T22:00:00",  # Jordania–Argentina (Dallas; Group J)
    # ── Knockout placeholders (R32 from ~28 Jun; times TBD / staggered TV windows) ──
    73: "2026-06-28T16:00:00",
    74: "2026-06-28T19:00:00",
    75: "2026-06-28T22:00:00",
    76: "2026-06-29T16:00:00",
    77: "2026-06-29T19:00:00",
    78: "2026-06-29T22:00:00",
    79: "2026-06-30T16:00:00",
    80: "2026-06-30T19:00:00",
    81: "2026-06-30T22:00:00",
    82: "2026-07-01T16:00:00",
    83: "2026-07-01T19:00:00",
    84: "2026-07-01T22:00:00",
    85: "2026-07-02T16:00:00",
    86: "2026-07-02T19:00:00",
    87: "2026-07-02T22:00:00",
    88: "2026-07-03T16:00:00",
    89: "2026-07-04T16:00:00",  # R16
    90: "2026-07-04T19:00:00",
    91: "2026-07-05T16:00:00",
    92: "2026-07-05T19:00:00",
    93: "2026-07-06T16:00:00",
    94: "2026-07-06T19:00:00",
    95: "2026-07-07T16:00:00",
    96: "2026-07-07T19:00:00",
    97: "2026-07-09T19:00:00",  # QF
    98: "2026-07-10T19:00:00",
    99: "2026-07-11T19:00:00",
    100: "2026-07-12T19:00:00",
    101: "2026-07-14T19:00:00",  # SF
    102: "2026-07-15T19:00:00",
    103: "2026-07-19T19:00:00",  # Final
    104: "2026-07-18T19:00:00",  # 3rd place
}


def get_flag_code(team: str) -> str:
    return TEAM_FLAGS.get(team, "")


def flag_emoji_from_code(code: str) -> str:
    if not code or "-" in code:
        # gb-eng, gb-sct use special handling; return empty and use image URL in frontend
        return ""
    if len(code) != 2:
        return ""
    return chr(0x1F1E6 + ord(code[0].upper()) - ord("A")) + chr(
        0x1F1E6 + ord(code[1].upper()) - ord("A")
    )


def stage_from_match_number(n: int, header: str) -> str:
    if n <= 72:
        return "group"
    if "16vos" in header or (73 <= n <= 88):
        return "r16"
    if "8vos" in header or (89 <= n <= 96):
        return "qf"
    if "4tos" in header or (97 <= n <= 100):
        return "sf"
    if "Semi" in header or n in (101, 102):
        return "sf"
    if "3ero" in header or n == 104:
        return "third"
    if "Final" in header or n == 103:
        return "final"
    return "knockout"
