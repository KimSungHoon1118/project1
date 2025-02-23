from fastapi import APIRouter, Depends, Query, HTTPException
from db.models import TourSpot, Schedule, Tourlist, PickUpList
from db.db import SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from itertools import groupby
from typing import List
from db.schemas import TourSpotDayTrip, TourSpotDetail, TourListDetail

tour_spot_router = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@tour_spot_router.get("/api/tour/spot/{duration}", response_model=List[TourSpotDayTrip])
def get_schedules_grouped_by_location(duration: str , db : Session = Depends(get_db)):
    schedules = (
        db.query(Schedule)
        .options(joinedload(Schedule.spots))
        .filter(Schedule.duration == duration)
        .order_by(Schedule.location)  # 그룹화를 위해 정렬
        .all()
    )

    # 데이터를 Pydantic 스키마로 직렬화
    day_trip_schedules = [
        TourSpotDayTrip(
            id=schedule.id,
            location=schedule.location,
            duration=schedule.duration,
            day=schedule.day,
            description=schedule.description,
            spots=[
                TourSpotDetail(
                    id=spot.id,
                    name=spot.name,
                    address=spot.address,
                    image_url=spot.image_url,
                    description=spot.description,
                    latitude=spot.latitude,
                    longitude=spot.longitude,
                )
                for spot in schedule.spots
            ],
        )
        for schedule in schedules
    ]

    return day_trip_schedules

@tour_spot_router.get("/api/tour/spot", response_model=List[TourSpotDayTrip])
def get_schedules_grouped_by_location_and_duration(
    location: str, duration: str, db: Session = Depends(get_db)
):
    # 데이터베이스에서 지역과 기간으로 필터링
    schedules = (
        db.query(Schedule)
        .options(joinedload(Schedule.spots))
        .filter(Schedule.location == location, Schedule.duration == duration)
        .order_by(Schedule.day)  # 일차(day) 순서로 정렬
        .all()
    )

    # 데이터를 Pydantic 스키마로 직렬화
    day_trip_schedules = [
        TourSpotDayTrip(
            id=schedule.id,
            location=schedule.location,
            duration=schedule.duration,
            day=schedule.day,
            description=schedule.description,
            spots=[
                TourSpotDetail(
                    id=spot.id,
                    name=spot.name,
                    address=spot.address,
                    image_url=spot.image_url,
                    description=spot.description,
                    latitude=spot.latitude,
                    longitude=spot.longitude,
                )
                for spot in schedule.spots
            ],
        )
        for schedule in schedules
    ]

    return day_trip_schedules

@tour_spot_router.get("/api/tour/detail", response_model=List[TourListDetail])
def get_schedules_grouped_by_location_and_duration_detail(
    name: str, db: Session = Depends(get_db)
):
    # 데이터베이스에서 지역과 기간으로 필터링
    schedules = (
        db.query(Tourlist)
        .filter(Tourlist.name == name)
        .all()
    )

    # 데이터를 Pydantic 스키마로 직렬화
    day_trip_schedules = [
        TourListDetail(
            id=schedule.id,
            name=schedule.name,
            address=schedule.address,
            image_url=schedule.image_url,
            description=schedule.description,            
        )
        for schedule in schedules
    ]

    return day_trip_schedules