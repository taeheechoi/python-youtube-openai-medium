import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import database, models, schemas

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_user_by_email(email: str, db: Session):
    return db.query(schemas.User).filter(schemas.User.email == email).first()


async def create_user(user: models.UserCreate, db: Session):
    user_obj = schemas.User(
        email=user.email, password=pwd_context.hash(
            user.password)
    )
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj


async def authenticate_user(email: str, password: str, db: Session):
    user = await get_user_by_email(email, db)

    if not user:
        return False
    if not user.verify_password(password):
        return False
    return user


async def create_token(user: schemas.User):
    user_obj = models.User.from_orm(user)

    token = jwt.encode(user_obj.dict(), JWT_SECRET_KEY)

    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user = db.get(schemas.User, payload["id"])
    except jwt.exceptions.DecodeError:
        raise HTTPException(
            status_code=401, detail="Invalid Email or Password"
        )

    return models.User.from_orm(user)
