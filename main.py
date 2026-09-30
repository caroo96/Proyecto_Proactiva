from unittest import result
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db_connection import Base, engine, get_session  # db_connection.py ya migrado a SQLAlchemy
from orm import Usuario, Caso                          # tus modelos ORM (SQLAlchemy)
from schemas import UsuarioIn, UsuarioOut
from datetime import timedelta
from auth import ( get_password_hash, verify_password, create_access_token, create_refresh_token,
    get_current_user,
    require_role,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    ALGORITHM
)

from routers import casos, competencias, programas, entregas, evaluaciones, rubricas, carga_caso
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from routers import casos, competencias, programas, entregas, evaluaciones, rubricas, carga_caso

class RefreshRequest(BaseModel):
    refresh_token: str


app = FastAPI(
    title="API Simulador de Casos",
    version="2.0.0",
)

origins = [
    "http://localhost:5173",
    "https://polite-meadow-044aeca10.7.azurestaticapps.net"
]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"],  # o ["http://localhost:5173"]
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(casos.router)
app.include_router(competencias.router)
app.include_router(programas.router)
app.include_router(entregas.router)
app.include_router(evaluaciones.router)
app.include_router(rubricas.router)
app.include_router(carga_caso.router)

@app.on_event("startup")
async def on_startup():
    # Si la BD ya existe con tu ER_Proactiva, puedes comentar estas dos líneas.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/", tags=["Sistema"])
async def root():
    """Endpoint raíz"""
    return {
        "status": "ok",
        "message": "API funcionando correctamente",
        "version": "1.0.0",
        
    }

@app.post("/token", tags=["Autenticación"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    print("form_data.username", form_data.username)
    """Endpoint de login que devuelve token JWT"""
    # Buscar usuario por nombre_usuario
    result = await session.execute(
        select(Usuario).where(Usuario.correo_electronico == form_data.username)
    )
    # user = result.scalar_one_or_none()
    user = result.scalars().first()
    
    # Verificar usuario y contraseña
    if not user or not verify_password(form_data.password, user.contrasena_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear token JWT
    access_token = create_access_token(
        data={"sub": str(user.id)},
        # expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "tiempo_expiracion": ACCESS_TOKEN_EXPIRE_MINUTES,
        "tiempo_expiracion_refresh": REFRESH_TOKEN_EXPIRE_DAYS,
        "rol": user.rol,
    }


@app.post("/refresh", tags=["Autenticación"])
async def refresh_token(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session)
):
    """Genera un nuevo access token usando refresh token"""

    try:
        payload = jwt.decode(
            request.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=401,
                detail="Token inválido"
            )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Token inválido"
            )

        # Verificar que el usuario exista
        result = await session.execute(
            select(Usuario).where(Usuario.id == int(user_id))
        )

        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Usuario no encontrado"
            )

        new_access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Refresh token inválido"
        )


@app.get("/me", response_model=UsuarioOut, tags=["Autenticación"])
async def read_me(
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener usuario actual autenticado"""
    return current_user

# === CRUD de ejemplo (Usuario) ===

@app.post("/usuarios/", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED, tags=["Usuarios"])
async def create_usuario(
    payload: UsuarioIn,
    session: AsyncSession = Depends(get_session)
):
    """Crear nuevo usuario"""
    try:
        # Verificar si ya existe
        result = await session.execute(
            select(Usuario).where(
                (Usuario.nombre_usuario == payload.nombre_usuario) |
                (Usuario.correo_electronico == payload.correo_electronico)
            )
        )
        # existing_user = result.scalar_one_or_none()
        
        usuario_existente = result.scalars().first()
        
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario o correo ya existe"
            )
        
        password_bytes = payload.contrasena.encode('utf-8')
        if len(password_bytes) > 72:
            password_to_hash = password_bytes[:72].decode('utf-8', errors='ignore')
        else:
            password_to_hash = payload.contrasena
            
        # Crear Usuario
        user = Usuario(
            nombre_usuario=payload.nombre_usuario,
            correo_electronico=payload.correo_electronico,
            contrasena_hash=get_password_hash(payload.contrasena),
            rol=payload.rol
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        print(f"❌ Error detallado: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear usuario: {str(e)}"
        )

@app.get("/usuarios/{user_id}", response_model=UsuarioOut, tags=["Usuarios"])
async def get_usuario(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener usuario por ID"""
    result = await session.execute(
        select(Usuario).where(Usuario.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return user


@app.get("/estudiantes/", response_model=list[UsuarioOut])
async def get_estudiantes(
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("profesor"))
):
    # print("current_user",current_user)
    """obtener todos los estudiantes si eres pofesor"""
    result = await session.execute(
        select(Usuario).where(Usuario.rol == "estudiante")
    )

    estudiantes = result.scalars().all()
    return estudiantes