"""Country catalogue.

One row per ISO-2 country code we ship names for. The display name, flag
emoji, currency symbol, and a hand-picked list of 5–7 major cities live
here so the UI doesn't have to mirror them.

Cities are listed roughly by prominence (capital first when applicable),
so a UI picking a default city can take ``cities[0]``.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    code: str       # ISO 3166-1 alpha-2
    name: str       # Display name
    flag: str       # Emoji flag (two regional-indicator chars)
    currency: str   # Symbol or short code, used by economy module
    cities: tuple[str, ...]


def _flag(code: str) -> str:
    base = ord("\U0001F1E6") - ord("A")
    return chr(base + ord(code[0])) + chr(base + ord(code[1]))


# Single source of truth: (code, display, currency, cities)
_RAW: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("AE", "United Arab Emirates", "AED", ("Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Al Ain", "Fujairah", "Ras al-Khaimah")),
    ("AF", "Afghanistan", "AFN", ("Kabul", "Kandahar", "Herat", "Mazar-i-Sharif", "Jalalabad", "Kunduz")),
    ("AL", "Albania", "ALL", ("Tirana", "Durrës", "Vlorë", "Shkodër", "Elbasan", "Korçë")),
    ("AO", "Angola", "AOA", ("Luanda", "Huambo", "Lobito", "Benguela", "Lubango", "Cabinda")),
    ("AR", "Argentina", "ARS", ("Buenos Aires", "Córdoba", "Rosario", "Mendoza", "La Plata", "Mar del Plata", "San Miguel de Tucumán")),
    ("AT", "Austria", "EUR", ("Vienna", "Graz", "Linz", "Salzburg", "Innsbruck", "Klagenfurt")),
    ("AZ", "Azerbaijan", "AZN", ("Baku", "Ganja", "Sumqayit", "Mingachevir", "Lankaran", "Shaki")),
    ("BD", "Bangladesh", "BDT", ("Dhaka", "Chittagong", "Khulna", "Rajshahi", "Sylhet", "Barisal", "Rangpur")),
    ("BE", "Belgium", "EUR", ("Brussels", "Antwerp", "Ghent", "Bruges", "Liège", "Charleroi", "Leuven")),
    ("BF", "Burkina Faso", "XOF", ("Ouagadougou", "Bobo-Dioulasso", "Koudougou", "Banfora", "Ouahigouya")),
    ("BG", "Bulgaria", "BGN", ("Sofia", "Plovdiv", "Varna", "Burgas", "Ruse", "Stara Zagora")),
    ("BH", "Bahrain", "BHD", ("Manama", "Riffa", "Muharraq", "Hamad Town", "Isa Town", "Sitra")),
    ("BI", "Burundi", "BIF", ("Gitega", "Bujumbura", "Muyinga", "Ruyigi", "Ngozi", "Rutana")),
    ("BN", "Brunei", "BND", ("Bandar Seri Begawan", "Kuala Belait", "Seria", "Tutong", "Bangar")),
    ("BO", "Bolivia", "BOB", ("La Paz", "Santa Cruz de la Sierra", "Cochabamba", "Sucre", "Oruro", "Potosí")),
    ("BR", "Brazil", "BRL", ("São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza", "Belo Horizonte", "Manaus")),
    ("BW", "Botswana", "BWP", ("Gaborone", "Francistown", "Molepolole", "Maun", "Serowe", "Selibe Phikwe")),
    ("CA", "Canada", "CAD", ("Toronto", "Montreal", "Vancouver", "Calgary", "Ottawa", "Edmonton", "Quebec City")),
    ("CH", "Switzerland", "CHF", ("Zurich", "Geneva", "Basel", "Bern", "Lausanne", "Lucerne")),
    ("CL", "Chile", "CLP", ("Santiago", "Valparaíso", "Concepción", "Antofagasta", "Viña del Mar", "Temuco")),
    ("CM", "Cameroon", "XAF", ("Yaoundé", "Douala", "Garoua", "Bamenda", "Maroua", "Bafoussam")),
    ("CN", "China", "CNY", ("Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Chengdu", "Chongqing", "Xi'an")),
    ("CO", "Colombia", "COP", ("Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Bucaramanga")),
    ("CR", "Costa Rica", "CRC", ("San José", "Alajuela", "Cartago", "Heredia", "Liberia", "Puntarenas")),
    ("CY", "Cyprus", "EUR", ("Nicosia", "Limassol", "Larnaca", "Paphos", "Famagusta", "Kyrenia")),
    ("CZ", "Czechia", "CZK", ("Prague", "Brno", "Ostrava", "Plzeň", "Liberec", "Olomouc")),
    ("DE", "Germany", "EUR", ("Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart", "Düsseldorf")),
    ("DJ", "Djibouti", "DJF", ("Djibouti", "Ali Sabieh", "Tadjoura", "Obock", "Dikhil", "Arta")),
    ("DK", "Denmark", "DKK", ("Copenhagen", "Aarhus", "Odense", "Aalborg", "Esbjerg", "Randers")),
    ("DZ", "Algeria", "DZD", ("Algiers", "Oran", "Constantine", "Annaba", "Blida", "Setif", "Batna")),
    ("EC", "Ecuador", "USD", ("Quito", "Guayaquil", "Cuenca", "Santo Domingo", "Machala", "Manta")),
    ("EE", "Estonia", "EUR", ("Tallinn", "Tartu", "Narva", "Pärnu", "Kohtla-Järve", "Viljandi")),
    ("EG", "Egypt", "EGP", ("Cairo", "Alexandria", "Giza", "Shubra El Kheima", "Port Said", "Suez", "Luxor")),
    ("ES", "Spain", "EUR", ("Madrid", "Barcelona", "Valencia", "Seville", "Zaragoza", "Málaga", "Bilbao")),
    ("ET", "Ethiopia", "ETB", ("Addis Ababa", "Dire Dawa", "Mek'ele", "Adama", "Gondar", "Hawassa")),
    ("FI", "Finland", "EUR", ("Helsinki", "Espoo", "Tampere", "Vantaa", "Turku", "Oulu")),
    ("FJ", "Fiji", "FJD", ("Suva", "Nadi", "Lautoka", "Labasa", "Ba", "Sigatoka")),
    ("FR", "France", "EUR", ("Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Bordeaux")),
    ("GB", "United Kingdom", "GBP", ("London", "Manchester", "Birmingham", "Edinburgh", "Glasgow", "Liverpool", "Bristol")),
    ("GE", "Georgia", "GEL", ("Tbilisi", "Batumi", "Kutaisi", "Rustavi", "Zugdidi", "Gori")),
    ("GH", "Ghana", "GHS", ("Accra", "Kumasi", "Tamale", "Sekondi-Takoradi", "Cape Coast", "Tema")),
    ("GR", "Greece", "EUR", ("Athens", "Thessaloniki", "Patras", "Heraklion", "Larissa", "Volos")),
    ("GT", "Guatemala", "GTQ", ("Guatemala City", "Mixco", "Villa Nueva", "Quetzaltenango", "Escuintla", "Chinautla")),
    ("HK", "Hong Kong", "HKD", ("Hong Kong", "Kowloon", "Tsuen Wan", "Sha Tin", "Yuen Long", "Tuen Mun")),
    ("HN", "Honduras", "HNL", ("Tegucigalpa", "San Pedro Sula", "Choloma", "La Ceiba", "El Progreso", "Comayagua")),
    ("HR", "Croatia", "EUR", ("Zagreb", "Split", "Rijeka", "Osijek", "Zadar", "Dubrovnik")),
    ("HT", "Haiti", "HTG", ("Port-au-Prince", "Cap-Haïtien", "Gonaïves", "Les Cayes", "Pétion-Ville", "Jacmel")),
    ("HU", "Hungary", "HUF", ("Budapest", "Debrecen", "Szeged", "Miskolc", "Pécs", "Győr")),
    ("ID", "Indonesia", "IDR", ("Jakarta", "Surabaya", "Bandung", "Medan", "Semarang", "Makassar", "Palembang")),
    ("IE", "Ireland", "EUR", ("Dublin", "Cork", "Limerick", "Galway", "Waterford", "Drogheda")),
    ("IL", "Israel", "ILS", ("Jerusalem", "Tel Aviv", "Haifa", "Rishon LeZion", "Petah Tikva", "Ashdod")),
    ("IN", "India", "INR", ("Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune")),
    ("IQ", "Iraq", "IQD", ("Baghdad", "Basra", "Mosul", "Erbil", "Najaf", "Karbala", "Kirkuk")),
    ("IR", "Iran", "IRR", ("Tehran", "Mashhad", "Isfahan", "Shiraz", "Tabriz", "Karaj", "Qom")),
    ("IS", "Iceland", "ISK", ("Reykjavík", "Kópavogur", "Hafnarfjörður", "Akureyri", "Reykjanesbær", "Garðabær")),
    ("IT", "Italy", "EUR", ("Rome", "Milan", "Naples", "Turin", "Palermo", "Florence", "Venice")),
    ("JM", "Jamaica", "JMD", ("Kingston", "Montego Bay", "Spanish Town", "Portmore", "Mandeville", "Ocho Rios")),
    ("JO", "Jordan", "JOD", ("Amman", "Zarqa", "Irbid", "Aqaba", "Madaba", "Salt")),
    ("JP", "Japan", "JPY", ("Tokyo", "Osaka", "Yokohama", "Nagoya", "Sapporo", "Kyoto", "Fukuoka")),
    ("KH", "Cambodia", "KHR", ("Phnom Penh", "Siem Reap", "Battambang", "Sihanoukville", "Kampong Cham", "Kampot")),
    ("KR", "South Korea", "KRW", ("Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju", "Suwon")),
    ("KW", "Kuwait", "KWD", ("Kuwait City", "Hawalli", "Al Ahmadi", "Salmiya", "Sabah Al Salem", "Jahra")),
    ("KZ", "Kazakhstan", "KZT", ("Almaty", "Astana", "Shymkent", "Karaganda", "Aktobe", "Taraz")),
    ("LB", "Lebanon", "LBP", ("Beirut", "Tripoli", "Sidon", "Tyre", "Baalbek", "Zahle")),
    ("LT", "Lithuania", "EUR", ("Vilnius", "Kaunas", "Klaipėda", "Šiauliai", "Panevėžys", "Alytus")),
    ("LU", "Luxembourg", "EUR", ("Luxembourg City", "Esch-sur-Alzette", "Dudelange", "Schifflange", "Bettembourg", "Differdange")),
    ("LY", "Libya", "LYD", ("Tripoli", "Benghazi", "Misrata", "Tarhuna", "Al Khums", "Sabha")),
    ("MA", "Morocco", "MAD", ("Casablanca", "Rabat", "Fes", "Marrakesh", "Tangier", "Agadir", "Meknes")),
    ("MD", "Moldova", "MDL", ("Chișinău", "Tiraspol", "Bălți", "Bender", "Cahul", "Ungheni")),
    ("MO", "Macao", "MOP", ("Macao", "Taipa", "Coloane", "Cotai", "Sé", "São Lázaro")),
    ("MT", "Malta", "EUR", ("Valletta", "Birkirkara", "Mosta", "Qormi", "Sliema", "St. Paul's Bay")),
    ("MU", "Mauritius", "MUR", ("Port Louis", "Beau Bassin-Rose Hill", "Vacoas-Phoenix", "Curepipe", "Quatre Bornes", "Triolet")),
    ("MV", "Maldives", "MVR", ("Malé", "Addu City", "Fuvahmulah", "Kulhudhuffushi", "Thinadhoo", "Naifaru")),
    ("MX", "Mexico", "MXN", ("Mexico City", "Guadalajara", "Monterrey", "Puebla", "Tijuana", "León", "Cancún")),
    ("MY", "Malaysia", "MYR", ("Kuala Lumpur", "George Town", "Ipoh", "Johor Bahru", "Shah Alam", "Malacca", "Kota Kinabalu")),
    ("NG", "Nigeria", "NGN", ("Lagos", "Abuja", "Kano", "Ibadan", "Port Harcourt", "Benin City", "Kaduna")),
    ("NL", "Netherlands", "EUR", ("Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven", "Groningen")),
    ("NO", "Norway", "NOK", ("Oslo", "Bergen", "Trondheim", "Stavanger", "Drammen", "Kristiansand")),
    ("OM", "Oman", "OMR", ("Muscat", "Salalah", "Sohar", "Nizwa", "Sur", "Ibri")),
    ("PA", "Panama", "PAB", ("Panama City", "San Miguelito", "Tocumen", "Las Cumbres", "David", "Colón")),
    ("PE", "Peru", "PEN", ("Lima", "Arequipa", "Trujillo", "Chiclayo", "Cusco", "Piura")),
    ("PH", "Philippines", "PHP", ("Manila", "Quezon City", "Davao", "Cebu City", "Zamboanga", "Taguig", "Makati")),
    ("PL", "Poland", "PLN", ("Warsaw", "Kraków", "Łódź", "Wrocław", "Poznań", "Gdańsk")),
    ("PR", "Puerto Rico", "USD", ("San Juan", "Bayamón", "Carolina", "Ponce", "Caguas", "Mayagüez")),
    ("PS", "Palestine", "ILS", ("Gaza", "Ramallah", "Hebron", "Nablus", "Bethlehem", "Jericho")),
    ("PT", "Portugal", "EUR", ("Lisbon", "Porto", "Vila Nova de Gaia", "Amadora", "Braga", "Coimbra")),
    ("QA", "Qatar", "QAR", ("Doha", "Al Rayyan", "Al Wakrah", "Al Khor", "Lusail", "Mesaieed")),
    ("RS", "Serbia", "RSD", ("Belgrade", "Novi Sad", "Niš", "Kragujevac", "Subotica", "Pančevo")),
    ("RU", "Russia", "RUB", ("Moscow", "Saint Petersburg", "Novosibirsk", "Yekaterinburg", "Kazan", "Nizhny Novgorod", "Sochi")),
    ("SA", "Saudi Arabia", "SAR", ("Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar", "Taif")),
    ("SD", "Sudan", "SDG", ("Khartoum", "Omdurman", "Port Sudan", "Kassala", "Nyala", "El Obeid")),
    ("SE", "Sweden", "SEK", ("Stockholm", "Gothenburg", "Malmö", "Uppsala", "Västerås", "Örebro")),
    ("SG", "Singapore", "SGD", ("Singapore", "Jurong", "Tampines", "Woodlands", "Bedok", "Punggol")),
    ("SI", "Slovenia", "EUR", ("Ljubljana", "Maribor", "Celje", "Kranj", "Koper", "Velenje")),
    ("SV", "El Salvador", "USD", ("San Salvador", "Santa Ana", "San Miguel", "Soyapango", "Mejicanos", "Apopa")),
    ("SY", "Syria", "SYP", ("Damascus", "Aleppo", "Homs", "Latakia", "Hama", "Deir ez-Zor")),
    ("TM", "Turkmenistan", "TMT", ("Ashgabat", "Türkmenabat", "Daşoguz", "Mary", "Balkanabat", "Türkmenbaşy")),
    ("TN", "Tunisia", "TND", ("Tunis", "Sfax", "Sousse", "Kairouan", "Bizerte", "Gabès")),
    ("TR", "Türkiye", "TRY", ("Istanbul", "Ankara", "Izmir", "Bursa", "Adana", "Antalya", "Gaziantep")),
    ("TW", "Taiwan", "TWD", ("Taipei", "Kaohsiung", "Taichung", "Tainan", "Hsinchu", "Keelung")),
    ("US", "United States", "USD", ("New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Francisco")),
    ("UY", "Uruguay", "UYU", ("Montevideo", "Salto", "Ciudad de la Costa", "Paysandú", "Las Piedras", "Rivera")),
    ("YE", "Yemen", "YER", ("Sanaa", "Aden", "Taiz", "Hodeidah", "Mukalla", "Ibb")),
    ("ZA", "South Africa", "ZAR", ("Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth", "Bloemfontein", "East London")),
]


COUNTRIES: dict[str, Country] = {
    code: Country(code=code, name=name, flag=_flag(code), currency=currency, cities=cities)
    for (code, name, currency, cities) in _RAW
}

# Default country if a lookup fails — used by name pool fallbacks.
DEFAULT_COUNTRY_CODE = "GB"

# Pre-computed name ↔ code mappings for the UI.
NAME_TO_CODE: dict[str, str] = {c.name: c.code for c in COUNTRIES.values()}
CODE_TO_NAME: dict[str, str] = {c.code: c.name for c in COUNTRIES.values()}


def resolve(country: str) -> Country:
    """Accept either a display name or an ISO-2 code. Falls back to default."""
    if country in COUNTRIES:
        return COUNTRIES[country]
    code = NAME_TO_CODE.get(country)
    if code and code in COUNTRIES:
        return COUNTRIES[code]
    return COUNTRIES[DEFAULT_COUNTRY_CODE]


def list_countries() -> list[Country]:
    """Display-name sorted list, suitable for UI dropdowns."""
    return sorted(COUNTRIES.values(), key=lambda c: c.name)


def cities_for(country: str) -> tuple[str, ...]:
    return resolve(country).cities


def flag_for(country: str) -> str:
    return resolve(country).flag


def currency_for(country: str) -> str:
    return resolve(country).currency
