import requests
import os
import re
import datetime
import subprocess 
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
TEMPORADA = '2025'
COMPETICION = '1'
HORAS_BUFFER = 12 
LOG_FILE = "data/log.txt"
BUFFER_FILE = "data/buffer_control.txt"

# API Key y Headers
API_KEY = '0dd94928-6f57-4c08-a3bd-b1b2f092976e'
HEADERS_API = {
    'x-apikey': API_KEY,
    'origin': 'https://live.acb.com',
    'referer': 'https://live.acb.com/',
    'user-agent': 'Mozilla/5.0'
}

# ==============================================================================
# ZONA 1: TUS FUNCIONES DE SCRAPING (VERIFICAR ESTADO)
# ==============================================================================

def get_last_jornada_from_log():
    if not os.path.exists(LOG_FILE):
        return 0
    last_jornada = 0
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                match = re.search(r'Jornada\s*[:#-]?\s*(\d+)', line, re.IGNORECASE)
                if match:
                    num = int(match.group(1))
                    if num > last_jornada:
                        last_jornada = num
    except Exception as e:
        print(f"Error leyendo log: {e}")
        return 0
    return last_jornada

def get_game_ids(temp_id, comp_id, jornada_id):
    url = f"https://www.acb.com/resultados-clasificacion/ver/temporada_id/{temp_id}/competicion_id/{comp_id}/jornada_numero/{jornada_id}"
    ids = []
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        for a in soup.find_all('a', href=True):
            if "/partido/estadisticas/id/" in a['href']:
                try:
                    pid = int(a['href'].split("/id/")[1].split("/")[0])
                    ids.append(pid)
                except: pass
        return list(set(ids))
    except: return []

def is_game_finished(game_id):
    url = "https://api2.acb.com/api/matchdata/Result/boxscores"
    try:
        r = requests.get(url, params={'matchId': game_id}, headers=HEADERS_API, timeout=5)
        if r.status_code != 200: return False
        data = r.json()
        if 'teamBoxscores' not in data or len(data['teamBoxscores']) < 2: return False
        return True
    except: return False

# ==============================================================================
# ZONA 2: EL PUENTE (ACTUALIZAR DATOS -> ESCRIBIR -> ENVIAR)
# ==============================================================================

def ejecutar_secuencia_completa(jornada):
    print(f"🔄 Iniciando secuencia completa para Jornada {jornada}...")

    # --- PASO 0: ACTUALIZAR EL CSV CON TU SCRAPER ---
    NOMBRE_SCRIPT_DATOS = "boxscore_ACB_headless.py" # <--- NOMBRE EXACTO PUESTO
    
    print(f"📥 0. Ejecutando {NOMBRE_SCRIPT_DATOS} para descargar estadísticas nuevas...")
    try:
        # Ejecutamos tu scraper. Como tu scraper sobrescribe el CSV Cumulative, 
        # al terminar tendremos los datos frescos listos para la IA.
        subprocess.run(["python", NOMBRE_SCRIPT_DATOS], check=True, text=True)
        print("✅ Datos actualizados correctamente.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico actualizando datos: {e}")
        return False

    # --- PASO 1: EJECUTAR LA IA ---
    print("🤖 1. Ejecutando ai_writer.py...")
    try:
        # La IA leerá el CSV que acabamos de actualizar en el paso 0
        subprocess.run(["python", "ai_writer.py"], check=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico en ai_writer: {e}")
        return False

    # --- PASO 2: ENVIAR EMAIL ---
    print("📧 2. Ejecutando email_sender.py...")
    try:
        # El sender leerá el .md generado por la IA en el paso 1
        subprocess.run(["python", "email_sender.py"], check=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error crítico en email_sender: {e}")
        return False

def gestionar_buffer(jornada):
    ahora = datetime.datetime.now()
    
    if os.path.exists(BUFFER_FILE):
        with open(BUFFER_FILE, "r") as f:
            contenido = f.read().strip().split(",")
            
        if len(contenido) != 2 or int(contenido[0]) != jornada:
            print(f"Detectado cambio de jornada o archivo corrupto. Reiniciando buffer para J{jornada}.")
            with open(BUFFER_FILE, "w") as f:
                f.write(f"{jornada},{ahora.timestamp()}")
            return False 

        timestamp_inicio = float(contenido[1])
        inicio_espera = datetime.datetime.fromtimestamp(timestamp_inicio)
        diferencia = ahora - inicio_espera
        horas_pasadas = diferencia.total_seconds() / 3600

        print(f"⏳ Buffer activo para J{jornada}. Llevamos {horas_pasadas:.2f} / {HORAS_BUFFER} horas.")

        if horas_pasadas >= HORAS_BUFFER:
            return True
        else:
            return False
            
    else:
        print(f"🆕 Jornada terminada detectada por primera vez. Iniciando cuenta atrás de {HORAS_BUFFER}h.")
        with open(BUFFER_FILE, "w") as f:
            f.write(f"{jornada},{ahora.timestamp()}")
        return False

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    last_sent = get_last_jornada_from_log()
    target_jornada = last_sent + 1
    
    print(f"--- INICIO SCRIPT DE CONTROL ---")
    print(f"Última enviada: {last_sent}. Revisando Jornada: {target_jornada}")

    game_ids = get_game_ids(TEMPORADA, COMPETICION, str(target_jornada))
    
    if not game_ids:
        print(f"⛔ Jornada {target_jornada} sin partidos o futura.")
        return

    finished_count = 0
    for gid in game_ids:
        if is_game_finished(gid):
            finished_count += 1
    
    print(f"📊 Estado J{target_jornada}: {finished_count}/{len(game_ids)} terminados.")

    if finished_count == len(game_ids) and len(game_ids) > 0:
        print("✅ Todos los partidos han terminado.")
        
        tiempo_cumplido = gestionar_buffer(target_jornada)
        
        if tiempo_cumplido:
            print("🚀 Buffer superado. Iniciando actualización de datos y envío...")
            
            exito = ejecutar_secuencia_completa(target_jornada)
            
            if exito:
                fecha_log = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                linea_log = f"{fecha_log} : ✅ Jornada {target_jornada} completada y enviada.\n"
                
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(linea_log)
                
                if os.path.exists(BUFFER_FILE):
                    os.remove(BUFFER_FILE)
                    
                print("🏁 Proceso finalizado con éxito.")
        else:
            print("zzz Esperando buffer...")
            
    else:
        print("⚽ Aún se está jugando.")
        if os.path.exists(BUFFER_FILE):
             os.remove(BUFFER_FILE)

if __name__ == "__main__":
    main()
