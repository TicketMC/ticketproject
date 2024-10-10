# Importar dependencias
from enum import Enum
import psycopg2
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

# Cargar variables de entorno desde .env
import os
from dotenv import load_dotenv
load_dotenv()

# Cargar la clave secreta, el algoritmo JWT y otros parámetros desde las variables de entorno
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Modelos Pydantic para usuarios y tokens
class UserCreate(BaseModel):
    email: str
    password: str

class User(BaseModel):
    id: int
    email: str
    rol: str
    is_active: bool
    
# Definir los posibles valores del rol
class Role(str, Enum):
    user = "user"
    admin = "admin"    

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginData(BaseModel):
    email: str
    password: str

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

# Configurar el router de autenticación
router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

# ERROR Contexto de encriptación de contraseñas
# TODO : Revisar un error en el bcrypt porque dice que esta desactualizado y ver otra opción
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ♥-♣ OAuth2 para rutas protegidas
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="loggin")

# ♥-♣  Función para verificar la contraseña
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# ♥-♣  Función para generar el hash de la contraseña
def get_password_hash(password):
    return pwd_context.hash(password)

# ♥-♣ Función para crear un token JWT
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

# Funcion para registro de un nuevo usuario
@router.post("/register/", response_model=User)
def register_user(user: UserCreate):
    conexion = conectar_bd()
    cursor = conexion.cursor()

    # Encriptar la contraseña
    hashed_password = get_password_hash(user.password)

    # Insertar el nuevo usuario en la base de datos
    try:
        cursor.execute(
            "INSERT INTO users (email, password, rol) VALUES (%s, %s, 'user') RETURNING id, email, rol, is_active;",
            (user.email, hashed_password)
        )
        new_user = cursor.fetchone()
        conexion.commit()
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    finally:
        cerrar_bd(conexion)

    return {"id": new_user[0], "email": new_user[1], "rol":new_user[2], "is_active": new_user[3]}


# ♥-♣-♠-♦ Ruta de inicio de sesión generando un token
@router.post("/token", response_model=Token)
def login_for_access_token(auth: LoginData): #OAuth2PasswordRequestForm = Depends()): 

    conexion = conectar_bd()
    cursor = conexion.cursor()
    # 3 Verificar si el usuario existe
    cursor.execute("SELECT id, email, password, rol FROM users WHERE email = %s;", (auth.email,))
    user = cursor.fetchone()

    print(user)
    # TODO : Revisar la tabla de permissions e integrar el filtro de permisos por rol
    """cursor.execute("SELECT * FROM permission WHERE rol = %s;", (user[3],))
    permission = cursor.fetchall()
    print(user)"""
    
    cerrar_bd(conexion)
    # 4 verifica si el password esta encriptado y es coherente
    if not user or not verify_password(auth.password, user[2]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Crear un token de acceso
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "user", "rol": user[3], "email": user[1], "id": user[0], "permissions": "pepito clavo un clavito"}, expires_delta=access_token_expires #user[1]
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Estamos aqui para continuar un token
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"auth": "Bearer"}, # se contesta como consideres el error
        )
    except JWTError:
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"auth": "Bearer"},
        )
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, email, is_active, rol FROM users WHERE email = %s;", (email,))
    user = cursor.fetchone()
    cerrar_bd(conexion)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"id": user[0], "email": user[1], "is_active": user[2], "rol": user[3]}


@router.post("/login/", response_model=User)
def login(token: Token): 
    user = get_current_user(token.access_token)
    print(user["id"])
    return { "id": user["id"], "email": user["email"], "rol": user["rol"], "is_active": user["is_active"]}

@router.get("/manualphash")
def manualphash(password: str):
    hashed_password = get_password_hash(password)
    return {"hashed_password": hashed_password}


def verificar_rol(roles_permitidos: list):
    def rol_dependency(token: str = Header(None)):
        if token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No autorizado, token no proporcionado",
            )

        try:
            # Decodificar el token JWT
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            rol = payload.get("rol").lower()  # Asegúrate de que el rol esté en minúsculas
            user_id = payload.get("id")  # Cambiar 'user_id' por 'id' si es necesario

            # Depuración: Imprimir el rol para asegurar que se está leyendo correctamente
            print(f"Rol en el token: {rol}")

            # Convertir los roles permitidos a minúsculas también
            if rol not in [r.lower() for r in roles_permitidos]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para acceder a este recurso"
                )

            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="El token no contiene un user_id válido"
                )

            return payload

        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token inválido"
            )
    
    return rol_dependency


