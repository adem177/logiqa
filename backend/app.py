import re
import logging
import secrets
import threading
import os
import uuid
import hashlib
import mimetypes
import tempfile
from datetime import datetime, timedelta, timezone
from functools import wraps

from init_db import seed_admin, init_database
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import safe_join, secure_filename
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

SESSION_DURATION_DAYS = 365  # Token valable 1 an
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

# Chemin vers les PDFs statiques du frontend (pour la génération de quiz)
FRONTEND_PDFS_DIR = os.path.join(BASE_DIR, '..', 'frontend', 'public', 'pdfs')
FRONTEND_VIDEOS_DIR = os.path.join(BASE_DIR, '..', 'frontend', 'public', 'videos')

# Mapping chapitre_id -> (course_slug, numero de chapitre)
# Les slugs doivent correspondre aux dossiers de frontend/public/pdfs et /videos.
CHAPTER_MAP = {
    1: ('langage-c', 1), 2: ('langage-c', 2), 3: ('langage-c', 3),
    4: ('langage-c', 4), 5: ('langage-c', 5), 6: ('langage-c', 6),
    7: ('algebre', 1), 8: ('algebre', 2), 9: ('algebre', 3),
    10: ('algebre', 4), 11: ('algebre', 5), 12: ('algebre', 6),
    13: ('analyse', 1), 14: ('analyse', 2), 15: ('analyse', 3),
    16: ('analyse', 4), 17: ('analyse', 5), 18: ('analyse', 6),
    19: ('systemes-logiques', 1), 20: ('systemes-logiques', 2),
    21: ('systemes-logiques', 3), 22: ('systemes-logiques', 4),
    23: ('systemes-logiques', 5), 24: ('systemes-logiques', 6),
    25: ('algorithmes', 1), 26: ('algorithmes', 2), 27: ('algorithmes', 3),
    28: ('algorithmes', 4), 29: ('algorithmes', 5), 30: ('algorithmes', 6),
    31: ('base-de-donnees', 1), 32: ('base-de-donnees', 2), 33: ('base-de-donnees', 3),
    34: ('base-de-donnees', 4), 35: ('base-de-donnees', 5), 36: ('base-de-donnees', 6),
    37: ('reseaux', 1), 38: ('reseaux', 2), 39: ('reseaux', 3),
    40: ('reseaux', 4), 41: ('reseaux', 5), 42: ('reseaux', 6),
    43: ('systeme-exploitation', 1), 44: ('systeme-exploitation', 2),
    45: ('systeme-exploitation', 3), 46: ('systeme-exploitation', 4),
    47: ('systeme-exploitation', 5), 48: ('systeme-exploitation', 6),
}

VIDEO_EXTENSIONS = ('.mp4', '.webm', '.mov', '.avi', '.mkv')


def _resolve_static_sources(chapitre_id):
    """PDFs et vidéos statiques de frontend/public pour un chapitre.

    Returns:
        (pdf_files, video_files) — listes vides si le chapitre n'est pas
        référencé dans CHAPTER_MAP ou si les dossiers n'existent pas.
    """
    if chapitre_id not in CHAPTER_MAP:
        return [], []

    course_slug, chap_num = CHAPTER_MAP[chapitre_id]
    pdf_files, video_files = [], []

    static_pdf_dir = os.path.join(FRONTEND_PDFS_DIR, course_slug, f'chapitre{chap_num}')
    if os.path.isdir(static_pdf_dir):
        pdf_files = [
            os.path.join(static_pdf_dir, f)
            for f in sorted(os.listdir(static_pdf_dir))
            if f.lower().endswith('.pdf')
        ]

    static_video_dir = os.path.join(FRONTEND_VIDEOS_DIR, course_slug, f'chapitre{chap_num}')
    if os.path.isdir(static_video_dir):
        video_files = [
            os.path.join(static_video_dir, f)
            for f in sorted(os.listdir(static_video_dir))
            if f.lower().endswith(VIDEO_EXTENSIONS)
        ]

    return pdf_files, video_files


def _merge_sources(static_pdfs, static_videos, ressources):
    """Fusionne les ressources statiques (frontend/public) et celles de la BDD.

    Les statiques passent en premier : le texte est tronqué à 8000 caractères
    en aval, on veut donc que le support de cours fasse autorité sur
    d'éventuels uploads erronés. Les doublons sont éliminés par chemin résolu.

    Returns:
        (pdf_files, video_files, temp_files) — temp_files à nettoyer en fin
        de requête (fichiers materialisés depuis des BLOB).
    """
    db_pdfs, db_videos, temp_files = _resolve_chapter_sources(ressources)

    def _dedupe(*groups):
        seen, out = set(), []
        for group in groups:
            for path in group:
                key = os.path.normcase(os.path.abspath(path))
                if key not in seen:
                    seen.add(key)
                    out.append(path)
        return out

    return _dedupe(static_pdfs, db_pdfs), _dedupe(static_videos, db_videos), temp_files

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

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=5) as server:
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email de réinitialisation envoyé à {to_email}")
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
    expires_naive = expires_at.replace(tzinfo=None).replace(microsecond=0)

    cursor.execute(
        "INSERT INTO sessions (user_id, jti, token_hash, expires_at) VALUES (%s, %s, %s, %s)",
        (user['id'], jti, token_hash, expires_naive)
    )
    cursor.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user['id'],))
    conn.commit()

    return {"success": True, "user": user, "token": token, "expires_at": expires_at.isoformat()}

# ===== ROUTES =====

# En production, Flask sert lui-même le bundle construit par `ng build`
# (frontend/dist/logiqa/browser) : une seule origine, donc aucune requête
# CORS et une seule URL à partager. En développement (`ng serve` sur le port
# 4200) ce dossier n'existe pas : on garde alors l'ancienne réponse JSON.
BROWSER_DIST = os.path.join(BASE_DIR, '..', 'frontend', 'dist', 'logiqa', 'browser')

# Sur Windows, le registre déclare .js en « text/plain » : le navigateur
# refuse alors d'exécuter un module ES (contrôle MIME strict) et la page
# reste blanche. On force le type correct, inoffensif sous Linux.
mimetypes.add_type('text/javascript', '.js')
mimetypes.add_type('text/javascript', '.mjs')


def _front_index():
    """Nom du shell Angular à servir.

    `index.html` quand le prerender a écrit la page, `index.csr.html` pour le
    rendu 100 % client (c'est ce que produit la configuration actuelle du
    projet, qui garde le SSR activé). Retourne None si rien n'est construit.
    """
    for nom in ('index.html', 'index.csr.html'):
        if os.path.isfile(os.path.join(BROWSER_DIST, nom)):
            return nom
    return None


@app.route('/')
def home():
    index = _front_index()
    if index:
        return send_from_directory(BROWSER_DIST, index)
    return jsonify({"message": "API LOGIQA fonctionne !"})


@app.route('/<path:chemin>')
def front(chemin):
    """Fichiers du bundle Angular, puis repli sur le shell (routage SPA).

    Les routes d'API ne sont pas concernées : elles sont déclarées ci-dessus
    et Werkzeug les priorise, mais on les exclut aussi par sécurité pour
    qu'une faute de frappe ne renvoie jamais une page HTML à un appel XHR.
    """
    if chemin.startswith(('api/', 'public/')):
        return jsonify({"error": "Ressource introuvable."}), 404

    index = _front_index()
    if index:
        cible = safe_join(BROWSER_DIST, chemin)
        if cible and os.path.isfile(cible):
            return send_from_directory(BROWSER_DIST, chemin)
        # URL de page (ex. /login, /quiz/3) : on laisse Angular router.
        return send_from_directory(BROWSER_DIST, index)

    return jsonify({"error": "Frontend non construit (ng build)."}), 404

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
    role = role_input if role_input in ['etudiant', 'enseignant', 'admin'] else 'etudiant'

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
            "SELECT id, nom, prenom, email, password, role, status FROM users WHERE email = %s", (email,)
        )
        user = cursor.fetchone()

        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            record_attempt_db(cursor, conn, rate_key)
            return jsonify({"error": "Email ou mot de passe incorrect."}), 401

        if not user['status']:
            return jsonify({"error": "Votre compte a été désactivé. Contactez l'administrateur."}), 403

        del user['password']

        # Les administrateurs se connectent directement :
        # aucun code OTP par e-mail, le token est délivré immédiatement.
        if user['role'] == 'admin':
            del user['status']
            return jsonify(create_token_response(user, cursor, conn))

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
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)

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

        cursor.execute("SELECT id, nom, prenom, email, role, status FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Utilisateur introuvable."}), 404
        if not user['status']:
            return jsonify({"error": "Votre compte a été désactivé."}), 403
        del user['status']

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

            # Vérifier que le compte existe toujours et est actif,
            # et recharger le rôle depuis la base (le JWT peut être périmé).
            cursor.execute("SELECT id, status, role FROM users WHERE id = %s", (payload['id'],))
            db_user = cursor.fetchone()
            if not db_user:
                return jsonify({"error": "Compte introuvable."}), 401
            if not db_user['status']:
                return jsonify({"error": "Compte désactivé."}), 403
            payload['role'] = db_user['role']

        finally:
            conn.close()

        request.user = payload
        return f(*args, **kwargs)
    return decorated


def enseignant_required(f):
    """À utiliser APRÈS @token_required : vérifie que l'utilisateur a le rôle enseignant ou admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user.get('role') not in ('enseignant', 'admin'):
            return jsonify({"error": "Action réservée aux enseignants."}), 403
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """À utiliser APRÈS @token_required : vérifie que l'utilisateur a le rôle admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user.get('role') != 'admin':
            return jsonify({"error": "Action réservée aux administrateurs."}), 403
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
        cursor.execute(
            """SELECT c.id, c.titre, c.description, c.categorie, c.niveau, c.enseignant_id,
                      (SELECT COUNT(*) FROM chapitres ch WHERE ch.cours_id = c.id) as nb_chapitres
               FROM cours c"""
        )
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

        cursor.execute("DELETE FROM cours WHERE id = %s", (cours_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Cours supprimé."})
    except Exception:
        logger.exception("Erreur suppression cours")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()

@app.route('/api/enseignant/cours', methods=['GET'])
@token_required
@enseignant_required
def enseignant_mes_cours():
    """Retourne tous les cours de la plateforme (visibles et gérables par l'enseignant)."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT c.id, c.titre, c.description, c.categorie, c.niveau, c.enseignant_id,
                      (SELECT COUNT(*) FROM chapitres ch WHERE ch.cours_id = c.id) as nb_chapitres
               FROM cours c
               ORDER BY c.id DESC"""
        )
        cours_list = cursor.fetchall()
        return jsonify(cours_list)
    except Exception:
        logger.exception("Erreur récupération cours enseignant")
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
        max_size = MAX_PDF_SIZE
        max_label = '20 Mo'
    else:
        if not allowed_extension(original_name, ALLOWED_VIDEO_EXTENSIONS):
            return jsonify({"error": "Le fichier doit être une vidéo."}), 400
        max_size = MAX_VIDEO_SIZE
        max_label = '500 Mo'

    # Lire le contenu du fichier en binaire
    file_content = file.read()
    file_size = len(file_content)

    if file_size > max_size:
        return jsonify({"error": f"Le fichier dépasse la limite de {max_label}."}), 400

    ext = original_name.rsplit('.', 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()

        if resource_type == 'pdf':
            # PDF → stocker en BLOB dans la base
            cursor.execute(
                """INSERT INTO chapitre_ressources
                   (chapitre_id, type, nom_original, contenu, taille, mime_type, enseignant_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (chapitre_id, resource_type, original_name, file_content,
                 file_size, 'application/pdf', request.user['id'])
            )
            url = f"/api/ressources/{cursor.lastrowid}/download"
        else:
            # Vidéo → stocker sur disque
            file_path = os.path.join(UPLOAD_VIDEOS_DIR, stored_name)
            with open(file_path, 'wb') as f:
                f.write(file_content)

            cursor.execute(
                """INSERT INTO chapitre_ressources
                   (chapitre_id, type, nom_original, nom_fichier, taille, mime_type, enseignant_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (chapitre_id, resource_type, original_name, stored_name,
                 file_size, file.content_type or 'video/mp4', request.user['id'])
            )
            url = f"/public/videos/{stored_name}"

        conn.commit()
        new_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "id": new_id,
            "type": resource_type,
            "nomOriginal": original_name,
            "url": url
        })
    except Exception:
        logger.exception("Erreur insertion ressource")
        # Nettoyage du fichier orphelin si la BD est indisponible
        if resource_type == 'video':
            file_path = os.path.join(UPLOAD_VIDEOS_DIR, stored_name)
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


@app.route('/api/ressources/<int:resource_id>/download', methods=['GET'])
def download_ressource(resource_id):
    """Télécharge un PDF stocké en BLOB dans la base."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT nom_original, contenu, mime_type, taille
               FROM chapitre_ressources WHERE id = %s AND type = 'pdf'""",
            (resource_id,)
        )
        resource = cursor.fetchone()

        if not resource or not resource['contenu']:
            return jsonify({"error": "Ressource introuvable."}), 404

        from flask import Response
        return Response(
            resource['contenu'],
            mimetype=resource['mime_type'] or 'application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{resource["nom_original"]}"',
                'Content-Length': resource['taille']
            }
        )
    except Exception:
        logger.exception("Erreur téléchargement ressource")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/public/<string:resource_type>/<path:filename>', methods=['GET'])
def serve_uploaded_file(resource_type, filename):
    if resource_type == 'videos':
        directory = UPLOAD_VIDEOS_DIR
    else:
        return jsonify({"error": "Type de ressource invalide."}), 404
    return send_from_directory(directory, filename)


# ===== QUIZ : GÉNÉRATION ET PASSAGE =====
from quiz_generator import generate_quiz_from_chapter, GROQ_API_KEY, GROQ_MODEL


def _resolve_chapter_sources(ressources):
    """Convertit les ressources d'un chapitre en chemins exploitables.

    Les PDF sont stockés en BLOB dans la colonne `contenu` (nom_fichier reste
    NULL), tandis que les vidéos vivent sur disque (nom_fichier renseigné).
    On materialise donc les BLOB dans des fichiers temporaires, et on ignore
    les lignes sans chemin pour éviter un os.path.join(None).

    Returns:
        (pdf_files, video_files, temp_files) — l'appelant doit supprimer
        les fichiers de `temp_files` une fois la génération terminée.
    """
    pdf_files, video_files, temp_files = [], [], []

    for r in ressources:
        if r['type'] == 'pdf':
            if r.get('nom_fichier'):
                pdf_files.append(os.path.join(UPLOAD_PDFS_DIR, r['nom_fichier']))
            elif r.get('contenu'):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                try:
                    tmp.write(r['contenu'])
                finally:
                    tmp.close()
                pdf_files.append(tmp.name)
                temp_files.append(tmp.name)
        elif r.get('nom_fichier'):
            video_files.append(os.path.join(UPLOAD_VIDEOS_DIR, r['nom_fichier']))

    return pdf_files, video_files, temp_files


def _cleanup_temp_files(temp_files):
    """Supprime les fichiers temporaires materialisés depuis les BLOB."""
    for path in temp_files or []:
        try:
            os.unlink(path)
        except OSError:
            logger.warning(f"Impossible de supprimer le fichier temporaire {path}")


@app.route('/api/test-groq', methods=['GET'])
def test_groq():
    """Teste la connexion à Groq."""
    if not GROQ_API_KEY:
        return jsonify({"error": "GROQ_API_KEY non définie"}), 400

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": "Dis bonjour en français"}],
            max_tokens=50
        )
        return jsonify({
            "success": True,
            "message": response.choices[0].message.content,
            "model": GROQ_MODEL
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chapitres/<int:chapitre_id>/quiz/generer', methods=['POST'])
@token_required
@enseignant_required
def generer_quiz(chapitre_id):
    """Génère un quiz QCM à partir des PDF et vidéos d'un chapitre."""
    data = request.get_json() or {}
    nombre_questions = data.get('nombre_questions', 10)
    methode = data.get('methode', 'auto')  # 'auto', 'openai' ou 'groq'

    if methode not in ('auto', 'openai', 'groq'):
        return jsonify({"error": "Méthode invalide. Utilisez 'auto', 'openai' ou 'groq'."}), 400

    if not isinstance(nombre_questions, int) or nombre_questions < 1 or nombre_questions > 50:
        return jsonify({"error": "Le nombre de questions doit être entre 1 et 50."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    temp_files = []  # PDF materialisés depuis des BLOB, à nettoyer en fin de requête

    try:
        cursor = conn.cursor()

        # Vérifier que le chapitre existe
        cursor.execute("SELECT id, titre FROM chapitres WHERE id = %s", (chapitre_id,))
        chapitre = cursor.fetchone()
        if not chapitre:
            return jsonify({"error": "Chapitre introuvable."}), 404

        # Récupérer les ressources du chapitre
        cursor.execute(
            "SELECT type, nom_fichier, contenu FROM chapitre_ressources WHERE chapitre_id = %s",
            (chapitre_id,)
        )
        ressources = cursor.fetchall()

        # Fusion : PDFs/vidéos statiques (frontend/public) + ressources uploadées (BDD)
        static_pdfs, static_videos = _resolve_static_sources(chapitre_id)
        pdf_files, video_files, temp_files = _merge_sources(static_pdfs, static_videos, ressources)

        logger.info(
            f"Sources chapitre {chapitre_id}: "
            f"{len(static_pdfs)} PDF statiques, {len(static_videos)} vidéos statiques, "
            f"{len(pdf_files)} PDF au total, {len(video_files)} vidéos au total"
        )

        # Générer les questions
        questions = generate_quiz_from_chapter(
            pdf_files, video_files, nombre_questions, methode,
            chapter_title=chapitre['titre']
        )

        if not questions:
            return jsonify({"error": "Impossible de générer des questions à partir des ressources."}), 400

        # Créer le quiz en base
        cursor.execute(
            """INSERT INTO quiz (chapitre_id, titre, description, nombre_questions, methode_generation, created_by)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (chapitre_id, f"Quiz - {chapitre['titre']}", f"Généré automatiquement ({methode})",
             len(questions), methode, request.user['id'])
        )
        quiz_id = cursor.lastrowid

        # Insérer les questions et options
        for ordre, q in enumerate(questions, 1):
            cursor.execute(
                "INSERT INTO quiz_questions (quiz_id, texte, ordre) VALUES (%s, %s, %s)",
                (quiz_id, q['texte'], ordre)
            )
            question_id = cursor.lastrowid

            for opt in q['options']:
                cursor.execute(
                    "INSERT INTO quiz_options (question_id, texte, est_correcte) VALUES (%s, %s, %s)",
                    (question_id, opt['texte'], opt['est_correcte'])
                )

        conn.commit()

        return jsonify({
            "success": True,
            "quiz_id": quiz_id,
            "titre": f"Quiz - {chapitre['titre']}",
            "nombre_questions": len(questions),
            "methode": methode
        })

    except Exception:
        logger.exception("Erreur génération quiz")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        _cleanup_temp_files(temp_files)
        conn.close()


@app.route('/api/chapitres/<int:chapitre_id>/quiz', methods=['GET'])
@token_required
def lister_quiz(chapitre_id):
    """Liste les quiz d'un chapitre."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT q.id, q.titre, q.description, q.nombre_questions, q.methode_generation,
                      q.created_at, u.nom as createur_nom, u.prenom as createur_prenom,
                      u.role as createur_role
               FROM quiz q
               LEFT JOIN users u ON u.id = q.created_by
               WHERE q.chapitre_id = %s ORDER BY q.created_at DESC""",
            (chapitre_id,)
        )
        quiz_list = cursor.fetchall()
        return jsonify(quiz_list)
    except Exception:
        logger.exception("Erreur liste quiz")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/quiz/<int:quiz_id>', methods=['GET'])
@token_required
def get_quiz(quiz_id):
    """Récupère un quiz avec ses questions et options (sans révéler les bonnes réponses)."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, titre, description, nombre_questions, methode_generation FROM quiz WHERE id = %s",
            (quiz_id,)
        )
        quiz = cursor.fetchone()
        if not quiz:
            return jsonify({"error": "Quiz introuvable."}), 404

        cursor.execute(
            "SELECT id, texte, ordre FROM quiz_questions WHERE quiz_id = %s ORDER BY ordre",
            (quiz_id,)
        )
        questions = cursor.fetchall()

        for q in questions:
            cursor.execute(
                "SELECT id, texte FROM quiz_options WHERE question_id = %s ORDER BY id",
                (q['id'],)
            )
            q['options'] = cursor.fetchall()

        quiz['questions'] = questions
        return jsonify(quiz)
    except Exception:
        logger.exception("Erreur récupération quiz")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/quiz/<int:quiz_id>/regenerer', methods=['POST'])
@token_required
def regenerer_quiz(quiz_id):
    """Régénère un nouveau quiz pour le même chapitre."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    temp_files = []  # PDF materialisés depuis des BLOB, à nettoyer en fin de requête

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT chapitre_id, nombre_questions, methode_generation FROM quiz WHERE id = %s", (quiz_id,))
        quiz = cursor.fetchone()
        if not quiz:
            return jsonify({"error": "Quiz introuvable."}), 404

        chapitre_id = quiz['chapitre_id']
        cursor.execute("SELECT id, titre FROM chapitres WHERE id = %s", (chapitre_id,))
        chapitre = cursor.fetchone()
        if not chapitre:
            return jsonify({"error": "Chapitre introuvable."}), 404

        # Récupérer les ressources
        cursor.execute("SELECT type, nom_fichier, contenu FROM chapitre_ressources WHERE chapitre_id = %s", (chapitre_id,))
        ressources = cursor.fetchall()

        # Fusion : PDFs/vidéos statiques (frontend/public) + ressources uploadées (BDD)
        static_pdfs, static_videos = _resolve_static_sources(chapitre_id)
        pdf_files, video_files, temp_files = _merge_sources(static_pdfs, static_videos, ressources)

        # Générer les nouvelles questions
        questions = generate_quiz_from_chapter(
            pdf_files, video_files, quiz['nombre_questions'], quiz['methode_generation'],
            chapter_title=chapitre['titre']
        )

        if not questions:
            return jsonify({"error": "Impossible de générer un nouveau quiz."}), 400

        # Créer le nouveau quiz
        cursor.execute(
            """INSERT INTO quiz (chapitre_id, titre, description, nombre_questions, methode_generation, created_by)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (chapitre_id, f"Quiz - {chapitre['titre']}", f"Nouveau quiz généré",
             len(questions), quiz['methode_generation'], request.user['id'])
        )
        new_quiz_id = cursor.lastrowid

        for ordre, q in enumerate(questions, 1):
            cursor.execute(
                "INSERT INTO quiz_questions (quiz_id, texte, ordre) VALUES (%s, %s, %s)",
                (new_quiz_id, q['texte'], ordre)
            )
            question_id = cursor.lastrowid
            for opt in q['options']:
                cursor.execute(
                    "INSERT INTO quiz_options (question_id, texte, est_correcte) VALUES (%s, %s, %s)",
                    (question_id, opt['texte'], opt['est_correcte'])
                )

        conn.commit()

        return jsonify({
            "success": True,
            "new_quiz_id": new_quiz_id,
            "message": "Nouveau quiz généré avec succès !"
        })

    except Exception:
        logger.exception("Erreur régénération quiz")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        _cleanup_temp_files(temp_files)
        conn.close()


@app.route('/api/quiz/<int:quiz_id>/soumettre', methods=['POST'])
@token_required
def soumettre_quiz(quiz_id):
    """Soumet les réponses d'un étudiant et calcule le score.
    Régénère automatiquement le quiz si l'étudiant l'a fait 3+ fois."""
    data = request.get_json() or {}
    reponses = data.get('reponses', [])  # Liste de {question_id, option_id}

    if not reponses:
        return jsonify({"error": "Aucune réponse provided."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    temp_files = []  # PDF materialisés depuis des BLOB, à nettoyer en fin de requête

    try:
        cursor = conn.cursor()

        # Vérifier que le quiz existe
        cursor.execute("SELECT id, nombre_questions, chapitre_id, methode_generation, created_at FROM quiz WHERE id = %s", (quiz_id,))
        quiz = cursor.fetchone()
        if not quiz:
            return jsonify({"error": "Quiz introuvable."}), 404

        # Vérifier si le quiz doit être régénéré AVANT d'enregistrer la tentative
        should_regenerate = False
        reason = ""

        # Condition 1 : Quiz de plus de 3 jours
        if quiz['created_at']:
            age_days = (datetime.now() - quiz['created_at']).days
            if age_days > 3:
                should_regenerate = True
                reason = f"Quiz ancien ({age_days} jours)"

        # Régénérer le quiz si nécessaire
        if should_regenerate:
            logger.info(f"Régénération du quiz {quiz_id}: {reason}")
            
            # Supprimer l'ancien quiz
            cursor.execute("DELETE FROM quiz_answers WHERE attempt_id IN (SELECT id FROM quiz_attempts WHERE quiz_id = %s)", (quiz_id,))
            cursor.execute("DELETE FROM quiz_attempts WHERE quiz_id = %s", (quiz_id,))
            cursor.execute("DELETE FROM quiz_options WHERE question_id IN (SELECT id FROM quiz_questions WHERE quiz_id = %s)", (quiz_id,))
            cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", (quiz_id,))
            cursor.execute("DELETE FROM quiz WHERE id = %s", (quiz_id,))
            conn.commit()
            
            # Message d'expiration
            if "ancien" in reason:
                return jsonify({"error": f"Le quiz a expiré car il a plus de 3 jours. Veuillez générer un nouveau quiz."}), 410

            # Générer un nouveau quiz
            chapitre_id = quiz['chapitre_id']
            cursor.execute("SELECT id, titre FROM chapitres WHERE id = %s", (chapitre_id,))
            chapitre = cursor.fetchone()
            if not chapitre:
                return jsonify({"error": "Chapitre introuvable."}), 404

            # Récupérer les ressources (contenu = BLOB pour les PDF uploadés)
            cursor.execute(
                "SELECT type, nom_fichier, contenu FROM chapitre_ressources WHERE chapitre_id = %s",
                (chapitre_id,)
            )
            ressources = cursor.fetchall()

            # Fusion : PDFs/vidéos statiques (frontend/public) + ressources uploadées (BDD)
            static_pdfs, static_videos = _resolve_static_sources(chapitre_id)
            pdf_files, video_files, temp_files = _merge_sources(static_pdfs, static_videos, ressources)

            # Générer les nouvelles questions
            questions = generate_quiz_from_chapter(
                pdf_files, video_files, quiz['nombre_questions'], quiz['methode_generation'],
                chapter_title=chapitre['titre']
            )

            if not questions:
                return jsonify({"error": "Impossible de régénérer le quiz."}), 400

            # Créer le nouveau quiz
            cursor.execute(
                """INSERT INTO quiz (chapitre_id, titre, description, nombre_questions, methode_generation, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (chapitre_id, f"Quiz - {chapitre['titre']}", f"Régénéré automatiquement",
                 len(questions), quiz['methode_generation'], request.user['id'])
            )
            new_quiz_id = cursor.lastrowid

            for ordre, q in enumerate(questions, 1):
                cursor.execute(
                    "INSERT INTO quiz_questions (quiz_id, texte, ordre) VALUES (%s, %s, %s)",
                    (new_quiz_id, q['texte'], ordre)
                )
                question_id = cursor.lastrowid
                for opt in q['options']:
                    cursor.execute(
                        "INSERT INTO quiz_options (question_id, texte, est_correcte) VALUES (%s, %s, %s)",
                        (question_id, opt['texte'], opt['est_correcte'])
                    )

            conn.commit()
            
            # Mettre à jour le quiz_id pour utiliser le nouveau quiz
            quiz_id = new_quiz_id
            
            # Récupérer les infos du nouveau quiz
            cursor.execute("SELECT id, nombre_questions FROM quiz WHERE id = %s", (quiz_id,))
            quiz = cursor.fetchone()

        # Récupérer les bonnes réponses
        cursor.execute(
            """SELECT q.id as question_id, o.id as option_id
               FROM quiz_questions q
               JOIN quiz_options o ON o.question_id = q.id
               WHERE q.quiz_id = %s AND o.est_correcte = TRUE""",
            (quiz_id,)
        )
        bonnes_reponses = {row['question_id']: row['option_id'] for row in cursor.fetchall()}

        # Calculer le score
        score = 0
        for rep in reponses:
            q_id = rep.get('question_id')
            o_id = rep.get('option_id')
            if q_id in bonnes_reponses and bonnes_reponses[q_id] == o_id:
                score += 1

        total = quiz['nombre_questions']

        # Enregistrer la tentative
        cursor.execute(
            """INSERT INTO quiz_attempts (quiz_id, user_id, score, total_questions)
               VALUES (%s, %s, %s, %s)""",
            (quiz_id, request.user['id'], score, total)
        )
        attempt_id = cursor.lastrowid

        # Enregistrer les réponses
        for rep in reponses:
            cursor.execute(
                """INSERT INTO quiz_answers (attempt_id, question_id, option_id)
                   VALUES (%s, %s, %s)""",
                (attempt_id, rep.get('question_id'), rep.get('option_id'))
            )

        conn.commit()

        # Récupérer les détails de la correction
        cursor.execute(
            """SELECT q.id as question_id, q.texte as question_texte,
                      o.id as option_id, o.texte as option_texte, o.est_correcte
               FROM quiz_questions q
               JOIN quiz_options o ON o.question_id = q.id
               WHERE q.quiz_id = %s
               ORDER BY q.ordre, o.id""",
            (quiz_id,)
        )
        all_options = cursor.fetchall()

        # Construire la correction détaillée
        correction = {}
        for row in all_options:
            q_id = row['question_id']
            if q_id not in correction:
                correction[q_id] = {
                    'question_texte': row['question_texte'],
                    'options': [],
                    'reponse_correcte': None,
                    'reponse_etudiant': None
                }
            correction[q_id]['options'].append({
                'option_id': row['option_id'],
                'option_texte': row['option_texte'],
                'est_correcte': bool(row['est_correcte'])
            })
            if row['est_correcte']:
                correction[q_id]['reponse_correcte'] = row['option_texte']

        # Ajouter la réponse de l'étudiant
        for rep in reponses:
            q_id = rep.get('question_id')
            o_id = rep.get('option_id')
            if q_id in correction:
                correction[q_id]['reponse_etudiant'] = o_id

        return jsonify({
            "success": True,
            "score": score,
            "total": total,
            "pourcentage": round((score / total) * 100, 1) if total > 0 else 0,
            "correction": correction
        })

    except Exception:
        logger.exception("Erreur soumission quiz")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        _cleanup_temp_files(temp_files)
        conn.close()


@app.route('/api/quiz/<int:quiz_id>/resultat', methods=['GET'])
@token_required
def resultat_quiz(quiz_id):
    """Récupère le dernier résultat d'un étudiant pour un quiz."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, score, total_questions, completed_at
               FROM quiz_attempts
               WHERE quiz_id = %s AND user_id = %s
               ORDER BY completed_at DESC LIMIT 1""",
            (quiz_id, request.user['id'])
        )
        resultat = cursor.fetchone()
        if not resultat:
            return jsonify({"error": "Aucune tentative trouvée."}), 404

        return jsonify({
            "score": resultat['score'],
            "total": resultat['total_questions'],
            "pourcentage": round((resultat['score'] / resultat['total_questions']) * 100, 1)
            if resultat['total_questions'] > 0 else 0,
            "completed_at": resultat['completed_at'].isoformat() if resultat['completed_at'] else None
        })
    except Exception:
        logger.exception("Erreur résultat quiz")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


# ===== ADMIN — STATISTIQUES =====
@app.route('/api/admin/stats', methods=['GET'])
@token_required
@admin_required
def admin_stats():
    """Retourne les statistiques globales pour le tableau de bord admin."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        stats = {}

        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        stats['total_users'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'etudiant'")
        stats['total_etudiants'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'enseignant'")
        stats['total_enseignants'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin'")
        stats['total_admins'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM cours")
        stats['total_cours'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM chapitres")
        stats['total_chapitres'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM chapitre_ressources")
        stats['total_ressources'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM quiz")
        stats['total_quiz'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) as cnt FROM quiz_attempts")
        stats['total_attempts'] = cursor.fetchone()['cnt']

        cursor.execute("SELECT COALESCE(AVG(score * 100.0 / NULLIF(total_questions, 0)), 0) as avg FROM quiz_attempts")
        stats['avg_score'] = round(cursor.fetchone()['avg'], 1)

        return jsonify(stats)
    except Exception:
        logger.exception("Erreur stats admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


# ===== ADMIN — UTILISATEURS =====
@app.route('/api/admin/users', methods=['GET'])
@token_required
@admin_required
def admin_list_users():
    """Liste tous les utilisateurs."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, nom, prenom, email, telephone, role, status, created_at, last_login_at
               FROM users ORDER BY created_at DESC"""
        )
        users = cursor.fetchall()
        return jsonify({"users": users})
    except Exception:
        logger.exception("Erreur liste users admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/admin/users/<int:user_id>/status', methods=['PUT'])
@token_required
@admin_required
def admin_toggle_user_status(user_id):
    """Active ou désactive un compte utilisateur."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, role, status FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Utilisateur introuvable."}), 404
        if user['id'] == request.user['id']:
            return jsonify({"error": "Vous ne pouvez pas désactiver votre propre compte."}), 400

        new_status = 0 if user['status'] else 1
        cursor.execute("UPDATE users SET status = %s WHERE id = %s", (new_status, user_id))
        conn.commit()
        return jsonify({"success": True, "status": new_status})
    except Exception:
        logger.exception("Erreur toggle status admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
@token_required
@admin_required
def admin_change_user_role(user_id):
    """Change le rôle d'un utilisateur."""
    data = request.get_json() or {}
    new_role = data.get('role', '')
    if new_role not in ('etudiant', 'enseignant', 'admin'):
        return jsonify({"error": "Rôle invalide."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Utilisateur introuvable."}), 404

        cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        conn.commit()
        return jsonify({"success": True, "role": new_role})
    except Exception:
        logger.exception("Erreur change role admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def admin_delete_user(user_id):
    """Supprime un utilisateur."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Utilisateur introuvable."}), 404
        if user_id == request.user['id']:
            return jsonify({"error": "Vous ne pouvez pas supprimer votre propre compte."}), 400

        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception:
        logger.exception("Erreur delete user admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


# ===== ADMIN — QUIZ =====
@app.route('/api/admin/quiz', methods=['GET'])
@token_required
@admin_required
def admin_list_quiz():
    """Liste tous les quiz avec leur chapitre et créateur."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT q.id, q.titre, q.description, q.nombre_questions, q.methode_generation,
                      q.created_at, c.titre as chapitre_titre, co.titre as cours_titre,
                      u.nom as createur_nom, u.prenom as createur_prenom,
                      (SELECT COUNT(*) FROM quiz_attempts qa WHERE qa.quiz_id = q.id) as nb_attempts
               FROM quiz q
               JOIN chapitres c ON c.id = q.chapitre_id
               JOIN cours co ON co.id = c.cours_id
               LEFT JOIN users u ON u.id = q.created_by
               ORDER BY q.created_at DESC"""
        )
        quiz_list = cursor.fetchall()
        return jsonify({"quiz": quiz_list})
    except Exception:
        logger.exception("Erreur liste quiz admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/admin/quiz/<int:quiz_id>', methods=['DELETE'])
@token_required
@admin_required
def admin_delete_quiz(quiz_id):
    """Supprime un quiz et toutes ses données."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM quiz WHERE id = %s", (quiz_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Quiz introuvable."}), 404

        cursor.execute("DELETE FROM quiz_answers WHERE attempt_id IN (SELECT id FROM quiz_attempts WHERE quiz_id = %s)", (quiz_id,))
        cursor.execute("DELETE FROM quiz_attempts WHERE quiz_id = %s", (quiz_id,))
        cursor.execute("DELETE FROM quiz_options WHERE question_id IN (SELECT id FROM quiz_questions WHERE quiz_id = %s)", (quiz_id,))
        cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", (quiz_id,))
        cursor.execute("DELETE FROM quiz WHERE id = %s", (quiz_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception:
        logger.exception("Erreur delete quiz admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


# ===== ADMIN — RESSOURCES =====
@app.route('/api/admin/ressources', methods=['GET'])
@token_required
@admin_required
def admin_list_ressources():
    """Liste toutes les ressources (PDF/vidéos) avec leur chapitre et cours."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT r.id, r.type, r.nom_original, r.taille, r.mime_type, r.created_at,
                      c.id as chapitre_id, c.titre as chapitre_titre,
                      co.titre as cours_titre,
                      u.nom as enseignant_nom, u.prenom as enseignant_prenom
               FROM chapitre_ressources r
               JOIN chapitres c ON c.id = r.chapitre_id
               JOIN cours co ON co.id = c.cours_id
               LEFT JOIN users u ON u.id = r.enseignant_id
               ORDER BY r.created_at DESC"""
        )
        ressources = cursor.fetchall()
        return jsonify({"ressources": ressources})
    except Exception:
        logger.exception("Erreur liste ressources admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/admin/ressources/<int:resource_id>', methods=['DELETE'])
@token_required
@admin_required
def admin_delete_ressource(resource_id):
    """Supprime une ressource (PDF ou vidéo)."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, type, nom_fichier FROM chapitre_ressources WHERE id = %s", (resource_id,))
        ressource = cursor.fetchone()
        if not ressource:
            return jsonify({"error": "Ressource introuvable."}), 404

        if ressource['type'] == 'video' and ressource['nom_fichier']:
            video_path = os.path.join(UPLOAD_VIDEOS_DIR, ressource['nom_fichier'])
            if os.path.exists(video_path):
                os.remove(video_path)

        cursor.execute("DELETE FROM chapitre_ressources WHERE id = %s", (resource_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception:
        logger.exception("Erreur delete ressource admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


# ===== ADMIN — MATIÈRES =====
@app.route('/api/admin/cours', methods=['GET'])
@token_required
@admin_required
def admin_list_cours():
    """Liste toutes les matières avec le nombre de chapitres."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT c.id, c.titre, c.description, c.categorie, c.niveau, c.created_at,
                      c.enseignant_id,
                      u.nom as enseignant_nom, u.prenom as enseignant_prenom,
                      (SELECT COUNT(*) FROM chapitres ch WHERE ch.cours_id = c.id) as nb_chapitres
               FROM cours c
               LEFT JOIN users u ON u.id = c.enseignant_id
               ORDER BY c.created_at DESC"""
        )
        cours_list = cursor.fetchall()
        return jsonify({"cours": cours_list})
    except Exception:
        logger.exception("Erreur liste cours admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/admin/cours', methods=['POST'])
@token_required
@admin_required
def admin_create_cours():
    """Crée une nouvelle matière."""
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

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO cours (titre, description, categorie, niveau, enseignant_id) VALUES (%s, %s, %s, %s, %s)",
            (titre, description, categorie, niveau, request.user['id'])
        )
        conn.commit()
        new_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "id": new_id, "titre": titre, "description": description,
            "categorie": categorie, "niveau": niveau
        }), 201
    except Exception:
        logger.exception("Erreur création cours admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


@app.route('/api/admin/cours/<int:cours_id>', methods=['DELETE'])
@token_required
@admin_required
def admin_delete_cours(cours_id):
    """Supprime une matière et tout son contenu."""
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM cours WHERE id = %s", (cours_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Cours introuvable."}), 404

        cursor.execute("DELETE FROM cours WHERE id = %s", (cours_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Matière supprimée."})
    except Exception:
        logger.exception("Erreur suppression cours admin")
        return jsonify({"error": "Erreur serveur."}), 500
    finally:
        conn.close()


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