import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
import lightgbm as lgb
from sklearn.metrics import accuracy_score, classification_report
import mlflow
import mlflow.sklearn

# PostgreSQL connection
engine = create_engine(
    'postgresql://admin:password123@localhost:5432/causalflow'
)

def prepare_features():
    """Prepare data for ML model"""

    print("Loading orders from PostgreSQL...")

    # Read table from PostgreSQL
    orders = pd.read_sql('SELECT * FROM orders', engine)

    print(f"Loaded {len(orders)} rows")

    # Create feature dataframe
    features = pd.DataFrame()

    # Convert timestamp
    purchase_time = pd.to_datetime(
        orders['order_purchase_timestamp']
    )

    # Feature engineering
    features['day_of_week'] = purchase_time.dt.dayofweek
    features['hour'] = purchase_time.dt.hour
    features['month'] = purchase_time.dt.month

    # Target column
    target = orders['is_late']

    # Remove null values
    mask = ~(features.isnull().any(axis=1) | target.isnull())

    features = features[mask]
    target = target[mask]

    return features, target

def train_model():

    print("Preparing features...")

    X, y = prepare_features()

    print(f"Training rows: {len(X)}")

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    # MLflow tracking
    mlflow.set_experiment("delay_prediction")

    with mlflow.start_run():

        print("Training LightGBM model...")

        model = lgb.LGBMClassifier(
            n_estimators=100,
            learning_rate=0.1,
            random_state=42
        )

        model.fit(X_train, y_train)

        # Predictions
        predictions = model.predict(X_test)

        # Accuracy
        accuracy = accuracy_score(y_test, predictions)

        print(f"\nAccuracy: {accuracy:.2%}")

        print("\nClassification Report:")
        print(
            classification_report(
                y_test,
                predictions,
                target_names=['On Time', 'Late']
            )
        )

        # Save metrics
        mlflow.log_metric("accuracy", accuracy)

        # Save model
        mlflow.sklearn.log_model(
            model,
            "delay_model"
        )

        print("\nModel saved successfully!")

        return model

if __name__ == '__main__':
    train_model()