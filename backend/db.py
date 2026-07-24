import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),  # Par défaut, sous XAMPP le mot de passe est vide ""
            database=os.getenv('DB_NAME', 'logiqa'), # Assure-toi que la base 'logiqa' existe dans phpMyAdmin
            port=int(os.getenv('DB_PORT', 3306))
        )
        return connection
    except mysql.connector.Error as err:
        print(f"❌ Erreur MySQL: {err}")
        return None