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
from init_db import init_database

load_dotenv()

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.getenv('JWT_SECRET', 'votre_secret_par_defaut')
SESSION_DURATION_DAYS = 2  # Durée de validité : 2 jours


def hash_token(token):
    """Hash le token avant de le stocker en base (jamais en clair)."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


@app.route('/')
def home():
    return jsonify({"message": "API LOGIQA fonctionne !"})


# ===== INSCRIPTION =====
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    nom = data.get('nom')
    prenom = data.get('prenom')
    email = data.get('email')
    password = data.get('password')
    telephone = data.get('telephone')
    role = data.get('role', 'etudiant')

    if not all([nom, prenom, email, password]):
        return jsonify({"error": "Tous les champs obligatoires doivent être remplis."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "Un compte existe déjà avec cet email."}), 409

        # Hachage du mot de passe
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute(
            "INSERT INTO users (nom, prenom, email, password, telephone, role) VALUES (%s, %s, %s, %s, %s, %s)",
            (nom, prenom, email, hashed_password, telephone, role)
        )
        conn.commit()

        return jsonify({"success": True, "message": "Compte créé avec succès."})
    except Exception as e:
        print(f"Erreur lors de l'inscription: {e}")
        return jsonify({"error": "Erreur serveur lors de la création du compte."}), 500
    finally:
        conn.close()


# ===== CONNEXION (avec création automatique de session) =====
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis."}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Erreur connexion base de données"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, nom, prenom, email, password, role FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Email ou mot de passe incorrect."}), 401

        # Vérification du mot de passe
        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return jsonify({"error": "Email ou mot de passe incorrect."}), 401

        del user['password']

        # Génération du token JWT avec identifiant unique et gestion UTC propre
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

        # Création automatique de la session en base (conversion en Naive UTC pour MySQL)
        token_hash = hash_token(token)
        expires_at_naive = expires_at.replace(tzinfo=None)

        cursor.execute(
            "INSERT INTO sessions (user_id, jti, token_hash, expires_at) VALUES (%s, %s, %s, %s)",
            (user['id'], jti, token_hash, expires_at_naive)
        )
        
        # Mise à jour de la dernière connexion
        cursor.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user['id'],))
        
        conn.commit()

        return jsonify({
            "success": True,
            "user": user,
            "token": token,
            "expires_at": expires_at.isoformat()
        })
    except Exception as e:
        print(f"Erreur lors de la connexion: {e}")
        return jsonify({"error": "Erreur serveur lors de la connexion."}), 500
    finally:
        conn.close()


# ===== MIDDLEWARE : vérifie le token ET la session =====
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

        # Vérifie que la session existe et n'est pas révoquée
        conn = get_connection()
        if not conn:
            return jsonify({"error": "Erreur base de données"}), 500

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT revoked, expires_at FROM sessions WHERE jti = %s",
                (payload['jti'],)
            )
            session = cursor.fetchone()

            if not session:
                return jsonify({"error": "Session introuvable."}), 401
            if session['revoked']:
                return jsonify({"error": "Session révoquée."}), 401
            
            # Gestion uniforme des comparaisons de date (avec ou sans tzinfo)
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


# ===== DÉCONNEXION (révoque la session) =====
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


# ===== ROUTE PROTÉGÉE (exemple) =====
@app.route('/api/me', methods=['GET'])
@token_required
def me():
    return jsonify({"user": request.user})


if __name__ == '__main__':
    if not init_database():
        raise SystemExit(1)
    port = int(os.getenv('PORT', 3000))
    app.run(debug=True, port=port)