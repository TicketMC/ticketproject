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
    fullname: str
    phone: str

class Rol (str, Enum):
    user = "user"
    admin = "admin"

class Profile(BaseModel):
    id: int
    email: str
    fullname: str
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
            headers={"auth": "Bearer"},
        )
    
    # Decodificar el token JWT para obtener el rol del usuario
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    rol: str = payload.get("rol")
    user_id: int = payload.get("id")

    conexion = conectar_bd()
    cursor = conexion.cursor()

    if rol == "admin":
        # Si el usuario es admin, obtenemos todos los usuarios
        sql = "SELECT * FROM users;"
        cursor.execute(sql)
    elif rol == "user":
        # Si es un usuario regular, solo puede obtener su propio perfil
        sql = "SELECT * FROM users WHERE id = %s;"
        cursor.execute(sql, (user_id,))
    else:
        cursor.close()
        conexion.close()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permisos para acceder a esta información")

    users = cursor.fetchall()
    cursor.close()
    conexion.close()

    if not users:
        raise HTTPException(status_code=404, detail="No se encontraron usuarios")

    return [dict(zip([desc[0] for desc in cursor.description], user)) for user in users]

@profile_router.get("/profiles/{id}", response_model=Profile, tags=["Profiles"])
def get_profile(id: int, token: Annotated[str | None, Header()] = None):
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usted no se encuentra autorizado",
            headers={"auth": "Bearer"},
        )

    # Decodificar el token JWT para obtener el rol del usuario
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    
    rol: str = payload.get("rol")
    user_id: int = payload.get("id")

    if rol == "user" and user_id != id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permiso para ver este perfil")
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    query = "SELECT * FROM users WHERE id = %s;"
    cursor.execute(query, (id,))
    profile = cursor.fetchone()
    cursor.close()
    conexion.close()

    if profile is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    
    return dict(zip([desc[0] for desc in cursor.description], profile))


@profile_router.put("/profiles/{id}", response_model=Profile, tags=["Profiles"])
def update_profile(id: int, profile: ProfileUpdate, token: Annotated[str | None, Header()] = None):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    query = """
    UPDATE users
    SET fullname = %s, phone = %s, updated_at = NOW()
    WHERE id = %s RETURNING *;
    """
    cursor.execute(query, (profile.fullname, profile.phone, id))
    updated_profile = cursor.fetchone()
    conexion.commit()
    cursor.close()
    conexion.close()

    if updated_profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return dict(zip([desc[0] for desc in cursor.description], updated_profile))

#-------------------------------PROFILES---------------------------->