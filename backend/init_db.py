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


def init_database():
    """Create the database, tables, and default admin if they do not already exist."""
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

        # 🔴 SUPPRIMER les anciennes tables si elles existent (pour recréer proprement)
        cursor.execute("DROP TABLE IF EXISTS sessions")
        cursor.execute("DROP TABLE IF EXISTS users")

        # 🔴 RECRÉER avec nom ET prenom (pas name)
        cursor.execute("""
            CREATE TABLE users (
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
            CREATE TABLE sessions (
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

        connection.commit()
        print(f"✅ Database `{DB_NAME}` ready (users, sessions).")

        seed_admin(cursor, connection)
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