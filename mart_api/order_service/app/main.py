# main.py
from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated,List
from app import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select, Sequence, Relationship
from fastapi import FastAPI, Depends, HTTPException,status
from typing import AsyncGenerator
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
import json
import logging


# only needed for psycopg 3 - replace postgresql
# with postgresql+psycopg in settings.DATABASE_URL
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)


# recycle connections after 5 minutes
# to correspond with the compute scale down
engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)

#engine = create_engine(
#    connection_string, connect_args={"sslmode": "require"}, pool_recycle=300
#)


def create_db_and_tables()->None:
    SQLModel.metadata.create_all(engine)

# The first part of the function, before the yield, will
# be executed before the application starts.
# https://fastapi.tiangolo.com/advanced/events/#lifespan-function
# loop = asyncio.get_event_loop()
@asynccontextmanager
async def lifespan(app: FastAPI)-> AsyncGenerator[None, None]:
    print("Creating tables..")
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, title="API end point for Order Service", 
    version="0.0.1",
    servers=[
        {
            "url": "https://0.0.0.0:8003", # ADD NGROK URL Here Before Creating GPT Action
            "description": "Development Server"
        }
        # ,
        #  {
        #     "url": "https://equilibrium-stylish-son-random.trycloudflare.com", # ADD NGROK URL Here Before Creating GPT Action
        #     "description": "Development Server1"
        # }
        ]
        )

def get_session():
    with Session(engine) as session:
        yield session


# Define the models using SQLModel

# SQLModel models for the database
class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = Field(default="")
    price: float
    inventory: int
    order_items: List["OrderItem"] = Relationship(back_populates="product")

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int
    
    product: Optional[Product] = Relationship(back_populates="order_items")
    order: Optional["Order"] = Relationship(back_populates="items")

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int
    items: List[OrderItem] = Relationship(back_populates="order")

# Create tables if they don't exist
SQLModel.metadata.create_all(engine)

# Dependency to get the DB session
def get_session():
    with Session(engine) as session:
        yield session

# Pydantic models for request validation
class OrderItemCreate(SQLModel):
    product_id: int
    quantity: int

class OrderCreate(SQLModel):
    customer_id: int
    items: List[OrderItemCreate]

# Endpoint to create an order
@app.post("/orders/")
def create_order(order: OrderCreate, session: Session = Depends(get_session)):
    # Validate that all products exist and have enough inventory
    for item in order.items:
        product = session.exec(select(Product).where(Product.id == item.product_id)).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {item.product_id} does not exist"
            )
        if product.inventory < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with id {item.product_id} does not have enough inventory"
            )

    # Create the order
    new_order = Order(customer_id=order.customer_id)
    session.add(new_order)
    session.commit()
    session.refresh(new_order)

    # Add order items and update inventory
    for item in order.items:
        order_item = OrderItem(order_id=new_order.id, product_id=item.product_id, quantity=item.quantity)
        product.inventory -= item.quantity  # Update product inventory
        session.add(order_item)
    
    session.commit()
    session.refresh(new_order)
    return new_order

# Endpoint to get details of an order by ID
@app.get("/orders/{order_id}")
def get_order(order_id: int, session: Session = Depends(get_session)):
    order = session.exec(select(Order).where(Order.id == order_id)).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order

# Endpoint to list all orders
@app.get("/orders/")
def list_orders(session: Session = Depends(get_session)):
    orders = session.exec(select(Order)).all()
    return orders

# Endpoint to delete an order by ID

@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, session: Session = Depends(get_session)):
    # Fetch the order to ensure it exists
    order = session.exec(select(Order).where(Order.id == order_id)).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    # Update the inventory for each product in the order
    for order_item in order.items:
        product = session.exec(select(Product).where(Product.id == order_item.product_id)).first()
        if product:
            product.inventory += order_item.quantity
            session.add(product)  # Update the product inventory
    
    # Delete the order and associated order items
    session.delete(order)
    session.commit()

    return None  # Returning None results in a 204 No Content response
