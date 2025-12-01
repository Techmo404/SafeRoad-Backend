from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth, credentials, firestore
import firebase_admin

# --- Inicializar Firebase ---
cred = credentials.Certificate("firebase-admin.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- Crear FastAPI ---
app = FastAPI(title="SafeRoad API", version="1.0")

# --- CORS Temporal (después limitarlo al dominio Angular) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Middleware para validar Token ---
async def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se envió token en la petición",
        )

    try:
        token = auth_header.split(" ")[1]  # "Bearer <token>"
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )


# --- ENDPOINTS ---

@app.get("/user-info")
async def get_user_info(user=Depends(verify_token)):
    return {
        "uid": user.get("uid"),
        "email": user.get("email"),
        "name": user.get("name") or user.get("display_name"),
        "picture": user.get("picture"),
        "firebase_raw": user,
    }


@app.post("/save-data")
async def save_data(request: Request, user=Depends(verify_token)):
    data = await request.json()
    data["uid"] = user.get("uid")  # 🔥 Relacionar datos con usuario
    doc = db.collection("test").add(data)
    return {"status": "ok", "id": doc[1].id, "saved": data}


@app.get("/")
def root():
    return {"status": "API ONLINE 🚦"}
