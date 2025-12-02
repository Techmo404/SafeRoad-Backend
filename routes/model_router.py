from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import firestore
from ml.model_training import train_model, predict_from_model
from services.weather_service import WeatherService
from services.traffic_service import TrafficService
from auth_utils import verify_token

router = APIRouter(prefix="/model", tags=["AI Model"])
db = firestore.client()


# ------------------ 📌 1) Obtener dataset guardado ---------------------
@router.get("/dataset")
async def get_training_data(user=Depends(verify_token)):
    docs = db.collection("records").where("uid", "==", user.get("uid")).stream()

    dataset = []

    for d in docs:
        r = d.to_dict()

        dataset.append({
            "lat": r.get("coords", {}).get("lat"),
            "lng": r.get("coords", {}).get("lng"),
            "temperature": r.get("weather", {}).get("main", {}).get("temp"),
            "visibility": r.get("weather", {}).get("visibility", 10000),
            "wind_speed": r.get("weather", {}).get("wind", {}).get("speed", 0),

            # FIX: datos opcionales
            "traffic_speed": r.get("traffic", {}).get("speed", 0),
            "jam_factor": r.get("traffic", {}).get("jam_factor", 0),

            "risk_score": r.get("risk_score", None),
            "risk_label": r.get("risk_level", None)
        })

    return {
        "total_records": len(dataset),
        "dataset": dataset
    }


# ------------------ 🤖 2) Entrenar IA ---------------------
@router.post("/train")
async def train(user=Depends(verify_token)):
    result = train_model(user.get("uid"))
    return result


# ------------------ 🔮 3) Predecir usando IA entrenada ---------------------
@router.post("/predict")
async def predict(location: dict, user=Depends(verify_token)):

    lat = location.get("lat")
    lng = location.get("lng")

    if lat is None or lng is None:
        raise HTTPException(400, "Debe enviar coordenadas válidas")

    # Obtener datos reales
    weather = WeatherService().get_weather(lat, lng)
    traffic = TrafficService().get_traffic(lat, lng)

    # Preparar estructura para IA
    input_data = {
        "temperature": weather.get("main", {}).get("temp"),
        "visibility": weather.get("visibility", 10000),
        "wind_speed": weather.get("wind", {}).get("speed", 0),
        "traffic_speed": traffic.get("speed", 0),
        "jam_factor": traffic.get("jam_factor", 0),
    }

    prediction = predict_from_model(user.get("uid"), input_data)

    return {
        "coords": {"lat": lat, "lng": lng},
        "input_used": input_data,
        "prediction": prediction
    }
