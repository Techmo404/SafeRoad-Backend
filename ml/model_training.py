import os
import joblib
import pandas as pd
from firebase_admin import firestore
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier


def get_db():
    return firestore.client()


def load_dataset(uid: str):
    """Carga datos reales guardados por el usuario desde Firestore."""
    
    db = get_db()
    docs = db.collection("records").where("uid", "==", uid).stream()

    dataset = []

    for d in docs:
        r = d.to_dict()

        dataset.append({
            "temperature": r.get("weather", {}).get("main", {}).get("temp", 0),
            "visibility": r.get("weather", {}).get("visibility", 10000),
            "wind_speed": r.get("weather", {}).get("wind", {}).get("speed", 0),
            "traffic_speed": r.get("traffic", {}).get("speed", 0),
            "jam_factor": r.get("traffic", {}).get("jam_factor", 0),
            "risk_label": r.get("risk_level", None)  # Puede venir vacío
        })

    return pd.DataFrame(dataset)


def generate_label(row):
    """Crea una etiqueta basada en lógica heurística cuando no existe."""
    
    if row["visibility"] < 4000 or row["wind_speed"] > 12 or row["traffic_speed"] < 20:
        return "Alto"
    if row["traffic_speed"] < 50 or row["wind_speed"] > 8:
        return "Medio"
    
    return "Bajo"


def train_model(uid: str):
    df = load_dataset(uid)


    if df.shape[0] < 30:
        return {"error": "❌ Se requieren mínimo 30 registros para entrenar."}


    df["risk_label"] = df["risk_label"].fillna(df.apply(generate_label, axis=1))


    X = df[["temperature", "visibility", "wind_speed", "traffic_speed", "jam_factor"]]
    y = df["risk_label"]


    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

  
    accuracy = round(model.score(X_test, y_test) * 100, 2)

    model_path = f"ml/model_{uid}.pkl"
    joblib.dump(model, model_path)

    return {
        "message": "🤖 Modelo de clasificación entrenado correctamente",
        "accuracy": accuracy,
        "samples_used": len(df),
        "generated_labels": int(df["risk_label"].isna().sum()),
        "model_path": model_path
    }


def predict_from_model(uid: str, input_data: dict):
    """Predice etiqueta usando el modelo entrenado."""
    
    model_path = f"ml/model_{uid}.pkl"

    if not os.path.exists(model_path):
        return {"warning": "⚠ El modelo aún no ha sido entrenado."}

    model = joblib.load(model_path)
    df = pd.DataFrame([input_data])

    prediction = model.predict(df)[0]

    return {
        "predicted_label": prediction,
        "input_used": input_data,
        "model": f"model_{uid}.pkl"
    }
