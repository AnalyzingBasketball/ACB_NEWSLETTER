import requests
import os
import sys
import re
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
TEMPORADA = '2025' 
COMPETICION = '1' 
LOG_FILE = "data/log.txt" # Ahora usamos este archivo

# API Key y Headers
API_KEY = '0dd94928-6f57-4c08-a3bd-b1b2f092976e'
HEADERS_API = {
    'x-apikey': API_KEY,
    'origin': 'https://live.acb.com',
    'referer': 'https://live.acb.com/',
    'user-agent': 'Mozilla/5.0'
}

# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def get_last_jornada_from_log():
    """Lee el log.txt y encuentra el número de jornada más alto enviado."""
    if not os.path.exists(LOG_FILE):
        return 0
    
    last_jornada = 0
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            for line in lines:
                # Buscamos patrones como "Jornada 17" o "Jornada: 17"
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
# MAIN
# ==============================================================================

def main():
    # 1. Averiguar última jornada enviada leyendo el LOG
    last_sent = get_last_jornada_from_log()
    target_jornada = last_sent + 1
    
    print(f"📖 LOG LEÍDO. Última jornada enviada: {last_sent}")
    print(f"🎯 OBJETIVO: Verificar estado de Jornada {target_jornada}")

    # 2. Buscar partidos
    game_ids = get_game_ids(TEMPORADA, COMPETICION, str(target_jornada))
    
    if not game_ids:
        print(f"⛔ Jornada {target_jornada} sin partidos o futura.")
        set_github_output("false", target_jornada)
        return

    # 3. Verificar estado
    finished_count = 0
    for gid in game_ids:
        if is_game_finished(gid):
            finished_count += 1
    
    print(f"📊 Estado Jornada {target_jornada}: {finished_count}/{len(game_ids)} terminados.")

    # 4. Decisión
    if finished_count == len(game_ids) and len(game_ids) > 0:
        print("🚀 ¡Jornada completa! Autorizando envío.")
        set_github_output("true", target_jornada)
    else:
        print("zzz Aún se está jugando.")
        set_github_output("false", target_jornada)

def set_github_output(should_run, jornada_num):
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            print(f"SHOULD_RUN={should_run}", file=fh)
            print(f"TARGET_JORNADA={jornada_num}", file=fh)

if __name__ == "__main__":
    main()
