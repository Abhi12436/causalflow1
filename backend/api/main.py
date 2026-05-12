# ============================================================
#  FILE: backend/api/main.py
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import joblib
import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..')
))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://admin:password123@localhost:5432/causalflow'
)

engine = create_engine(DATABASE_URL)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ============================================================
# LOAD MODELS
# ============================================================

def load_model(path):
    try:
        return joblib.load(path)
    except:
        return None


DELAY_MODEL = load_model('backend/models/saved/delay_model.pkl')
STATE_ENCODER = load_model('backend/models/saved/state_encoder.pkl')
FORECAST_MODEL = load_model('backend/models/saved/forecast_model.pkl')
FORECAST_FEATS = load_model('backend/models/saved/forecast_features.pkl')


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="CausalFlow API",
    version="1.0.0",
    docs_url="/docs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPERS
# ============================================================

def run_query(sql: str):
    try:
        return pd.read_sql(sql, engine)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def safe_float(val):
    try:
        if pd.isna(val):
            return 0.0
        return float(val)
    except:
        return 0.0


def safe_int(val):
    try:
        if pd.isna(val):
            return 0
        return int(val)
    except:
        return 0


# ============================================================
# MODELS
# ============================================================

class DelayRequest(BaseModel):
    day_of_week: int
    hour: int
    month: int
    total_payment: float
    customer_state: str = "SP"
    payment_installments: int = 1
    estimated_days: int = 15


class CounterfactualRequest(BaseModel):
    intervention: str
    effect_size: float


class CausalEffectRequest(BaseModel):
    treatment: str
    outcome: str


class NLQueryRequest(BaseModel):
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
            "status": "error",
            "message": str(e)
        }


# ============================================================
# SUMMARY
# ============================================================

@app.get("/api/v1/analytics/summary")
def get_summary():

    df = run_query("""
        SELECT
            COUNT(*) AS total_orders,
            ROUND(AVG(delivery_days)::numeric, 1) AS avg_delivery_days,
            SUM(is_late) AS late_orders,
            ROUND(AVG(is_late::numeric) * 100, 1) AS late_rate_pct,
            ROUND(AVG(total_payment)::numeric, 2) AS avg_order_value,
            COUNT(DISTINCT customer_state) AS states_covered,
            MIN(order_purchase_timestamp::date)::text AS first_order_date,
            MAX(order_purchase_timestamp::date)::text AS last_order_date
        FROM public."orders"
    """)

    row = df.iloc[0]

    return {
        "total_orders": safe_int(row['total_orders']),
        "avg_delivery_days": safe_float(row['avg_delivery_days']),
        "late_orders": safe_int(row['late_orders']),
        "late_rate_pct": safe_float(row['late_rate_pct']),
        "avg_order_value": safe_float(row['avg_order_value']),
        "states_covered": safe_int(row['states_covered']),
        "first_order_date": str(row['first_order_date']),
        "last_order_date": str(row['last_order_date']),
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

            COUNT(*) AS orders,

            ROUND(AVG(delivery_days)::numeric, 1) AS avg_days,

            ROUND(AVG(is_late::numeric) * 100, 1) AS late_pct,

            ROUND(AVG(total_payment)::numeric, 2) AS avg_value

        FROM public."orders"

        GROUP BY DATE_TRUNC('month', order_purchase_timestamp)

        ORDER BY 1
    """)

    return df.to_dict(orient='records')


# ============================================================
# STATE ANALYTICS
# ============================================================

@app.get("/api/v1/analytics/by-state")
def by_state():

    df = run_query("""
        SELECT
            customer_state AS state,

            COUNT(*) AS orders,

            ROUND(AVG(is_late::numeric) * 100, 1) AS late_rate_pct,

            ROUND(AVG(delivery_days)::numeric, 1) AS avg_delivery_days,

            ROUND(AVG(total_payment)::numeric, 2) AS avg_order_value

        FROM public."orders"

        WHERE customer_state IS NOT NULL

        GROUP BY customer_state

        ORDER BY orders DESC

        LIMIT 15
    """)

    return df.to_dict(orient='records')


# ============================================================
# HOURLY
# ============================================================

@app.get("/api/v1/analytics/hourly")
def hourly():

    df = run_query("""
        SELECT
            hour AS hour_of_day,

            COUNT(*) AS orders,

            ROUND(AVG(is_late::numeric) * 100, 1) AS late_rate_pct

        FROM public."orders"

        GROUP BY hour

        ORDER BY hour
    """)

    return df.to_dict(orient='records')


# ============================================================
# WEEKDAY
# ============================================================

@app.get("/api/v1/analytics/weekday-pattern")
def weekday():

    day_names = {
        0: "Mon",
        1: "Tue",
        2: "Wed",
        3: "Thu",
        4: "Fri",
        5: "Sat",
        6: "Sun"
    }

    df = run_query("""
        SELECT
            day_of_week,

            COUNT(*) AS orders,

            ROUND(AVG(is_late::numeric) * 100, 1) AS late_rate_pct,

            ROUND(AVG(delivery_days)::numeric, 1) AS avg_days

        FROM public."orders"

        GROUP BY day_of_week

        ORDER BY day_of_week
    """)

    df['day_name'] = df['day_of_week'].map(day_names)

    return df.to_dict(orient='records')


# ============================================================
# PREDICTION
# ============================================================

@app.post("/api/v1/predict/delay")
def predict_delay(req: DelayRequest):

    probability = 0.05

    if req.day_of_week >= 5:
        probability += 0.04

    if req.month in [11, 12]:
        probability += 0.06

    if req.hour >= 20:
        probability += 0.02

    if req.total_payment > 500:
        probability += 0.03

    probability = min(probability, 0.99)

    prediction = "LATE RISK 🔴" if probability > 0.12 else "ON TIME 🟢"

    return {
        "prediction": prediction,
        "late_probability_pct": round(probability * 100, 1)
    }


# ============================================================
# COUNTERFACTUAL
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

    total = safe_int(row['total_orders'])
    current_rate = safe_float(row['late_rate'])
    current_late = safe_int(row['late_count'])

    new_rate = max(0.0, current_rate - req.effect_size)

    new_late = int(total * new_rate)

    prevented = current_late - new_late

    return {
        "current_late_rate_pct": round(current_rate * 100, 1),
        "new_late_rate_pct": round(new_rate * 100, 1),
        "late_orders_prevented": prevented
    }


# ============================================================
# FORECAST
# ============================================================

@app.get("/api/v1/forecast/next-7-days")
def forecast():

    return {
        "message": "Forecast endpoint working"
    }


# ============================================================
# AI QUERY
# ============================================================

@app.post("/api/v1/query/natural-language")
async def nl_query(req: NLQueryRequest):

    try:

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": req.question
                }
            ]
        )

        answer = response.choices[0].message.content

        return {
            "answer": answer
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# RUN
# ============================================================

# RUN THIS:
# python -m uvicorn backend.api.main:app --reload --port 8000