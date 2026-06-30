"""Spanish (CSV) team names -> English names used by API-Football / common feeds."""

SPANISH_TO_ENGLISH: dict[str, str] = {
    "México": "Mexico",
    "Mexico": "Mexico",
    "Sudáfrica": "South Africa",
    "Sudafrica": "South Africa",
    "Corea": "South Korea",
    "Republica Checa": "Czech Republic",
    "República Checa": "Czech Republic",
    "Canadá": "Canada",
    "Canada": "Canada",
    "Bosnia y Herzegovina": "Bosnia and Herzegovina",
    "USA": "United States",
    "Estados Unidos": "United States",
    "Paraguay": "Paraguay",
    "Qatar": "Qatar",
    "Suiza": "Switzerland",
    "Brasil": "Brazil",
    "Marruecos": "Morocco",
    "Haití": "Haiti",
    "Haiti": "Haiti",
    "Escocia": "Scotland",
    "Australia": "Australia",
    "Turquía": "Turkey",
    "Turquia": "Turkey",
    "Alemania": "Germany",
    "Curazao": "Curacao",
    "Holanda": "Netherlands",
    "Japón": "Japan",
    "Japon": "Japan",
    "Costa de Marfil": "Ivory Coast",
    "Ecuador": "Ecuador",
    "Suecia": "Sweden",
    "Túnez": "Tunisia",
    "Tunez": "Tunisia",
    "España": "Spain",
    "Espana": "Spain",
    "Cabo Verde": "Cape Verde",
    "Bélgica": "Belgium",
    "Belgica": "Belgium",
    "Egipto": "Egypt",
    "Arabia Saudita": "Saudi Arabia",
    "Uruguay": "Uruguay",
    "Irán": "Iran",
    "Iran": "Iran",
    "Nueva Zelanda": "New Zealand",
    "Francia": "France",
    "Senegal": "Senegal",
    "Iraq": "Iraq",
    "Irak": "Iraq",
    "Noruega": "Norway",
    "Argentina": "Argentina",
    "Argelia": "Algeria",
    "Austria": "Austria",
    "Jordania": "Jordan",
    "Portugal": "Portugal",
    "Congo": "Congo",
    "Inglaterra": "England",
    "Croacia": "Croatia",
    "Ghana": "Ghana",
    "Panamá": "Panama",
    "Panama": "Panama",
    "Uzbekistán": "Uzbekistan",
    "Uzbekistan": "Uzbekistan",
    "Colombia": "Colombia",
}

# API sometimes returns alternate spellings
ENGLISH_ALIASES: dict[str, set[str]] = {
    "South Korea": {"korea republic", "korea", "south korea"},
    "Czech Republic": {"czechia", "czech republic"},
    "United States": {"united states", "usa", "us", "u.s.", "u.s.a."},
    "USA": {"united states", "usa", "us"},
    "Ivory Coast": {"cote d'ivoire", "côte d'ivoire", "ivory coast", "côte d’ivoire"},
    "Curaçao": {"curaçao", "curacao"},
    "Netherlands": {"holland", "netherlands"},
    "Cape Verde": {"cabo verde", "cape verde", "cape verde islands"},
    "Bosnia and Herzegovina": {"bosnia", "bosnia-herzegovina", "bosnia and herzegovina"},
    "Congo": {"congo dr", "dr congo", "congo", "republic of the congo"},
    "Iran": {"ir iran", "iran"},
    "Turkey": {"türkiye", "turkiye", "turkey", "turkiye"},
    "Curacao": {"curaçao", "curacao"},
    "Saudi Arabia": {"saudi arabia", "ksa"},
    "South Korea": {"korea republic", "korea", "south korea", "korea rep"},
}


def to_english(spanish_name: str) -> str:
    return SPANISH_TO_ENGLISH.get(spanish_name, spanish_name)


def _norm(name: str) -> str:
    return (
        name.lower()
        .replace(".", "")
        .replace("-", " ")
        .replace("'", "")
        .strip()
    )


def names_match(our_spanish: str, api_english: str) -> bool:
    target = to_english(our_spanish)
    a = _norm(api_english)
    b = _norm(target)
    if a == b or a in b or b in a:
        return True
    aliases = ENGLISH_ALIASES.get(target, set())
    if a in aliases:
        return True
    for al in aliases:
        if al in a or a in al:
            return True
    return False
