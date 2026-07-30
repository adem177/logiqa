import re
import threading
from init_db import seed_admin, init_database
from flask import Flask, request, jsonify
from flask_cors import CORS
import bcrypt
import jwt
import os
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from functools import wraps
from db import get_connection
from collections import defaultdict
from time import time
import smtplib
import random
from email.mime.text import MIMEText
from pymysql.err import IntegrityError

load_dotenv()

app = Flask(__name__)

# ===== CORS RESTREINT (production) =====
# Remplacez '*' par votre domaine Angular exact
CORS(app, origins=os.getenv('FRONTEND_URL', 'http://localhost:4200'))

JWT_SECRET = os.getenv('JWT_SECRET')
if not JWT_SECRET:
    raise ValueError("JWT_SECRET est obligatoire dans les variables d'environnement")

SESSION_DURATION_DAYS = 2
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD')

# ===== OTP EN BASE DE DONNÉES (pas en RAM) =====
# Remplacez OTP_STORE = {} par une table SQL :
# CREATE TABLE otp_codes (
#   user_id INT PRIMARY KEY,
#   code VARCHAR(6) NOT NULL,
#   expires_at DATETIME NOT NULL,
#   attempts INT DEFAULT 0,
#   created_at DATETIME DEFAULT NOW()
# );

# ===== RATE LIMITING EN BASE (pas en RAM) =====
# Ou utilisez Flask-Limiter. Exemple simple avec DB :
def is_rate_limited_db(cursor, key, max_attempts=5, window_sec=300):
    """Vérifie les tentatives en base (compatible multi-worker)."""
    since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM login_attempts WHERE identifier=%s AND attempted_at > %s",
        (key, since.replace(tzinfo=None))
    )
    return cursor.fetchone()['cnt'] >= max_attempts

def record_attempt_db(cursor, conn, key):
    cursor.execute("INSERT INTO login_attempts (identifier, attempted_at) VALUES (%s, NOW())", (key,))
    conn.commit()

# ===== FONCTIONS UTILITAIRES =====
def hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def is_valid_password(password):
    return len(password) >= 8 and re.search(r'[A-Za-z]', password) and re.search(r'\d', password)

def contains_suspicious_html(text):
    return bool(re.search(r'<[^>]*>', text)) if text else False

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(to_email, code):
    """Retourne True si envoyé, False sinon."""
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        print("⚠️ Credentials email manquants")
        return False
    try:
        msg = MIMEText(
            f"Votre code de vérification LOGIQA est : {code}\n\n"
            f"Ce code expire dans 5 minutes.\n"
            f"Si vous n'avez pas demandé ce code, ignorez cet email."
        )
        msg['Subject'] = 'Votre code de vérification LOGIQA'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False

def create_token_response(user, cursor, conn):
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=SESSION_DURATION_DAYS)

    token = jwt.encode(
        {"id": user['id'], "email": user['email'], "role": user['role'],
         "jti": jti, "exp": expires_at},
        JWT_SECRET, algorithm="HS256"
    )

    token_hash = hash_token(token)
    expires_naive = expires_at.replace(tzinfo=None)

    cursor.execute(
        "INSERT INTO sessions (user_id, jti, token_hash, expires_at) VALUES (%s, %s, %s, %s)",
        (user['id'], jti, token_hash, expires_naive)
    )
    cursor.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user['id'],))
    conn.commit()

    return {"success": True, "user": user, "token": token, "expires_at": expires_at.isoformat()}

# ===== ROUTES =====
@app.route('/')
def home():
    return jsonify({"message": "API LOGIQA fonctionne !"})

# ===== INSCRIPTION =====
@app.route('/api/register', methods=['POST'])
def register():
    if not request.is_json:
        return jsonify({"error": "Content-Type application/json requis."}), 400

    data = request.get_json() or {}
    nom = data.get('nom', '').strip()
    prenom = data.get('prenom', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    telephone = data.get('telephone', '').strip()
    role_input = data.get('role', 'etudiant').strip()
    role = role_input if role_input in ['etudiant', 'enseignant'] else 'etudiant'

    if not all([nom, prenom, email, password]):
        return jsonify({"error": "Tous les champs obligatoires doivent être remplis."}), 400

    if not is_valid_password(password):
        return jsonify({"error": "Le mot de passe doit contenir au moins 8 caractères, une lettre et un chiffre."}), 400

    for field in [nom, prenom, email, telephone]:
        if field and contains_suspicious_html(field):
            return jsonify({"error": "Caractères non autorisés détectés."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "Un compte existe déjà avec cet email."}), 409

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (nom, prenom, email, password, telephone, role) VALUES (%s, %s, %s, %s, %s, %s)",
            (nom, prenom, email, hashed, telephone, role)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Compte créé avec succès."})
    except IntegrityError:
        return jsonify({"error": "Un compte existe déjà avec cet email."}), 409
    except Exception as e:
        print(f"Erreur inscription: {e}")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== CONNEXION ÉTAPE 1 (avec CAPTCHA côté serveur) =====
@app.route('/api/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"error": "Content-Type application/json requis."}), 400

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    captcha = data.get('captcha', '').strip()          # ← AJOUTÉ
    captcha_session = data.get('captcha_session', '')   # ← AJOUTÉ

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis."}), 400

    # TODO: Vérifier le captcha côté serveur (ex: stocké en session Redis/DB)
    # if not verify_server_captcha(captcha_session, captcha):
    #     return jsonify({"error": "Captcha incorrect."}), 403

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()

        # Rate limiting DB
        rate_key = email
        if is_rate_limited_db(cursor, rate_key):
            return jsonify({"error": "Trop de tentatives. Réessayez dans 5 minutes."}), 429

        cursor.execute(
            "SELECT id, nom, prenom, email, password, role FROM users WHERE email = %s", (email,)
        )
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            record_attempt_db(cursor, conn, rate_key)
            return jsonify({"error": "Email ou mot de passe incorrect."}), 401

        del user['password']

        # Vérifier cooldown OTP existant
        cursor.execute(
            "SELECT code, expires_at FROM otp_codes WHERE user_id = %s", (user['id'],)
        )
        existing = cursor.fetchone()
        if existing and datetime.now(timezone.utc) < existing['expires_at'].replace(tzinfo=timezone.utc):
            return jsonify({
                "success": True, "user_id": user['id'],
                "message": "Un code a déjà été envoyé. Vérifiez votre boîte mail."
            })

        # Générer OTP
        code = generate_otp()
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)

        cursor.execute(
            """INSERT INTO otp_codes (user_id, code, expires_at, attempts)
               VALUES (%s, %s, %s, 0)
               ON DUPLICATE KEY UPDATE code=%s, expires_at=%s, attempts=0""",
            (user['id'], code, expires.replace(tzinfo=None), code, expires.replace(tzinfo=None))
        )
        conn.commit()

        # Envoi asynchrone mais avec retour d'erreur loggé
        def async_send():
            ok = send_otp_email(user['email'], code)
            if not ok:
                print(f"⚠️ Échec envoi OTP à {user['email']}")

        threading.Thread(target=async_send, daemon=True).start()

        return jsonify({"success": True, "user_id": user['id']})

    except Exception as e:
        print(f"Erreur login: {e}")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== RENVOYER OTP (protégé par vérification basique) =====
@app.route('/api/resend-email', methods=['POST'])
def resend_email():
    if not request.is_json:
        return jsonify({"error": "Content-Type application/json requis."}), 400

    data = request.get_json() or {}
    user_id = data.get('user_id')
    email = data.get('email', '').strip().lower()

    if not user_id or not email:
        return jsonify({"error": "Champs manquants."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        # Vérifier que l'user existe et correspond à l'email
        cursor.execute("SELECT id, email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user or user['email'] != email:
            return jsonify({"error": "Non autorisé."}), 403

        code = generate_otp()
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)

        cursor.execute(
            """INSERT INTO otp_codes (user_id, code, expires_at, attempts)
               VALUES (%s, %s, %s, 0)
               ON DUPLICATE KEY UPDATE code=%s, expires_at=%s, attempts=0""",
            (user_id, code, expires.replace(tzinfo=None), code, expires.replace(tzinfo=None))
        )
        conn.commit()

        threading.Thread(target=send_otp_email, args=(email, code), daemon=True).start()
        return jsonify({"success": True, "message": "Un nouveau code a été envoyé."})

    except Exception as e:
        print(f"Erreur resend: {e}")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== VÉRIFICATION OTP (avec rate limiting par tentative) =====
@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    if not request.is_json:
        return jsonify({"error": "Content-Type application/json requis."}), 400

    data = request.get_json() or {}
    user_id = data.get('user_id')
    code = data.get('code', '').strip()

    if not user_id or not code:
        return jsonify({"error": "Champs manquants."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT code, expires_at, attempts FROM otp_codes WHERE user_id = %s", (user_id,)
        )
        entry = cursor.fetchone()

        if not entry:
            return jsonify({"error": "Aucun code en attente. Reconnectez-vous."}), 400

        # Incrémenter les tentatives
        new_attempts = entry['attempts'] + 1
        if new_attempts > 5:
            cursor.execute("DELETE FROM otp_codes WHERE user_id = %s", (user_id,))
            conn.commit()
            return jsonify({"error": "Trop de tentatives. Reconnectez-vous."}), 429

        cursor.execute(
            "UPDATE otp_codes SET attempts = %s WHERE user_id = %s",
            (new_attempts, user_id)
        )
        conn.commit()

        if datetime.now(timezone.utc) > entry['expires_at'].replace(tzinfo=timezone.utc):
            cursor.execute("DELETE FROM otp_codes WHERE user_id = %s", (user_id,))
            conn.commit()
            return jsonify({"error": "Code expiré. Reconnectez-vous."}), 400

        if code != entry['code']:
            return jsonify({"error": "Code incorrect."}), 401

        # Succès : supprimer l'OTP
        cursor.execute("DELETE FROM otp_codes WHERE user_id = %s", (user_id,))
        conn.commit()

        cursor.execute("SELECT id, nom, prenom, email, role FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Utilisateur introuvable."}), 404

        response = create_token_response(user, cursor, conn)
        return jsonify(response)

    except Exception as e:
        print(f"Erreur verify-otp: {e}")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== MIDDLEWARE (inchangé, fonctionnel) =====
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "Token manquant."}), 401

        token = auth_header.replace('Bearer ', '').strip()

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expiré."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token invalide."}), 401

        conn = get_connection()
        if not conn:
            return jsonify({"error": "Erreur base de données"}), 500

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT revoked, expires_at FROM sessions WHERE jti = %s", (payload['jti'],))
            session = cursor.fetchone()

            if not session:
                return jsonify({"error": "Session introuvable."}), 401
            if session['revoked']:
                return jsonify({"error": "Session révoquée."}), 401

            exp = session['expires_at']
            if isinstance(exp, datetime) and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if isinstance(exp, datetime) and exp < datetime.now(timezone.utc):
                return jsonify({"error": "Session expirée."}), 401

        finally:
            conn.close()

        request.user = payload
        return f(*args, **kwargs)
    return decorated

@app.route('/api/logout', methods=['POST'])
@token_required
def logout():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET revoked = TRUE WHERE jti = %s", (request.user['jti'],))
        conn.commit()
        return jsonify({"success": True, "message": "Déconnexion réussie."})
    except Exception as e:
        print(f"Erreur logout: {e}")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

@app.route('/api/me', methods=['GET'])
@token_required
def me():
    return jsonify({"user": request.user})

# ===== PURGE SESSIONS (à appeler via cron ou au démarrage) =====
def purge_expired_sessions():
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE expires_at < NOW()")
            conn.commit()
        finally:
            conn.close()

# ===== DÉMARRAGE =====
if __name__ == '__main__':
    if not init_database():
        raise SystemExit(1)

    purge_expired_sessions()

    port = int(os.getenv('PORT', 3000))
    # debug=False obligatoire en production
    app.run(host='0.0.0.0', debug=False, port=port)