import re
import logging
import secrets
import threading
import os
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from functools import wraps

from init_db import seed_admin, init_database
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import bcrypt
import jwt
from dotenv import load_dotenv
from db import get_connection
import smtplib
from email.mime.text import MIMEText
from pymysql.err import IntegrityError

load_dotenv()

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ===== CORS =====
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:4200", "http://127.0.0.1:4200"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

JWT_SECRET = os.getenv('JWT_SECRET')
if not JWT_SECRET:
    raise ValueError("JWT_SECRET est obligatoire dans les variables d'environnement")

SESSION_DURATION_DAYS = 2
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD')

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
NIVEAUX_VALIDES = ['Débutant', 'Intermédiaire', 'Avancé']

MAX_FIELD_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 5000

# ===== UPLOAD CONFIG =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, 'public')
UPLOAD_VIDEOS_DIR = os.path.join(UPLOAD_ROOT, 'videos')
UPLOAD_PDFS_DIR = os.path.join(UPLOAD_ROOT, 'pdfs')
os.makedirs(UPLOAD_VIDEOS_DIR, exist_ok=True)
os.makedirs(UPLOAD_PDFS_DIR, exist_ok=True)

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi', 'mkv'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 Mo
MAX_PDF_SIZE = 20 * 1024 * 1024     # 20 Mo


def allowed_extension(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


# ===== RATE LIMITING EN BASE =====
def is_rate_limited_db(cursor, key, max_attempts=5, window_sec=300):
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

def is_valid_email(email):
    return bool(EMAIL_REGEX.match(email)) if email else False

def is_valid_field_length(text, max_length=MAX_FIELD_LENGTH):
    return text is not None and len(text) <= max_length

def contains_suspicious_html(text):
    return bool(re.search(r'<[^>]*>', text)) if text else False

def generate_otp():
    return str(secrets.randbelow(900000) + 100000)

def send_otp_email(to_email, code):
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        logger.warning("Credentials email manquants, envoi OTP annulé")
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
    except Exception:
        logger.exception(f"Erreur envoi email à {to_email}")
        return False

def send_reset_password_email(to_email, reset_link):
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        logger.warning("Credentials email manquants, envoi de réinitialisation annulé")
        return False
    try:
        msg = MIMEText(
            f"Bonjour,\n\n"
            f"Vous avez demandé la réinitialisation de votre mot de passe pour votre compte LOGIQA.\n"
            f"Cliquez sur le lien ci-dessous pour créer un nouveau mot de passe :\n\n"
            f"{reset_link}\n\n"
            f"Ce lien expire dans 15 minutes.\n"
            f"Si vous n'êtes pas à l'origine de cette demande, ignorez cet e-mail."
        )
        msg['Subject'] = 'Réinitialisation de votre mot de passe - LOGIQA'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception(f"Erreur envoi email de réinitialisation à {to_email}")
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

    if not is_valid_email(email):
        return jsonify({"error": "Adresse email invalide."}), 400

    if not is_valid_password(password):
        return jsonify({"error": "Le mot de passe doit contenir au moins 8 caractères, une lettre et un chiffre."}), 400

    for field in [nom, prenom, telephone]:
        if field and not is_valid_field_length(field):
            return jsonify({"error": "Un des champs dépasse la longueur autorisée."}), 400

    for field in [nom, prenom, email, telephone]:
        if field and contains_suspicious_html(field):
            return jsonify({"error": "Caractères non autorisés détectés."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()

        if is_rate_limited_db(cursor, f"register:{email}", max_attempts=5, window_sec=600):
            return jsonify({"error": "Trop de tentatives. Réessayez plus tard."}), 429

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            record_attempt_db(cursor, conn, f"register:{email}")
            return jsonify({"error": "Un compte existe déjà avec cet email."}), 409

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (nom, prenom, email, password, telephone, role) VALUES (%s, %s, %s, %s, %s, %s)",
            (nom, prenom, email, hashed, telephone, role)
        )
        record_attempt_db(cursor, conn, f"register:{email}")
        conn.commit()
        return jsonify({"success": True, "message": "Compte créé avec succès."})
    except IntegrityError:
        return jsonify({"error": "Un compte existe déjà avec cet email."}), 409
    except Exception:
        logger.exception("Erreur inscription")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== CONNEXION ÉTAPE 1 =====
@app.route('/api/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"error": "Content-Type application/json requis."}), 400

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
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

        cursor.execute(
            "SELECT code, expires_at FROM otp_codes WHERE user_id = %s", (user['id'],)
        )
        existing = cursor.fetchone()
        if existing and datetime.now(timezone.utc) < existing['expires_at'].replace(tzinfo=timezone.utc):
            return jsonify({
                "success": True, "user_id": user['id'],
                "message": "Un code a déjà été envoyé. Vérifiez votre boîte mail."
            })

        code = generate_otp()
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)

        cursor.execute(
            """INSERT INTO otp_codes (user_id, code, expires_at, attempts)
               VALUES (%s, %s, %s, 0)
               ON DUPLICATE KEY UPDATE code=%s, expires_at=%s, attempts=0""",
            (user['id'], code, expires.replace(tzinfo=None), code, expires.replace(tzinfo=None))
        )
        conn.commit()

        def async_send():
            ok = send_otp_email(user['email'], code)
            if not ok:
                logger.warning(f"Échec envoi OTP à {user['email']}")

        threading.Thread(target=async_send, daemon=True).start()

        return jsonify({"success": True, "user_id": user['id']})

    except Exception:
        logger.exception("Erreur login")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== DEMANDE DE RÉINITIALISATION DE MOT DE PASSE =====
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    if not request.is_json:
        return jsonify({"error": "Content-Type application/json requis."}), 400

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email or not is_valid_email(email):
        return jsonify({"error": "Adresse email invalide."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()

        if is_rate_limited_db(cursor, f"forgot:{email}", max_attempts=3, window_sec=600):
            return jsonify({"error": "Trop de demandes. Réessayez dans 10 minutes."}), 429

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        record_attempt_db(cursor, conn, f"forgot:{email}")

        if user:
            raw_token = secrets.token_urlsafe(32)
            token_hash = hash_token(raw_token)  # ← on ne stocke jamais le token en clair
            expires = datetime.now(timezone.utc) + timedelta(minutes=15)

            cursor.execute(
                """INSERT INTO otp_codes (user_id, code, expires_at, attempts)
                   VALUES (%s, %s, %s, 0)
                   ON DUPLICATE KEY UPDATE code=%s, expires_at=%s, attempts=0""",
                (user['id'], token_hash, expires.replace(tzinfo=None), token_hash, expires.replace(tzinfo=None))
            )
            conn.commit()

            # Le lien envoyé par email contient le token EN CLAIR ; seule sa version hachée est en base.
            reset_url = f"http://localhost:4200/reset-password?token={raw_token}&user_id={user['id']}"

            threading.Thread(target=send_reset_password_email, args=(email, reset_url), daemon=True).start()

        return jsonify({"success": True, "message": "Si l'adresse existe, un lien de réinitialisation a été envoyé."})

    except Exception:
        logger.exception("Erreur forgot-password")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== VALIDATION ET MISE À JOUR DU MOT DE PASSE =====
@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    if not request.is_json:
        return jsonify({"error": "Content-Type application/json requis."}), 400

    data = request.get_json() or {}
    user_id = data.get('user_id')
    token = data.get('token', '').strip()
    new_password = data.get('password', '')

    if not user_id or not token or not new_password:
        return jsonify({"error": "Champs manquants."}), 400

    if not is_valid_password(new_password):
        return jsonify({"error": "Le mot de passe doit contenir au moins 8 caractères, une lettre et un chiffre."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT code, expires_at FROM otp_codes WHERE user_id = %s", (user_id,))
        entry = cursor.fetchone()

        # On compare le hash du token reçu au hash stocké, jamais le token en clair.
        if not entry or entry['code'] != hash_token(token):
            return jsonify({"error": "Lien invalide ou expiré."}), 400

        if datetime.now(timezone.utc) > entry['expires_at'].replace(tzinfo=timezone.utc):
            cursor.execute("DELETE FROM otp_codes WHERE user_id = %s", (user_id,))
            conn.commit()
            return jsonify({"error": "Le lien a expiré. Veuillez refaire une demande."}), 400

        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_pw, user_id))
        cursor.execute("DELETE FROM otp_codes WHERE user_id = %s", (user_id,))
        cursor.execute("UPDATE sessions SET revoked = TRUE WHERE user_id = %s", (user_id,))

        conn.commit()

        return jsonify({"success": True, "message": "Mot de passe modifié avec succès. Vous pouvez vous connecter."})

    except Exception:
        logger.exception("Erreur reset-password")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== RENVOYER OTP =====
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

        if is_rate_limited_db(cursor, f"resend:{email}", max_attempts=5, window_sec=600):
            return jsonify({"error": "Trop de tentatives. Réessayez plus tard."}), 429

        cursor.execute("SELECT id, email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user or user['email'] != email:
            record_attempt_db(cursor, conn, f"resend:{email}")
            return jsonify({"error": "Non autorisé."}), 403

        code = generate_otp()
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)

        cursor.execute(
            """INSERT INTO otp_codes (user_id, code, expires_at, attempts)
               VALUES (%s, %s, %s, 0)
               ON DUPLICATE KEY UPDATE code=%s, expires_at=%s, attempts=0""",
            (user_id, code, expires.replace(tzinfo=None), code, expires.replace(tzinfo=None))
        )
        record_attempt_db(cursor, conn, f"resend:{email}")
        conn.commit()

        threading.Thread(target=send_otp_email, args=(email, code), daemon=True).start()
        return jsonify({"success": True, "message": "Un nouveau code a été envoyé."})

    except Exception:
        logger.exception("Erreur resend")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== VÉRIFICATION OTP =====
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

        cursor.execute("DELETE FROM otp_codes WHERE user_id = %s", (user_id,))
        conn.commit()

        cursor.execute("SELECT id, nom, prenom, email, role FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Utilisateur introuvable."}), 404

        response = create_token_response(user, cursor, conn)
        return jsonify(response)

    except Exception:
        logger.exception("Erreur verify-otp")
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


def enseignant_required(f):
    """À utiliser APRÈS @token_required : vérifie que l'utilisateur a le rôle enseignant."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user.get('role') != 'enseignant':
            return jsonify({"error": "Action réservée aux enseignants."}), 403
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
    except Exception:
        logger.exception("Erreur logout")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

@app.route('/api/me', methods=['GET'])
@token_required
def me():
    return jsonify({"user": request.user})

# ===== COURS (CRUD) =====
@app.route('/api/cours', methods=['GET'])
def get_cours():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, titre, description, categorie, niveau, enseignant_id FROM cours")
        cours_list = cursor.fetchall()
        return jsonify(cours_list)
    except Exception:
        logger.exception("Erreur récupération cours")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

@app.route('/api/cours/<int:cours_id>', methods=['GET'])
def get_cours_by_id(cours_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, titre, description, categorie, niveau, enseignant_id FROM cours WHERE id = %s",
            (cours_id,)
        )
        cours = cursor.fetchone()
        if not cours:
            return jsonify({"error": "Cours introuvable."}), 404
        return jsonify(cours)
    except Exception:
        logger.exception("Erreur récupération cours")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

@app.route('/api/cours', methods=['POST'])
@token_required
@enseignant_required
def create_cours():
    data = request.get_json() or {}
    titre = data.get('titre', '').strip()
    description = data.get('description', '').strip()
    categorie = data.get('categorie', '').strip()
    niveau = data.get('niveau', 'Débutant').strip()

    if not titre or not description:
        return jsonify({"error": "Le titre et la description sont obligatoires."}), 400

    if not is_valid_field_length(titre) or not is_valid_field_length(description, MAX_DESCRIPTION_LENGTH):
        return jsonify({"error": "Le titre ou la description dépasse la longueur autorisée."}), 400

    if niveau not in NIVEAUX_VALIDES:
        return jsonify({"error": f"Niveau invalide. Valeurs acceptées : {', '.join(NIVEAUX_VALIDES)}."}), 400

    if contains_suspicious_html(titre) or contains_suspicious_html(description):
        return jsonify({"error": "Caractères non autorisés détectés."}), 400

    enseignant_id = request.user['id']

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO cours (titre, description, categorie, niveau, enseignant_id) VALUES (%s, %s, %s, %s, %s)",
            (titre, description, categorie, niveau, enseignant_id)
        )
        conn.commit()
        new_id = cursor.lastrowid

        return jsonify({
            "id": new_id, "titre": titre, "description": description,
            "categorie": categorie, "niveau": niveau, "enseignant_id": enseignant_id
        })
    except Exception:
        logger.exception("Erreur création cours")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

@app.route('/api/cours/<int:cours_id>', methods=['PUT'])
@token_required
@enseignant_required
def update_cours(cours_id):
    data = request.get_json() or {}
    titre = data.get('titre', '').strip()
    description = data.get('description', '').strip()
    categorie = data.get('categorie', '').strip()
    niveau = data.get('niveau', 'Débutant').strip()

    if not titre or not description:
        return jsonify({"error": "Le titre et la description sont obligatoires."}), 400

    if not is_valid_field_length(titre) or not is_valid_field_length(description, MAX_DESCRIPTION_LENGTH):
        return jsonify({"error": "Le titre ou la description dépasse la longueur autorisée."}), 400

    if niveau not in NIVEAUX_VALIDES:
        return jsonify({"error": f"Niveau invalide. Valeurs acceptées : {', '.join(NIVEAUX_VALIDES)}."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT enseignant_id FROM cours WHERE id = %s", (cours_id,))
        existing = cursor.fetchone()
        if not existing:
            return jsonify({"error": "Cours introuvable."}), 404

        if existing['enseignant_id'] != request.user['id']:
            return jsonify({"error": "Action non autorisée."}), 403

        cursor.execute(
            "UPDATE cours SET titre = %s, description = %s, categorie = %s, niveau = %s WHERE id = %s",
            (titre, description, categorie, niveau, cours_id)
        )
        conn.commit()

        return jsonify({
            "id": cours_id, "titre": titre, "description": description,
            "categorie": categorie, "niveau": niveau, "enseignant_id": existing['enseignant_id']
        })
    except Exception:
        logger.exception("Erreur modification cours")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

@app.route('/api/cours/<int:cours_id>', methods=['DELETE'])
@token_required
@enseignant_required
def delete_cours(cours_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT enseignant_id FROM cours WHERE id = %s", (cours_id,))
        existing = cursor.fetchone()
        if not existing:
            return jsonify({"error": "Cours introuvable."}), 404

        if existing['enseignant_id'] != request.user['id']:
            return jsonify({"error": "Action non autorisée."}), 403

        cursor.execute("DELETE FROM cours WHERE id = %s", (cours_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Cours supprimé."})
    except Exception:
        logger.exception("Erreur suppression cours")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

# ===== CHAPITRES : UPLOAD ET SUPPRESSION DE RESSOURCES =====
@app.route('/api/chapitres/<int:chapitre_id>/upload', methods=['POST'])
@token_required
@enseignant_required
def upload_ressource(chapitre_id):
    if 'fichier' not in request.files:
        return jsonify({"error": "Aucun fichier reçu."}), 400

    file = request.files['fichier']
    resource_type = request.form.get('type', '').strip()

    if resource_type not in ('video', 'pdf'):
        return jsonify({"error": "Type de ressource invalide."}), 400

    if file.filename == '':
        return jsonify({"error": "Nom de fichier vide."}), 400

    original_name = secure_filename(file.filename)

    if resource_type == 'pdf':
        if not allowed_extension(original_name, ALLOWED_PDF_EXTENSIONS):
            return jsonify({"error": "Le fichier doit être un PDF."}), 400
        target_dir = UPLOAD_PDFS_DIR
        max_size = MAX_PDF_SIZE
        max_label = '20 Mo'
    else:
        if not allowed_extension(original_name, ALLOWED_VIDEO_EXTENSIONS):
            return jsonify({"error": "Le fichier doit être une vidéo."}), 400
        target_dir = UPLOAD_VIDEOS_DIR
        max_size = MAX_VIDEO_SIZE
        max_label = '500 Mo'

    # Vérification de la taille réelle du fichier reçu
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > max_size:
        return jsonify({"error": f"Le fichier dépasse la limite de {max_label}."}), 400

    ext = original_name.rsplit('.', 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(target_dir, stored_name)

    try:
        file.save(file_path)
    except Exception:
        logger.exception("Erreur sauvegarde fichier")
        return jsonify({"error": "Erreur lors de l'enregistrement du fichier."}), 500

    conn = get_connection()
    if not conn:
        # Nettoyage du fichier orphelin si la BD est indisponible
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO chapitre_ressources
               (chapitre_id, type, nom_original, nom_fichier, enseignant_id)
               VALUES (%s, %s, %s, %s, %s)""",
            (chapitre_id, resource_type, original_name, stored_name, request.user['id'])
        )
        conn.commit()
        new_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "id": new_id,
            "type": resource_type,
            "nomOriginal": original_name,
            "url": f"/public/{resource_type}s/{stored_name}"
        })
    except Exception:
        logger.exception("Erreur insertion ressource")
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/chapitres/<int:chapitre_id>/resources', methods=['GET'])
@token_required
def list_ressources(chapitre_id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, type, nom_original, nom_fichier, created_at
               FROM chapitre_ressources
               WHERE chapitre_id = %s
               ORDER BY type, id ASC""",
            (chapitre_id,)
        )
        rows = cursor.fetchall()
        for r in rows:
            r['url'] = f"/public/{r['type']}s/{r['nom_fichier']}"
        return jsonify(rows)
    except Exception:
        logger.exception("Erreur récupération ressources")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/chapitres/<int:chapitre_id>/resources/<string:resource_type>/<int:index>', methods=['DELETE'])
@token_required
@enseignant_required
def delete_ressource(chapitre_id, resource_type, index):
    if resource_type not in ('video', 'pdf'):
        return jsonify({"error": "Type de ressource invalide."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, nom_fichier, enseignant_id FROM chapitre_ressources
               WHERE chapitre_id = %s AND type = %s
               ORDER BY id ASC""",
            (chapitre_id, resource_type)
        )
        rows = cursor.fetchall()

        if index < 0 or index >= len(rows):
            return jsonify({"error": "Ressource introuvable."}), 404

        resource = rows[index]

        if resource['enseignant_id'] != request.user['id']:
            return jsonify({"error": "Action non autorisée."}), 403

        cursor.execute("DELETE FROM chapitre_ressources WHERE id = %s", (resource['id'],))
        conn.commit()

        target_dir = UPLOAD_PDFS_DIR if resource_type == 'pdf' else UPLOAD_VIDEOS_DIR
        file_path = os.path.join(target_dir, resource['nom_fichier'])
        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({"success": True, "message": "Fichier supprimé."})
    except Exception:
        logger.exception("Erreur suppression ressource")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/public/<string:resource_type>/<path:filename>', methods=['GET'])
def serve_uploaded_file(resource_type, filename):
    if resource_type == 'pdfs':
        directory = UPLOAD_PDFS_DIR
    elif resource_type == 'videos':
        directory = UPLOAD_VIDEOS_DIR
    else:
        return jsonify({"error": "Type de ressource invalide."}), 404
    return send_from_directory(directory, filename)


# ===== PURGE PÉRIODIQUE =====
def purge_expired_sessions():
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE expires_at < NOW()")
            conn.commit()
        finally:
            conn.close()

def purge_old_security_records():
    """Nettoie les OTP/tokens expirés et les tentatives de connexion anciennes."""
    conn = get_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM otp_codes WHERE expires_at < NOW()")
        cursor.execute("DELETE FROM login_attempts WHERE attempted_at < NOW() - INTERVAL 1 DAY")
        conn.commit()
    except Exception:
        logger.exception("Erreur purge sécurité")
    finally:
        conn.close()

# ===== DÉMARRAGE =====
if __name__ == '__main__':
    if not init_database():
        raise SystemExit(1)

    purge_expired_sessions()
    purge_old_security_records()

    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', debug=False, port=port)