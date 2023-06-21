import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException

import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import database, models, schemas

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def get_user_by_email(email: str, db: Session):
    return db.query(models.User).filter(models.User.email == email).first()


async def create_user(user: schemas.UserCreate, db: Session):
    user_obj = models.User(email=user.email, password=pwd_context.hash(user.password))
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

async def create_token(user: models.User):
    user_obj = schemas.User.from_orm(user)
    token = jwt.encode(user_obj.dict(), JWT_SECRET_KEY)
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(token: str, db: Session):

    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

    user = db.get(models.User, payload["id"])
    return schemas.User.from_orm(user)




# async def delete_user_by_email(email: str, db: Session):
#     user = db.query(models.User).filter(models.User.email == email).first()
#     if user:
#         db.delete(user)
#         db.commit()









