from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from api.map import kakaomap_router
from api.oath2 import oath_router
from router.festivalrouter import festival_router
from router.router import router
from router.tourspotrouter import tour_spot_router
from starlette.middleware.sessions import SessionMiddleware
from tourg import tourg
from db.models import Base
from db.db import engine
from db.mongodb import session_main
from pydantic import BaseModel
import os
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from util.scheduler import start_scheduler
import uuid

# # .env 파일 로드
# load_dotenv()

app = FastAPI()

# 스케줄러 시작
# start_scheduler()

# # 세션 관리 미들웨어 추가
app.add_middleware(SessionMiddleware, secret_key="asdafasfafgah2fa66161")
# 정적 파일 마운트
app.mount("/static", StaticFiles(directory="static"), name="static")

from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React 개발 서버 도메인
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# 요청 데이터 모델 정의
class ChatRequest(BaseModel):
    user_id: str
    user_message: str
    ai_response: str

@app.post("/api/db/mongodb_save")
async def mongodb_save(request: ChatRequest):
    """
    MongoDB에 사용자와 AI의 대화를 저장하는 API 엔드포인트.
    """
    try:
        # 요청 데이터 추출
        user_id = request.user_id
        user_message = request.user_message
        ai_response = request.ai_response

        # MongoDB 세션 시작 및 데이터 저장/조회
        await session_main(user_id, user_message, ai_response)

        return {"status": "success", "message": "Conversation saved successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save conversation: {e}")



@app.get("/auth/status")
async def check_login_status(request: Request):
    user = request.session.get("user")  # 세션에서 사용자 정보 가져오기
    if user:
        return {"logged_in": True, "user": user, "google_user_id": user["id"]}
    else:
        return {"logged_in": False, "uuid": str(uuid.uuid4())}


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 라우터 등록
app.include_router(kakaomap_router,  tags=["Kakao"])
app.include_router(oath_router,  tags=["Google"])
app.include_router(festival_router, tags=["Festival"])
app.include_router(router, tags=["WebPage"])
app.include_router(tour_spot_router, tags=["TourSpot"])
app.include_router(tourg)

# app.include_router(tourList.router,  tags=["Naver","tourApi"])



# FastAPI 애플리케이션 실행
if __name__ == '__main__':
    # 테이블 생성
    # Base.metadata.create_all(engine)
    import uvicorn
    # uvicorn.run(app, host="localhost", port=5000)
    uvicorn.run(app, host="0.0.0.0", port=5000)