# Importar dependencias
from fastapi import Depends, FastAPI, HTTPException, Header, status
from fastapi.responses import HTMLResponse
from typing import Annotated, List
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import date, datetime
from auth import router, SECRET_KEY, ALGORITHM, verificar_rol
from emailprueba import send_email_admin, send_email_user
from users import profile_router
from jose import JWTError, jwt
from enum import Enum
from dotenv import load_dotenv
import psycopg2
import os 

# Cargar las variables de entorno desde el archivo .env
load_dotenv()
# Inicializar la aplicación FastAPI
app = FastAPI()
# Incluir el router de autenticación definido en auth.py
app.include_router(router)
app.include_router(profile_router)

# Permitir CORS para todas las orígenes (*)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Definir el modelo Pydantic para representar un ticket
class Ticket(BaseModel):
    user_id: int
    title: str
    description: str
    status: str
    priority: str

# Enums para definir los valores permitidos en los campos de tickets
class Status(str, Enum):
    abierto = "abierto"
    cerrado = "cerrado"

class Priority(str, Enum):
    baja = "baja"
    media = "media"
    alta = "alta"

# Modelo de entrada para crear un ticket con validaciones en los campos
class Ticket_create(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    status: Status
    priority: Priority
    category: str

class TicketSolution(BaseModel):
    id: int
    tech_id: int
    user_id: int
    title: str
    description: str
    status: Status
    priority: Priority
    title_solution: str
    date_solution: datetime
    tech_description: str
    
class TicketSolutionUpdate(BaseModel):
    id: int
    tech_id: int
    status: Status
    priority: Priority
    title_solution: str
    date_solution: datetime
    tech_description: str

# Modelo Pydantic para la respuesta de tickets con y sin solución
class TicketSolutionCount(BaseModel):
    null_tickets: int
    not_null_tickets: int

# Modelo Pydantic para la respuesta de la cantidad de tickets por usuario
class TicketCountPerUser(BaseModel):
    user_id: int
    ticket_count: int
    
class TicketStatistics(BaseModel):
    ticket_solution_count: TicketSolutionCount
    tickets_per_user: List[TicketCountPerUser]
    
class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    date_solution: date

"""
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    title VARCHAR(255),
    description TEXT,
    status CHAR(1),
    category VARCHAR(100),
    priority VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

DATABASE_URL = os.getenv('PG_APIKEY')
# Función para conectar a la base de datos PostgreSQL
def conectar_bd():
    conexion = psycopg2.connect(
        DATABASE_URL #"postgresql://user:password@localhost/mydatabase"
    )
    return conexion

# Función para cerrar la conexión a la base de datos
def cerrar_bd(conexion):
    conexion.close()

# ♣-♥-♦ CREATE - POST # Endpoint para crear un nuevo ticket
@app.post('/ticket/', response_model=Ticket, tags=["Tickets"], description="Create a new ticket")
def create_ticket(ticket: Ticket_create, token: Annotated[str | None, Header()] = None):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Decodificar el token JWT para obtener el rol del usuario
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    rol: str = payload.get("rol")
    user_id: str = payload.get("id")

    # 3 Verificar si el usuario existe    
    if token is None and rol != "admin":
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usted no se encuentra autorizado",
            headers={"auth": "Bearer"}, # se contesta como consideres el error
        )
    
    query = """
    INSERT INTO tickets (user_id, title, description, status, priority, category, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s,%s, NOW(), NULL) RETURNING *;
    """
    cursor.execute(query, (
        user_id, ticket.title, ticket.description, ticket.status, ticket.priority, ticket.category
    ))
    new_ticket = cursor.fetchone()
    conexion.commit()

    # Enviar notificación al administrador.
    send_email_admin("Horacio", "admin@gmail.com", "Horacio", "Un usuario ha creado un nuevo ticket.", "Gracias por la atencion, buen dia.")

    cursor.close()
    conexion.close()

    return dict(zip([desc[0] for desc in cursor.description], new_ticket))



# doc, url, sql, front
# ♣-♥-♦ READ - GET # Endpoint para obtener todos los tickets (solo usuarios autorizados)
@app.get('/ticket/', tags=["Tickets"])
def get_all_tickets(token: Annotated[str | None, Header()] = None):
    
    if token is None:
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usted no se encuentra autorizado",
            headers={"auth": "Bearer"}, # se contesta como consideres el error
        )
    # Decodificar el token JWT para obtener el rol del usuario
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    rol: str = payload.get("rol")
    user_id: str = payload.get("id")
    
    conexion = conectar_bd()
    cursor = conexion.cursor()
    sql = "SELECT * FROM tickets;"
    if rol == "user": 
        sql = f"SELECT * FROM tickets WHERE user_id = {user_id}"
    cursor.execute(sql)
    Ticket = cursor.fetchall() 
    cursor.close()
    conexion.close()
    return [dict(zip([desc[0] for desc in cursor.description], ticket)) for ticket in Ticket]
    

@app.get("/users/{user_id}/tickets-solutions", response_model=List[TicketSolution], tags=["Tickets"])
def get_user_tickets_solutions(user_id: int, token: str = Header(None)):
    # Verificar si el token fue proporcionado
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación no proporcionado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decodificar el token JWT para obtener el user_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_user_id: int = payload.get("id")
        if token_user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    
    # Verificar que el user_id en la ruta coincida con el del token
    if user_id != token_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permiso para consultar estos tickets")

    # Conectar a la base de datos y obtener los tickets del usuario
    conexion = conectar_bd()
    cursor = conexion.cursor()

    # Consulta SQL para obtener los tickets del usuario con la información del modelo TicketSolution
    query = """
    SELECT id, tech_id, user_id, title, description, status, priority, title_solution, date_solution, tech_description
    FROM tickets
    WHERE user_id = %s AND date_solution IS NOT NULL;  -- Asegurarse de obtener solo tickets con solución
    """
    cursor.execute(query, (user_id,))
    result = cursor.fetchall()

    cursor.close()
    conexion.close()

    # Formatear el resultado en una lista de diccionarios
    tickets_solutions = [
        {
            "id": row[0],
            "tech_id": row[1],
            "user_id": row[2],
            "title": row[3],
            "description": row[4],
            "status": row[5],
            "priority": row[6],
            "title_solution": row[7],
            "date_solution": row[8],
            "tech_description": row[9],
        }
        for row in result
    ]

    if not tickets_solutions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontraron tickets resueltos para este usuario")

    return tickets_solutions


# READ - GET by ID # Endpoint para obtener un ticket por su ID
@app.get('/ticket/{ticket_id}', response_model=Ticket, tags=["Tickets"])
def get_ticket(ticket_id: int):
    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # Consulta para obtener un ticket específico por ID
    cursor.execute("SELECT * FROM tickets WHERE id = %s;", (ticket_id,))
    ticketfin = cursor.fetchone()
    cursor.close()
    conexion.close()

    if ticketfin is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    
    print(ticketfin)
    return dict(zip([desc[0] for desc in cursor.description], ticketfin))


# UPDATE - PUT # Endpoint para actualizar un ticket
@app.put('/ticket/{ticket_id}', response_model=Ticket, tags=["Tickets"])
def update_ticket(ticket_id: int, ticket: Ticket_create, token: Annotated[str | None, Header()] = None):
    conexion = conectar_bd()
    cursor = conexion.cursor()

    # Decodificar el token JWT para obtener el rol del usuario
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    rol: str = payload.get("rol")
    user_id: str = payload.get("id")

    # 3 Verificar si el usuario existe    
    if token is None and rol != "admin":
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usted no se encuentra autorizado",
            headers={"auth": "Bearer"}, # se contesta como consideres el error
        )
    
    query = """
    UPDATE tickets
    SET user_id = %s, title = %s, description = %s, status = %s, priority = %s, updated_at = NOW()
    WHERE id = %s RETURNING *;
    """

    cursor.execute(query, (
        user_id, ticket.title, ticket.description, ticket.status, ticket.priority, ticket_id
    ))
    update_ticket = cursor.fetchone()
    conexion.commit()
    send_email_user("Gustavo", "usuario@gmail.com", "Gustavo", "Tu ticket a recibido una actualizacion.", "Gracias por la atencion, buen dia.")
    cursor.close()
    conexion.close()

    if update_ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return dict(zip([desc[0] for desc in cursor.description], update_ticket))

# DELETE - DELETE # Endpoint para eliminar un ticket
@app.delete('/ticket/{ticket_id}', response_model=dict, tags=["Tickets"])
def deleted_ticket(ticket_id: int, payload: dict = Depends(verificar_rol(["user"]))):
    conexion = conectar_bd()
    cursor = conexion.cursor()

    cursor.execute("DELETE FROM tickets WHERE id = %s RETURNING id;", (ticket_id,))
    deleted_ticket = cursor.fetchone()
    conexion.commit()
    cursor.close()
    conexion.close()

    if deleted_ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return {"message": "Ticket deleted successfully", "id": deleted_ticket[0]}

@app.put("/ticket/solution/{id}", response_model=TicketSolution, tags=["Tickets"])
def ticket_solution(id: int, ticket: TicketSolutionUpdate, payload: dict = Depends(verificar_rol(["admin"]))):
    conexion = conectar_bd()
    cursor = conexion.cursor()

    query = """
    UPDATE tickets
    SET tech_id = %s, status = %s, priority = %s, title_solution = %s, date_solution = %s, tech_description = %s,
    updated_at = NOW()
    WHERE id = %s 
    RETURNING *;
    """

    cursor.execute(query, (
        ticket.tech_id, ticket.status, ticket.priority, ticket.title_solution, ticket.date_solution, ticket.tech_description, id
        ))
    updated_ticket = cursor.fetchone()
    conexion.commit()
    send_email_user("Gustavo", "usuario@gmail.com", "Gustavo", "Tu ticket a recibido una actualizacion.", "Gracias por la atencion, buen dia.")
    cursor.close()
    conexion.close()

    if updated_ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return dict(zip([desc[0] for desc in cursor.description], updated_ticket))

@app.get("/ticket-statistics", response_model=TicketStatistics, tags=["Tickets"])
def get_ticket_statistics():
    conexion = conectar_bd()
    cursor = conexion.cursor()

    # Ejecutar la primera consulta (tickets con y sin solución)
    query1 = """
    SELECT
        COUNT(CASE WHEN date_solution IS NULL THEN 1 END) AS null_tickets,
        COUNT(CASE WHEN date_solution IS NOT NULL THEN 1 END) AS not_null_tickets
    FROM tickets;
    """
    cursor.execute(query1)
    result1 = cursor.fetchone()

    # Ejecutar la segunda consulta (cantidad de tickets por usuario)
    query2 = """
    SELECT user_id, COUNT(*) AS ticket_count
    FROM tickets
    GROUP BY user_id;
    """
    cursor.execute(query2)
    result2 = cursor.fetchall()

    cursor.close()
    conexion.close()

    # Procesar los resultados
    ticket_solution_count = {
        "null_tickets": result1[0],
        "not_null_tickets": result1[1]
    }

    tickets_per_user = [
        {"user_id": row[0], "ticket_count": row[1]} for row in result2
    ]

    # Retornar la respuesta combinada
    return {
        "ticket_solution_count": ticket_solution_count,
        "tickets_per_user": tickets_per_user
    }
    
@app.get("/users/{user_id}/solved-tickets", response_model=List[TicketResponse], tags=["Tickets"])
def get_solved_tickets(
    user_id: int, 
    token: str = Header(None)
):
    # Verificar si el token fue proporcionado
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación no proporcionado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decodificar el token JWT para obtener el user_id
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_user_id: int = payload.get("id")
        if token_user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    
    # Verificar que el user_id en la ruta coincida con el del token
    if user_id != token_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permiso para consultar estos tickets")

    # Conectar a la base de datos y obtener los tickets resueltos del usuario
    conexion = conectar_bd()
    cursor = conexion.cursor()

    # Consulta SQL para obtener los tickets del usuario con una solución proporcionada
    query = """
    SELECT id, title, description, date_solution, status, priority
    FROM tickets
    WHERE user_id = %s AND date_solution IS NOT NULL;
    """
    cursor.execute(query, (user_id,))
    result = cursor.fetchall()

    cursor.close()
    conexion.close()

    # Formatear el resultado en una lista de diccionarios
    tickets = [
        {"id": row[0], "title": row[1], "description": row[2], "date_solution": row[3], "status": row[4], "priority": row[5]}
        for row in result
    ]

    if not tickets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontraron tickets resueltos")

    return tickets