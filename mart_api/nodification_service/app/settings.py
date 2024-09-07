

from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

DATABASE_URL = config("DATABASE_URL", cast=Secret)
BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)
KAFKA_NODIFICATION_TOPIC = config("KAFKA_NODIFICATION_TOPIC", cast=str)
KAFKA_SIGNUP_TOPIC = config("KAFKA_SIGNUP_TOPIC", cast=str)
KAFKA_TOPIC = "auth-user"

# Fastapi-mail
MAIL_USERNAME= config("MAIL_USERNAME", cast=str)
MAIL_PASSWORD= config("MAIL_PASSWORD", cast=str)

KAFKA_PASSWORD_RESET_TOPIC = "password_reset"

# KAFKA_CONSUMER_GROUP_ID_FOR_NODIFICATION = config("KAFKA_CONSUMER_GROUP_ID_FOR_NODIFICATION", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_NOTIFICATION="Group_Id_Nodification"
TEST_DATABASE_URL = config("TEST_DATABASE_URL", cast=Secret)
