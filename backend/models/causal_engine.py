import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import dowhy
from dowhy import CausalModel
import warnings

warnings.filterwarnings('ignore')

# PostgreSQL connection
engine = create_engine(
    'postgresql://admin:password123@localhost:5432/causalflow'
)

def run_causal_analysis():
    """
    Analyze whether high-value orders cause longer delivery times
    """

    print("Loading data for causal analysis...")

    # Load tables from PostgreSQL
    orders = pd.read_sql('SELECT * FROM orders', engine)

    order_items = pd.read_sql(
        'SELECT order_id, price, freight_value FROM order_items',
        engine
    )

    print("Merging datasets...")

    # Merge price information
    df = orders.merge(
        order_items.groupby('order_id').agg(
            total_price=('price', 'sum'),
            freight_value=('freight_value', 'mean')
        ).reset_index(),
        on='order_id',
        how='inner'
    )

    # Create additional features
    df['day_of_week'] = pd.to_datetime(
        df['order_purchase_timestamp']
    ).dt.dayofweek

    df['month'] = pd.to_datetime(
        df['order_purchase_timestamp']
    ).dt.month

    # Keep only needed columns
    df = df[
        [
            'delivery_days',
            'total_price',
            'freight_value',
            'day_of_week',
            'month'
        ]
    ].dropna()

    # Remove extreme outliers
    df = df[df['delivery_days'] < 60]
    df = df[df['delivery_days'] > 0]

    # Treatment variable
    # High-value order = above median price
    df['high_value_order'] = (
        df['total_price'] > df['total_price'].median()
    ).astype(int)

    print(f"Analyzing {len(df)} orders...")
    print(f"Average delivery days: {df['delivery_days'].mean():.1f}")

    # Causal graph
    causal_graph = """
    digraph {
        high_value_order -> delivery_days;
        freight_value -> delivery_days;
        month -> delivery_days;
        month -> high_value_order;
        day_of_week -> delivery_days;
    }
    """

    print("\nBuilding causal model...")

    # Create causal model
    model = CausalModel(
        data=df,
        treatment='high_value_order',
        outcome='delivery_days',
        graph=causal_graph
    )

    # Identify causal effect
    identified_estimand = model.identify_effect(
        proceed_when_unidentifiable=True
    )

    print("Estimating causal effect...")

    # Estimate effect
    estimate = model.estimate_effect(
        identified_estimand,
        method_name="backdoor.linear_regression"
    )

    causal_effect = estimate.value

    print("\n" + "=" * 50)
    print("CAUSAL ANALYSIS RESULTS")
    print("=" * 50)

    print("\nQuestion:")
    print("Do high-value orders take longer to deliver?")

    print(f"\nCausal Effect: {causal_effect:.2f} days")

    if causal_effect > 0:
        print(
            f"\nConclusion: High-value orders take "
            f"{causal_effect:.1f} MORE days to deliver"
        )
    else:
        print(
            f"\nConclusion: High-value orders take "
            f"{abs(causal_effect):.1f} FEWER days"
        )

    return {
        'causal_effect': causal_effect,
        'sample_size': len(df)
    }


def counterfactual_simulation(
    base_late_rate,
    intervention_name,
    effect_size
):
    """
    Simulate business intervention impact
    """

    print(
        f"\nCounterfactual Simulation: {intervention_name}"
    )

    print(f"Current late delivery rate: {base_late_rate:.1%}")

    new_late_rate = max(
        0,
        base_late_rate - effect_size
    )

    orders_count = 100000

    current_late = int(
        orders_count * base_late_rate
    )

    new_late = int(
        orders_count * new_late_rate
    )

    prevented = current_late - new_late

    print(f"New late rate: {new_late_rate:.1%}")
    print(f"Late orders prevented: {prevented:,}")

    return {
        'intervention': intervention_name,
        'orders_prevented': prevented
    }


if __name__ == '__main__':

    # Run causal analysis
    result = run_causal_analysis()

    # Run simulation
    counterfactual_simulation(
        base_late_rate=0.08,
        intervention_name="Priority handling",
        effect_size=0.03
    )