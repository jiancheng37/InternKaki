import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# Connect to PostgreSQL
def connect_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
# Initialize Database (Run once to ensure table exists)
def init_db():
    conn = connect_db()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id BIGINT PRIMARY KEY,
            roles TEXT[],
            name TEXT,
            email TEXT,
            contact TEXT,
            start_date TEXT,
            end_date TEXT,
            summary TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users_jobs_sent (
            chat_id BIGINT NOT NULL,
            job_link TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (chat_id, job_link)
        );
    """)
    
    conn.commit()
    cur.close()
    conn.close()

init_db()  # Call this once at the start
