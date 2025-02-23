from fastapi import APIRouter, Depends, Query, HTTPException
from db.models import Festival, AreaList
from db.db import get_db
from sqlalchemy.orm import Session
from db.schemas import FestivalSchema, PaginatedResponse
from typing import Dict, Any
import requests
from datetime import datetime
from db.db import SessionLocal

festival_router = APIRouter( )


# 페이징 처리 함수
def paginate(query: Query, page: int, limit: int) -> Dict[str, Any]:
    """
    페이징 처리 로직을 재사용 가능한 함수로 분리.
    
    :param query: SQLAlchemy Query 객체
    :param page: 현재 페이지 번호
    :param limit: 한 페이지에 표시할 항목 수
    :return: 페이징 처리된 결과와 메타데이터
    """
    offset = (page - 1) * limit
    total_count = query.count()
    total_pages = (total_count + limit - 1) // limit  # 전체 페이지 계산 (올림)
    items = query.offset(offset).limit(limit).all()
    
    return {
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "data": items,
    }

@festival_router.get("/api/festivals", response_model=PaginatedResponse)
def get_paginated_festivals(
    page: int = Query(1, ge=1),  # 페이지 번호 (기본값: 1)
    limit: int = Query(9, ge=1),  # 한 페이지에 표시할 항목 수 (기본값: 9)
    db: Session = Depends(get_db),
):
    """
    페이징 처리된 Festival 데이터를 반환하는 API.
    """
    
    query = db.query(Festival)  # 기본 쿼리
    result = paginate(query, page, limit)


    # SQLAlchemy 객체를 Pydantic 스키마로 변환
    result["data"] = [FestivalSchema.model_validate(festival) for festival in result["data"]]
    return result

@festival_router.get("/api/festivals/ongoing", response_model=PaginatedResponse)
async def get_ongoing_festivals(
    page: int = Query(1, ge=1),
    limit: int = Query(9, ge=1),
    db: Session = Depends(get_db),
):
    """
    진행 중인 축제를 반환하는 API.
    """
    
    current_date = datetime.now().strftime("%Y%m%d")
    query = db.query(Festival).filter(
        Festival.start_date <= current_date,
        Festival.end_date >= current_date,
    )
    result = paginate(query, page, limit)

    # SQLAlchemy 객체를 Pydantic 스키마로 변환
    result["data"] = [FestivalSchema.model_validate(festival) for festival in result["data"]]
    return result

@festival_router.get("/api/festivals/upcoming", response_model=PaginatedResponse)
async def get_upcoming_festivals(
    page: int = Query(1, ge=1),
    limit: int = Query(9, ge=1),
    db: Session = Depends(get_db),
):
    """
    예정된 축제를 반환하는 API.
    """
    
    current_date = datetime.now().strftime("%Y%m%d")
    query = db.query(Festival).filter(
        Festival.start_date > current_date,
    )
    result = paginate(query, page, limit)

    # SQLAlchemy 객체를 Pydantic 스키마로 변환
    result["data"] = [FestivalSchema.model_validate(festival) for festival in result["data"]]
    return result

@festival_router.get("/api/festivals/{area}", response_model=PaginatedResponse)
async def get_filter_area_festivals(
    area: str, # 경로 변수로 지역 이름을 받음
    page: int = Query(1, ge=1),
    limit: int = Query(9, ge=1),
    db: Session = Depends(get_db),
    time : str = Query(None),
):
    """
    지역 이름에 따라 필터를 걸어서 반환하는 API
    """
    
    query = db.query(Festival).filter(Festival.location.contains(area))  # 지역 이름으로 필터링
    current_date = datetime.now().strftime("%Y%m%d")
    if time == "ongoing":
        query = query.filter(
            Festival.start_date <= current_date,
            Festival.end_date >= current_date,
        )
    elif time == "upcoming":
        query = query.filter(Festival.start_date > current_date)

    result = paginate(query, page, limit)

    if not result["data"]:
        raise HTTPException(status_code=404, detail="No festivals found in this area.")

    # 데이터 변환
    result["data"] = [FestivalSchema.model_validate(festival) for festival in result["data"]]
    return result

@festival_router.get("/api/area")
def get_area(db: Session = Depends(get_db)):
    """
    지역 이름 가져오는 api
    """
    
    areas = db.query(AreaList).all()
    if not areas :
        raise HTTPException(status_code=404, detail="No areas found.")
    return areas

@festival_router.get("/api/festivals/filter/{area}", response_model=PaginatedResponse)
def get_filtered_festivals(
    area: str | None,
    time: str = Query(None, regex="^(ongoing|upcoming)$"),  # 기본값 None      
    page: int = Query(1, ge=1),
    limit: int = Query(9, ge=1),
    db: Session = Depends(get_db),
):
    """
    시기 및 지역 필터가 모두 적용된 축제를 반환하는 API.
    """
    

    query = db.query(Festival).filter(Festival.location.contains(area))  # 지역 이름으로 필터링
    

    # 시기 필터 적용
    current_date = datetime.now().strftime("%Y%m%d")
    if time == "ongoing":
        query = query.filter(
            Festival.start_date <= current_date,
            Festival.end_date >= current_date,
        )
    elif time == "upcoming":
        query = query.filter(Festival.start_date > current_date)

    # 기본 동작 (조건이 없을 경우 모든 데이터를 반환)
    if not time and not area:
        query = db.query(Festival)  # 모든 데이터를 반환하는 쿼리

     # 결과 처리
    result = paginate(query, page, limit)
    if not result["data"]:  # 데이터가 없을 경우 빈 배열 반환
        result["data"] = []

    # 데이터 변환
    result["data"] = [FestivalSchema.model_validate(festival) for festival in result["data"]]
    return result