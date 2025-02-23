from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from env import get_env_vars  # 종속성 가져오기
import os
from sqlalchemy.orm import Session
from db.models import User
from db.db import get_db
#Oath2 구글 로그인

# HTTP 허용 (테스트 환경)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# load_dotenv()

oath_router = APIRouter()

GOOGLE_CLIENT_ID = get_env_vars("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = get_env_vars("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = get_env_vars("REDIRECT_URI")



# Google OAuth 2.0 Flow 설정
client_secrets = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uris": [REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

# @router.get("/")
# async def index(request: Request):
#     if "credentials" in request.session:
#         credentials = Credentials(**request.session["credentials"])
#         service = build("oauth2", "v2", credentials=credentials)
#         user_info = service.userinfo().get().execute()
#         return {"message": f"Hello, {user_info['name']} ({user_info['email']})"}
#     return {"message": "Welcome! Please log in with Google.", "login_url": "/auth/login"}

@oath_router.get("/auth/login")
async def login(request: Request):
    flow = Flow.from_client_config(
        client_secrets,
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        redirect_uri=REDIRECT_URI,
    )
    auth_url, state = flow.authorization_url(prompt="consent")
    # 애플리케이션 상태에 상태 저장
    request.app.state.oauth_state = state
    return RedirectResponse(auth_url)

# @router.get("/login/oauth2/code/google")
# async def callback(request: Request):
#     # 애플리케이션 상태에서 상태 가져오기
#     state = request.app.state.oauth_state

#     flow = Flow.from_client_config(
#         client_secrets,
#         scopes=[
#             "openid",
#             "https://www.googleapis.com/auth/userinfo.profile",
#             "https://www.googleapis.com/auth/userinfo.email",
#         ],
#         state=state,
#         redirect_uri=REDIRECT_URI,
#     )

#     # 인증 응답 URL에서 토큰 가져오기
#     flow.fetch_token(authorization_response=str(request.url))
#     credentials = flow.credentials

#     # 세션에 저장
#     request.session["credentials"] = {
#         "token": credentials.token,
#         "refresh_token": credentials.refresh_token,
#         "token_uri": credentials.token_uri,
#         "client_id": credentials.client_id,
#         "client_secret": credentials.client_secret,
#         "scopes": credentials.scopes,
#     }

#     return RedirectResponse("/")

# @router.get("/login/oauth2/code/google")
@oath_router.get("/auth/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    state = request.app.state.oauth_state
    flow = Flow.from_client_config(
        client_secrets,
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        state=state,
        redirect_uri=REDIRECT_URI,
    )

    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    # Google API를 사용해 사용자 정보 가져오기
    service = build("oauth2", "v2", credentials=credentials)
    user_info = service.userinfo().get().execute()

    # 이메일로 사용자 확인
    email = user_info["email"]
    name = user_info.get("name", "Unknown")

    # 데이터베이스에서 사용자 확인
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # 신규 사용자 등록
        user = User(
            email=email,
            name=name,            
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 세션에 사용자 정보 저장
    request.session["user"] = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
    }

    return RedirectResponse("/")  # 로그인 후 리다이렉트할 페이지

@oath_router.get("/auth/logout")
async def logout(request: Request):
    # if "user" in request.session:
    #     del request.session["user"]
    # if "credentials" in request.session:
    #     del request.session["credentials"]
    # return {"message": "Logged out successfully"}, RedirectResponse("/")
    
    # 세션에서 사용자 정보 삭제
    request.session.clear()  # 세션 초기화

    # 로그아웃 후 홈페이지("/")로 리디렉트
    return RedirectResponse(url="/", status_code=302)

def refresh_token(request: Request):
    credentials = Credentials(**request.session["credentials"])
    if credentials.expired:
        credentials.refresh(Request())
        request.session["credentials"] = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

def get_current_user(request: Request):
    if "user" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return request.session["user"]