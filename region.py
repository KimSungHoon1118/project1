from db.db import SessionLocal
from db.models import Schedule, PickUpList, Tourlist, TourSpot
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session
import requests
from env import get_env_vars
from fpdf import FPDF
import os
from rich import print as rprint
from sqlalchemy.dialects.postgresql import insert

### api로 지역+ 도시 정보 받아서 해당 지역, 도시로 관광지 api로 받아와서 상세소개랑 같이
### 지역 a + 해당 지역 관광지~ , 지역 b 해당 지역 관광지~ 형식으로
### pdf 만들어서 임베딩 모델로 벡터화 하려고 만든 py

env_vars = get_env_vars()
SERVICE_KEY = env_vars["SERVICE_KEY"]

# 세션 의존성 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_all_regions(db: Session = Depends(get_db)):
    return db.query(PickUpList).all()

def get_region(db: Session = Depends(get_db), region_code: int = 0):
    """
    특정 지역 코드를 기반으로 데이터를 조회
    :param db: 데이터베이스 세션
    :param region_code: 지역 코드 (기본값: 0)
    :return: 해당 지역 코드에 해당하는 데이터 쿼리 결과
    """
    return db.query(PickUpList).filter(PickUpList.id == region_code).all()

def get_tourist_spots_by_location(latitude, longitude, radius=10000):
    """
    위치기반 관광지 조회 API 호출
    :param latitude: 위도
    :param longitude: 경도
    :param radius: 검색 반경 (단위: 미터)
    :return: 관광지 목록
    """
    url = "http://apis.data.go.kr/B551011/KorService1/locationBasedList1"
    params = {
        "serviceKey": SERVICE_KEY,
        "numOfRows": 35,
        "pageNo": 1,
        "MobileOS": "ETC",
        "MobileApp": "AppTest",
        "arrange": "O",
        "mapX": longitude,
        "mapY": latitude,
        "radius": radius,
        "contentTypeId": 12,
        "_type": "json"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return items
    else:
        print(f"API 호출 실패: {response.status_code}")
        return []

def fetch_tourist_spot_overview(contentid):
    """
    공통정보조회 API를 사용하여 특정 관광지의 개요를 가져옴
    :param content_id: 관광지 contentid
    :return: 관광지 개요 (overview)
    """
    # API 키와 기본 URL
    url = "http://apis.data.go.kr/B551011/KorService1/detailCommon1"
    params = {
        "serviceKey": SERVICE_KEY,
        "numOfRows": 1,
        "pageNo": 1,
        "MobileOS": "ETC",
        "MobileApp": "AppTest",
        "contentId": contentid,
        "contentTypeId": 12,
        "overviewYN": "Y",
        "_type": "json"
    }

    try:
        
        response = requests.get(url, params=params)
        
        # rprint(f"Response Text: {response.text}")  # 응답 내용 확인
        response.raise_for_status()  # HTTP 오류가 발생하면 예외 처리
        data = response.json()
        
        # item 필드가 리스트로 반환되는 경우 처리
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, list) and len(items) > 0:
            overview = items[0].get("overview", "개요 정보 없음")  # 리스트의 첫 번째 요소에서 overview 추출
        else:
            overview = "개요 정보 없음"

        return overview
    except requests.exceptions.RequestException as e:
        print(f"API 호출 오류: {e}")
        return "개요 정보 가져오기 실패"


def fetch_tourist_spot_keyword(keyword):
    """
    키워드조회 API를 사용하여 특정 관광지의 정보를 가져옴
    :param content_id: 관광지 contentid
    :return: 관광지 개요 (overview)
    """
    # API 키와 기본 URL
    url = "http://apis.data.go.kr/B551011/KorService1/searchKeyword1"
    params = {
        "serviceKey": SERVICE_KEY,
        "numOfRows": 10,
        "pageNo": 1,
        "MobileOS": "ETC",
        "MobileApp": "AppTest",
        "listYN": "Y",
        "keyword": keyword,
        "contentTypeId": 12,
        "arrange": "O",
        "overviewYN": "Y",
        "_type": "json"
    }

    try:
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            return items
        else:
            print(f"API 호출 실패: {response.status_code}")
            return []
    
    except requests.exceptions.RequestException as e:
        print(f"API 호출 오류: {e}")
        return "개요 정보 가져오기 실패"


def group_tourist_spots_by_region(regions, db):
    """
    지역별로 관광지 정보를 그룹화하며, 개요를 포함
    :param regions: 지역 정보 리스트
    :return: 지역별 관광지 그룹
    """
    region_list = ["서울", "부산", "대구","춘천", "충주"]
    grouped_data = {}
    for region in regions:
        if region in region_list:
            continue
        spots = get_tourist_spots_by_location(region.latitude, region.longitude)  # 기존 함수 호출
        # rprint(spots)
        enriched_spots = []
        for spot in spots:
            content_id = spot.get("contentid")  # 관광지의 contentid
            if content_id:
                overview = fetch_tourist_spot_overview(content_id)  # 공통정보조회 API 호출
                spot["overview"] = overview  # 개요 추가
            
            # 필터링: 주소가 지역 이름을 포함하는 경우만 추가
            address = spot.get("addr1", "")
            if region.area_name_kor in address:
                enriched_spots.append(spot)
            # rprint(enriched_spots)
        
        grouped_data[region.area_name_kor] = enriched_spots
    
    return grouped_data

class PDFGenerator(FPDF):
    def header(self):
        self.set_font("NotoSans", size=12)
        self.cell(0, 10, "지역별 관광지 정보", align="C", ln=True)
        self.ln(10)

    def add_region_data(self, region_name, spots):
        """
        지역별 관광지 데이터를 PDF에 추가
        :param region_name: 지역 이름
        :param spots: 관광지 리스트
        """
        self.set_font("NotoSans", size=10)

        # 새 페이지 추가 (필요 시)
        if self.get_y() > 260:  # 페이지 하단(260mm)에 도달한 경우 새 페이지 추가
            self.add_page()

        self.cell(0, 10, f"지역: {region_name}", ln=True)
        self.ln(5)

        self.set_font("NotoSans", size=9)
        for spot in spots:
            title = spot.get("title", "N/A")
            address = spot.get("addr1", "주소 정보 없음")
            image = spot.get("firstimage", "이미지 없음")
            overview = spot.get("overview", "개요 정보 없음")  # 개요 추가

            # 새 페이지 추가 (필요 시)
            if self.get_y() > 260:
                self.add_page()

            self.cell(0, 10, f"- {title}", ln=True)
            self.cell(0, 10, f"  주소: {address}", ln=True)
            self.cell(0, 10, f"  이미지: {image}", ln=True)
            # 개요 출력 (자동 줄바꿈 처리)
            self.multi_cell(0, 10, f"  개요: {overview}")
            self.ln(5)

def setup_korean_font(pdf):
    font_path = "./fonts/static/NotoSansKR-Regular.ttf"  # 폰트 파일 경로
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Error: 폰트 파일을 찾을 수 없습니다. 경로: {font_path}")

    pdf.add_font("NotoSans", "", font_path, uni=True)
    pdf.set_font("NotoSans", size=12)
    print("NotoSans 폰트가 성공적으로 등록되었습니다.")

# PDF 생성 및 저장
def generate_pdf(grouped_data):
    pdf = PDFGenerator()
    setup_korean_font(pdf)  # 폰트를 먼저 설정
    pdf.add_page()          # 이후에 페이지 추가

    print("Adding text to PDF:")
    for region_name, spots in grouped_data.items():
        print(f"Region: {region_name}")
        print(f"Spot: {spots}")
        pdf.add_region_data(region_name, spots)
    
    pdf.output("tourist_spots.pdf", "F")
    print("PDF 저장 완료!")

def group_tourist_spots_by_region_one(regions, db):
    """
    지역별로 관광지 정보를 그룹화하며, 개요를 포함
    :param regions: 지역 정보 리스트
    :return: 지역별 관광지 그룹
    """
    grouped_data = {}
    for region in regions:
        spots = get_tourist_spots_by_location(region.latitude, region.longitude)  # 기존 함수 호출
    # rprint(spots)
    enriched_spots = []
    for spot in spots:
        # content_id = spot.get("contentid")  # 관광지의 contentid
        # if content_id:
        #     overview = fetch_tourist_spot_overview(content_id)  # 공통정보조회 API 호출
        #     spot["overview"] = overview  # 개요 추가
        
        # 필터링: 주소가 지역 이름을 포함하는 경우만 추가
        address = spot.get("addr1", "")
        if region.area_name_kor in address:
            enriched_spots.append(spot)
        # rprint(enriched_spots)
    
    grouped_data[region.area_name_kor] = enriched_spots
    
    return grouped_data

def save_tourlist_to_db(grouped_data, session):
    """
    그룹화된 관광지 데이터를 Tourlist 테이블에 저장
    :param grouped_data: 지역별 그룹화된 관광지 데이터
    :param session: SQLAlchemy 세션
    """
    for region, spots in grouped_data.items():
        for spot in spots:
            stmt = insert(Tourlist).values(
                location=region,
                name=spot.get("title", "알 수 없음"),
                address=spot.get("addr1", "알 수 없음"),
                image_url=spot.get("firstimage", None),
                description=spot.get("overview", None),
            ).on_conflict_do_update(
                index_elements=["id"],  # 고유 제약 조건 컬럼
                set_={
                    "description": spot.get("overview", None),  # 업데이트할 필드
                    "image_url": spot.get("firstimage", None),
                    "address": spot.get("addr1", "알 수 없음"),
                }
            )
            session.execute(stmt)

    session.commit()
    print("관광지 데이터가 Tourlist 테이블에 저장되었습니다.")


regions_list = ["서울", "부산", "대구","춘천","강릉","공주","전주","경주","통영","제주특별자치도", "충주"]

def create_predefined_schedules(session, regions_list):
    """
    주어진 지역 리스트를 기반으로 Schedule 데이터를 생성합니다.
    :param session: SQLAlchemy 세션
    :param regions_list: 지역 이름 리스트
    """
    for region in regions_list:
        schedules = [
            {"location": region, "duration": "당일치기", "day": 1, "description": f"{region} 당일치기 여행 일정"},
            {"location": region, "duration": "1박2일", "day": 1, "description": f"{region} 1박2일 첫째 날"},
            {"location": region, "duration": "1박2일", "day": 2, "description": f"{region} 1박2일 둘째 날"},
            {"location": region, "duration": "2박3일", "day": 1, "description": f"{region} 2박3일 첫째 날"},
            {"location": region, "duration": "2박3일", "day": 2, "description": f"{region} 2박3일 둘째 날"},
            {"location": region, "duration": "2박3일", "day": 3, "description": f"{region} 2박3일 셋째 날"},
        ]

        for schedule_data in schedules:
            schedule = Schedule(**schedule_data)
            session.add(schedule)

    session.commit()
    print("모든 지역에 대한 기본 Schedule 데이터가 저장되었습니다.")


def update_spot_images_and_record_unmatched(tourlist_data, tourspot_data, db):
    """
    Tourlist와 TourSpot 데이터를 비교하여 업데이트 및 기록
    :param tourlist_data: Tourlist 테이블에서 가져온 데이터 (query로 가져옴)
    :param tourspot_data: TourSpot 테이블에서 가져온 데이터 (query로 가져옴)
    :param db: SQLAlchemy 세션
    :return: 이름이 다른 TourSpot 항목 리스트
    """
    unmatched_spots = []  # 이름이 일치하지 않는 TourSpot 항목 저장

    # Tourlist 데이터를 이름 기준으로 빠르게 조회할 수 있도록 딕셔너리 생성
    tourlist_dict = {entry.name.strip().lower(): entry for entry in tourlist_data}

    for spot in tourspot_data:
        spot_name = spot.name.strip().lower()
        if spot_name in tourlist_dict:
            # 이름이 같은 경우 image_url 업데이트
            tourlist_entry = tourlist_dict[spot_name]
            if tourlist_entry.image_url:  # 유효한 이미지 URL인지 확인
                spot.image_url = tourlist_entry.image_url
                db.flush()  # 세션에 즉시 반영
        else:
            # 이름이 일치하지 않는 경우 리스트에 추가
            unmatched_spots.append({
                "name": spot.name,
                "address": spot.address,
                "description": spot.description,
                "latitude": spot.latitude,
                "longitude": spot.longitude,
            })

    db.commit()  # 최종 커밋
    return unmatched_spots


if __name__ == "__main__":
    db = SessionLocal()

    # SQLAlchemy 세션을 사용하여 데이터 쿼리
    tourlist_data = db.query(Tourlist).all()
    tourspot_data = db.query(TourSpot).all()

    # 함수 호출
    unmatched_spots = update_spot_images_and_record_unmatched(tourlist_data, tourspot_data, db)

    # 이름이 일치하지 않는 TourSpot 항목 출력
    print("이름이 일치하지 않는 TourSpot 항목:")
    for spot in unmatched_spots:
        print(spot)

    # # 지역 정보 가져오기
    # regions = get_all_regions(db)

    # # 지역별 관광지 데이터 그룹화
    # grouped_data = group_tourist_spots_by_region(regions, db)
    # # Tourlist 테이블에 저장
    # save_tourlist_to_db(grouped_data, db)

    # # # PDF 생성
    # generate_pdf(grouped_data)
    # create_predefined_schedules(db, regions_list) # 2번째 지역 여행코스용 목록
    db.close()