
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer
import smtplib
from email.message import EmailMessage
import asyncio
import json
import logging
from typing import AsyncGenerator
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional
from starlette.config import Config
from starlette.datastructures import Secret

# Load environment variables from the .env file
try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

# Settings for Kafka, email, and database
DATABASE_URL = config("DATABASE_URL", cast=Secret)
BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)
KAFKA_NODIFICATION_TOPIC = config("KAFKA_NODIFICATION_TOPIC", cast=str)
KAFKA_SIGNUP_TOPIC = config("KAFKA_SIGNUP_TOPIC", cast=str)
KAFKA_TOPIC = config("KAFKA_TOPIC", default="auth-user")
KAFKA_PRODUCT_TOPIC = config("KAFKA_PRODUCT_TOPIC", cast=str)

# FastAPI Mail configuration
MAIL_USERNAME = config("MAIL_USERNAME", cast=str)
MAIL_PASSWORD = config("MAIL_PASSWORD", cast=str)

# Consumer Group IDs
KAFKA_CONSUMER_GROUP_ID_FOR_NOTIFICATION = config("KAFKA_CONSUMER_GROUP_ID_FOR_NOTIFICATION", cast=str, default="Group_Id_Notification")
KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT = config("KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT", cast=str)

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
connection_string = str(DATABASE_URL).replace("postgresql", "postgresql+psycopg")
engine = create_engine(connection_string, connect_args={}, pool_recycle=300)

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = Field(default="")
    price: float
    

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Function to send email using smtplib
def send_email(subject: str, body: str, to_email: str):
    from_email = MAIL_USERNAME
    password = MAIL_PASSWORD
    
    # Create the email
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    # Send the email using SMTP_SSL
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:  # Use SMTP_SSL for secure connection
            server.login(from_email, password)
            server.send_message(msg)
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")

# Kafka Consumer for auth-user topic (notification service)
async def consume_auth_user_messages():
    while True:
        try:
            consumer = AIOKafkaConsumer(
                KAFKA_TOPIC,  # Topic to consume
                bootstrap_servers=BOOTSTRAP_SERVER,
                group_id=KAFKA_CONSUMER_GROUP_ID_FOR_NOTIFICATION,  # Consumer group ID
                auto_offset_reset='earliest'
            )
            await consumer.start()
            try:
                async for message in consumer:
                    data = json.loads(message.value.decode("utf-8"))
                    logger.info(f"Received data: {data}")

                    event_type = data.get("type")
                    email = data.get("email")
                    token = data.get("token")

                    if event_type == "signup":
                        if not email or not token:
                            logger.error("Missing email or token in signup data")
                            continue
                        
                        # Send the signup confirmation email
                        subject = "Welcome! Your Signup is Successful"
                        body = f"Hello, your account has been successfully created."
                        send_email(subject, body, email)

                    elif event_type == "password_reset":
                        if not email or not token:
                            logger.error("Missing email or token in password reset data")
                            continue
                        
                        # Send the password reset email
                        subject = "Password Reset Request"
                        body = (
                            f"Hi, to reset your password.\n"
                            f"Here is your access token (valid for 5 minutes):\n"
                            f"-------------------Access Token-----------------------\n"
                            f"{token}\n"
                            f"--------------------------------------------------------\n"
                            f"Note: Kindly paste this token and your new password in the reset password endpoint."
                        )
                        send_email(subject, body, email)

            finally:
                await consumer.stop()
        except Exception as e:
            logger.error(f"Error in Kafka consumer loop: {e}")
            await asyncio.sleep(5)

# Kafka Consumer for product management
async def consume_product_messages():
    while True:
        try:
            consumer = AIOKafkaConsumer(
                KAFKA_PRODUCT_TOPIC,  # Topic to consume
                bootstrap_servers=BOOTSTRAP_SERVER,
                group_id=KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT,
                auto_offset_reset='earliest'
            )
            await consumer.start()
            logger.info("Product Consumer started successfully")
            # 
            try:
                async for message in consumer:
                    data = json.loads(message.value.decode("utf-8"))
                    action = data.get("action")
                    product = data.get("product")
                    product_id = data.get("product_id")
                    email=data.get("email")

                    if action == "create":
                        subject = "Product Created"
                        body = f"A new product has been created: {product['name']}."
                        send_email(subject, body, email)

                    elif action == "update":
                        subject = "Product Updated"
                        body = f"Product ID {product_id} has been updated."
                        send_email(subject, body, email)

                    elif action == "delete":
                        subject = "Product Deleted"
                        body = f"Product ID {product_id} has been deleted."
                        send_email(subject, body, email)

                    
                    
            # 
            finally:
                await consumer.stop()
        except Exception as e:
            logger.error(f"Error in Kafka product consumer loop: {e}")
        finally:
            await asyncio.sleep(5)

# Lifespan function to manage both consumers
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    task1 = asyncio.create_task(consume_auth_user_messages())
    task2 = asyncio.create_task(consume_product_messages())
    try:
        yield
    finally:
        task1.cancel()
        task2.cancel()
        await task1
        await task2

# FastAPI app setup
app = FastAPI(lifespan=lifespan, title="Combined Notification and Product Service", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Nodification Service"}

