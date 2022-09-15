import os
import uvicorn
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client import OAuthError
from fastapi import FastAPI
from fastapi import Request
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse
from starlette.responses import RedirectResponse
from fastapi_sso.sso.facebook import FacebookSSO


app = FastAPI()
config = Config(".env")

config_data = {'CLIENT_ID':config("CLIENT_ID"),
                'CLIENT_SECRET':config("CLIENT_SECRET")
                }

starlette_config = Config(environ=config_data)

oauth = OAuth(starlette_config)

oauth.register(
        name='facebook',
        server_metadata_url='https://facebook.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

# Set up the middleware to read the request session
SECRET_KEY = config("CLIENT_SECRET")
if SECRET_KEY is None:
    raise 'Missing SECRET_KEY'
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


@app.get('/')
def public(request: Request):
    return HTMLResponse('<a href=/login>Login through facebook account</a>')

    
@app.route('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth')  # This creates the url for our /auth endpoint
    return await oauth.facebook.authorize_redirect(request, redirect_uri)
    

@app.route('/auth')
async def auth(request: Request):
    try:
        access_token = await oauth.facebook.authorize_access_token(request)
        print(access_token)
    except OAuthError:
        return RedirectResponse(url='/')
    return RedirectResponse(url='/')




    
 




