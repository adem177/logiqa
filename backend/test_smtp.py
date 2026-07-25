"""
Script de test isolé pour vérifier la connexion SMTP Gmail.
Usage : python test_smtp.py
"""
import smtplib
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText

load_dotenv()

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD')

print(f"EMAIL_ADDRESS lu depuis .env : {repr(EMAIL_ADDRESS)}")
print(f"EMAIL_APP_PASSWORD lu depuis .env : {repr(EMAIL_APP_PASSWORD)}")
print(f"Longueur du mot de passe : {len(EMAIL_APP_PASSWORD) if EMAIL_APP_PASSWORD else 0} caractères")

if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
    print("\n❌ EMAIL_ADDRESS ou EMAIL_APP_PASSWORD est vide/absent dans .env")
    exit(1)

try:
    msg = MIMEText("Ceci est un test de connexion SMTP.")
    msg['Subject'] = 'Test SMTP Logiqa'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS  # on s'envoie le test à soi-même

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)

    print("\n✅ Email envoyé avec succès ! Vérifie ta boîte de réception.")
except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ Erreur d'authentification SMTP : {e}")
    print("→ Le mot de passe d'application est probablement incorrect ou mal copié.")
except Exception as e:
    print(f"\n❌ Erreur : {e}")