from fastapi import FastAPI, Depends, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.openapi.utils import get_openapi
from firebase_admin import auth, credentials, firestore
import firebase_admin
from datetime import datetime
from dotenv import load_dotenv
import os


from services.incidents_service import IncidentService
from services.weather_service import WeatherService
from services.traffic_service import TrafficService


from ml.model_training import predict_from_model


from auth_utils import verify_token

load_dotenv()

print("🔧 WEATHER KEY DETECTADA:", os.getenv("WEATHER_API_KEY"))

#inicio de firebase
cred = credentials.Certificate("firebase-admin.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

#creacion de fast api
app = FastAPI(title="SafeRoad API", version="1.0")

#cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#endpoints
@app.get("/")
def root():
    return {"status": "API ONLINE 🚦"}

@app.get("/user-info")
async def get_user_info(user=Depends(verify_token)):
    return {
        "uid": user.get("uid"),
        "email": user.get("email"),
        "name": user.get("name") or user.get("display_name"),
        "picture": user.get("picture"),
    }

@app.post("/save-data")
async def save_data(request: Request, user=Depends(verify_token)):
    data = await request.json()
    data["uid"] = user.get("uid")
    
    doc = db.collection("records").add(data)
    return {"status": "ok", "id": doc[1].id, "saved": data}

@app.get("/history")
async def get_history(user=Depends(verify_token)):

    query = db.collection("records").where("uid", "==", user.get("uid")).stream()

    history = [
        {**doc.to_dict(), "id": doc.id}
        for doc in query
    ]

    history = sorted(history, key=lambda x: x["datetime"], reverse=True)

    return {
        "user": user.get("email"),
        "records": history
    }

# ver los riesgos
@app.post("/risk-check")
async def risk_check(
    user=Depends(verify_token),
    location: dict = Body(default={})
):
    lat = location.get("lat")
    lng = location.get("lng")

    if lat is None or lng is None:
        raise HTTPException(400, "Se requieren coordenadas válidas.")

    weather = WeatherService().get_weather(lat, lng)
    traffic = TrafficService().get_traffic(lat, lng)

    ai_input = {
        "temperature": weather["main"]["temp"],
        "visibility": weather.get("visibility", 10000),
        "wind_speed": weather.get("wind", {}).get("speed", 0),
        "traffic_speed": traffic.get("speed", 0),
        "jam_factor": traffic.get("jam_factor", 0),
    }


    prediction = predict_from_model(user.get("uid"), ai_input)

    if "predicted_label" in prediction:
        risk_result = prediction["predicted_label"]
        model_used = "Machine Learning"
    else:

        model_used = "Fallback Rules"

        if ai_input["visibility"] < 4000 or ai_input["wind_speed"] > 12:
            risk_result = "Alto"
        elif ai_input["traffic_speed"] < 50:
            risk_result = "Medio"
        else:
            risk_result = "Bajo"

    result = {
        "uid": user.get("uid"),
        "coords": {"lat": lat, "lng": lng},
        "weather": weather,
        "traffic": traffic,
        "ai_input": ai_input,
        "predicted_risk": risk_result,
        "model": model_used,
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "AI powered"
    }

    # guardado en db
    result["id"] = db.collection("records").add(result)[1].id

    return result



# incidentes API
@app.get("/incidents")
async def get_incidents(user=Depends(verify_token), lat: float = None, lng: float = None):
    
    if not lat or not lng:
        raise HTTPException(400, "Se requieren coordenadas")

    incidents = IncidentService().get_incidents(lat, lng)

    return {
        "coords": { "lat": lat, "lng": lng },
        "incidents": incidents
    }


from routes.model_router import router as model_router
app.include_router(model_router)


#Token
security = HTTPBearer()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="SafeRoad API",
        version="1.0.0",
        description="Sistema IA para predicción de riesgo vial",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return openapi_schema

app.openapi = custom_openapi
