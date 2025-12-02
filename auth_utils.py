from fastapi import HTTPException, Request
from firebase_admin import auth

async def verify_token(request: Request):

    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")

    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="No se envió token en la petición"
        )

    try:
        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise ValueError("Formato inválido del token")

        token = parts[1]
        decoded = auth.verify_id_token(token)
        return decoded

    except Exception as e:
        print(" Error token:", e)
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado"
        )
