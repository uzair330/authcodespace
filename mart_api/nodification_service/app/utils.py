# # utils.py
# from jose import jwt, JWTError
# from datetime import datetime, timedelta

# ALGORITHM = "HS256"
# SECRET_KEY = "This is my secure key"

# def create_access_token(subject: str , expires_delta: timedelta) -> str:
#     expire = datetime.utcnow() + expires_delta
#     to_encode = {"exp": expire, "sub": str(subject)}
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# def decode_access_token(access_token: str):
#     decoded_jwt = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
#     return decoded_jwt

# # from jose import jwt
# # from datetime import datetime, timedelta
# # from passlib.context import CryptContext

# # ALGORITHM = "HS256"
# # SECRET_KEY = "This is my secure key"  # Store this securely in an environment variable

# # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# # def create_access_token(subject: str, expires_delta: timedelta) -> str:
# #     expire = datetime.utcnow() + expires_delta
# #     to_encode = {"exp": expire, "sub": str(subject)}
# #     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
# #     return encoded_jwt

# # def decode_access_token(access_token: str):
# #     decoded_jwt = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
# #     return decoded_jwt

# # def hash_password(password: str) -> str:
# #     return pwd_context.hash(password)

# # def verify_password(plain_password: str, hashed_password: str) -> bool:
# #     return pwd_context.verify(plain_password, hashed_password)


from jose import jwt
from datetime import datetime, timedelta

ALGORITHM = "HS256"
SECRET_KEY = "This is my secure key"  # Store this securely in an environment variable

def create_access_token(subject: str, email: str, expires_delta: timedelta) -> str:
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "exp": expire,
        "sub": subject,
        "email": email
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(access_token: str):
    decoded_jwt = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    return decoded_jwt
