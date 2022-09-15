import secrets
import pprint
from unittest import result 
# from pymongo import MongoClient

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()

security = HTTPBasic()

fake_data_base={"vinay":"vini@107","rajesh":"raj101"}

@app.get("/")
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username=credentials.username in fake_data_base
    correct_password = secrets.compare_digest(credentials.password, fake_data_base[credentials.username])
    if correct_username and correct_password:
        return "Welcome to page"
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Basic"},
        )


    

    



