import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import markdown
import sys
import pandas as pd

# --- 1. CONFIGURACIÓN ---
URL_LOGO = "https://raw.githubusercontent.com/AnalyzingBasketball/ACB_2526_NEWSLETTER/refs/heads/main/logo.png"
# AQUÍ AÑADIMOS LA URL DE TU LOGO DE LA ACB
URL_LOGO_ACB = "https://raw.githubusercontent.com/AnalyzingBasketball/ACB_2526_NEWSLETTER/refs/heads/main/logo_acb.png"
URL_BAJA = "https://www.analyzingbasketball.com/home/baja"

gmail_user = os.environ.get("GMAIL_USER")
gmail_password = os.environ.get("GMAIL_PASSWORD")
url_suscriptores = os.environ.get("URL_SUSCRIPTORES")

if not gmail_user or not gmail_password:
    print("❌ Error: Faltan credenciales GMAIL_USER o GMAIL_PASSWORD.")
    sys.exit(1)

# --- 2. LEER INFORME ---
ARCHIVO_MD = "newsletter_borrador.md"
if not os.path.exists(ARCHIVO_MD):
    print(f"❌ Error: No se encuentra {ARCHIVO_MD}")
    sys.exit(1)

# LEEMOS TODO EL CONTENIDO RESPETANDO ESPACIOS (Clave para listas Markdown)
with open(ARCHIVO_MD, "r", encoding="utf-8") as f:
    raw_content = f.read()

# Dividimos en líneas pero manteniendo el formato
lines = raw_content.split('\n')
first_line = lines[0].strip() if lines else "Informe ACB"

# LÓGICA DE ASUNTO CLICKBAIT
if first_line.startswith("ASUNTO:"):
    # 1. Extraemos el asunto "Clickbait"
    asunto_texto = first_line.replace("ASUNTO:", "").strip()
    asunto_email = f"🏀 {asunto_texto}"
    
    # 2. Quitamos la primera línea del cuerpo del mensaje para no repetirla
    # Unimos el resto de líneas recuperando los saltos de línea
    md_content = "\n".join(lines[1:])
else:
    # Lógica antigua (por si la IA falla y no pone ASUNTO:)
    md_content = raw_content
    titulo_clean = first_line.replace('#', '').strip()
    asunto_email = f"🏀 Informe: {titulo_clean}"

# --- 3. PREPARAR CAMPAÑA ---
print("📥 Preparando campaña de Email...")

# Convertimos a HTML (Markdown detectará bien las listas ahora)
html_body = markdown.markdown(md_content)

plantilla_html_base = f"""
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
            
            <div style='text-align: center; margin-bottom: 25px;'>
                <img src="{URL_LOGO_ACB}" alt="Liga Endesa ACB" style="max-width: 90px; height: auto; display: inline-block;">
            </div>

            {html_body}
        </div>

        <div style='background-color: #ffffff; padding: 20px; text-align: center; padding-bottom: 40px;'>
            <a href="https://www.analyzingbasketball.com/" 
               style='display: inline-block; background-color: #000000; color: #ffffff; padding: 14px 30px; text-decoration: none; font-weight: bold; font-size: 14px; letter-spacing: 1px; border-radius: 4px;'>
                HOME
            </a>
        </div>

        <div style='background-color: #f9f9f9; padding: 30px; text-align: center; border-top: 1px solid #eeeeee;'>
            <a href='https://www.analyzingbasketball.com/' style='color: #000000; font-weight: bold; text-decoration: none; font-size: 14px; text-transform: uppercase;'>Analyzing Basketball</a>
            <p style='color: #999999; font-size: 11px; margin-top: 10px;'>&copy; 2026 AB</p>
            
            <p style='margin-top: 20px;'>
                <a href="{URL_BAJA}" style='color: #cccccc; font-size: 10px; text-decoration: underline;'>
                    Darse de baja
                </a>
            </p>
        </div>

    </div>
</body>
</html>
"""

# --- 4. GESTIÓN DE SUSCRIPTORES ---
lista_emails = []
if gmail_user: lista_emails.append(gmail_user)

if url_suscriptores:
    try:
        print(f"🔍 Descargando lista de suscriptores...")
        df_subs = pd.read_csv(url_suscriptores, on_bad_lines='skip', engine='python')
        df_subs.columns = [str(c).lower().strip() for c in df_subs.columns]
        
        col_email = None
        for col in df_subs.columns:
            if col in ['email', 'correo', 'e-mail', 'mail']:
                col_email = col
                break
        
        if not col_email:
            for col in df_subs.columns:
                sample = df_subs[col].astype(str).head(5).tolist()
                if any("@" in s for s in sample):
                    col_email = col
                    break

        if col_email:
            nuevos = df_subs[col_email].dropna().astype(str).unique().tolist()
            # Filtro estricto: Debe tener @ y .
            nuevos = [e.strip() for e in nuevos if "@" in e and "." in e]
            
            count = 0
            for e in nuevos:
                if e not in lista_emails:
                    lista_emails.append(e)
                    count += 1
            print(f"✅ Se encontraron {count} suscriptores nuevos en el CSV.")
        else:
            print(f"⚠️ ATENCIÓN: No se encontró columna de Email.")

    except Exception as e:
        print(f"⚠️ Error crítico leyendo suscriptores: {e}")

# --- 5. ENVÍO MASIVO ---
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
            msg['Subject'] = asunto_email
            msg.attach(MIMEText(plantilla_html_base, 'html'))
            
            server.sendmail(gmail_user, email, msg.as_string())
            enviados += 1
            print(f"📨 Enviado a: {email}")
            
        except Exception as e:
            print(f"❌ Error enviando a {email}: {e}")
            errores += 1

    server.quit()
    print(f"\n📊 FIN: {enviados} enviados | {errores} fallidos.")

except Exception as e:
    print(f"❌ Error conectando con Gmail: {e}")
