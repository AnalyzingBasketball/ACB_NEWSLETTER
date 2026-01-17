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

# --- CARGA Y LIMPIEZA ---
df = pd.read_csv(FILE_PATH)
if 'Week' not in df.columns: guardar_salida("❌ CSV sin columna Week.")

ultima_jornada_label = df['Week'].unique()[-1]
df_week = df[df['Week'] == ultima_jornada_label]
print(f"🤖 Procesando {ultima_jornada_label} | Perfil: Data Scientist...")

# --- 1. MVP (Criterio: Victoria + Valoración + Eficiencia) ---
ganadores = df_week[df_week['Win'] == 1]
pool = ganadores if not ganadores.empty else df_week
mvp = pool.sort_values('VAL', ascending=False).iloc[0]

# Preparamos un bloque de texto técnico para el MVP
txt_mvp = (
    f"JUGADOR: {mvp['Name']} ({mvp['Team']})\n"
    f"VALORACIÓN: {mvp['VAL']} | PUNTOS: {mvp['PTS']} | REBOTES: {mvp['Reb_T']} | ASISTENCIAS: {mvp['AST']}\n"
    f"MÉTRICAS AVANZADAS: {mvp['TS%']}% True Shooting (TS%), {mvp['eFG%']}% Effective Field Goal (eFG%), "
    f"{mvp['USG%']}% Usage Rate (USG%), {mvp['GmSc']} Game Score.\n"
    f"IMPACTO: +/- en pista de {mvp['+/-']}."
)

# --- 2. DESTACADOS (TOP 3 PERO CON DATOS AVANZADOS) ---
resto = df_week[df_week['PlayerID'] != mvp['PlayerID']]
top_rest = resto.sort_values('VAL', ascending=False).head(3)
txt_rest = ""
for _, row in top_rest.iterrows():
    txt_rest += (
        f"- {row['Name']} ({row['Team']}): {row['PTS']} pts, {row['VAL']} VAL. "
        f"Eficiencia: {row['TS%']}% TS con un uso del {row['USG%']}%.\n"
    )

# --- 3. ANÁLISIS DE EQUIPOS (FOUR FACTORS SIMPLIFICADOS) ---
# Agrupamos
team_stats = df_week.groupby('Team').agg({
    'PTS': 'sum', 'Game_Poss': 'mean', 
    'T3_M': 'sum', 'T3_A': 'sum',
    'Reb_O': 'sum', 'Reb_D': 'sum',
    'TO': 'sum'
}).reset_index()

# Cálculos avanzados de equipo
team_stats['ORTG'] = (team_stats['PTS'] / team_stats['Game_Poss']) * 100
team_stats['eFG'] = (team_stats['PTS'] - team_stats['TO']) # Simplificación para contexto, usamos mejor T3%
team_stats['T3_PCT'] = (team_stats['T3_M'] / team_stats['T3_A']) * 100

best_offense = team_stats.sort_values('ORTG', ascending=False).iloc[0]
highest_pace = team_stats.sort_values('Game_Poss', ascending=False).iloc[0]
best_shooter = team_stats.sort_values('T3_PCT', ascending=False).iloc[0]

txt_teams = (
    f"- Eficiencia Ofensiva (ORTG): {best_offense['Team']} lideró con {best_offense['ORTG']:.1f} puntos/100 posesiones.\n"
    f"- Ritmo (Pace): {highest_pace['Team']} jugó a {highest_pace['Game_Poss']:.1f} posesiones.\n"
    f"- Acierto Exterior: {best_shooter['Team']} firmó un {best_shooter['T3_PCT']:.1f}% en triples ({best_shooter['T3_M']}/{best_shooter['T3_A']})."
)

# --- 4. TENDENCIAS (LAST 3 GAMES) ---
# Solo si hay histórico suficiente
jornadas = df['Week'].unique()
txt_trends = "Datos insuficientes para análisis de tendencias (Week 1)."
if len(jornadas) >= 3:
    last_3 = jornadas[-3:]
    df_last_3 = df[df['Week'].isin(last_3)]
    # Calculamos medias
    means = df_last_3.groupby(['Name', 'Team'])[['VAL', 'TS%', 'USG%']].mean().reset_index()
    # Filtro: Jugadores con >15 VAL media
    hot = means[means['VAL'] > 18].sort_values('VAL', ascending=False).head(3)
    
    txt_trends = ""
    for _, row in hot.iterrows():
        txt_trends += (
            f"- {row['Name']} ({row['Team']}): Promedio {row['VAL']:.1f} VAL | {row['TS%']:.1f}% TS | {row['USG%']:.1f}% USG (Últimos 3 partidos).\n"
        )

# --- 5. EL PROMPT TÉCNICO ---
prompt = f"""
Actúa como Lead Data Scientist para la consultora "Analyzing Basketball".
Escribe un informe técnico semanal sobre la {ultima_jornada_label} de la Liga Endesa.

OBJETIVO:
Proveer un análisis sobrio, basado puramente en métricas avanzadas, eliminando cualquier subjetividad periodística.

REGLAS DE ESTILO (ESTRICTAS):
- TONO: Serio, profesional, clínico. Cero entusiasmo.
- FORMATO: Sin emojis. Uso de negritas solo para nombres o métricas clave.
- NOMBRES: Usa EXACTAMENTE los nombres proporcionados en los datos. No los modifiques (Ej: Si dice Ante Tomic, no escribas Andrej).
- FIRMA: Analyzing Basketball.

DATOS INPUT:

1. MVP DE LA JORNADA (Datos):
{txt_mvp}

2. RENDIMIENTO INDIVIDUAL (Top Performers):
{txt_rest}

3. MÉTRICAS DE EQUIPO (Advanced Stats):
{txt_teams}

4. TENDENCIAS Y FORMA (Last 3 Games):
{txt_trends}

ESTRUCTURA DEL INFORME:
**INFORME TÉCNICO: {ultima_jornada_label}**

**1. Análisis de Impacto Individual (MVP)**
Desglosa el rendimiento del MVP centrándote en la eficiencia (TS%, eFG%) y el volumen de uso (USG%). Explica por qué su valoración es relevante en el contexto de la victoria. Se analítico.

**2. Cuadro de Honor Estadístico**
Resumen breve de los otros destacados, citando sus métricas de eficiencia.

**3. Desempeño Colectivo (ORTG & Pace)**
Análisis de los equipos destacados en eficiencia ofensiva y ritmo de juego.

**4. Proyección Estadística (Tendencias)**
Menciona a los jugadores con mejor promedio en las últimas 3 jornadas como activos a vigilar.

---
Firma: Analyzing Basketball
"""

# --- 6. GENERACIÓN ---
nombre_modelo = 'gemini-2.5-flash'
try:
    print(f"⚡ Generando informe técnico con {nombre_modelo}...")
    model = genai.GenerativeModel(nombre_modelo)
    response = model.generate_content(prompt)
    guardar_salida(response.text)
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
