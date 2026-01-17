import pandas as pd
import os
import google.generativeai as genai
import sys

def guardar_salida(mensaje, nombre_archivo="newsletter_borrador.md"):
    print(mensaje)
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(mensaje)
    sys.exit(0)

# --- 1. CONFIGURACIÓN ---
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key: guardar_salida("❌ Error: Falta GEMINI_API_KEY.")

try:
    genai.configure(api_key=api_key)
except Exception as e:
    guardar_salida(f"❌ Error config Gemini: {e}")

FILE_PATH = "data/BoxScore_ACB_2025_Cumulative.csv"
if not os.path.exists(FILE_PATH): guardar_salida("❌ No hay CSV de datos.")

# --- 2. CARGA DE DATOS ---
df = pd.read_csv(FILE_PATH)
if 'Week' not in df.columns: guardar_salida("❌ CSV sin columna Week.")

# Detectar última jornada
jornadas = df['Week'].unique()
ultima_jornada_label = jornadas[-1] # Ej: "Jornada 15"
# Extraer el número de la jornada (ej: 15)
try:
    num_jornada = int(''.join(filter(str.isdigit, ultima_jornada_label)))
except:
    num_jornada = 0

df_week = df[df['Week'] == ultima_jornada_label]
print(f"🤖 Analizando {ultima_jornada_label} (MVP Real + Tendencias)...")

# --- 3. LÓGICA MVP OFICIAL (VALORACIÓN + VICTORIA) ---
# Filtramos jugadores que ganaron (Win = 1)
ganadores = df_week[df_week['Win'] == 1]

# Si por lo que sea no hay ganadores en la data, usamos a todos
pool_mvp = ganadores if not ganadores.empty else df_week

# El MVP es el de mayor VALORACIÓN (no GmSc)
mvp_row = pool_mvp.sort_values('VAL', ascending=False).iloc[0]

txt_mvp = (
    f"NOMBRE: {mvp_row['Name']} ({mvp_row['Team']})\n"
    f"STATS: {mvp_row['VAL']} de Valoración, {mvp_row['PTS']} puntos, {mvp_row['Reb_T']} rebotes.\n"
    f"RESULTADO: Su equipo ganó."
)

# --- 4. DESTACADOS SECUNDARIOS ---
# Quitamos al MVP para no repetirlo
resto = df_week[df_week['PlayerID'] != mvp_row['PlayerID']]
# Top 2 por Valoración
top_2 = resto.sort_values('VAL', ascending=False).head(2)
txt_destacados = ""
for _, row in top_2.iterrows():
    txt_destacados += f"- {row['Name']} ({row['Team']}): {row['VAL']} VAL, {row['PTS']} pts.\n"

# --- 5. DETECTAR RACHAS (FORM STATE) PARA EL CIERRE ---
# Queremos ver quién está "on fire" en los últimos 3 partidos
jugadores_hot = []

# Si tenemos suficientes datos históricos
if len(jornadas) >= 3:
    # Cogemos las últimas 3 jornadas
    ultimas_3 = jornadas[-3:]
    df_last_3 = df[df['Week'].isin(ultimas_3)]
    
    # Calculamos media de VAL por jugador
    medias = df_last_3.groupby(['Name', 'Team'])['VAL'].mean().reset_index()
    # Filtramos los que tengan media > 20 (Estrellas en forma)
    en_forma = medias[medias['VAL'] > 20].sort_values('VAL', ascending=False).head(3)
    
    for _, row in en_forma.iterrows():
        jugadores_hot.append(f"{row['Name']} ({row['Team']}) promedia {row['VAL']:.1f} VAL en los últimos 3 partidos.")

txt_rachas = "\n".join(jugadores_hot) if jugadores_hot else "No hay datos suficientes de rachas aún."

# --- 6. DATOS DE EQUIPO (Eficiencia) ---
team_stats = df_week.groupby('Team').agg({'PTS': 'sum', 'Game_Poss': 'mean', 'T3_M': 'sum', 'T3_A': 'sum'}).reset_index()
team_stats['ORTG'] = (team_stats['PTS'] / team_stats['Game_Poss']) * 100
mejor_ataque = team_stats.sort_values('ORTG', ascending=False).iloc[0]

# --- 7. PROMPT AVANZADO ---
prompt = f"""
Actúa como un periodista experto de la ACB (estilo Gigantes del Basket).
Escribe una crónica de la {ultima_jornada_label}.

DATOS OFICIALES:
🏆 MVP DE LA JORNADA (Oficial por Valoración):
{txt_mvp}

🌟 EL QUINTETO DE LA SEMANA (Otros destacados):
{txt_destacados}

📊 DATO TÁCTICO:
El mejor ataque fue {mejor_ataque['Team']} con un Ratio Ofensivo de {mejor_ataque['ORTG']:.1f} puntos/100 posesiones.

🔥 JUGADORES EN RACHA (Para la próxima jornada):
{txt_rachas}

INSTRUCCIONES DE ESTRUCTURA:
1. **Titular**: Épico, mencionando al MVP.
2. **El MVP**: Céntrate en su Valoración y dominio. Confirma que fue clave en la victoria.
3. **Zona Noble**: Repaso rápido a los otros destacados y al dato táctico del mejor equipo.
4. **🔭 Radar de la Jornada {num_jornada + 1} (El Cierre)**: 
   - No digas "veremos qué pasa".
   - Usa los datos de "JUGADORES EN RACHA" para advertir a los lectores de a quién vigilar la semana que viene.
   - Di que estos jugadores llegan en un estado de forma terrorífico.
   - Despide con una firma propia de newsletter (ej: "Hasta el próximo bocinazo").

Escribe en español de España. Tono profesional pero apasionado.
"""

# --- 8. GENERACIÓN ---
nombre_modelo = 'gemini-2.5-flash'
try:
    print(f"⚡ Generando newsletter con {nombre_modelo}...")
    model = genai.GenerativeModel(nombre_modelo)
    response = model.generate_content(prompt)
    guardar_salida(response.text)
except Exception as e:
    guardar_salida(f"❌ Error Gemini: {e}")
