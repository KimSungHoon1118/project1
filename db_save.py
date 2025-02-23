from db.db import SessionLocal
from api.data_fetcher import fetch_and_save_regions ,fetch_and_save_regions_eng, process_all_locations 
from api.data_fetcher import fetch_and_save_all_cities, process_city_locations_with_area, get_tour
from fastapi import FastAPI, Query, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session
from db.festivalc import save_festivals_to_db, crawl_festivals;
import logging


app = FastAPI()

logging.basicConfig(level=logging.INFO, filename="scheduler.log", filemode="a",
                    format="%(asctime)s - %(levelname)s - %(message)s")

# 세션 의존성 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def job_fetch_regions():
    db = SessionLocal()
    try:
        fetch_and_save_regions(db)
    finally:
        db.close()

def job_fetch_regions_eng():
    db = SessionLocal()
    try:
        fetch_and_save_regions_eng(db)
    finally:
        db.close()


def job_fetch_all_cities():
    db = SessionLocal()
    try:
        # 모든 지역코드 가져와서 해당하는 지역의 도시코드 전부 넣기
        fetch_and_save_all_cities(db)
    finally:
        db.close()

def job_fetch_festival():
    logging.info("Starting festival data fetch...")
    db = SessionLocal()
    try:
        # 크롤링 데이터 가져오기
        festival_data = crawl_festivals()
        if festival_data:
            save_festivals_to_db(festival_data, db)
            logging.info("Festival data successfully saved.")
        else:
            logging.warning("No festival data collected.")
    except Exception as e:
        logging.error(f"Error fetching festival data: {e}")        
    finally:
        db.close()
        logging.info("Database connection closed.")

# def job_fetch_get_tour():
#     db = SessionLocal()
#     try:
#         #문체부 추천 여행지 정보 저장
#         get_tour(db)
#     finally:
#         db.close()

# @app.post("/update-all-locations")
# def update_all_locations(db: Session = Depends(get_db)):
#     db = SessionLocal()
#     """
#     모든 지역/도시의 좌표를 업데이트합니다.
#     """
#     process_all_locations(db)
#     return {"message": "All locations have been processed."}

# @app.post("/update-all-locations-city")
# def update_all_locations(db: Session = Depends(get_db)):
#     db = SessionLocal()
#     """
#     모든 지역/도시의 좌표를 업데이트합니다.
#     """
#     process_city_locations_with_area(db)
#     return {"message": "All locations have been processed."}

# @app.get("/get")
# def festival(region: Optional[str] = Query(None), date: Optional[str] = Query(None)):
#     """
#     축제/행사 정보를 반환하는 API 엔드포인트.
#     Args:
#         region (str): 지역 필터 (예: "서울").
#         date (str): 조회할 날짜 (YYYYMMDD 형식).

#     Returns:
#         list[dict]: 축제/행사 정보 리스트.
#     """
#     try:
#         events = fetch_event_data(region=region, date=date)
        
#         if not events:
#             return {"message": "No events found for the given filters.", "data": []}
        
#         return {"message": "Success", "data": events}
    
#     except ValueError as ve:
#         raise HTTPException(status_code=400, detail=f"Invalid input: {str(ve)}")
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# FastAPI 애플리케이션 실행
if __name__ == '__main__':
    # 테이블 생성
    import uvicorn
    # job_fetch_regions()  #지역 저장
    # job_fetch_regions_eng() # 지역 영문 이름저장
    # job_fetch_all_cities() # 시군구 도시 정보 저장
    job_fetch_festival() # 축제 정보 크롤링해서 저장
    uvicorn.run(app, host="localhost", port=5000)