
from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated
from app import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import FastAPI, Depends, HTTPException, Request, status
from typing import AsyncGenerator
from aiokafka import AIOKafkaProducer
import asyncio
import json
import logging
from app.utils import decode_access_token
from app.verification import verify_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductBase(SQLModel):
    name: str = Field(index=True)
    description: str = Field(default="")
    price: float

class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

connection_string = str(settings.DATABASE_URL).replace("postgresql", "postgresql+psycopg")

engine = create_engine(connection_string, connect_args={}, pool_recycle=300)

def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    print("Creating tables..")
    create_db_and_tables()
    yield

app = FastAPI(
    lifespan=lifespan,
    title="API end point for Consumer Service", 
    version="0.0.1",
    servers=[
        {
            "url": "https://redesigned-dollop-vxprjgj46p2467-8000.app.github.dev",  
            "description": "Development Server"
        }
    ]
)

def get_session():
    with Session(engine) as session:
        yield session

async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()



def get_current_user(token: str):
    # Decode the token
    token_payload = decode_access_token(token)
    
    # Log the token payload to inspect its structure
    print(f"Token Payload: {token_payload}")

    # Extract username and email from token payload
    username = token_payload.get("sub")
    email = token_payload.get("email")
    
    # Check if username and email are valid
    if not username or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    # Return the extracted user data
    return {"username": username, "email": email}


@app.get("/")
def read_root():
    return {"message": "Consumer Service"}


@app.post("/products/", response_model=Product, tags=["Create Product"])
async def create_product(
    product: ProductBase,
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)],
    token: str
):
    # Call get_current_user to extract user data from the token
    user_data = get_current_user(token)
    
    # Extract email and username from user_data
    email = user_data['email'] 
    username = user_data['username']  # Change from 'sub' to 'username'

    # Create product and save to the database
    product_data = Product(**product.dict())
    session.add(product_data)
    session.commit()
    session.refresh(product_data)

    # Prepare message for Kafka
    message = {
        "action": "create",
        "product": product.dict(),
        "username": username,
        "email": email
    }

    # Send message to Kafka
    await producer.send_and_wait(settings.KAFKA_PRODUCT_TOPIC, json.dumps(message).encode("utf-8"))

    return product_data


@app.put("/products/{product_id}", tags=["Update Product"])
async def update_product(
    product_id: int,
    updated_product: ProductBase,
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)],
     token: str
):
    # Call get_current_user to extract user data from the token
    user_data = get_current_user(token)
    
    # Extract email and username from user_data
    email = user_data['email'] 
    username = user_data['username']  # Change from 'sub' to 'username'

    
    message = {
        "action": "update",
        "product_id": product_id,
        "updated_data": updated_product.dict(exclude_unset=True),
        "username": username,
        "email": email
    }

    await producer.send_and_wait(settings.KAFKA_PRODUCT_TOPIC, json.dumps(message).encode("utf-8"))

    return {"status": "Update message sent to Kafka broker", "product_id": product_id}

@app.delete("/products/{product_id}", tags=["Delete Product"])
async def delete_product(
    product_id: int,
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)],
  token: str
):
    # Call get_current_user to extract user data from the token
    user_data = get_current_user(token)
    
    # Extract email and username from user_data
    email = user_data['email'] 
    username = user_data['username']  # Change from 'sub' to 'username'
    
    message = {
        "action": "delete",
        "product_id": product_id,
        "username": username,
        "email": email
    }

    await producer.send_and_wait(settings.KAFKA_PRODUCT_TOPIC, json.dumps(message).encode("utf-8"))

    return {"status": "Deletion message sent to Kafka broker", "product_id": product_id}

@app.get("/products/", response_model=list[Product])
def read_products(session: Annotated[Session, Depends(get_session)]):
        products = session.exec(select(Product)).all()
        return products
