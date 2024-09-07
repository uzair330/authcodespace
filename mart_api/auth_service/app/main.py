# # main (auth)
from contextlib import asynccontextmanager
from typing import Optional, Annotated, List, AsyncGenerator
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from aiokafka import AIOKafkaProducer
import json
import logging
from sqlalchemy.exc import SQLAlchemyError
from datetime import timedelta
from jose import JWTError
from passlib.context import CryptContext
from app import settings
from app.utils import create_access_token, decode_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User models
class UserBase(SQLModel):
    username: str
    phone: str

class User_Auth(SQLModel):
    email: str
    password: str

class UserModel(User_Auth, UserBase):
    pass

class User(UserModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)

# Response model
class UserRead(SQLModel):
    user_id: int
    username: str
    email: str
    phone: str

class ResetPasswordRequest(SQLModel):
    token: str
    new_password: str

class Config:
    orm_mode = True

# Database configuration
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)
engine = create_engine(connection_string, connect_args={}, pool_recycle=300)

def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

# Lifespan function to manage app lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    print("Creating tables..")
    create_db_and_tables()
    yield

app = FastAPI(
    lifespan=lifespan,
    title="API end point for User Service",
    version="0.0.1",
    servers=[
        # {"url": "http://localhost:8005", "description": "Local Server"}
        # ,
        {"url": "https://redesigned-dollop-vxprjgj46p2467-8005.app.github.dev", "description": "Development Server"}
    ]
)

# Dependency to get DB session
def get_session():
    with Session(engine) as session:
        yield session

@app.get("/")
def read_root():
    return {"message": "User Auth Service"}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Kafka Producer as a dependency
async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

def authenticate_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends],
    session: Annotated[Session, Depends(get_session)]
):
    statement = select(User).where(User.username == form_data.username)
    user_in_db = session.exec(statement).first()

    if not user_in_db or not pwd_context.verify(form_data.password, user_in_db.password):
        return None

    return user_in_db

@app.post("/create_user/", response_model=UserRead)
async def create_user(
    user: UserModel,
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
) -> UserRead:
    existing_user = session.exec(
        select(User).where(
            (User.email == user.email) | (User.phone == user.phone)
        )
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400, detail="A user with this email or phone already exists."
        )

    # Hash the password
    user.password = pwd_context.hash(user.password)

    # Create the user instance
    created_user = User(**user.dict())

    try:
        # Add and commit the new user
        session.add(created_user)
        session.commit()
        session.refresh(created_user)

        # Generate an access token
        access_token_expires = timedelta(minutes=15)
        access_token = create_access_token(
            subject=created_user.username, 
            email=created_user.email,
            expires_delta=access_token_expires
        )

        # Prepare and send Kafka message
        message = {
            "type": "signup",
            "token": access_token,
            "email": created_user.email
        }

        await producer.send_and_wait(
            settings.KAFKA_TOPIC, json.dumps(message).encode("utf-8")
        )

    except SQLAlchemyError:
        session.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")

    # Return the response using UserRead model
    return UserRead.from_orm(created_user)

@app.post("/forgot-password")
async def forgot_password(
    email: str, 
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
):
    # Find user by email
    user_in_db = session.exec(select(User).where(User.email == email)).first()

    if not user_in_db:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate password reset token (valid for a longer period, e.g., 1 hour)
    access_token_expires = timedelta(minutes=5)
    reset_token = create_access_token(
        subject=user_in_db.username, 
        email=user_in_db.email,
        expires_delta=access_token_expires
    )

    # Password reset link (this could be a frontend URL where the user can reset the password)
    reset_link = f"https://your-app.com/reset-password?token={reset_token}"

    # Prepare the message for Kafka
    message = {
        "type": "password_reset",
        "token": reset_token,
        "reset_link": reset_link,
        "email": email
    }

    await producer.send_and_wait(
        settings.KAFKA_TOPIC, json.dumps(message).encode("utf-8")
    )

    return {"message": "Password reset instructions sent to your email"}

@app.post("/login")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)]
):
    user = authenticate_user(form_data, session)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=15)

    access_token = create_access_token(
        subject=user.username,
        email=user.email,
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": access_token_expires.total_seconds()
    }

@app.get("/get-access-token")
def get_access_token(user_name: str, email: str):
    access_token_expires = timedelta(minutes=15)
    access_token = create_access_token(
        subject=user_name, 
        email=email,
        expires_delta=access_token_expires
    )

    return {"access_token": access_token}

@app.get("/decode_token")
def decoding_token(access_token: str, token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        decoded_token_data = decode_access_token(access_token)
        return {"decoded_token": decoded_token_data}
    except JWTError as e:
        return {"error": str(e)}

@app.get("/users/all", response_model=List[UserRead])
def get_all_users(session: Annotated[Session, Depends(get_session)]):
    users = session.exec(select(User)).all()
    return [UserRead.from_orm(user) for user in users]

@app.get("/users/me", response_model=UserRead)
def read_users_me(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)]
):
    user_token_data = decode_access_token(token)
    username = user_token_data["sub"]
    email = user_token_data["email"]

    # Use `username` to find the user in the database, email is also available if needed
    user_in_db = session.exec(
        select(User).where(User.username == username)
    ).first()

    if not user_in_db:
        raise HTTPException(status_code=404, detail="User not found")

    return UserRead.from_orm(user_in_db)

# Password update endpoint
@app.put("/update-password/")
async def update_password(
    token: Annotated[str, Depends(oauth2_scheme)], # Default argument (Depends) comes first
    current_password: Annotated[str, Body(...)],   # Non-default argument
    new_password: Annotated[str, Body(...)],       # Non-default argument
    session: Annotated[Session, Depends(get_session)]
):
    user_token_data = decode_access_token(token)
    username = user_token_data["sub"]

    # Fetch the user by username
    user_in_db = session.exec(select(User).where(User.username == username)).first()

    if not user_in_db:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify the current password
    if not pwd_context.verify(current_password, user_in_db.password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    # Update the user's password
    user_in_db.password = pwd_context.hash(new_password)
    session.add(user_in_db)
    session.commit()

    return {"message": "Password updated successfully"}

@app.post("/reset-password/")
async def reset_password(
    reset_request: ResetPasswordRequest,  # Now using SQLModel
    session: Annotated[Session, Depends(get_session)]
):
    try:
        # Decode the reset token
        token_data = decode_access_token(reset_request.token)
        username = token_data["sub"]
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Find the user in the database
    user_in_db = session.exec(select(User).where(User.username == username)).first()
    if not user_in_db:
        raise HTTPException(status_code=404, detail="User not found")

    # Hash the new password and update it in the database
    user_in_db.password = pwd_context.hash(reset_request.new_password)
    session.add(user_in_db)
    session.commit()

    return {"message": "Password has been reset successfully"}


