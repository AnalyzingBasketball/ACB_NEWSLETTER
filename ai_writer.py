import pandas as pd
import os
import google.generativeai as genai
import sys

# --- CONFIGURACIÓN Y FUNCIONES AUXILIARES ---
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

# --- CARGA Y PREPARACIÓN DE DATOS ---
df = pd.read_csv(FILE_PATH)
if 'Week' not in df.columns: guardar_salida("❌ CSV sin columna Week.")

ultima_jornada = df['Week'].unique()[-1]
df_week = df[df['Week'] == ultima_jornada]
print(f"🤖 Analizando {ultima_jornada} con enfoque avanzado...")

# --- 1. ANÁLISIS DE JUGADORES (MVP y Top) ---
# Ordenamos por Game Score (GmSc) que es más moderna que la Valoración
top_players = df_week.sort_values('GmSc', ascending=False).head(4)
txt_players = ""
for _, row in top_players.iterrows():
    txt_players += f"- {row['Name']} ({row['Team']}): {row['PTS']}pts, {row['Reb_T']}reb, {row['AST']}ast. TS%: {row['TS%']}%. GmSc: {row['GmSc']}.\n"

# --- 2. ANÁLISIS DE EQUIPOS (NUEVO) ---
# Agrupamos por equipo sumando estadísticas clave
team_stats = df_week.groupby('Team').agg({
    'PTS': 'sum', 'Reb_T': 'sum', 'AST': 'sum', 
    'T3_M': 'sum', 'T3_A': 'sum',
    'Game_Poss': 'mean', # Las posesiones son las mismas para todo el equipo
    'Win': 'max' # 1 si ganaron, 0 si perdieron
}).reset_index()

# Calculamos Eficiencia Ofensiva (Puntos por 100 posesiones)
team_stats['ORTG'] = (team_stats['PTS'] / team_stats['Game_Poss']) * 100
team_stats['TS_Percent'] = team_stats['PTS'] / (2 * (team_stats['PTS'] + 0.44 * team_stats['T3_A'])) # Aproximación rápida

# Mejor Ataque
best_offense = team_stats.sort_values('ORTG', ascending=False).iloc[0]
# Equipo con más ritmo (Pace)
fastest_team = team_stats.sort_values('Game_Poss', ascending=False).iloc[0]
# Equipo bombardero (Más T3 intentados)
bombers = team_stats.sort_values('T3_A', ascending=False).iloc[0]

txt_teams = (
    f"- Mejor Ataque: {best_offense['Team']} con {best_offense['ORTG']:.1f} puntos/100 posesiones.\n"
    f"- Ritmo más alto: {fastest_team['Team']} ({fastest_team['Game_Poss']:.1f} posesiones).\n"
    f"- Francotiradores: {bombers['Team']} tiró {bombers['T3_A']} triples (metió {bombers['T3_M']})."
)

# --- 3. EL "OUTSIDER" / CURIOSIDAD (NUEVO) ---
# Buscamos un jugador de rotación (menos de 20 min) con alto impacto
# O un especialista defensivo (muchos robos/tapones)
micro_wave = df_week[(df_week['Min'].str.slice(0,2).astype(int) < 20) & (df_week['PTS'] > 12)]
if not micro_wave.empty:
    mw = micro_wave.sort_values('PTS', ascending=False).iloc[0]
    txt_outsider = f"El 'Microondas': {mw['Name']} ({mw['Team']}) metió {mw['PTS']} puntos en solo {mw['Min']} minutos."
else:
    # Si no hay microondas, buscamos al "Muro" (Tapones + Robos > 3)
    wall = df_week[(df_week['BLK'] + df_week['STL']) >= 4].sort_values('BLK', ascending=False)
    if not wall.empty:
        w = wall.iloc[0]
        txt_outsider = f"El Muro: {w['Name']} sumó {w['BLK']} tapones y {w['STL']} robos."
    else:
        txt_outsider = "Sin anomalías estadísticas destacables esta semana."

# --- 4. GENERACIÓN DEL PROMPT (TONO HUMANO) ---
prompt = f"""
Actúa como un analista de datos de baloncesto senior (estilo Zach Lowe o Kirk Goldsberry).
Tu objetivo es escribir una newsletter analítica, sobria pero interesante.
⛔ PROHIBIDO: Usar frases clichés como "festival de baloncesto", "amigos del balón naranja", "estratosférico", "buenos días".
✅ PERMITIDO: Usar jerga técnica (Spacing, Rim protection, Eficiencia, Pace) y un tono conversacional directo.

DATOS DE LA {ultima_jornada}:

TOP JUGADORES (Contexto):
{txt_players}

ANÁLISIS DE EQUIPOS (Contexto):
{txt_teams}

LA RAREZA ESTADÍSTICA (Outsider):
{txt_outsider}

ESTRUCTURA DEL ARTÍCULO (En Markdown):
1. **Titular**: Que sea un juego de palabras inteligente sobre el MVP o el equipo dominante.
2. **El Foco (MVP)**: Analiza por qué sus números son buenos (menciona el True Shooting o el impacto global, no solo los puntos).
3. **Pizarra Táctica (Equipos)**: Comenta qué equipo ha dominado el ritmo o el ataque. Usa los datos de ORTG (Puntos por 100 posesiones).
4. **Under the Radar (El Outsider)**: Menciona brevemente al jugador sorpresa.
5. **Cierre**: Una frase seca y directa sobre lo que esperar la próxima semana.

Escribe en español de España. Sé crítico si hace falta.
"""

# --- 5. LLAMADA A GEMINI ---
nombre_modelo = 'gemini-2.5-flash' # Tu modelo potente
try:
    print(f"⚡ Generando análisis con {nombre_modelo}...")
    model = genai.GenerativeModel(nombre_modelo)
    response = model.generate_content(prompt)
    guardar_salida(response.text)
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
