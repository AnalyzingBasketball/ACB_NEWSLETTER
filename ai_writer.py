import pandas as pd
import os
import google.generativeai as genai
import sys
import re
import numpy as np

# ==============================================================================
# 1. CONFIGURACIÓN
# ==============================================================================
MODEL_NAME = "gemini-2.5-flash" 
FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"

# Diccionario de Equipos
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
    """Formatea números en negrita Markdown (ej: **24**)."""
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
genai.configure(api_key=api_key)

if not os.path.exists(FILE_PATH): guardar_salida("❌ No hay CSV.")

df = pd.read_csv(FILE_PATH)

# Asegurar numéricos
cols_num = ['VAL', 'PTS', 'Reb_T', 'AST', 'Win', 'Game_Poss', 'TO', 'TS%', 'USG%']
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Detectar última jornada
jornadas_unicas = sorted(df['Week'].unique(), key=extraer_numero_jornada)
ultima_jornada_label = jornadas_unicas[-1]
df_week = df[df['Week'] == ultima_jornada_label]

print(f"🤖 Analizando {ultima_jornada_label}...")

# ==============================================================================
# 4. PREPARACIÓN DE DATOS (Usando columnas del CSV)
# ==============================================================================

# --- A. MVP ---
ganadores = df_week[df_week['Win'] == 1]
pool = ganadores if not ganadores.empty else df_week
mvp = pool.sort_values('VAL', ascending=False).iloc[0]

# Usamos TS% directo del CSV
txt_mvp = (f"{mvp['Name']} ({get_team_name(mvp['Team'])}): {b(mvp['VAL'])} VAL, "
           f"{b(mvp['PTS'])} PTS (TS%: {b(mvp['TS%'], 1, True)}), {b(mvp['Reb_T'])} REB.")

# --- B. DESTACADOS ---
resto = df_week[df_week['PlayerID'] != mvp['PlayerID']]
top_rest = resto.sort_values('VAL', ascending=False).head(3)
txt_rest = ""
for _, row in top_rest.iterrows():
    txt_rest += f"- {row['Name']} ({get_team_name(row['Team'])}): {b(row['VAL'])} VAL.\n"

# --- C. EQUIPOS (Agregación necesaria) ---
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

# --- D. CONTEXTO (Usando columnas CSV) ---
# Líder en TS% (min 10 pts)
lider_ts = df_week[df_week['PTS'] >= 10].sort_values('TS%', ascending=False).iloc[0]
lider_reb = df_week.sort_values('Reb_T', ascending=False).iloc[0]
# Líder en USG% (quién amasó más balón)
lider_usg = df_week.sort_values('USG%', ascending=False).iloc[0]

txt_context = f"""
- Francotirador (TS%): {lider_ts['Name']} ({b(lider_ts['TS%'], 1, True)}).
- Dominador (USG%): {lider_usg['Name']} ({b(lider_usg['USG%'], 1, True)} de uso).
- Rebotes: {lider_reb['Name']} ({b(lider_reb['Reb_T'])}).
"""

# --- E. TENDENCIAS ---
txt_trends = ""
if len(jornadas_unicas) >= 1:
    last_3 = jornadas_unicas[-3:]
    df_last = df[df['Week'].isin(last_3)]
    
    # Media directa de las columnas del CSV
    means = df_last.groupby(['Name', 'Team'])[['VAL', 'PTS', 'TS%']].mean().reset_index()
    hot = means.sort_values('VAL', ascending=False).head(5)
    
    for _, row in hot.iterrows():
        txt_trends += (f"- {row['Name']} ({get_team_name(row['Team'], False)}): "
                       f"{b(row['VAL'], 1)} VAL, {b(row['PTS'], 1)} PTS.\n")

# ==============================================================================
# 5. GENERACIÓN IA
# ==============================================================================
prompt = f"""
Actúa como Periodista ACB. Escribe la crónica de la {ultima_jornada_label}.

DATOS (Números en negrita listos):
MVP: {txt_mvp}
DESTACADOS:
{txt_rest}
EQUIPOS:
{txt_teams}
CONTEXTO AVANZADO:
{txt_context}
TENDENCIAS (3 semanas):
{txt_trends}

INSTRUCCIONES:
1. **NOMBRES COMPLETOS**: Expande las iniciales (ej: "A. Tomic" -> "Ante Tomic") usando tu conocimiento.
2. **NARRATIVA**: Periodística y densa en datos.
3. **EQUIPOS**: Nombres completos en texto, siglas en listas.

ESTRUCTURA:
## 🏀 Crónica {ultima_jornada_label}

### 👑 El MVP
[Analiza al MVP con nombre completo]

### 🚀 Radar de Eficiencia
[Destacados y datos de contexto (TS%, USG%)]

### 🧠 Pizarra Táctica
[Análisis de equipos]

### 🔥 Tendencias
{txt_trends}
"""

try:
    print("🚀 Generando crónica...")
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    texto = response.text.replace(":\n-", ":\n\n-")
    guardar_salida(texto)
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
