import pandas as pd
from sqlalchemy import create_engine
import numpy as np

# Connect to PostgreSQL database
engine = create_engine(
    'postgresql://admin:password123@localhost:5432/causalflow'
)

def load_orders():
    """Load and clean orders data"""

    print("Loading orders data...")

    # Read CSV files
    orders = pd.read_csv('data/olist_orders_dataset.csv')
    order_items = pd.read_csv('data/olist_order_items_dataset.csv')
    customers = pd.read_csv('data/olist_customers_dataset.csv')

    # Convert date columns into datetime format
    orders['order_purchase_timestamp'] = pd.to_datetime(
        orders['order_purchase_timestamp']
    )

    orders['order_delivered_customer_date'] = pd.to_datetime(
        orders['order_delivered_customer_date']
    )

    orders['order_estimated_delivery_date'] = pd.to_datetime(
        orders['order_estimated_delivery_date']
    )

    # Create feature: was delivery late?
    orders['is_late'] = (
        orders['order_delivered_customer_date'] >
        orders['order_estimated_delivery_date']
    ).astype(int)

    # Create feature: delivery duration in days
    orders['delivery_days'] = (
        orders['order_delivered_customer_date'] -
        orders['order_purchase_timestamp']
    ).dt.days

    # Remove rows with missing delivery dates
    orders = orders.dropna(
        subset=['order_delivered_customer_date']
    )

    print(f"Loaded {len(orders)} orders")

    # Save cleaned data into PostgreSQL
    orders.to_sql(
        'orders',
        engine,
        if_exists='replace',
        index=False
    )
    

    order_items.to_sql(
        'order_items',
        engine,
        if_exists='replace',
        index=False
    )

    print("Saved order_items to database!")

    print("Orders table saved to PostgreSQL!")

    return orders


def load_products():
    """Load products dataset"""

    print("Loading products data...")

    products = pd.read_csv(
        'data/olist_products_dataset.csv'
    )

    products.to_sql(
        'products',
        engine,
        if_exists='replace',
        index=False
    )

    print(f"Saved {len(products)} products")


if __name__ == '__main__':
    load_orders()
    load_products()