import re
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

# ===== RATE LIMITING =====
FAILED_LOGINS = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SEC = 300  # 5 minutes

def is_rate_limited(key):
    now = time()
    FAILED_LOGINS[key] = [t for t in FAILED_LOGINS[key] if now - t < WINDOW_SEC]
    return len(FAILED_LOGINS[key]) >= MAX_ATTEMPTS

def record_failed_attempt(key):
    FAILED_LOGINS[key].append(time())

def reset_attempts(key):
    FAILED_LOGINS[key] = []

# ===== CHARGEMENT ENV =====
load_dotenv()

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.getenv('JWT_SECRET', 'votre_secret_par_defaut')
SESSION_DURATION_DAYS = 2

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD')

# ===== STOCKAGE TEMPORAIRE DES CODES OTP (en mémoire) =====
OTP_STORE = {}
OTP_VALIDITY_MINUTES = 5

# ===== FONCTIONS UTILITAIRES =====
def hash_token(token):
    """Hash le token avant de le stocker en base (jamais en clair)."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def is_valid_password(password):
    """Vérifie la force du mot de passe."""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Za-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True

def contains_suspicious_html(text):
    """Détecte les balises HTML suspectes."""
    if not text:
        return False
    return bool(re.search(r'<[^>]*>', text))

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(to_email, code):
    msg = MIMEText(
        f"Votre code de vérification LOGIQA est : {code}\n\n"
        f"Ce code expire dans {OTP_VALIDITY_MINUTES} minutes."
    )
    msg['Subject'] = 'Votre code de vérification LOGIQA'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)

def create_token_response(user, cursor, conn):
    """Génère le JWT, crée la session en base, et renvoie la réponse complète."""
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=SESSION_DURATION_DAYS)

    token = jwt.encode(
        {
            "id": user['id'],
            "email": user['email'],
            "role": user['role'],
            "jti": jti,
            "exp": expires_at
        },
        JWT_SECRET,
        algorithm="HS256"
    )

    token_hash = hash_token(token)
    expires_at_naive = expires_at.replace(tzinfo=None)

    cursor.execute(
        "INSERT INTO sessions (user_id, jti, token_hash, expires_at) VALUES (%s, %s, %s, %s)",
        (user['id'], jti, token_hash, expires_at_naive)
    )
    cursor.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user['id'],))
    conn.commit()

    return {
        "success": True,
        "user": user,
        "token": token,
        "expires_at": expires_at.isoformat()
    }

# ===== ROUTES =====
@app.route('/')
def home():
    return jsonify({"message": "API LOGIQA fonctionne !"})

# ===== INSCRIPTION =====
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    # Récupérer depuis le formulaire Angular
    nom = data.get('nom', '').strip()
    prenom = data.get('prenom', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    telephone = data.get('telephone', '').strip()
    role = 'etudiant'

    if not all([nom, prenom, email, password]):
        return jsonify({"error": "Tous les champs obligatoires doivent être remplis."}), 400

    if not is_valid_password(password):
        return jsonify({"error": "Le mot de passe doit contenir au moins 8 caractères, une lettre et un chiffre."}), 400

    for field in [nom, prenom, email, telephone]:
        if field and contains_suspicious_html(field):
            return jsonify({"error": "Caractères non autorisés détectés."}), 400

    if len(nom) > 100 or len(prenom) > 100:
        return jsonify({"error": "Nom ou prénom trop long."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "Un compte existe déjà avec cet email."}), 409

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # ✅ CORRECTION : Utiliser nom ET prenom (colonnes séparées)
        cursor.execute(
            "INSERT INTO users (nom, prenom, email, password, telephone, role) VALUES (%s, %s, %s, %s, %s, %s)",
            (nom, prenom, email, hashed_password, telephone, role)
        )
        conn.commit()

        return jsonify({"success": True, "message": "Compte créé avec succès."})
    except IntegrityError:
        # Cas où deux requêtes concurrentes (double-clic, double-submit) passent
        # le SELECT avant que l'une des deux ait fait son INSERT.
        return jsonify({"error": "Un compte existe déjà avec cet email."}), 409
    except Exception as e:
        print(f"Erreur lors de l'inscription: {e}")
        return jsonify({"error": "Erreur serveur lors de la création du compte."}), 500
    finally:
        conn.close()

# ===== CONNEXION (étape 1 : identifiants -> envoi OTP) =====
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis."}), 400

    rate_key = email.lower()
    if is_rate_limited(rate_key):
        return jsonify({"error": "Trop de tentatives. Réessayez dans quelques minutes."}), 429

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()

        # ✅ CORRECTION : Sélectionner nom ET prenom (pas name)
        cursor.execute(
            "SELECT id, nom, prenom, email, password, role FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()

        if not user:
            record_failed_attempt(rate_key)
            return jsonify({"error": "Email ou mot de passe incorrect."}), 401

        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            record_failed_attempt(rate_key)
            return jsonify({"error": "Email ou mot de passe incorrect."}), 401

        reset_attempts(rate_key)
        del user['password']

        # ===== Génère et envoie le code OTP =====
        code = generate_otp()
        OTP_STORE[user['id']] = {
            "code": code,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_VALIDITY_MINUTES)
        }

        try:
            send_otp_email(user['email'], code)
        except Exception as e:
            print(f"Erreur envoi email OTP: {e}")
            return jsonify({"error": "Impossible d'envoyer le code de vérification."}), 500

        return jsonify({"success": True, "user_id": user['id']})
    except Exception as e:
        print(f"Erreur lors de la connexion: {e}")
        return jsonify({"error": "Erreur serveur lors de la connexion."}), 500
    finally:
        conn.close()

# ===== VÉRIFICATION OTP (étape 2 : code -> token final) =====
@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    code = data.get('code', '').strip()

    if not user_id or not code:
        return jsonify({"error": "Champs manquants."}), 400

    entry = OTP_STORE.get(user_id)
    if not entry:
        return jsonify({"error": "Aucun code en attente. Reconnectez-vous."}), 400

    if datetime.now(timezone.utc) > entry["expires_at"]:
        del OTP_STORE[user_id]
        return jsonify({"error": "Code expiré. Reconnectez-vous."}), 400

    if code != entry["code"]:
        return jsonify({"error": "Code incorrect."}), 401

    del OTP_STORE[user_id]

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nom, prenom, email, role FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Utilisateur introuvable."}), 404

        response = create_token_response(user, cursor, conn)
        return jsonify(response)
    except Exception as e:
        print(f"Erreur lors de la vérification OTP: {e}")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== MIDDLEWARE =====
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
            cursor.execute(
                "SELECT revoked, expires_at FROM sessions WHERE jti = %s",
                (payload['jti'],)
            )
            session = cursor.fetchone()

            if not session:
                return jsonify({"error": "Session introuvable."}), 401
            if session['revoked']:
                return jsonify({"error": "Session révoquée."}), 401

            session_exp = session['expires_at']
            if isinstance(session_exp, datetime):
                if session_exp.tzinfo is None:
                    session_exp = session_exp.replace(tzinfo=timezone.utc)
                if session_exp < datetime.now(timezone.utc):
                    return jsonify({"error": "Session expirée."}), 401

        finally:
            conn.close()

        request.user = payload
        return f(*args, **kwargs)
    return decorated

# ===== DÉCONNEXION =====
@app.route('/api/logout', methods=['POST'])
@token_required
def logout():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET revoked = TRUE WHERE jti = %s",
            (request.user['jti'],)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Déconnexion réussie."})
    except Exception as e:
        print(f"Erreur lors de la déconnexion: {e}")
        return jsonify({"error": "Erreur serveur lors de la déconnexion."}), 500
    finally:
        conn.close()

# ===== ROUTE PROTÉGÉE =====
@app.route('/api/me', methods=['GET'])
@token_required
def me():
    return jsonify({"user": request.user})

# ===== DÉMARRAGE =====
if __name__ == '__main__':
    if not init_database():
        raise SystemExit(1)

    port = int(os.getenv('PORT', 3000))
    app.run(debug=True, port=port)
