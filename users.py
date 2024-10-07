from datetime import datetime
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException
import psycopg2
from pydantic import BaseModel
from auth import User, UserCreate, conectar_bd, get_current_user, get_password_hash


router = APIRouter()
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
""""CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    name VARCHAR(50),
    lastname VARCHAR(50),
    cellphone VARCHAR(15),
    created TIMESTAMP DEFAULT NOW(),
    updated TIMESTAMP DEFAULT NOW()
);"""

class ProfileCreate(BaseModel):
    user_id: int
    name: str
    lastname: str
    cellphone: str

class Profile(BaseModel):
    id: int
    user_id: int
    name: str
    lastname: str
    cellphone: str
    created: datetime
    updated: datetime
    
@profile_router.post("/profiles/", response_model=Profile, tags=["profiles"])
def create_profile(profile: ProfileCreate):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    query = """
    INSERT INTO profiles (user_id, name, lastname, cellphone, created, updated)
    VALUES (%s, %s, %s, %s, NOW(), NOW()) RETURNING *;
    """
    cursor.execute(query, (profile.user_id, profile.name, profile.lastname, profile.cellphone))
    new_profile = cursor.fetchone()
    conexion.commit()
    cursor.close()
    conexion.close()
    return dict(zip([desc[0] for desc in cursor.description], new_profile))

@profile_router.get("/profiles/{user_id}", response_model=Profile, tags=["profiles"])
def get_profile(user_id: int):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    query = "SELECT * FROM profiles WHERE user_id = %s;"
    cursor.execute(query, (user_id,))
    profile = cursor.fetchone()
    cursor.close()
    conexion.close()

    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return dict(zip([desc[0] for desc in cursor.description], profile))

@profile_router.put("/profiles/{user_id}", response_model=Profile, tags=["profiles"])
def update_profile(user_id: int, profile: ProfileCreate):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    query = """
    UPDATE profiles
    SET name = %s, lastname = %s, cellphone = %s, updated = NOW()
    WHERE user_id = %s RETURNING *;
    """
    cursor.execute(query, (profile.name, profile.lastname, profile.cellphone, user_id))
    updated_profile = cursor.fetchone()
    conexion.commit()
    cursor.close()
    conexion.close()

    if updated_profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return dict(zip([desc[0] for desc in cursor.description], updated_profile))

#-------------------------------PROFILES---------------------------->
