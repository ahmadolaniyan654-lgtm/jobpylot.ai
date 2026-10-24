import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "jobpylot.db"


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    return conn
def create_jobs_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, company TEXT, city TEXT, application_link TEXT)""")
    conn.commit()
    conn.close()
def add_job(title, company, city, application_link):
    conn = connect_db()
    cursor= conn.cursor()
    cursor.execute("INSERT INTO jobs (title, company, city, application_link) VALUES (?,?,?,?)", (title, company, city, application_link))
    conn.commit()
    conn.close()
def search_jobs(title, city):
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM jobs WHERE LOWER(title) = LOWER(?) AND LOWER(city) = LOWER(?)",
            (title, city),
        )
        return cursor.fetchall()
    finally:
        conn.close()
def search_jobs_by_city(city):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE LOWER(city) = LOWER(?)", (city,))
    jobs = cursor.fetchall()
    conn.close()
    return jobs
