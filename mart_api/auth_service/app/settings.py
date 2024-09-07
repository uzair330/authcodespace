# settings
from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

DATABASE_URL = config("DATABASE_URL", cast=Secret)

TEST_DATABASE_URL = config("TEST_DATABASE_URL", cast=Secret)


BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)
# KAFKA_TOPIC = config("KAFKA_TOPIC", cast=str)
KAFKA_TOPIC ="auth-user"
KAFKA_CONSUMER_GROUP_ID_FOR_SIGNUP = config("KAFKA_CONSUMER_GROUP_ID_FOR_SIGNUP", cast=str)


KAFKA_PASSWORD_RESET_TOPIC = "password_reset"
# # Kafka Bootstrap Server
# BOOTSTRAP_SERVER=broker:19092

# #TOPIC For user_signup

# KAFKA_TOPIC=signup
# #CONSIUMER GRPOUP For signup
# KAFKA_CONSUMER_GROUP_ID_FOR_SIGNUP="signup"