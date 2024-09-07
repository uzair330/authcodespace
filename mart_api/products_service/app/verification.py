from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# # def verify_token(token: str = Depends(oauth2_scheme)):
# #     try:
# #         payload = decode_access_token(token)
# #         username: str = payload.get("sub")
# #         if username is None:
# #             raise HTTPException(
# #                 status_code=status.HTTP_401_UNAUTHORIZED,
# #                 detail="Could not validate credentials",
# #                 headers={"WWW-Authenticate": "Bearer"},
# #             )
# #         return username
# #     except JWTError:
# #         raise HTTPException(
# #             status_code=status.HTTP_401_UNAUTHORIZED,
# #             detail="Could not validate credentials",
# #             headers={"WWW-Authenticate": "Bearer"},
# #         )

# from fastapi import FastAPI, Depends, HTTPException
# from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
# from jose import JWTError
# from app.utils import decode_access_token

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# def verify_token(token: str = Depends(oauth2_scheme)):
#     try:
#         payload = decode_access_token(token)
#         username: str = payload.get("sub")
#         if username is None:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Could not validate credentials",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )
#         return username
#     except JWTError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")  # Extracting the username
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload  # Return the entire payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
