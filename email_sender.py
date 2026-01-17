import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import markdown
import sys
import pandas as pd
import requests

# --- 1. TU URL DEL LOGO (LA BUENA) ---
URL_LOGO = "https://raw.githubusercontent.com/AnalyzingBasketball/acb-newsletter-bot/refs/heads/main/logo.png"

# --- 2. CONFIGURACIÓN ---
gmail_user = os.environ.get("GMAIL_USER")
gmail_password = os.environ.get("GMAIL_PASSWORD")
url_suscriptores = os.environ.get("URL_SUSCRIPTORES")
webhook_make = os.environ.get("MAKE_WEBHOOK_URL")

if not gmail_user or not gmail_password:
    sys.exit("❌ Error: Faltan credenciales.")

# --- 3. LEER INFORME ---
if not os.path.exists("newsletter_borrador.md"):
    sys.exit("❌ No hay informe generado.")

with open("newsletter_borrador.md", "r", encoding="utf-8") as f:
    md_content = f.read()

titulo_redes = md_content.split('\n')[0].replace('#', '').strip()

# --- 4. LINKEDIN ---
texto_linkedin = f"""🏀 {titulo_redes}

📊 Nuevo análisis de datos disponible.
Lee el informe completo y suscríbete aquí: https://analyzingbasketball.wixsite.com/home/newsletter

#ACB #DataScouting #AnalyzingBasketball"""

if webhook_make:
    try:
        requests.post(webhook_make, json={"texto": texto_linkedin})
        print("✅ LinkedIn OK")
    except: pass

# --- 5. EMAIL ---
print("📥 Enviando Email...")
html_content = markdown.markdown(md_content)

plantilla = f"""
<html><body style='font-family: Helvetica, Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;'>
<div style='background-color: #ffffff; max-width: 600px; margin: 0 auto; border: 1px solid #dddddd;'>
    
    <div style='background-color: #000000; padding: 30px 20px; text-align: center;'>
        <img src="{URL_LOGO}" alt="Analyzing Basketball" style="max-width: 150px; height: auto; display: block; margin: 0 auto;">
    </div>

    <div style='padding: 40px 30px; color: #333333; line-height: 1.6; font-size: 16px;'>
        {html_content}
    </div>

    <div style='background-color: #ffffff; padding: 20px; text-align: center; padding-bottom: 40px;'>
        <a href="https://analyzingbasketball.wixsite.com/home/newsletter" style='display: inline-block; background-color: #000000; color: #ffffff; padding: 14px 30px; text-decoration: none; font-weight: bold; font-size: 14px; letter-spacing: 1px;'>RECOMENDAR</a>
    </div>

    <div style='background-color: #f9f9f9; padding: 30px; text-align: center; border-top: 1px solid #eeeeee;'>
        <a href='https://analyzingbasketball.wixsite.com/home' style='color: #000000; font-weight: bold; text-decoration: none; font-size: 14px; text-transform: uppercase;'>Analyzing Basketball</a>
        <p style='color: #999999; font-size: 11px; margin-top: 10px;'>&copy; 2026 AB</p>
    </div>

</div>
</body></html>
"""

# Envío
lista_emails = []
if url_suscriptores:
    try:
        df = pd.read_csv(url_suscriptores, on_bad_lines='skip', engine='python')
        col = next((c for c in df.columns if "@" in str(df[c].iloc[0])), None)
        if col: lista_emails = df[col].dropna().unique().tolist()
    except: pass

if gmail_user not in lista_emails: lista_emails.append(gmail_user)

server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(gmail_user, gmail_password)

for email in lista_emails:
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Analyzing Basketball <{gmail_user}>"
        msg['To'] = email.strip()
        msg['Subject'] = f"🏀 Informe: {titulo_redes}"
        msg.attach(MIMEText(plantilla, 'html'))
        server.sendmail(gmail_user, email.strip(), msg.as_string())
    except: continue

server.quit()
print("✅ TODO COMPLETADO.")
