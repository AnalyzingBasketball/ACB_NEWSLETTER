import pandas as pd
import os
import google.generativeai as genai
import sys
import re
import numpy as np

# ==============================================================================
# 1. CONFIGURACIÓN ESPECIAL LIGA ENDESA (ACB)
# ==============================================================================
MODEL_NAME = "gemini-2.5-flash"
FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"

# Mapa de Equipos (Los 18 de la Liga Endesa)
TEAM_MAP = {
    'UNI': 'Unicaja', 'SBB': 'Bilbao Basket', 'BUR': 'San Pablo Burgos', 'GIR': 'Bàsquet Girona',
    'TEN': 'La Laguna Tenerife', 'MAN': 'BAXI Manresa', 'LLE': 'Hiopos Lleida', 'BRE': 'Río Breogán',
    'COV': 'Covirán Granada', 'JOV': 'Joventut Badalona', 'RMB': 'Real Madrid', 'GCA': 'Dreamland Gran Canaria',
    'CAZ': 'Casademont Zaragoza', 'BKN': 'Baskonia', 'UCM': 'UCAM Murcia', 'MBA': 'MoraBanc Andorra',
    'VBC': 'Valencia Basket', 'BAR': 'Barça'
}

# Mapa de Entrenadores (Temporada 2025/2026 - ACTUALIZADO OFICIAL)
COACH_MAP = {
    'BAR': 'Xavi Pascual', 'RMB': 'Sergio Scariolo', 'UNI': 'Ibon Navarro',
    'BKN': 'Paolo Galbiati', 'VBC': 'Pedro Martínez', 'UCM': 'Sito Alonso',
    'GCA': 'Jaka Lakovic', 'TEN': 'Txus Vidorreta', 'JOV': 'Dani Miret',
    'MAN': 'Diego Ocampo', 'SBB': 'Jaume Ponsarnau', 'CAZ': 'Joan Plaza',
    'GIR': 'Moncho Fernández', 'BRE': 'Luis Casimiro', 'LLE': 'Gerard Encuentra',
    'COV': 'Arturo Ruíz', 'MBA': 'Zan Tabak', 'BUR': 'Porfi Fisac'
}

# ==============================================================================
# 2. DICCIONARIO MAESTRO DE JUGADORES (ACB)
# ==============================================================================
CORRECCIONES_VIP = {
    # --- BARÇA (BAR) ---
    "D. Brizuela": "Darío Brizuela", "D. González": "Dani González", "J. Marcos": "Juani Marcos", "J. Parra": "Joel Parra", "J. Vesely": "Jan Vesely", "K. Punter": "Kevin Punter", "M. Cale": "Myles Cale", "M. Norris": "Miles Norris", "N. Kusturica": "Nikola Kusturica", "N. Laprovittola": "Nico Laprovittola", "S. Keita": "Sayon Keita", "T. Satoransky": "Tomas Satoransky", "T. Shengelia": "Toko Shengelia", "W. Clyburn": "Will Clyburn", "W. Hernangómez": "Willy Hernangómez", "Y. Fall": "Youssoupha Fall",
    # --- BASKONIA (BKN) ---
    "C. Frisch": "Clément Frisch", "E. Omoruyi": "Eugene Omoruyi", "G. Radzevicius": "Gytis Radzevicius", "H. Diallo": "Hamidou Diallo", "K. Diop": "Khalifa Diop", "K. Simmons": "Kobi Simmons", "L. Samanic": "Luka Samanic", "Luwawu-Cabarrot": "Timothé Luwawu-Cabarrot", "M. Diakite": "Mamadi Diakite", "M. Howard": "Markus Howard", "M. Nowell": "Markquis Nowell", "M. Spagnolo": "Matteo Spagnolo", "R. Kurucs": "Rodions Kurucs", "R. Villar": "Rafa Villar", "S. Joksimovic": "Stefan Joksimovic", "T. Forrest": "Trent Forrest", "T. Sedekerskis": "Tadas Sedekerskis",
    # --- RÍO BREOGÁN (BRE) ---
    "A. Aranitovic": "Aleksandar Aranitovic", "A. Kurucs": "Arturs Kurucs", "B. Dibba": "Bamba Dibba", "D. Apic": "Dragan Apic", "D. Brankovic": "Danko Brankovic", "D. Drežnjak": "Dario Drežnjak", "D. Mavra": "Dominik Mavra", "D. Russell": "Daron Russell", "E. Quintela": "Erik Quintela", "F. Alonso": "Francis Alonso", "J. Sakho": "Jordan Sakho", "K. Cook": "Keaton Cook", "M. Andric": "Mihajlo Andric",
    # --- SAN PABLO BURGOS (BUR) ---
    "D. Díez": "Dani Díez", "E. Happ": "Ethan Happ", "G. Corbalán": "Gonzalo Corbalán", "J. Gudmundsson": "Jon Axel Gudmundsson", "J. Jackson": "Justin Jackson", "J. Rubio": "Joan Rubio", "J. Samuels": "Jermaine Samuels", "L. Fischer": "Luke Fischer", "L. Meindl": "Leo Meindl", "P. Almazán": "Pablo Almazán", "R. Neto": "Raulzinho Neto", "R. Rodríguez": "Rodrigo Rodríguez", "S. García": "Sergi García", "S. de Sousa": "Silvio de Sousa", "Y. Nzosa": "Yannick Nzosa",
    # --- CASADEMONT ZARAGOZA (CAZ) ---
    "B. Dubljevic": "Bojan Dubljevic", "C. Alías": "Carlos Alías", "C. Koumadje": "Christ Koumadje", "D. Robinson": "Devin Robinson", "D. Stephens": "D.J. Stephens", "E. Kabaca": "Emir Kabaca", "E. Stevenson": "Erik Stevenson", "J. Fernández": "Jaime Fernández", "J. Rodríguez": "Joaquín Rodríguez", "J. Soriano": "Joel Soriano", "L. Langarita": "Lucas Langarita", "M. González": "Miguel González", "M. Lukic": "Matija Lukic", "M. Spissu": "Marco Spissu", "S. Yusta": "Santi Yusta", "T. Bell-Haynes": "Trae Bell-Haynes", "Y. Traoré": "Youssouf Traoré",
    # --- COVIRÁN GRANADA (COV) ---
    "A. Alibegovic": "Amar Alibegovic", "A. Brimah": "Amida Brimah", "B. Burjanadze": "Beka Burjanadze", "B. Olumuyiwa": "Babatunde Olumuyiwa", "E. Durán": "Edu Durán", "E. Valtonen": "Elias Valtonen", "I. Aurrecoechea": "Iván Aurrecoechea", "J. Kljajic": "Jovan Kljajic", "J. Pérez": "Josep Pérez", "J. Rousselle": "Jonathan Rousselle", "L. Bozic": "Luka Bozic", "L. Costa": "Lluís Costa", "M. Ngouama": "Mehdy Ngouama", "M. Speight": "Micah Speight", "M. Thomas": "Malcolm Thomas", "O. Cerdá": "Osi Cerdá", "P. Tomàs": "Pere Tomàs", "T. Munnings": "Travis Munnings", "W. Howard": "William Howard", "Z. Hankins": "Zach Hankins",
    # --- DREAMLAND GRAN CANARIA (GCA) ---
    "A. Albicy": "Andrew Albicy", "B. Angola": "Braian Angola", "C. Alocén": "Carlos Alocén", "E. Vila": "Eric Vila", "I. Wong": "Isaiah Wong", "K. Kuath": "Kur Kuath", "L. Labeyrie": "Louis Labeyrie", "L. Maniema": "Lucas Maniema", "M. Salvó": "Miquel Salvó", "M. Tobey": "Mike Tobey", "N. Brussino": "Nico Brussino", "P. Pelos": "Pierre Pelos", "Z. Samar": "Ziga Samar",
    # --- BÀSQUET GIRONA (GIR) ---
    "D. Needham": "Derek Needham", "G. Ferrando": "Guillem Ferrando", "J. Fernández": "Juan Fernández", "M. Fjellerup": "Máximo Fjellerup", "M. Geben": "Martinas Geben", "M. Hughes": "Michael Hughes", "M. Susinskas": "Mindaugas Susinskas", "N. Maric": "Nikola Maric", "O. Livingston": "Otis Livingston", "P. Busquets": "Pep Busquets", "P. Vildoza": "Pato Vildoza", "S. Hollanders": "Sander Hollanders", "S. Martínez": "Sergi Martínez",
    # --- JOVENTUT BADALONA (JOV) ---
    "A. Hanga": "Adam Hanga", "A. Tomic": "Ante Tomic", "A. Torres": "Adrià Torres", "C. Hunt": "Cameron Hunt", "F. Mauri": "Ferran Mauri", "G. Vives": "Guillem Vives", "H. Drell": "Henri Drell", "L. Hakanson": "Ludde Hakanson", "M. Allen": "Miguel Allen", "M. Ruzic": "Michael Ruzic", "R. Rubio": "Ricky Rubio", "S. Birgander": "Simon Birgander", "S. Dekker": "Sam Dekker", "Y. Kraag": "Yannick Kraag",
    # --- HIOPOS LLEIDA (LLE) ---
    "A. Diagne": "Amadou Diagne", "C. Agada": "Caleb Agada", "C. Krutwig": "Cameron Krutwig", "C. Walden": "Corey Walden", "G. Golomán": "Gyorgy Golomán", "I. Dabo": "Ibrahim Dabo", "J. Batemon": "James Batemon", "J. Shurna": "John Shurna", "K. Zoriks": "Kristers Zoriks", "M. Ejim": "Melvin Ejim", "M. Jiménez": "Millán Jiménez", "M. Sanz": "Miquel Sanz", "O. Paulí": "Oriol Paulí", "P. Rios": "Pau Rios",
    # --- BAXI MANRESA (MAN) ---
    "A. Izaw-Bolavie": "Alexandre Izaw-Bolavie", "A. Plummer": "Alfonso Plummer", "A. Reyes": "Álex Reyes", "A. Ubal": "Agustín Ubal", "D. Pérez": "Dani Pérez", "E. Brooks": "Emanuel Brooks", "F. Bassas": "Ferran Bassas", "F. Torreblanca": "Ferran Torreblanca", "G. Fernández": "Guillem Fernández", "G. Golden": "Grant Golden", "G. Knudsen": "Gustav Knudsen", "H. Benitez": "Hugo Benítez", "K. Akobundu": "Kaodirichi Akobundu", "L. Olinde": "Louis Olinde", "M. Gaspà": "Marc Gaspà", "M. Steinbergs": "Marcis Steinbergs", "P. Oriola": "Pierre Oriola", "R. Obasohan": "Retin Obasohan",
    # --- MORABANC ANDORRA (MBA) ---
    "A. Best": "Aaron Best", "A. Ganal": "Aaron Ganal", "A. Pustovyi": "Artem Pustovyi", "C. Ortega": "Chumi Ortega", "F. Bassas": "Ferran Bassas", "J. McKoy": "Jordy McKoy", "K. Kostadinov": "Konstantin Kostadinov", "K. Kuric": "Kyle Kuric", "M. Udeze": "Morris Udeze", "R. Guerrero": "Rubén Guerrero", "R. Luz": "Rafa Luz", "S. Evans": "Shannon Evans", "S. Okoye": "Stan Okoye", "X. Castañeda": "Xavier Castañeda", "Y. Pons": "Yves Pons",
    # --- REAL MADRID (RMB) ---
    "A. Abalde": "Alberto Abalde", "A. Feliz": "Andrés Feliz", "A. Len": "Alex Len", "B. Fernando": "Bruno Fernando", "C. Okeke": "Chuma Okeke", "D. Kramer": "David Kramer", "F. Campazzo": "Facundo Campazzo", "G. Deck": "Gabriel Deck", "G. Grinvalds": "Gunars Grinvalds", "G. Procida": "Gabriele Procida", "I. Almansa": "Izan Almansa", "M. Hezonja": "Mario Hezonja", "S. Llull": "Sergio Llull", "T. Lyles": "Trey Lyles", "T. Maledon": "Théo Maledon", "U. Garuba": "Usman Garuba", "W. Tavares": "Edy Tavares",
    # --- BILBAO BASKET (SBB) ---
    "A. Font": "Aleix Font", "A. Sylla": "Amar Sylla", "A. Zecevic": "Allan Zecevic", "B. Bagayoko": "Bassala Bagayoko", "B. Errasti": "Beñat Errasti", "D. Hilliard": "Darrun Hilliard", "H. Frey": "Harald Frey", "J. Jaworski": "Justin Jaworski", "L. Petrasek": "Luke Petrasek", "M. Krampelj": "Martin Krampelj", "M. Normantas": "Margiris Normantas", "M. Pantzar": "Melwin Pantzar", "S. Lazarevic": "Stefan Lazarevic", "T. Hlinason": "Tryggvi Hlinason",
    # --- LA LAGUNA TENERIFE (TEN) ---
    "A. Doornekamp": "Aaron Doornekamp", "B. Fitipaldo": "Bruno Fitipaldo", "D. Bordón": "Diego Bordón", "F. Guerra": "Fran Guerra", "G. Shermadini": "Giorgi Shermadini", "H. Alderete": "Hector Alderete", "J. Fernández": "Jaime Fernández", "J. Sastre": "Joan Sastre", "K. Kostadinov": "Konstantin Kostadinov", "L. Costa": "Lluís Costa", "M. Huertas": "Marcelinho Huertas", "R. Giedraitis": "Rokas Giedraitis", "T. Abromaitis": "Tim Abromaitis", "T. Scrubb": "Thomas Scrubb", "W. Van Beck": "Wesley Van Beck",
    # --- UCAM MURCIA (UCM) ---
    "D. Cacok": "Devontae Cacok", "D. DeJulius": "David DeJulius", "D. Ennis": "Dylan Ennis", "D. García": "Dani García", "E. Cate": "Emanuel Cate", "H. Sant-Roos": "Howard Sant-Roos", "J. Radebaugh": "Jonah Radebaugh", "M. Diagné": "Moussa Diagné", "M. Forrest": "Michael Forrest", "R. López": "Rubén López de la Torre", "S. Raieste": "Sander Raieste", "T. Nakic": "Toni Nakic", "W. Falk": "Wilhelm Falk", "Z. Hicks": "Zach Hicks",
    # --- UNICAJA (UNI) ---
    "A. Butajevas": "Arturas Butajevas", "A. Díaz": "Alberto Díaz", "A. Rubit": "Augustine Rubit", "C. Audige": "Chase Audige", "C. Duarte": "Chris Duarte", "D. Kravish": "David Kravish", "E. Sulejmanovic": "Emir Sulejmanovic", "J. Barreiro": "Jonathan Barreiro", "J. Webb": "James Webb III", "K. Perry": "Kendrick Perry", "K. Tillie": "Killian Tillie", "N. Djedovic": "Nihad Djedovic", "O. Balcerowski": "Olek Balcerowski", "T. Kalinoski": "Tyler Kalinoski", "T. Pérez": "Tyson Pérez", "X. Castañeda": "Xavier Castañeda",
    # --- VALENCIA BASKET (VBC) ---
    "B. Badio": "Brancou Badio", "B. Key": "Braxton Key", "D. Thompson": "Darius Thompson", "I. Iroegbu": "Ike Iroegbu", "I. Nogués": "Isaac Nogués", "J. Montero": "Jean Montero", "J. Pradilla": "Jaime Pradilla", "J. Puerto": "Josep Puerto", "K. Taylor": "Kameron Taylor", "López-Arostegui": "Xabi López-Arostegui", "M. Costello": "Matt Costello", "N. Reuvers": "Nathan Reuvers", "N. Sako": "Neal Sako", "O. Moore": "Omari Moore", "S. de Larrea": "Sergio de Larrea", "Y. Sima": "Yankuba Sima"
}

# ==============================================================================
# 3. FUNCIONES AUXILIARES
# ==============================================================================
def guardar_salida(mensaje, nombre_archivo="newsletter_borrador.md"):
    print(mensaje)
    try:
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(mensaje)
        print(f"\n✅ Newsletter guardada: {nombre_archivo}")
    except Exception as e:
        print(f"❌ Error guardando archivo: {e}")
    sys.exit(0)

def b(val, decimals=0, is_percent=False):
    if pd.isna(val) or val == np.inf or val == -np.inf: val = 0
    suffix = "%" if is_percent else ""
    if isinstance(val, (int, float)):
        if val % 1 == 0 and decimals == 0: return f"**{int(val)}**{suffix}"
        return f"**{val:.{decimals}f}**{suffix}"
    return f"**{val}**{suffix}"

def get_team_name(abbr, use_full=True):
    return TEAM_MAP.get(abbr, abbr) if use_full else abbr

def extraer_numero_jornada(texto):
    match = re.search(r'\d+', str(texto))
    return int(match.group()) if match else 0

def clean_name(name_raw):
    return CORRECCIONES_VIP.get(name_raw, name_raw)

# ==============================================================================
# 4. CARGA DE DATOS Y EXTRACCIÓN DE LA JORNADA
# ==============================================================================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key: guardar_salida("❌ Error: Falta GEMINI_API_KEY.")
genai.configure(api_key=api_key)

if not os.path.exists(FILE_PATH): guardar_salida(f"❌ No hay CSV en {FILE_PATH}.")
df = pd.read_csv(FILE_PATH)

cols_num = ['VAL', 'PTS', 'Reb_T', 'AST', 'Win', 'Game_Poss', 'TO', 'TS%', 'USG%']
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Buscamos la última jornada registrada
jornadas_unicas = sorted(df['Week'].unique(), key=extraer_numero_jornada)
ultima_jornada_label = jornadas_unicas[-1]
df_week = df[df['Week'] == ultima_jornada_label]

print(f"Analizando {ultima_jornada_label}...")

# ==============================================================================
# 5. PREPARACIÓN DE DATOS (Top Performers, Equipos, Tendencias)
# ==============================================================================

# A. CO-MVP: buscamos el máximo VAL en TODA la jornada (ganadores y perdedores)
# Si el empate se da entre jugadores de equipos distintos (uno gana, otro pierde),
# el filtro de ganadores romperia la detección. Por eso buscamos en df_week completo.
max_val_jornada = df_week['VAL'].max()
mejores = df_week[df_week['VAL'] == max_val_jornada]
num_mvps = len(mejores)

txt_mejores = ""
mejores_ids = []
for _, row in mejores.iterrows():
    m_name = clean_name(row['Name'])
    resultado = "victoria" if row['Win'] == 1 else "derrota"
    txt_mejores += (f"- {m_name} ({get_team_name(row['Team'])}, {resultado}): "
                    f"{b(row['VAL'])} VAL, {b(row['PTS'])} PTS "
                    f"(TS%: {b(row['TS%'], 1, True)}), {b(row['Reb_T'])} REB, "
                    f"{b(row['AST'])} AST, USG%: {b(row['USG%'], 1, True)}.\n")
    mejores_ids.append(row['PlayerID'])

# B. DESTACADOS SECUNDARIOS (excluye a los MVP(s))
resto = df_week[~df_week['PlayerID'].isin(mejores_ids)]
top_rest = resto.sort_values('VAL', ascending=False).head(3)
txt_rest = ""
for _, row in top_rest.iterrows():
    r_name = clean_name(row['Name'])
    txt_rest += f"- {r_name} ({get_team_name(row['Team'])}): {b(row['VAL'])} VAL, {b(row['PTS'])} PTS.\n"

# C. EQUIPOS DE LA JORNADA
team_agg = df_week.groupby('Team').agg({
    'PTS': 'sum', 'Game_Poss': 'mean', 'Reb_T': 'sum', 'AST': 'sum', 'TO': 'sum'
}).reset_index()
team_agg['ORTG'] = (team_agg['PTS'] / team_agg['Game_Poss']) * 100
team_agg['AST_Ratio'] = (team_agg['AST'] / team_agg['Game_Poss']) * 100
team_agg['TO_Ratio'] = (team_agg['TO'] / team_agg['Game_Poss']) * 100

best_offense = team_agg.sort_values('ORTG', ascending=False).iloc[0]
best_passing = team_agg.sort_values('AST_Ratio', ascending=False).iloc[0]
most_careful = team_agg.sort_values('TO_Ratio', ascending=True).iloc[0]

txt_teams = f"""
- Mejor Ataque: {get_team_name(best_offense['Team'])} ({COACH_MAP.get(best_offense['Team'], 'su técnico')}) con {b(best_offense['ORTG'], 1)} pts/100 pos.
- Mejor Fluidez: {get_team_name(best_passing['Team'])} ({COACH_MAP.get(best_passing['Team'], 'su técnico')}) con {b(best_passing['AST_Ratio'], 1)} ast/100 pos.
- Mejor Control: {get_team_name(most_careful['Team'])} ({COACH_MAP.get(most_careful['Team'], 'su técnico')}) con {b(most_careful['TO_Ratio'], 1)} pérdidas/100 pos.
"""

# D. TENDENCIAS (Últimas 3 Jornadas)
txt_trends = ""
if len(jornadas_unicas) >= 1:
    last_3 = jornadas_unicas[-3:]
    df_last = df[df['Week'].isin(last_3)]
    means = df_last.groupby(['Name', 'Team'])[['VAL', 'PTS', 'AST', 'TS%']].mean().reset_index()
    hot = means.sort_values('VAL', ascending=False).head(5)
    for _, row in hot.iterrows():
        t_name = clean_name(row['Name'])
        txt_trends += (f"- {t_name} ({get_team_name(row['Team'], False)}): "
                       f"{b(row['VAL'], 1)} VAL, {b(row['PTS'], 1)} PTS, "
                       f"{b(row['AST'], 1)} AST, TS%: {b(row['TS%'], 1, True)}.\n")

# ==============================================================================
# 6. CONSTRUCCIÓN DEL PROMPT
# ==============================================================================

if num_mvps > 1:
    mvp_instruccion = (f"JORNADA CON CO-MVPs: hay {num_mvps} jugadores empatados en la máxima "
                       f"valoración ({int(max_val_jornada)} VAL). Tratálos como co-MVPs con IGUAL "
                       f"protagonismo. No elijas uno principal. Pueden ser de equipos distintos "
                       f"y hasta de equipos que perdieron, eso es parte del interés.")
else:
    mvp_instruccion = "MVP Único: un solo jugador lidera la valoración de la jornada."

prompt = f"""Eres el redactor de la newsletter 'Analyzing Basketball', especializada en análisis 
de la Liga Endesa (ACB). Tu newsletter la leen aficionados con alto nivel de conocimiento 
de baloncesto. Tu voz es directa, concisa y técnica, sin florituras.

JORNADA: {ultima_jornada_label}
{mvp_instruccion}

--- DATOS MVP(S) ---
{txt_mejores}
--- OTROS DESTACADOS ---
{txt_rest}
--- EFICIENCIA EQUIPOS ---
{txt_teams}
--- FORMA RECIENTE (3 jornadas) ---
{txt_trends}

=== EJEMPLO DE ESTILO (imita este tono exacto, no el contenido) ===
ASUNTO: Shermadini y Montero comparten el liderato de una jornada sin dominator claro

## Informe Liga Endesa: Jornada 18

### MVP y Puntos Clave
Dos jugadores, un mismo techo. Giorgi Shermadini y Jean Montero acabaron la jornada con 
**28** VAL cada uno, liderando sus respectivos equipos en victorias. El pivot georgiano 
terminó con **22** puntos y **12** rebotes, un 71.4% de TS% que refleja cómo aprovechó 
cada tiro cerca del aro. Montero, en cambio, tiró menos pero repartió más: **18** puntos 
y **7** asistencias con un USG% del 28.3% que apunta a que Valencia le demandó mucho 
balón en los momentos clave.

Ambas actuaciones llegaron en partidos que sus equipos necesitaban ganar. Tenerife sigue 
colgado en zona de copas; Valencia recorta terreno en la parte media de la tabla.

### Radar de Eficiencia
- Unicaja (Ibon Navarro): **134.2** pts/100 pos. El espaciado y la ejecución siguen siendo 
el mejor ataque de la competición por margen.
- Bilbao Basket (Jaume Ponsarnau): **31.8** ast/100 pos. El balón se mueve, pero el ratio 
AST/TO sugiere que algunos de esos pases son forzados.
- Tenerife (Txus Vidorreta): **8.2** pérdidas/100 pos. El equipo más cuidadoso con el 
balón de la jornada.

### En Racha (3 jornadas)
- Trent Forrest (BKN): **26.7** VAL, **16.3** PTS, **4.7** AST, TS%: **58.2%**.
- Giorgi Shermadini (TEN): **24.5** VAL, **21.0** PTS, **0.5** AST, TS%: **69.1%**.
=== FIN EJEMPLO ===

REGLAS ABSOLUTAS (incumplirlas invalida el texto):
1. LONGITUD: máximo 350 palabras en el cuerpo (no cuentan bullet points de "En Racha").
2. ARRANQUE: primera frase = dato más importante. Sin introducción genérica.
3. SIN CIERRE: no escribas frases de despedida. El texto termina con el último dato.
4. SIN EMOJIS: ni en asunto, ni en títulos, ni en cuerpo.
5. IMPERSONAL: sin "tú", "vosotros", "usted". Tercera persona o formas impersonales.
6. ESPAÑOL DE ESPAÑA: "mate" no volcada, "cancha/parqué" no duela, "tiros libres" no lanzamiento personal.
7. INFERENCIA TÁCTICA: sin visión ni play-by-play. Cualquier lectura táctica debe ir 
   enmarcada: "el USG% sugiere...", "la ratio AST/TO apunta a...", "con ese ORTG, el sistema 
   de [entrenador] parece...". PROHIBIDO narrar acciones reales ("en el minuto 34...").
8. ENTRENADORES: solo los nombres de los datos. No inventes.
9. DATOS EN NEGRITA: todos los números estadísticos en **negrita** Markdown.
10. VOCABULARIO PROHIBIDO: "créditos de valoración", "maestría", "denota", "subraya", 
    "exhibe", "estelar", "galvaniza", "crisol", "abanico", "diametralmente", "en definitiva",
    "sin lugar a dudas", "no es casualidad". Usa lenguaje directo y concreto.

FORMATO DE SALIDA (respeta exactamente):

ASUNTO: [una línea periodística, sin emoji, con el dato o hecho más llamativo]

## Informe Liga Endesa: {ultima_jornada_label}

### MVP y Puntos Clave
[máx. 2 párrafos cortos. Arranca con el dato. Si hay co-MVPs, dáles el mismo espacio.]

### Radar de Eficiencia
[máx. 3 bullets o 1 párrafo. ORTG, AST ratio, TO ratio con inferencia táctica y entrenadores.]

### En Racha (3 jornadas)
{txt_trends}"""

# ==============================================================================
# 7. GENERACIÓN CON GEMINI
# ==============================================================================
try:
    print(f"Generando newsletter para {ultima_jornada_label}...")
    model = genai.GenerativeModel(model_name=MODEL_NAME)
    response = model.generate_content(prompt)
    texto = response.text.replace(":\n-", ":\n\n-")
    guardar_salida(texto)
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
