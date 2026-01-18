import pandas as pd
import os
import google.generativeai as genai
import sys
import re
import numpy as np

# ==============================================================================
# 1. CONFIGURACIÓN
# ==============================================================================
# Usamos el modelo con capacidad de búsqueda
MODEL_NAME = "gemini-2.5-flash"
FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"

# Diccionario de Equipos (Esto sí conviene mantenerlo para limpieza visual rápida)
TEAM_MAP = {
    'UNI': 'Unicaja', 'SBB': 'Bilbao Basket', 'BUR': 'San Pablo Burgos', 'GIR': 'Bàsquet Girona',
    'TEN': 'La Laguna Tenerife', 'MAN': 'BAXI Manresa', 'LLE': 'Hiopos Lleida', 'BRE': 'Río Breogán',
    'COV': 'Covirán Granada', 'JOV': 'Joventut Badalona', 'RMB': 'Real Madrid', 'GCA': 'Dreamland Gran Canaria',
    'CAZ': 'Casademont Zaragoza', 'BKN': 'Baskonia', 'UCM': 'UCAM Murcia', 'MBA': 'MoraBanc Andorra',
    'VBC': 'Valencia Basket', 'BAR': 'Barça'
}

# ==============================================================================
# 2. FUNCIONES AUXILIARES
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

# ==============================================================================
# 3. CARGA DE DATOS
# ==============================================================================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key: guardar_salida("❌ Error: Falta GEMINI_API_KEY.")

# Configuración básica
genai.configure(api_key=api_key)

if not os.path.exists(FILE_PATH): guardar_salida("❌ No hay CSV.")
df = pd.read_csv(FILE_PATH)

# Limpieza rápida
cols_num = ['VAL', 'PTS', 'Reb_T', 'AST', 'Win', 'Game_Poss', 'TO', 'TS%', 'USG%']
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

jornadas_unicas = sorted(df['Week'].unique(), key=extraer_numero_jornada)
ultima_jornada_label = jornadas_unicas[-1]
df_week = df[df['Week'] == ultima_jornada_label]

print(f"🤖 Analizando {ultima_jornada_label}...")

# ==============================================================================
# 4. PREPARACIÓN DE DATOS
# ==============================================================================

# A. MVP
ganadores = df_week[df_week['Win'] == 1]
pool = ganadores if not ganadores.empty else df_week
mvp = pool.sort_values('VAL', ascending=False).iloc[0]

# Nota: Pasamos el nombre tal cual ("F. Alonso"), Gemini buscará quién es.
txt_mvp = (f"{mvp['Name']} ({get_team_name(mvp['Team'])}): {b(mvp['VAL'])} VAL, "
           f"{b(mvp['PTS'])} PTS (TS%: {b(mvp['TS%'], 1, True)}), {b(mvp['Reb_T'])} REB.")

# B. DESTACADOS
resto = df_week[df_week['PlayerID'] != mvp['PlayerID']]
top_rest = resto.sort_values('VAL', ascending=False).head(3)
txt_rest = ""
for _, row in top_rest.iterrows():
    txt_rest += f"- {row['Name']} ({get_team_name(row['Team'])}): {b(row['VAL'])} VAL.\n"

# C. EQUIPOS
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
- Mejor Ataque: {get_team_name(best_offense['Team'])} ({b(best_offense['ORTG'], 1)} pts/100).
- Fluidez: {get_team_name(best_passing['Team'])} ({b(best_passing['AST_Ratio'], 1)} ast/100).
- Control: {get_team_name(most_careful['Team'])} ({b(most_careful['TO_Ratio'], 1)} perdidas/100).
"""

# D. CONTEXTO
lider_ts = df_week[df_week['PTS'] >= 10].sort_values('TS%', ascending=False).iloc[0]
lider_usg = df_week.sort_values('USG%', ascending=False).iloc[0]

txt_context = f"""
- Francotirador (TS%): {lider_ts['Name']} ({b(lider_ts['TS%'], 1, True)}).
- Dominador (USG%): {lider_usg['Name']} ({b(lider_usg['USG%'], 1, True)} de uso).
"""

# E. TENDENCIAS
txt_trends = ""
if len(jornadas_unicas) >= 1:
    last_3 = jornadas_unicas[-3:]
    df_last = df[df['Week'].isin(last_3)]
    means = df_last.groupby(['Name', 'Team'])[['VAL', 'PTS', 'TS%']].mean().reset_index()
    hot = means.sort_values('VAL', ascending=False).head(5)
    for _, row in hot.iterrows():
        txt_trends += (f"- {row['Name']} ({get_team_name(row['Team'], False)}): "
                       f"{b(row['VAL'], 1)} VAL, {b(row['PTS'], 1)} PTS.\n")

# ==============================================================================
# 5. GENERACIÓN IA CON GOOGLE SEARCH
# ==============================================================================

# PROMPT ESPECIAL PARA BÚSQUEDA
prompt = f"""
Eres un Analista de Baloncesto experto en Liga Endesa (ACB).

TU MISIÓN:
Escribir la crónica de la jornada {ultima_jornada_label} usando los datos proporcionados.

HERRAMIENTA OBLIGATORIA:
Tienes acceso a Google Search. **ÚSALO** para verificar los nombres de los jugadores que aparecen abreviados en los datos.
- Ejemplo: Si ves "F. Alonso" en los datos, busca "F. Alonso baloncesto equipo actual". Verás que es **Francis Alonso** (jugador del Breogán), NO Fernando Alonso (F1).
- Ejemplo: Si ves "D. Musa", verifica si sigue en el Real Madrid o si fichó por otro equipo en 2025 (ej: Dubai).
- NO ALUCINES POSICIONES: Busca la posición real del jugador si no la sabes.

DATOS DE LA JORNADA:
MVP: {txt_mvp}
DESTACADOS:
{txt_rest}
EQUIPOS:
{txt_teams}
CONTEXTO AVANZADO:
{txt_context}
TENDENCIAS (Últimas semanas):
{txt_trends}

ESTRUCTURA DE LA CRÓNICA:
## 🏀 Informe ACB: {ultima_jornada_label}

### 👑 El MVP
[Analiza al MVP usando su nombre completo verificado.]

### 🚀 Radar de Eficiencia
[Destacados. Verifica sus nombres.]

### 🧠 Pizarra Táctica
[Equipos.]

### 🔥 Tendencias
{txt_trends}
"""

try:
    print("🚀 Generando crónica (Buscando datos reales en Google)...")
    
    # ACTIVAMOS LA HERRAMIENTA DE BÚSQUEDA
    tools_config = [
        {"google_search": {}} 
    ]
    
    model = genai.GenerativeModel(MODEL_NAME, tools=tools_config)
    
    # Enviamos el prompt
    response = model.generate_content(prompt)
    
    # Procesamos la respuesta
    texto = response.text
    texto = texto.replace(":\n-", ":\n\n-")
    guardar_salida(texto)

except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
