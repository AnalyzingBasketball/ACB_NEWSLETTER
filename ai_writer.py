import pandas as pd
import os
import google.generativeai as genai
import sys

# --- CONFIGURACIÓN ---
def guardar_salida(mensaje, nombre_archivo="newsletter_borrador.md"):
    print(mensaje)
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(mensaje)
    sys.exit(0)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key: guardar_salida("❌ Error: Falta GEMINI_API_KEY.")

try:
    genai.configure(api_key=api_key)
except Exception as e:
    guardar_salida(f"❌ Error config Gemini: {e}")

FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"
if not os.path.exists(FILE_PATH): guardar_salida("❌ No hay CSV de datos.")

# --- CARGA DATOS ---
df = pd.read_csv(FILE_PATH)
if 'Week' not in df.columns: guardar_salida("❌ CSV sin columna Week.")

ultima_jornada_label = df['Week'].unique()[-1]
df_week = df[df['Week'] == ultima_jornada_label]
print(f"🤖 Procesando {ultima_jornada_label}...")

# --- 1. MVP ---
ganadores = df_week[df_week['Win'] == 1]
pool = ganadores if not ganadores.empty else df_week
mvp = pool.sort_values('VAL', ascending=False).iloc[0]
txt_mvp = f"{mvp['Name']} ({mvp['Team']}): {mvp['VAL']} VAL, {mvp['PTS']} pts, {mvp['Reb_T']} reb."

# --- 2. DESTACADOS ---
resto = df_week[df_week['PlayerID'] != mvp['PlayerID']]
top_rest = resto.sort_values('VAL', ascending=False).head(3)
txt_rest = ""
for _, row in top_rest.iterrows():
    txt_rest += f"- {row['Name']} ({row['Team']}): {row['VAL']} VAL.\n"

# --- 3. EQUIPOS ---
team_stats = df_week.groupby('Team').agg({'PTS': 'sum', 'Game_Poss': 'mean'}).reset_index()
team_stats['ORTG'] = (team_stats['PTS'] / team_stats['Game_Poss']) * 100
best_offense = team_stats.sort_values('ORTG', ascending=False).iloc[0]
txt_teams = f"Mejor Ataque: {best_offense['Team']} ({best_offense['ORTG']:.1f} pts/100 poss)."

# --- 4. TENDENCIAS (SIN RESTRICCIONES) ---
jornadas = df['Week'].unique()

# Cogemos hasta las últimas 3 que existan (si solo hay 1, coge 1)
last_3 = jornadas[-3:]
df_last = df[df['Week'].isin(last_3)]

# Definimos columnas exactas (He verificado que tu CSV tiene 'AST')
cols_calc = ['VAL', 'PTS', 'Reb_T', 'AST']

# Calculamos medias
means = df_last.groupby(['Name', 'Team'])[cols_calc].mean().reset_index()
hot = means.sort_values('VAL', ascending=False).head(5)

txt_trends = ""
for _, row in hot.iterrows():
    # Construimos la línea limpia con AST
    txt_trends += f"- {row['Name']} ({row['Team']}): {row['VAL']:.1f} VAL, {row['PTS']:.1f} PTS, {row['Reb_T']:.1f} REB, {row['AST']:.1f} AST.\n"

# --- 5. PROMPT ---
prompt = f"""
Actúa como Data Scientist de "Analyzing Basketball". Escribe un informe técnico de la {ultima_jornada_label}.

DATOS:
MVP: {txt_mvp}
TOP: {txt_rest}
EQUIPO: {txt_teams}
TENDENCIAS (Medias recientes):
{txt_trends}

ESTRUCTURA OBLIGATORIA (Usa saltos de línea para las listas):
**INFORME TÉCNICO: {ultima_jornada_label}**

**1. Análisis de Impacto Individual**
[Analiza al MVP en 3 líneas]

**2. Cuadro de Honor**
[Menciona a los destacados]

**3. Desempeño Colectivo**
[Menciona el mejor ataque]

**4. Proyección Estadística (Tendencias)**
A continuación, los jugadores a vigilar la próxima semana por su estado de forma (Medias últimas jornadas):

[INSTRUCCIÓN CRÍTICA: Copia la lista de tendencias TAL CUAL. Usa guiones para crear una lista vertical. NO añadas texto repetitivo como 'Media ult. 3 partidos'. Solo los datos.]
{txt_trends}

---
AB
"""

# --- 6. GENERACIÓN ---
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    
    texto_final = response.text
    # Forzamos visualmente la separación de la lista
    texto_final = texto_final.replace(". -", ".\n\n-").replace(": -", ":\n\n-")
    
    guardar_salida(texto_final)
    
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
