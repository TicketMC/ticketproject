from datetime import datetime
from enum import Enum
import os
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Header, status
import psycopg2
from jose import jwt
from pydantic import BaseModel
from auth import ALGORITHM, SECRET_KEY, User, UserCreate, conectar_bd, get_current_user, get_password_hash

profile_router = APIRouter()

# Conexión a la base de datos PostgreSQL
DATABASE_URL = os.getenv('PG_APIKEY')
# Conectar a la base de datos
def conectar_bd():
    conexion = psycopg2.connect(
        DATABASE_URL #"postgresql://user:password@localhost/mydatabase"
    )
    return conexion

# Cerrar la conexión
def cerrar_bd(conexion):
    conexion.close()

#-------------------------------PROFILES---------------------------->

class ProfileUpdate(BaseModel):
    id: int
    names: str
    lastnames: str
    phone: str

class Rol (str, Enum):
    user = "user"
    admin = "admin"

class Profile(BaseModel):
    id: int
    email: str
    names: str
    lastnames: str
    rol: Rol
    phone: str
    created_at: datetime
    updated_at: datetime
    
# ♣-♥ Get users from roles
@profile_router.get('/users/', tags=["Profiles"])
def get_all_users(token: Annotated[str | None, Header()] = None):
    
    if token is None:
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usted no se encuentra autorizado",
            headers={"auth": "Bearer"}, # se contesta como consideres el error
        )
    # Decodificar el token JWT para obtener el rol del usuario
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    rol: str = payload.get("rol")
    id: str = payload.get("id")
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    sql = "SELECT * FROM users;"
    if rol == "user": 
        sql = f"SELECT * FROM users WHERE id = {id}"
    cursor.execute(sql)
    users = cursor.fetchall() 
    cursor.close()
    conexion.close()
    return [dict(zip([desc[0] for desc in cursor.description], user)) for user in users]

@profile_router.get("/profiles/{id}", response_model=Profile, tags=["Profiles"])
def get_profile(id: int):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    query = "SELECT * FROM users WHERE id = %s;"
    cursor.execute(query, (id,))
    profile = cursor.fetchone()
    cursor.close()
    conexion.close()

    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return dict(zip([desc[0] for desc in cursor.description], profile))

@profile_router.put("/profiles/{id}", response_model=Profile, tags=["Profiles"])
def update_profile(id: int, profile: ProfileUpdate):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    query = """
    UPDATE users
    SET names = %s, lastnames = %s, phone = %s, updated_at = NOW()
    WHERE id = %s RETURNING *;
    """
    cursor.execute(query, (profile.names, profile.lastnames, profile.phone, id))
    updated_profile = cursor.fetchone()
    conexion.commit()
    cursor.close()
    conexion.close()

    if updated_profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return dict(zip([desc[0] for desc in cursor.description], updated_profile))

#-------------------------------PROFILES---------------------------->
