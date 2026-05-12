import pandas as pd
from sqlalchemy import create_engine

DATABASE_URL = "postgresql://postgres:password123@localhost:5433/causalflow"

engine = create_engine(DATABASE_URL)

print("Loading dataset...")

df = pd.read_csv(
    r"C:\Users\ABHIYA\Downloads\archive\olist_orders_dataset.csv"
)

print("Rows loaded:", len(df))

# Keep needed columns
df = df[[
    'order_purchase_timestamp',
    'order_delivered_customer_date',
    'order_estimated_delivery_date'
]]

# Convert to datetime
df['order_purchase_timestamp'] = pd.to_datetime(
    df['order_purchase_timestamp']
)

df['order_delivered_customer_date'] = pd.to_datetime(
    df['order_delivered_customer_date']
)

df['order_estimated_delivery_date'] = pd.to_datetime(
    df['order_estimated_delivery_date']
)

# Remove null rows
df = df.dropna()

# Create features
df['delivery_days'] = (
    df['order_delivered_customer_date'] -
    df['order_purchase_timestamp']
).dt.days

df['is_late'] = (
    df['order_delivered_customer_date'] >
    df['order_estimated_delivery_date']
).astype(int)

df['day_of_week'] = df['order_purchase_timestamp'].dt.dayofweek
df['month'] = df['order_purchase_timestamp'].dt.month
df['hour'] = df['order_purchase_timestamp'].dt.hour

df['is_weekend'] = (
    df['day_of_week'] >= 5
).astype(int)

df['is_holiday_season'] = (
    df['month'].isin([11, 12])
).astype(int)

# Dummy values
df['customer_state'] = 'SP'
df['total_payment'] = 250

# Final dataframe
final_df = df[[
    'customer_state',
    'order_purchase_timestamp',
    'delivery_days',
    'is_late',
    'total_payment',
    'day_of_week',
    'month',
    'hour',
    'is_weekend',
    'is_holiday_season'
]]

print("Processed rows:", len(final_df))

# Upload to PostgreSQL
final_df.to_sql(
    'orders',
    engine,
    if_exists='replace',
    index=False
)

print("SUCCESS: Dataset imported successfully")