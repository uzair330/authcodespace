# # #verification.py

# from fastapi import Depends, HTTPException, status
# from jose import JWTError
# from app.utils import decode_access_token
# from fastapi.security import OAuth2PasswordBearer

# # Reuse the OAuth2PasswordBearer dependency
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# def verify_token(token: str = Depends(oauth2_scheme)):
#     try:
#         payload = decode_access_token(token)
#         username: str = payload.get("sub")
#         email: str = payload.get("email")
#         if username is None or email is None:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Could not validate credentials",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )
#         return {"username": username, "email": email}
#     except JWTError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )


from fastapi import Depends, HTTPException, status
from jose import JWTError
from fastapi.security import OAuth2PasswordBearer
from app.utils import decode_access_token  # Ensure utils.py is in the same module

# Reuse the OAuth2PasswordBearer dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        email: str = payload.get("email")
        
        if username is None or email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"username": username, "email": email}
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
