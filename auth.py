# auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
from dotenv import load_dotenv
from db_connection import get_session
from orm import Usuario
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
# Configuración JWT (deberías mover esto a .env)
SECRET_KEY =  os.getenv("SECRET_KEY")
ALGORITHM =  os.getenv("ALGORITHM","HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))  # 8 horas
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 480))  # 8 horas

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está definida en .env")
print(f"✅ SECRET_KEY cargada correctamente (primeros 10 caracteres): {SECRET_KEY[:10]}...")
# Configuración de bcrypt para hashear contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme para extraer el token del header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# =================== FUNCIONES DE CONTRASEÑA ===================

def get_password_hash(password: str) -> str:
    """Hashea una contraseña usando bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash"""
    return pwd_context.verify(plain_password, hashed_password)


# =================== FUNCIONES JWT ===================

def create_access_token(data: dict):
# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT"""
    to_encode = data.copy()
    print("ACCESS_TOKEN_EXPIRE_MINUTES:", ACCESS_TOKEN_EXPIRE_MINUTES)
    # if expires_delta:
    #     expire = datetime.utcnow() + expires_delta
    # else:
    #     expire = datetime.utcnow() + timedelta(minutes=15)
    expire = datetime.utcnow() + timedelta(minutes= ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Crea un refresh token"""
    to_encode = data.copy()
    
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


# =================== DEPENDENCIAS DE AUTENTICACIÓN ===================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> Usuario:
    """Obtiene el usuario actual desde el token JWT"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Buscar usuario en la base de datos
    result = await session.execute(
        select(Usuario).where(Usuario.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


def require_role(*allowed_roles: str):
    """Decorador para requerir roles específicos"""
    
    async def role_checker(current_user: Usuario = Depends(get_current_user)):
        if current_user.rol not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permisos. Se requiere rol: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker