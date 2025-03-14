from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import openai
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file
openai.api_key = os.getenv("OPENAI_API_KEY")  # Load API Key securely

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Vaskular Backend is Live!"}

DB_NAME = "/tmp/vaskular.db" if "RENDER" in os.environ else "vaskular.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

class HealthData(BaseModel):
    user_id: str
    circulation: float
    oxygen: float
    swelling_risk: float
    fatigue: float

def setup_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            circulation REAL,
            oxygen REAL,
            swelling_risk REAL,
            fatigue REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

setup_database()

@app.post("/submit_scores/")
def submit_scores(data: HealthData):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO health_scores (user_id, circulation, oxygen, swelling_risk, fatigue)
        VALUES (?, ?, ?, ?, ?)
    """, (data.user_id, data.circulation, data.oxygen, data.swelling_risk, data.fatigue))
    conn.commit()
    conn.close()
    return {"message": "Health scores recorded successfully!"}

@app.get("/get_recovery_plan/{user_id}")
def get_recovery_plan(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM health_scores WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No health data found for this user")

    circulation, oxygen, swelling_risk, fatigue = row["circulation"], row["oxygen"], row["swelling_risk"], row["fatigue"]

    prompt = f"Based on these health scores: Circulation: {circulation}%, Oxygen: {oxygen}%, Swelling Risk: {swelling_risk}%, Fatigue: {fatigue}%, what should this athlete do for optimal recovery?"
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a fitness recovery expert."},
                  {"role": "user", "content": prompt}]
    )

    ai_recommendation = response["choices"][0]["message"]["content"]

    return {"recovery_plan": ai_recommendation}

@app.get("/get_history/{user_id}")
def get_history(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM health_scores WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    history = cursor.fetchall()
    conn.close()

    if not history:
        raise HTTPException(status_code=404, detail="No health data found")

    return {"history": [dict(row) for row in history]}
