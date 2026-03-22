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

TEAM_MAP = {
    'UNI': 'Unicaja', 'SBB': 'Bilbao Basket', 'BUR': 'San Pablo Burgos', 'GIR': 'Bàsquet Girona',
    'TEN': 'La Laguna Tenerife', 'MAN': 'BAXI Manresa', 'LLE': 'Hiopos Lleida', 'BRE': 'Río Breogán',
    'COV': 'Covirán Granada', 'JOV': 'Joventut Badalona', 'RMB': 'Real Madrid', 'GCA': 'Dreamland Gran Canaria',
    'CAZ': 'Casademont Zaragoza', 'BKN': 'Baskonia', 'UCM': 'UCAM Murcia', 'MBA': 'MoraBanc Andorra',
    'VBC': 'Valencia Basket', 'BAR': 'Barça'
}

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

jornadas_unicas = sorted(df['Week'].unique(), key=extraer_numero_jornada)
ultima_jornada_label = jornadas_unicas[-1]
df_week = df[df['Week'] == ultima_jornada_label]

print(f"Analizando {ultima_jornada_label}...")

# ==============================================================================
# 5. PREPARACIÓN DE DATOS
# ==============================================================================

# CO-MVP: máximo VAL en TODA la jornada (no solo ganadores).
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

# --- OTROS DESTACADOS (top 5 excluyendo MVPs, con más detalle) ---
resto = df_week[~df_week['PlayerID'].isin(mejores_ids)]
top_rest = resto.sort_values('VAL', ascending=False).head(5)
txt_rest = ""
for _, row in top_rest.iterrows():
    r_name = clean_name(row['Name'])
    resultado = "W" if row['Win'] == 1 else "L"
    txt_rest += (f"- {r_name} ({get_team_name(row['Team'])}, {resultado}): "
                 f"{b(row['VAL'])} VAL, {b(row['PTS'])} PTS, "
                 f"{b(row['Reb_T'])} REB, {b(row['AST'])} AST, "
                 f"TS%: {b(row['TS%'], 1, True)}.\n")

# --- OUTSIDER: jugador cuya VAL de esta jornada más supera su media de temporada ---
txt_outsider = ""
try:
    df_prev = df[df['Week'] != ultima_jornada_label]
    if len(df_prev) > 0:
        season_avg = df_prev.groupby(['Name', 'Team'])['VAL'].mean().reset_index()
        season_avg.columns = ['Name', 'Team', 'VAL_avg']
        game_counts = df_prev.groupby(['Name', 'Team']).size().reset_index(name='games')
        season_avg = season_avg.merge(game_counts, on=['Name', 'Team'])
        season_avg = season_avg[season_avg['games'] >= 5]
        week_data = df_week[['Name', 'Team', 'VAL', 'PTS', 'Reb_T', 'AST', 'TS%', 'Win']].copy()
        merged = week_data.merge(season_avg, on=['Name', 'Team'], how='inner')
        merged['VAL_delta'] = merged['VAL'] - merged['VAL_avg']
        merged = merged[~merged['Name'].isin([row['Name'] for _, row in mejores.iterrows()])]
        if len(merged) > 0:
            outsider = merged.sort_values('VAL_delta', ascending=False).iloc[0]
            o_name = clean_name(outsider['Name'])
            resultado = "victoria" if outsider['Win'] == 1 else "derrota"
            txt_outsider = (f"- {o_name} ({get_team_name(outsider['Team'])}, {resultado}): "
                           f"{b(outsider['VAL'])} VAL esta jornada vs {b(outsider['VAL_avg'], 1)} de media en temporada "
                           f"(+{outsider['VAL_delta']:.1f}). {b(outsider['PTS'])} PTS, "
                           f"{b(outsider['Reb_T'])} REB, {b(outsider['AST'])} AST, "
                           f"TS%: {b(outsider['TS%'], 1, True)}.")
except Exception as e:
    print(f"Aviso: no se pudo calcular outsider: {e}")
    txt_outsider = ""

# --- EFICIENCIA EQUIPOS ---
team_agg = df_week.groupby('Team').agg({
    'PTS': 'sum', 'Game_Poss': 'mean', 'Reb_T': 'sum', 'AST': 'sum', 'TO': 'sum'
}).reset_index()
team_agg['ORTG'] = (team_agg['PTS'] / team_agg['Game_Poss']) * 100
team_agg['AST_Ratio'] = (team_agg['AST'] / team_agg['Game_Poss']) * 100
team_agg['TO_Ratio'] = (team_agg['TO'] / team_agg['Game_Poss']) * 100

best_offense = team_agg.sort_values('ORTG', ascending=False).iloc[0]
worst_offense = team_agg.sort_values('ORTG', ascending=True).iloc[0]
best_passing = team_agg.sort_values('AST_Ratio', ascending=False).iloc[0]
most_careful = team_agg.sort_values('TO_Ratio', ascending=True).iloc[0]

txt_teams = f"""
- Mejor Ataque: {get_team_name(best_offense['Team'])} ({COACH_MAP.get(best_offense['Team'], 'su técnico')}) con {b(best_offense['ORTG'], 1)} pts/100 pos.
- Peor Ataque: {get_team_name(worst_offense['Team'])} ({COACH_MAP.get(worst_offense['Team'], 'su técnico')}) con {b(worst_offense['ORTG'], 1)} pts/100 pos.
- Mejor Fluidez: {get_team_name(best_passing['Team'])} ({COACH_MAP.get(best_passing['Team'], 'su técnico')}) con {b(best_passing['AST_Ratio'], 1)} ast/100 pos.
- Mejor Control: {get_team_name(most_careful['Team'])} ({COACH_MAP.get(most_careful['Team'], 'su técnico')}) con {b(most_careful['TO_Ratio'], 1)} pérdidas/100 pos.
"""

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
    mvp_instruccion = (f"JORNADA CON CO-MVPs: {num_mvps} jugadores empatados en {int(max_val_jornada)} VAL. "
                       f"Trátalos con IGUAL protagonismo. No elijas uno principal. "
                       f"Pueden ser de equipos distintos o incluso de equipos que perdieron.")
else:
    mvp_instruccion = "MVP único: un solo jugador lidera la valoración."

bloque_outsider_datos = ""
bloque_outsider_formato = ""
if txt_outsider:
    bloque_outsider_datos = f"\n--- OUTSIDER DE LA JORNADA (mayor salto vs su media) ---\n{txt_outsider}\n"
    bloque_outsider_formato = """\n### Nombre Propio\n[1 párrafo sobre el outsider. Usa el contraste entre su media de temporada y lo que hizo esta jornada.\nNo hace falta que sea largo. Una observación con criterio vale más que tres frases de relleno.]"""

prompt = f"""Eres el autor de la newsletter 'Analyzing Basketball' sobre la Liga Endesa (ACB).

Tu voz: formal pero sin rigidez, analítica pero no académica. Escribes como alguien que
sabe de lo que habla y no necesita demostrarlo. Frases cortas que rematan una idea.
Opinión cuando los datos la justifican, dicha con naturalidad, sin dramatismo ni adornos.
Cuando un dato es llamativo, lo dices claro: "Es una barbaridad", "No es el baloncesto
más vistoso, pero funciona". Sin rodeos, sin relleno, sin intentar sonar inteligente.

JORNADA: {ultima_jornada_label}
{mvp_instruccion}

--- DATOS MVP(S) ---
{txt_mejores}
--- OTROS DESTACADOS (top 5) ---
{txt_rest}
--- EFICIENCIA EQUIPOS ---
{txt_teams}{bloque_outsider_datos}
--- FORMA RECIENTE (3 jornadas) ---
{txt_trends}

=== EJEMPLO 1 — Newsletter Jornada 21 (escrita por el propio autor) ===

ASUNTO: Forrest, MVP de la Jornada 21

Liga Endesa, Jornada 21

Trent Forrest se llevó el MVP con **30** de valoración. **18** puntos, **73.3**% de TS%,
**5** rebotes. No es un jugador que necesite dominar el balón para hacer daño, y eso
es lo que lo hace peligroso.

Donde más se notó fue en el pick & roll. Forrest obliga a la defensa a elegir mal, y
cuando eso pasa, aparecen huecos. Penetraciones, tiros abiertos, lo que venga. También
se metió en el rebote ofensivo, que es algo que no siempre hace pero que en esta jornada
dio segundas oportunidades en momentos tensos.

El Barça sigue siendo una máquina de anotar: **142.1** puntos por **100** posesiones.
Transición, estático, da igual. Xavi Pascual tiene un equipo que te puede hacer daño
de cualquier forma.

El Joventut movió el balón mejor que nadie con **36.1** asistencias por **100** posesiones.
No tienen un anotador dominante, pero tampoco lo necesitan. Juegan juntos.

Y luego está el UCAM Murcia, que perdió solo **6.1** balones por **100** posesiones.
Sito Alonso lleva años haciendo lo mismo: ritmo lento, cero regalos, cada posesión
exprimida. No es el baloncesto más vistoso, pero funciona.

=== EJEMPLO 2 — Newsletter Jornada 22, co-MVPs (escrita por el propio autor) ===

ASUNTO: Happ y Bozic se reparten el MVP de la Jornada 22

Liga Endesa, Jornada 22

Ethan Happ y Luka Bozic terminaron empatados en **33** de valoración. Happ (San Pablo Burgos)
hizo un doble-doble silencioso: **16** puntos, **10** rebotes y un **73.5**% de TS%. Lo llamativo
es que su USG% fue del **21.8**%. No necesitó dominar el balón para dominar el partido.

Bozic (Covirán Granada) tiró más del carro en anotación con **20** puntos, pero donde
realmente hizo daño fue en el rebote: **13**. También un USG% bajo, del **21.7**%. Dos jugadores
que producen mucho sin acaparar. Raro verlo dos veces en la misma jornada.

El Unicaja sigue siendo otro planeta en ataque. **137.1** puntos por **100** posesiones.
Ibon Navarro tiene montado un sistema que hace que defender a su equipo sea un infierno.

Bilbao Basket repartió **33.2** asistencias por **100** posesiones, la mejor marca de la jornada.
Y Tenerife perdió solo **8.8** balones por **100** posesiones. Txus Vidorreta y lo de siempre:
nada de regalos.

=== EJEMPLO 3 — Fragmentos de Copa del Rey (tono del autor en formato más narrativo) ===

"Da igual cómo intentes defenderlos. Si corres con ellos, te matan en transición.
Si te plantas y organizas la defensa, te desarman con movimiento y pases."

"Sito Alonso lleva años haciendo lo mismo: ritmo lento, cero regalos, cada posesión exprimida."

"Es el tipo de jugador que no valoras del todo hasta que miras la hoja de estadísticas
al final y piensas: ah, claro, Lyles otra vez."

"No es el baloncesto más vistoso. No vas a ver highlights del Barça en esta Copa.
Pero vas a verlos en semifinales, que al final es lo que importa."

=== FIN EJEMPLOS ===

PATRONES DEL AUTOR QUE DEBES REPLICAR:
- Frase corta que remata: "Raro verlo dos veces en la misma jornada." Sin desarrollar más.
- Dato primero, interpretación después en UNA frase. Nunca al revés.
- Opinión integrada con naturalidad: "otro planeta en ataque", "lo de siempre: nada de regalos".
- Contraste inesperado: "No necesitó dominar el balón para dominar el partido."
- Sin conectores vacíos: NUNCA "por otro lado", "cabe destacar", "en este sentido", "es importante señalar".
- Cuando algo es llamativo, lo dice sin rodeos. Cuando no lo es, no lo fuerza.
- Menciona a otros jugadores destacados cuando aporten algo a la narrativa, no como lista.

=== PARES INCORRECTO / CORRECTO — aprende la diferencia ===

INCORRECTO: "Un USG% de 21.8% indica que su producción fue significativa sin una carga excesiva en la distribución de tiros."
CORRECTO: "USG% del 21.8%. No necesitó dominar el balón para dominar el partido."

INCORRECTO: "Este dato sugiere que el sistema de Ibon Navarro continúa optimizando la selección de tiro y la ejecución ofensiva."
CORRECTO: "Ibon Navarro tiene montado un sistema que hace que defender a su equipo sea un infierno."

INCORRECTO: "Un alto ratio de asistencia habitualmente apunta a una buena circulación y movimiento sin balón, lo que permite generar ventajas."
CORRECTO: "No tienen un anotador dominante, pero tampoco lo necesitan. Juegan juntos."

INCORRECTO: "Minimizar los errores no forzados es clave para un baloncesto eficiente, y esta cifra destaca la disciplina."
CORRECTO: "Sito Alonso lleva años haciendo lo mismo: ritmo lento, cero regalos, cada posesión exprimida."

INCORRECTO: "Su impacto en el rebote fue determinante, capturando 13 rebotes que consolidaron su dominio bajo los aros."
CORRECTO: "Donde realmente hizo daño fue en el rebote: 13."

=== FIN PARES ===

REGLAS ABSOLUTAS:
1. LONGITUD: entre 400 y 550 palabras en el cuerpo (bullets de "En Racha" no cuentan).
2. ARRANQUE: primera frase = dato concreto. Sin "Una nueva jornada..." ni similares.
3. SIN CIERRE: sin despedidas. El texto termina con el último dato o idea.
4. SIN EMOJIS: en ninguna parte.
5. IMPERSONAL: sin "tú", "vosotros", "usted". Tercera persona o formas impersonales.
6. ESPAÑOL DE ESPAÑA: "mate" no volcada, "cancha/parqué" no duela, "tiros libres" no lanzamiento personal.
7. INFERENCIA TÁCTICA: sin vídeo ni play-by-play. Enmarca como inferencia:
   "el USG% sugiere...", "la ratio AST/TO apunta a...", "con ese ORTG el sistema de X parece...".
   PROHIBIDO narrar acciones en tiempo real.
8. ENTRENADORES: solo los de los datos. No inventes.
9. NEGRITA en todos los números estadísticos.
10. VOCABULARIO PROHIBIDO: "créditos de valoración", "maestría", "denota", "subraya", "exhibe",
    "estelar", "galvaniza", "sin lugar a dudas", "no es casualidad", "en definitiva",
    "es importante señalar", "cabe destacar", "por otro lado", "en este sentido",
    "notable eficiencia", "producción significativa", "excepcional", "sobresaliente",
    "impresionante", "espectacular", "magistral", "portentoso".
11. NO EXPLIQUES LO OBVIO: el lector sabe qué es el USG%, el TS%, el ORTG y las demás métricas.
    NUNCA definas ni parafrasees lo que significa una estadística. Usa el dato directamente
    con tu interpretación. Si escribes algo parecido a "un alto ratio de asistencia apunta a
    buena circulación de balón", BÓRRALO. El lector ya lo sabe. Di algo con criterio propio
    o no digas nada.

FORMATO DE SALIDA:

ASUNTO: [sin emoji, con el hecho más relevante]

## Informe Liga Endesa: {ultima_jornada_label}

### MVP y Puntos Clave
[máx. 2-3 párrafos. Arranca con el dato. Co-MVPs = mismo espacio para cada uno.
Menciona a 1-2 jugadores destacados más si aportan algo a la narrativa.]

### Radar de Eficiencia
[máx. 4 bullets o 2 párrafos. ORTG mejor y peor, AST ratio, TO ratio.
Inferencia táctica. Entrenadores. Opinión con criterio.]{bloque_outsider_formato}

### En Racha (3 jornadas)
{txt_trends}"""

# ==============================================================================
# 7. GENERACIÓN CON GEMINI
# ==============================================================================
try:
    print(f"Generando newsletter para {ultima_jornada_label}...")
    model = genai.GenerativeModel(model_name=MODEL_NAME)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=0.7)
    )
    texto = response.text.replace(":\n-", ":\n\n-")
    guardar_salida(texto)
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
