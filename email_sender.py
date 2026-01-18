import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import markdown
import sys
import pandas as pd
import requests

# --- 1. CONFIGURACIÓN ---
URL_LOGO = "https://raw.githubusercontent.com/AnalyzingBasketball/acb-newsletter-bot/refs/heads/main/logo.png"

gmail_user = os.environ.get("GMAIL_USER")
gmail_password = os.environ.get("GMAIL_PASSWORD")
url_suscriptores = os.environ.get("URL_SUSCRIPTORES")
webhook_make = os.environ.get("MAKE_WEBHOOK_URL")

if not gmail_user or not gmail_password:
    print("❌ Error: Faltan credenciales GMAIL_USER o GMAIL_PASSWORD.")
    sys.exit(1)

# --- 2. LEER INFORME ---
ARCHIVO_MD = "newsletter_borrador.md"
if not os.path.exists(ARCHIVO_MD):
    print(f"❌ Error: No se encuentra {ARCHIVO_MD}")
    sys.exit(1)

with open(ARCHIVO_MD, "r", encoding="utf-8") as f:
    # Leemos líneas y quitamos las vacías al inicio para encontrar el título real
    lines = [line.strip() for line in f.readlines() if line.strip()]
    md_content = "\n".join(lines) # Reconstruimos el contenido limpio

# Extraemos título (primera línea no vacía, quitando #)
titulo_clean = lines[0].replace('#', '').strip() if lines else "Informe ACB"

# --- 3. PUBLICAR EN LINKEDIN (vía Make) ---
if webhook_make:
    texto_linkedin = f"""🏀 {titulo_clean}

📊 Nuevo análisis de datos disponible.
Lee el informe completo y suscríbete aquí: https://analyzingbasketball.wixsite.com/home/newsletter

#ACB #DataScouting #AnalyzingBasketball"""
    
    try:
        requests.post(webhook_make, json={"texto": texto_linkedin})
        print("✅ LinkedIn: Notificación enviada a Make.")
    except Exception as e:
        print(f"⚠️ Error LinkedIn: {e}")

# --- 4. PREPARAR EMAIL ---
print("📥 Preparando campaña de Email...")
html_body = markdown.markdown(md_content)

# Estilos CSS Inline mejorados para compatibilidad
plantilla_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style='font-family: Helvetica, Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0;'>
    <div style='background-color: #ffffff; max-width: 600px; margin: 20px auto; border: 1px solid #dddddd; border-radius: 8px; overflow: hidden;'>
        
        <div style='background-color: #0066FF; padding: 30px 20px; text-align: center;'>
            <img src="{URL_LOGO}" alt="Analyzing Basketball" style="max-width: 150px; width: 100%; height: auto; display: block; margin: 0 auto;">
        </div>

        <div style='padding: 40px 30px; color: #333333; line-height: 1.6; font-size: 16px;'>
            {html_body}
        </div>

        <div style='background-color: #ffffff; padding: 20px; text-align: center; padding-bottom: 40px;'>
            <a href="https://analyzingbasketball.wixsite.com/home/newsletter" 
               style='display: inline-block; background-color: #000000; color: #ffffff; padding: 14px 30px; text-decoration: none; font-weight: bold; font-size: 14px; letter-spacing: 1px; border-radius: 4px;'>
               RECOMENDAR
            </a>
        </div>

        <div style='background-color: #f9f9f9; padding: 30px; text-align: center; border-top: 1px solid #eeeeee;'>
            <a href='https://analyzingbasketball.wixsite.com/home' style='color: #000000; font-weight: bold; text-decoration: none; font-size: 14px; text-transform: uppercase;'>Analyzing Basketball</a>
            <p style='color: #999999; font-size: 11px; margin-top: 10px;'>&copy; 2026 AB</p>
            <p style='color: #cccccc; font-size: 10px;'>Si no deseas recibir estos correos, responde con BAJA.</p>
        </div>

    </div>
</body>
</html>
"""

# --- 5. GESTIÓN DE SUSCRIPTORES ---
lista_emails = []

# Añadir siempre al admin para verificar
if gmail_user:
    lista_emails.append(gmail_user)

if url_suscriptores:
    try:
        print("🔍 Descargando lista de suscriptores...")
        df_subs = pd.read_csv(url_suscriptores, on_bad_lines='skip', engine='python')
        
        # Lógica mejorada para encontrar la columna de emails
        col_email = None
        
        # 1. Buscar por nombre de columna
        possible_names = ['email', 'correo', 'e-mail', 'mail']
        for col in df_subs.columns:
            if str(col).lower() in possible_names:
                col_email = col
                break
        
        # 2. Si falla, buscar contenido con @
        if not col_email:
            for col in df_subs.columns:
                # Miramos los primeros 5 valores para ver si hay arrobas
                sample = df_subs[col].dropna().head(5).astype(str)
                if any("@" in x for x in sample):
                    col_email = col
                    break
        
        if col_email:
            nuevos_emails = df_subs[col_email].dropna().unique().tolist()
            # Limpieza básica de espacios
            nuevos_emails = [e.strip() for e in nuevos_emails if "@" in str(e)]
            
            # Evitar duplicados con el admin
            for e in nuevos_emails:
                if e not in lista_emails:
                    lista_emails.append(e)
            print(f"✅ Se encontraron {len(nuevos_emails)} suscriptores.")
        else:
            print("⚠️ No se detectó columna de Email en el CSV.")
            
    except Exception as e:
        print(f"⚠️ Error leyendo suscriptores: {e}")

# --- 6. ENVÍO MASIVO ---
print(f"🚀 Iniciando envío a {len(lista_emails)} destinatarios...")

try:
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(gmail_user, gmail_password)

    enviados = 0
    errores = 0

    for email in lista_emails:
        try:
            msg = MIMEMultipart()
            msg['From'] = f"Analyzing Basketball <{gmail_user}>"
            msg['To'] = email
            msg['Subject'] = f"🏀 Informe: {titulo_clean}"
            msg.attach(MIMEText(plantilla_html, 'html'))
            
            server.sendmail(gmail_user, email, msg.as_string())
            enviados += 1
            # Pequeña pausa para no saturar SMTP si la lista es grande
            # time.sleep(0.5) 
        except Exception as e:
            print(f"❌ Error enviando a {email}: {e}")
            errores += 1

    server.quit()
    print(f"\n📊 RESUMEN: {enviados} enviados | {errores} fallidos.")

except Exception as e:
    print(f"❌ Error crítico de conexión SMTP: {e}")
