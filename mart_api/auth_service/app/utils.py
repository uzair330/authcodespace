# # utils.py
# from jose import jwt
# from datetime import datetime, timedelta

# ALGORITHM = "HS256"
# SECRET_KEY = "This is my secure key"  # Store this securely in an environment variable

# def create_access_token(subject: str, email: str, expires_delta: timedelta) -> str:
#     expire = datetime.utcnow() + expires_delta
#     to_encode = {
#         "exp": expire,
#         "sub": subject,
#         "email": email
#     }
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# def decode_access_token(access_token: str):
#     decoded_jwt = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
#     return decoded_jwt


from jose import jwt, JWTError
from datetime import datetime, timedelta

ALGORITHM = "HS256"
SECRET_KEY = "This is my secure key"  # Move this to an environment variable for security (recommended)

def create_access_token(subject: str, email: str, expires_delta: timedelta) -> str:
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "exp": expire,
        "sub": subject,  # Typically the username or user ID
        "email": email
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(access_token: str):
    try:
        decoded_jwt = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_jwt
    except JWTError as e:
        raise JWTError(f"Invalid token: {e}")
