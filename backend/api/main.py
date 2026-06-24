from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pandas as pd
import joblib
import os
import re

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from groq import Groq

# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# ============================================================
# DATABASE
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:password123@localhost:5433/causalflow"
)

engine = create_engine(DATABASE_URL)

# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="CausalFlow API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# LOAD MODEL
# ============================================================

def load_model(path):

    try:
        return joblib.load(path)

    except:
        return None


DELAY_MODEL = load_model(
    "backend/models/saved/delay_model.pkl"
)

# ============================================================
# HELPERS
# ============================================================

def run_query(sql):

    try:
        return pd.read_sql(sql, engine)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


def safe_float(v):

    try:
        return float(v)

    except:
        return 0.0


def safe_int(v):

    try:
        return int(v)

    except:
        return 0

# ============================================================
# REQUEST MODELS
# ============================================================

class DelayRequest(BaseModel):

    day_of_week: int
    hour: int
    month: int
    total_payment: float


class CounterfactualRequest(BaseModel):

    intervention: str
    effect_size: float = 0.02


class QuestionRequest(BaseModel):

    question: str

# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "service": "CausalFlow API",
        "status": "running"
    }

# ============================================================
# HEALTH
# ============================================================

@app.get("/api/v1/health")
def health():

    try:

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:

        return {
            "status": "unhealthy",
            "error": str(e)
        }

# ============================================================
# SUMMARY ANALYTICS
# ============================================================

@app.get("/api/v1/analytics/summary")
def summary():

    df = run_query("""
        SELECT
            COUNT(*) AS total_orders,
            ROUND(AVG(delivery_days)::numeric, 1) AS avg_delivery_days,
            SUM(is_late) AS late_orders,
            ROUND(AVG(is_late::numeric) * 100, 1) AS late_rate_pct
        FROM public."orders"
    """)

    row = df.iloc[0]

    return {
        "total_orders": safe_int(row["total_orders"]),
        "avg_delivery_days": safe_float(row["avg_delivery_days"]),
        "late_orders": safe_int(row["late_orders"]),
        "late_rate_pct": safe_float(row["late_rate_pct"])
    }

# ============================================================
# MONTHLY TREND
# ============================================================

@app.get("/api/v1/analytics/monthly-trend")
def monthly_trend():

    df = run_query("""
        SELECT
            TO_CHAR(
                DATE_TRUNC('month', order_purchase_timestamp),
                'YYYY-MM'
            ) AS month,
            COUNT(*) AS order_count
        FROM public."orders"
        GROUP BY DATE_TRUNC('month', order_purchase_timestamp)
        ORDER BY 1
    """)

    return df.to_dict(orient="records")

# ============================================================
# DELAY PREDICTION
# ============================================================

@app.post("/api/v1/predict/delay")
def predict_delay(req: DelayRequest):

    risk_score = 0.05
    risk_factors = []

    if req.day_of_week >= 5:
        risk_score += 0.04
        risk_factors.append("Weekend order")

    if req.month in [11, 12]:
        risk_score += 0.06
        risk_factors.append("Holiday season")

    if req.hour >= 20:
        risk_score += 0.02
        risk_factors.append("Late night order")

    if req.total_payment > 500:
        risk_score += 0.03
        risk_factors.append("High value order")

    probability = min(risk_score, 0.95)

    prediction = (
        "LATE RISK"
        if probability > 0.12
        else "ON TIME"
    )

    return {
        "prediction": prediction,
        "late_probability_pct": round(
            probability * 100,
            1
        ),
        "risk_factors": risk_factors
    }

# ============================================================
# WHAT-IF AI SIMULATOR
# ============================================================

@app.post("/api/v1/causal/counterfactual")
def counterfactual(req: CounterfactualRequest):

    df = run_query("""
        SELECT
            COUNT(*) AS total_orders,
            AVG(is_late::numeric) AS late_rate,
            SUM(is_late) AS late_count
        FROM public."orders"
    """)

    row = df.iloc[0]

    total = safe_int(row["total_orders"])

    current_rate = safe_float(
        row["late_rate"]
    )

    current_late = safe_int(
        row["late_count"]
    )

    text_input = req.intervention.lower()

    impact = req.effect_size

    # Extract percentage automatically

    match = re.search(
        r'(\d+)',
        text_input
    )

    if match:

        percent = int(
            match.group(1)
        ) / 100

    else:

        percent = req.effect_size

    # ========================================================
    # AI-LIKE BUSINESS LOGIC
    # ========================================================

    if any(word in text_input for word in [
        "staff",
        "worker",
        "employee",
        "manpower"
    ]):

        if (
            "reduce" in text_input
            or
            "decrease" in text_input
        ):

            impact = -(percent * 0.05)

        else:

            impact = percent * 0.05

    elif any(word in text_input for word in [
        "warehouse",
        "inventory",
        "storage"
    ]):

        impact = percent * 0.04

    elif any(word in text_input for word in [
        "delivery",
        "shipping",
        "courier",
        "logistics"
    ]):

        impact = percent * 0.06

    elif any(word in text_input for word in [
        "discount",
        "sale",
        "promotion"
    ]):

        impact = percent * 0.03

    # ========================================================
    # FINAL CALCULATIONS
    # ========================================================

    new_rate = max(
        0.0,
        current_rate - impact
    )

    new_late = int(
        total * new_rate
    )

    prevented = (
        current_late - new_late
    )

    # ========================================================
    # GROQ AI ANALYSIS
    # ========================================================

    ai_prompt = f"""
    You are an AI business operations analyst.

    Analyze this operational intervention.

    User Intervention:
    {req.intervention}

    Current Late Delivery Rate:
    {round(current_rate * 100, 1)}%

    Predicted New Late Delivery Rate:
    {round(new_rate * 100, 1)}%

    Late Orders Prevented:
    {prevented}

    Explain:
    1. Why this operational change affects delivery performance
    2. Business impact
    3. Operational risks
    4. Recommended next actions

    Keep response concise, professional and realistic.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": ai_prompt
            }
        ],
        temperature=0.7
    )

    ai_reasoning = (
        response
        .choices[0]
        .message
        .content
    )

    return {
        "intervention": req.intervention,
        "current_late_rate_pct": round(
            current_rate * 100,
            1
        ),
        "new_late_rate_pct": round(
            new_rate * 100,
            1
        ),
        "late_orders_prevented": prevented,
        "estimated_impact_pct": round(
            impact * 100,
            1
        ),
        "ai_reasoning": ai_reasoning
    }

# ============================================================
# AI BUSINESS ASSISTANT
# ============================================================

@app.post("/api/v1/query/natural-language")
def ask_business_ai(req: QuestionRequest):

    prompt = f"""
    You are an AI business analyst assistant.

    Answer this business question professionally and clearly.

    Question:
    {req.question}
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7
    )

    answer = (
        response
        .choices[0]
        .message
        .content
    )

    return {
        "answer": answer
    }

# ============================================================
# RUN SERVER
# ============================================================

# uvicorn backend.api.main:app --reload --port 8000