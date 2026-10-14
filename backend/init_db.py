import mysql.connector
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'logiqa')
DB_PORT = int(os.getenv('DB_PORT', 3306))

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@logiqa.local')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Admin123!')
ADMIN_NOM = os.getenv('ADMIN_NOM', 'Admin')
ADMIN_PRENOM = os.getenv('ADMIN_PRENOM', 'Logiqa')


def seed_admin(cursor, connection):
    """Create the default admin account if it does not already exist."""
    cursor.execute("SELECT id FROM users WHERE email = %s", (ADMIN_EMAIL,))
    if cursor.fetchone():
        print(f"ℹ️  Admin already exists ({ADMIN_EMAIL}).")
        return

    hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute(
        """
        INSERT INTO users (nom, prenom, email, password, telephone, role)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (ADMIN_NOM, ADMIN_PRENOM, ADMIN_EMAIL, hashed, None, 'admin'),
    )
    connection.commit()
    print(f"✅ Default admin created ({ADMIN_EMAIL}). Change ADMIN_PASSWORD in .env for production.")


# Données statiques des cours et chapitres (miroir de course-data.ts frontend)
COURSES_DATA = [
    {
        "id": 1, "titre": "Langage C", "slug": "langage-c",
        "description": "Apprenez le langage C de zéro",
        "categorie": "Programmation", "niveau": "Débutant",
        "chapters": [
            (1, "Introduction et structure d'un programme C"),
            (2, "Variables, types de données et opérateurs"),
            (3, "Structures de contrôle (if, switch, while, for)"),
            (4, "Fonctions et passage de paramètres"),
            (5, "Pointeurs et gestion de la mémoire"),
            (6, "Tableaux, chaînes et structures (struct)"),
        ]
    },
    {
        "id": 2, "titre": "Algèbre", "slug": "algebre",
        "description": "Maîtrisez les fondements de l'algèbre",
        "categorie": "Mathématiques", "niveau": "Débutant",
        "chapters": [
            (7, "Introduction à l'algèbre"),
            (8, "Les nombres réels et les opérations"),
            (9, "Équations du premier et second degré"),
            (10, "Polynômes et factorisation"),
            (11, "Fonctions affines et linéaires"),
            (12, "Fonctions polynômes du second degré"),
        ]
    },
    {
        "id": 3, "titre": "Analyse", "slug": "analyse",
        "description": "Découvrez l'analyse mathématique",
        "categorie": "Mathématiques", "niveau": "Intermédiaire",
        "chapters": [
            (13, "Introduction aux suites numériques"),
            (14, "Suites arithmétiques et géométriques"),
            (15, "Limites et continuité"),
            (16, "Règles de dérivation"),
            (17, "Étude de fonctions"),
            (18, "Primitives et intégrales"),
        ]
    },
    {
        "id": 4, "titre": "Systèmes logiques et architecture", "slug": "systemes-logiques",
        "description": "Comprenez l'architecture des ordinateurs",
        "categorie": "Informatique", "niveau": "Intermédiaire",
        "chapters": [
            (19, "Systèmes de numération et codage de l'information"),
            (20, "Algèbre de Boole et portes logiques"),
            (21, "Simplification des fonctions logiques (Tables de Karnaugh)"),
            (22, "Circuits combinatoires (Multiplexeurs, Décodeurs, Additionneurs)"),
            (23, "Circuits séquentiels (Basculeurs, Compteurs, Registres)"),
            (24, "Architecture de Von Neumann et jeu d'instructions"),
        ]
    },
    {
        "id": 5, "titre": "Algorithmes", "slug": "algorithmes",
        "description": "Apprenez à concevoir des algorithmes efficaces",
        "categorie": "Informatique", "niveau": "Intermédiaire",
        "chapters": [
            (25, "Introduction à l'algorithmique"),
            (26, "Variables, conditions et boucles"),
            (27, "Complexité algorithmique et notation Big O"),
            (28, "Algorithmes de tri (bulles, insertion, rapide)"),
            (29, "Recherche linéaire et dichotomique"),
            (30, "Piles, files et listes chaînées"),
        ]
    },
    {
        "id": 6, "titre": "Base de données", "slug": "base-de-donnees",
        "description": "Maîtrisez SQL et la conception de bases de données",
        "categorie": "Informatique", "niveau": "Intermédiaire",
        "chapters": [
            (31, "Introduction et modèle entité-association"),
            (32, "Passage au modèle relationnel et normalisation"),
            (33, "Création et manipulation des tables (DDL/DML)"),
            (34, "Requêtes de sélection et filtres SQL"),
            (35, "Jointures et sous-requêtes SQL"),
            (36, "Index, transactions et performances"),
        ]
    },
    {
        "id": 7, "titre": "Réseaux", "slug": "reseaux",
        "description": "Comprenez les réseaux informatiques",
        "categorie": "Informatique", "niveau": "Avancé",
        "chapters": [
            (37, "Introduction aux réseaux et modèle OSI"),
            (38, "Le modèle TCP/IP"),
            (39, "Adressage IP et sous-réseaux"),
            (40, "Routage et commutation"),
            (41, "Protocoles applicatifs (HTTP, DNS, DHCP)"),
            (42, "Sécurité réseau de base (pare-feu, VPN)"),
        ]
    },
    {
        "id": 8, "titre": "Système d'exploitation", "slug": "systeme-exploitation",
        "description": "Découvrez le fonctionnement des systèmes d'exploitation",
        "categorie": "Informatique", "niveau": "Avancé",
        "chapters": [
            (43, "Architecture d'un système d'exploitation"),
            (44, "Notion de processus et de thread"),
            (45, "Ordonnancement des processus"),
            (46, "Synchronisation et interblocage"),
            (47, "Mémoire virtuelle et pagination"),
            (48, "Systèmes de fichiers et entrées/sorties"),
        ]
    },
]


def seed_courses_and_chapters(cursor, connection):
    """Peuple la base avec les cours et chapitres statiques (idempotent)."""
    # Vérifier si les cours sont déjà seedés
    cursor.execute("SELECT COUNT(*) as cnt FROM cours")
    result = cursor.fetchone()
    # mysql.connector retourne un tuple (pas un dict) sans dictionary=True
    count = result[0] if isinstance(result, tuple) else result['cnt']
    if count > 0:
        print("ℹ️  Cours déjà seedés.")
        return

    # Récupérer l'ID d'un enseignant existant (ou utiliser l'admin)
    cursor.execute("SELECT id FROM users WHERE role = 'enseignant' LIMIT 1")
    teacher = cursor.fetchone()
    if not teacher:
        cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        teacher = cursor.fetchone()
    if not teacher:
        print("⚠️  Aucun utilisateur trouvé pour seed des cours.")
        return

    # mysql.connector retourne un tuple sans dictionary=True
    teacher_id = teacher[0] if isinstance(teacher, tuple) else teacher['id']

    for course in COURSES_DATA:
        cursor.execute(
            """INSERT INTO cours (id, titre, description, categorie, niveau, enseignant_id)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (course["id"], course["titre"], course["description"],
             course["categorie"], course["niveau"], teacher_id)
        )
        for i, (chap_id, chap_title) in enumerate(course["chapters"], 1):
            cursor.execute(
                """INSERT INTO chapitres (id, cours_id, numero, titre)
                   VALUES (%s, %s, %s, %s)""",
                (chap_id, course["id"], i, chap_title)
            )

    connection.commit()
    print(f"✅ {len(COURSES_DATA)} cours et {sum(len(c['chapters']) for c in COURSES_DATA)} chapitres seedés.")


def init_database():
    """Create the database, tables, and default admin if they do not already exist.
    IMPORTANT: this function is idempotent and non-destructive — it never drops
    existing tables, so data created by users is preserved across restarts."""
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
        )
        cursor = connection.cursor()

        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{DB_NAME}`")

        # ✅ CREATE TABLE IF NOT EXISTS : ne touche jamais aux données existantes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                nom VARCHAR(100) NOT NULL,
                prenom VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                telephone VARCHAR(50) NULL,
                role ENUM('admin','etudiant','enseignant') NOT NULL DEFAULT 'etudiant',
                email_verified_at TIMESTAMP NULL,
                status TINYINT(1) NOT NULL DEFAULT 1,
                last_login_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                jti VARCHAR(100) NOT NULL UNIQUE,
                token_hash VARCHAR(255) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                revoked BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_jti (jti),
                INDEX idx_user_id (user_id)
            )
        """)

        # Table des codes OTP / tokens de réinitialisation.
        # user_id est PRIMARY KEY car app.py fait un "ON DUPLICATE KEY UPDATE" dessus.
        # ⚠️ code = VARCHAR(255) : /api/forgot-password y stocke un hash SHA-256 (64 caractères).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otp_codes (
                user_id BIGINT PRIMARY KEY,
                code VARCHAR(255) NOT NULL,
                expires_at DATETIME NOT NULL,
                attempts INT NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        # Met à jour une table otp_codes déjà existante (ancienne version : VARCHAR(6))
        cursor.execute("ALTER TABLE otp_codes MODIFY code VARCHAR(255) NOT NULL")

        # Table de suivi des tentatives (rate limiting)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                identifier VARCHAR(255) NOT NULL,
                attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_identifier (identifier),
                INDEX idx_attempted_at (attempted_at)
            )
        """)

        # ✅ DÉPLACÉ : cours doit être créé AVANT chapitres (clé étrangère)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cours (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                titre VARCHAR(255) NOT NULL,
                description TEXT,
                categorie VARCHAR(100),
                niveau VARCHAR(50) DEFAULT 'Débutant',
                enseignant_id BIGINT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (enseignant_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Table des chapitres
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chapitres (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                cours_id BIGINT NOT NULL,
                numero INT NOT NULL,
                titre VARCHAR(255) NOT NULL,
                description TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cours_id) REFERENCES cours(id) ON DELETE CASCADE
            )
        """)

        # Table des ressources de chapitres (PDF en BLOB, vidéos sur disque)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chapitre_ressources (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                chapitre_id BIGINT NOT NULL,
                type ENUM('video', 'pdf') NOT NULL,
                nom_original VARCHAR(255) NOT NULL,
                nom_fichier VARCHAR(255),
                contenu LONGBLOB,
                taille INT,
                mime_type VARCHAR(100),
                enseignant_id BIGINT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chapitre_id) REFERENCES chapitres(id) ON DELETE CASCADE,
                FOREIGN KEY (enseignant_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Table des quiz générés automatiquement
        # ✅ 'groq' ajouté : app.py accepte 'auto', 'openai' et 'groq'
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                chapitre_id BIGINT NOT NULL,
                titre VARCHAR(255) NOT NULL,
                description TEXT,
                nombre_questions INT NOT NULL DEFAULT 10,
                methode_generation ENUM('auto', 'openai', 'groq') NOT NULL DEFAULT 'auto',
                created_by BIGINT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chapitre_id) REFERENCES chapitres(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        # Met à jour une table quiz déjà existante (ancienne version sans 'groq')
        cursor.execute(
            "ALTER TABLE quiz MODIFY methode_generation "
            "ENUM('auto', 'openai', 'groq') NOT NULL DEFAULT 'auto'"
        )

        # Table des questions de quiz
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_questions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                quiz_id BIGINT NOT NULL,
                texte TEXT NOT NULL,
                ordre INT NOT NULL,
                FOREIGN KEY (quiz_id) REFERENCES quiz(id) ON DELETE CASCADE
            )
        """)

        # Table des options/réponses pour chaque question
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_options (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                question_id BIGINT NOT NULL,
                texte VARCHAR(500) NOT NULL,
                est_correcte BOOLEAN NOT NULL DEFAULT FALSE,
                FOREIGN KEY (question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE
            )
        """)

        # Table des tentatives de quiz par les étudiants
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                quiz_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                score INT NOT NULL DEFAULT 0,
                total_questions INT NOT NULL DEFAULT 0,
                completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quiz_id) REFERENCES quiz(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Table des réponses données par les étudiants
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_answers (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                attempt_id BIGINT NOT NULL,
                question_id BIGINT NOT NULL,
                option_id BIGINT NOT NULL,
                FOREIGN KEY (attempt_id) REFERENCES quiz_attempts(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE,
                FOREIGN KEY (option_id) REFERENCES quiz_options(id) ON DELETE CASCADE
            )
        """)

        connection.commit()
        print(f"✅ Database `{DB_NAME}` ready (users, sessions, otp_codes, login_attempts, cours, chapitres, quiz).")

        seed_admin(cursor, connection)
        seed_courses_and_chapters(cursor, connection)
        return True
    except mysql.connector.Error as err:
        print(f"❌ Database init failed: {err}")
        return False
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == '__main__':
    init_database()