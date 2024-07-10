import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from authlib.jose import jwt, JWTClaims
from authlib.jose.errors import JoseError
from dotenv import load_dotenv
import time

load_dotenv()

class Auth:
    def __init__(self):
        self.public_key_path = os.getenv("PUBLIC_KEY_PATH")
        self.testing = os.getenv("TESTING", "false").lower() == "true"
        
        with open(self.public_key_path, 'rb') as f:
            self.public_key = f.read()

    async def decode_token(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())):
        if self.testing:
            return True
        
        try:
            claims = jwt.decode(credentials.credentials, self.public_key)
            JWTClaims(claims)
            return claims
        except JoseError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

auth_handler = Auth()