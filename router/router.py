from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from .festivalrouter import get_area, get_paginated_festivals
from sqlalchemy.orm import Session
from db.db import get_db

router = APIRouter()


templates = Jinja2Templates(directory="templates")


@router.get("/festival")
def festival(request: Request, db: Session = Depends(get_db)):
    areas = get_area(db=db)  # 비동기 함수는 await 키워드 사용
    festivals = get_paginated_festivals(page=1, limit=9, db=db)  # await 추가
    total_pages = festivals["total_pages"]
    return templates.TemplateResponse(
        "page1.html",
        {
            "request": request,
            "areas": areas,
            "festivals": festivals["data"],
            "page": festivals["page"], # 현재 페이지 번호
            "total_pages": total_pages,
        },
    )



@router.get("/aischedule")
def aiSchedule(request: Request):
    return templates.TemplateResponse("page2.html", {"request": request})


@router.get("/aichat")
def aiChat(request: Request):
    return templates.TemplateResponse("page3.html", {"request": request})


@router.get("/spot-details")
def spotDetails(request: Request):
    return templates.TemplateResponse("map.html", {"request": request})