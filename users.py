import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException
import psycopg2
from pydantic import BaseModel
from auth import User, UserCreate, conectar_bd, get_current_user, get_password_hash
from main import Status

router = APIRouter()

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

# Modelo Pydantic para actualizar usuarios
class UserUpdate(BaseModel):
    email: str
    password: str
    is_active: bool

# Obtener todos los usuarios (Solo Admin)
@router.get('/users/', response_model=List[User])
def get_all_users(current_user: User = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=Status.HTTP_403_FORBIDDEN, detail="Not authorized")

    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, email, role, is_active FROM users")
    users = cursor.fetchall()
    cerrar_bd(conexion)

    return [{"id": u[0], "email": u[1], "role": u[2], "is_active": u[3]} for u in users]

# Obtener un usuario por ID (Admin o el mismo usuario)
@router.get('/users/{user_id}', response_model=User)
def get_user(user_id: int, current_user: User = Depends(get_current_user)):
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=Status.HTTP_403_FORBIDDEN, detail="Not authorized")

    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, email, role, is_active FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cerrar_bd(conexion)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"id": user[0], "email": user[1], "role": user[2], "is_active": user[3]}

# Actualizar un usuario (Admin o el mismo usuario)
@router.put('/users/{user_id}', response_model=User)
def update_user(user_id: int, user: UserUpdate, current_user: User = Depends(get_current_user)):
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=Status.HTTP_403_FORBIDDEN, detail="Not authorized")

    conexion = conectar_bd()
    cursor = conexion.cursor()
    hashed_password = get_password_hash(user.password)
    cursor.execute("""
        UPDATE users SET email = %s, password = %s, is_active = %s WHERE id = %s RETURNING id, email, role, is_active;
    """, (user.email, hashed_password, user.is_active, user_id))
    updated_user = cursor.fetchone()
    conexion.commit()
    cerrar_bd(conexion)

    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"id": updated_user[0], "email": updated_user[1], "role": updated_user[2], "is_active": updated_user[3]}

# Eliminar un usuario (Solo Admin)
@router.delete('/users/{user_id}', response_model=dict)
def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=Status.HTTP_403_FORBIDDEN, detail="Not authorized")

    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s RETURNING id;", (user_id,))
    deleted_user = cursor.fetchone()
    conexion.commit()
    cerrar_bd(conexion)

    if deleted_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully", "id": deleted_user[0]}

