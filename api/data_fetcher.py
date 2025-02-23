import requests, json
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse
from db.models import AreaList, CityList, Tourlist
from sqlalchemy.orm import Session
from env import get_env_vars # 종속성 가져오기
import os, urllib.request, platform
import urllib.parse
from urllib.parse import quote
# from requests.adapters import HTTPAdapter
# from urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class TLSAdapter(HTTPAdapter):
    def __init__(self, ssl_version=None, **kwargs):
        self.ssl_version = ssl_version
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_version'] = self.ssl_version
        return PoolManager(*args, **kwargs)
# class SSLAdapter(HTTPAdapter):
#     """TLS 버전 강제 설정"""
#     def __init__(self, ssl_context=None, **kwargs):
#         self.ssl_context = ssl_context or ssl.create_default_context()
#         super().__init__(**kwargs)

#     def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
#         kwargs["ssl_context"] = self.ssl_context
#         return PoolManager(num_pools=connections, maxsize=maxsize, block=block, **kwargs)

# # SSLContext 생성 및 TLS 버전 지정
# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

# # SSLAdapter에 SSLContext를 전달
# adapter = SSLAdapter(ssl_context=ssl_context)
# session = requests.Session()
# session.mount("https://", adapter)

app = FastAPI()

env_vars = get_env_vars()
SERVICE_KEY = env_vars["SERVICE_KEY"]
REST_API_KEY = env_vars["REST_API_KEY"]

# 한글 지역 코드, 이름 저장
def fetch_and_save_regions(db: Session):
    """
    API에서 국문 지역 정보를 가져와 국문 이름과 지역 코드를 저장합니다.
    """
    url = "http://apis.data.go.kr/B551011/KorService1/areaCode1"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "AppTest",
        "_type": "json",
        "numOfRows": 20,
        "pageNo": 1,
    }

    response = requests.get(url, params=params)
    data = response.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
    for region in data:
        area = db.query(AreaList).filter(AreaList.areacode_id == region["code"]).first()
        if not area:
            new_area = AreaList(areacode_id=region["code"], area_name_kor=region["name"])
            db.add(new_area)
    db.commit()

# 영문 지역 코드, 이름 저장
def fetch_and_save_regions_eng(db: Session):
    """
    API에서 영문 지역 정보를 가져와 이미 저장된 국문 지역 정보에 영문 이름을 업데이트합니다.
    """
    url = "http://apis.data.go.kr/B551011/EngService1/areaCode1"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "AppTest",
        "_type": "json",
        "numOfRows": 20,
        "pageNo": 1,
    }

    response = requests.get(url, params=params)
    data = response.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
    for region in data:
        # 지역 코드를 기준으로 기존 데이터를 조회
        area = db.query(AreaList).filter(AreaList.areacode_id == region["code"]).first()
        if area:
            # 영문 이름을 업데이트
            area.area_name_eng = region["name"]
        else:
            # 국문 정보가 없는 경우 새로 추가
            new_area = AreaList(
                areacode_id=region["code"],
                area_name_kor=None,  # 국문 정보가 없는 상태
                area_name_eng=region["name"]
            )
            db.add(new_area)
    db.commit()

def get_all_area_codes(db: Session) -> list[int]:
    """
    데이터베이스에서 모든 지역 코드를 가져옵니다.
    """
    return [area.areacode_id for area in db.query(AreaList.areacode_id).all()]

# 한글 도시 코드, 이름 저장
def fetch_and_save_cities(region_code: int, db: Session):
    """
    지역 코드에 해당하는 국문 도시 데이터를 가져와 데이터베이스에 업데이트합니다.
    """
    url = "http://apis.data.go.kr/B551011/KorService1/areaCode1"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "App",
        "_type": "json",
        "numOfRows": 35,
        "pageNo": 1,
        "areaCode": region_code,
    }

    response = requests.get(url, params=params)
    data = response.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
    for city in data:
        area = db.query(AreaList).filter(AreaList.areacode_id == region_code).first()
        if area:
            city_entry = db.query(CityList).filter(
                CityList.area_areacode_id == area.areacode_id,
                CityList.sigungucode_id == city["code"]
            ).first()
            if not city_entry:
                new_city = CityList(
                    area_areacode_id=area.areacode_id,
                    sigungucode_id=city["code"],
                    city_name_kor=city["name"]
                )
                db.add(new_city)
    db.commit()

# 영문 도시 코드, 이름 저장
def fetch_and_save_cities_eng(region_code: int, db: Session):
    """
    지역 코드에 해당하는 영문 도시 데이터를 가져와 데이터베이스에 업데이트합니다.
    """
    url = "http://apis.data.go.kr/B551011/EngService1/areaCode1"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "App",
        "_type": "json",
        "numOfRows": 35,
        "pageNo": 1,
        "areaCode": region_code,
    }

    response = requests.get(url, params=params)
    data = response.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
    for city in data:
        # 해당 지역 코드로 AreaList 조회
        area = db.query(AreaList).filter(AreaList.areacode_id == region_code).first()
        if area:
            # 해당 시군구 코드로 CityList 조회
            city_entry = db.query(CityList).filter(
                CityList.area_areacode_id == area.areacode_id,
                CityList.sigungucode_id == city["code"]
            ).first()

            if city_entry:
                # 이미 존재하는 경우 영문 이름 업데이트
                city_entry.city_name_eng = city["name"]
            else:
                # 존재하지 않는 경우 새 데이터 추가
                new_city = CityList(
                    area_id=area.id,
                    sigungucode_id=city["code"],
                    city_name_eng=city["name"]
                )
                db.add(new_city)
    db.commit()

def fetch_and_save_all_cities(db: Session):
    """
    데이터베이스에서 지역 코드를 가져와 해당 지역에 대한 도시 데이터를 저장합니다.
    """
    # 모든 지역 코드 가져오기
    area_codes = get_all_area_codes(db)

    for region_code in area_codes:
        # 한글 도시 데이터 저장
        fetch_and_save_cities(region_code, db)

        # 영문 도시 데이터 저장
        fetch_and_save_cities_eng(region_code, db)


# 이미지 검색 엔드포인트
@app.get("/api/img_search")
def search_img(query: str = Query(...)):
   
    # KA 헤더 설정
    NAVER_CLIENT_ID = env_vars["NAVER_CLIENT_ID"]
    NAVER_CLIENT_SECRET = env_vars["NAVER_CLIENT_SECRET"]    
    
    params = urllib.parse.quote(query)
    print(params)
    url = "http://openapi.naver.com/v1/search/image?query=" + params
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id",NAVER_CLIENT_ID)
    request.add_header("X-Naver-Client-Secret",NAVER_CLIENT_SECRET)
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode == 200:
        # 데이터를 JSON으로 변환
        response_body = response.read()
        data = json.loads(response_body)        
        
        if 'items' in data and data['items']:
                # 첫 번째 검색 결과의 이미지 반환
                img = data["items"][0]  # 딕셔너리에서 'items' 키 접근
                print(img)
                return {
                    "thumbnail_url": img.get("thumbnail"),
                    "image_url": img.get("link"),
                }                  
        else:
            return JSONResponse(content={"message": "Location not found"}, status_code=404)
    else:        
        return JSONResponse(content={"message": "Failed to connect to Naver API"}, status_code=500)


# 지역 이름을 기준으로 lat, lng 가져오기
def get_location_from_kakao(query: str ):
    url = f"https://dapi.kakao.com/v2/local/search/keyword.json"
    REST_API_KEY = env_vars["REST_API_KEY"]
    # KA 헤더 설정
    os_name = platform.system()  # 운영체제 이름 (예: 'Windows', 'Linux')
    ka_header = f"sdk/1.0 os/{os_name} lang/ko app/mapApi"
    # print(f"KA Header: {ka_header}")  # 디버깅 용도
    headers = {
        "Authorization": f"KakaoAK {REST_API_KEY}",
        "KA": ka_header ,
    }
    params = {"query": query}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['documents']:
            location = data['documents'][0]
            return {
                "name": location["place_name"],
                "lat": float(location["y"]),
                "lng": float(location["x"]),
            }
    return None


def get_unmapped_locations(db: Session):
    """
    위도와 경도가 없는 지역이나 도시 데이터를 가져옵니다.
    """
    return db.query(AreaList).filter(AreaList.latitude.is_(None), AreaList.longitude.is_(None)).all()

def update_location_coordinates(db: Session, location_name: str, lat: float, lng: float):
    """
    특정 지역/도시의 위도와 경도를 업데이트합니다.
    """
    area = db.query(AreaList).filter(AreaList.area_name_kor == location_name).first()
    if area:
        area.latitude = lat
        area.longitude = lng        
        print(f"Updated: {location_name} -> Lat: {lat}, Lng: {lng}")
    else:
        print(f"Location not found in DB: {location_name}")

def process_all_locations(db: Session):
    """
    DB에서 모든 지역/도시 이름을 가져와 카카오맵 API를 통해 좌표를 업데이트합니다.
    """
    locations = get_unmapped_locations(db)
    for location in locations:
        kakao_response = get_location_from_kakao(query=location.area_name_kor)
        if kakao_response:
            lat = kakao_response["lat"]
            lng = kakao_response["lng"]
            update_location_coordinates(db, location.area_name_kor, lat, lng)
        else:
            print(f"Failed to fetch coordinates for {location.area_name_kor}")
    db.commit()

# 지역 이름과 도시 이름을 기준으로 lat, lng 좌표 저장
def process_city_locations_with_area(db: Session):
    """
    CityList의 모든 도시 이름에 대해 AreaList의 지역 이름을 붙여
    카카오맵 API를 통해 좌표를 가져와 저장합니다.
    """
    cities = db.query(CityList).filter(CityList.latitude.is_(None), CityList.longitude.is_(None)).all()

    if not cities:
        print("No unmapped city locations found.")
        return

    for city in cities:
        # AreaList에서 지역 이름 가져오기
        area = db.query(AreaList).filter(AreaList.areacode_id == city.area_areacode_id).first()
        if not area:
            print(f"Area not found for City: {city.city_name_kor}")
            continue

        # 지역 이름과 시군구 이름 결합
        full_query = f"{area.area_name_kor} {city.city_name_kor}"  # 예: "전라북도 순창군"

        # 카카오맵 API 호출
        kakao_response = get_location_from_kakao(query=full_query)
        if kakao_response:
            # 좌표 업데이트
            city.latitude = kakao_response["lat"]
            city.longitude = kakao_response["lng"]
            print(f"Updated: {full_query} -> Lat: {city.latitude}, Lng: {city.longitude}")
        else:
            print(f"Failed to fetch coordinates for {full_query}")

    # 모든 업데이트 완료 후 commit
    db.commit()

# HTML 태그 제거하고 텍스트만 저장하기 위한용도
def clean_html(raw_html):
    """
    HTML 태그를 제거하고 텍스트만 반환
    Args:
        raw_html (str): HTML 포함된 문자열
    Returns:
        str: 순수 텍스트
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text()

#문체부 추천 여행지 받아오는 api
# def get_tour(db_session):
#     api_url = "http://api.kcisa.kr/openapi/API_CNV_061/request"
#     serviceKey = env_vars["CNV_SERVICE_KEY"]
#     query_params = {
#         "serviceKey": serviceKey,
#         "numOfRows": 20,
#         "pageNo": 1
#     }

#     # API 요청
#     api_response = requests.get(api_url, params=query_params)
#     if api_response.status_code != 200:
#         return {"error": "Failed to fetch data from API"}

#     # XML 데이터 파싱
#     import xml.etree.ElementTree as ET
#     root = ET.fromstring(api_response.content)
#     items = root.find('.//items')
#     if items is None:
#         return {"error": "No items found in XML data"}

#     for item in items.findall('item'):
#         title = item.find('title').text
#         description_raw = item.find('description').text  # HTML 포함된 텍스트
#         description_clean = clean_html(description_raw)  # HTML 제거
#         detail_url = item.find('url').text
#         spatialCoverage = item.find('spatialCoverage').text

#         try:
#             detail_response = requests.get(detail_url)
#             soup = BeautifulSoup(detail_response.text, 'html.parser')

#             # 이미지 태그 찾기
#             image_div = soup.find('div', class_='culture_view_img')
#             if image_div:
#                 image_tag = image_div.find('img')
#                 if image_tag and 'src' in image_tag.attrs:
#                     image_url = urljoin(detail_url, image_tag['src'])  # 절대 경로 변환
#                 else:
#                     image_url = "No Image Found"
#             else:
#                 image_url = "No Image Found"

#         except Exception as e:
#             image_url = f"Error fetching image: {str(e)}"

#         # DB에 저장 (예시)
#         db_tour_list = Tourlist(
#             tour_name_kor=title,
#             description=description_clean,  # HTML 제거된 텍스트
#             url=detail_url,
#             spatial_coverage = spatialCoverage,
#             image_url = image_url
#         )
#         db_session.add(db_tour_list)

#     db_session.commit()
#     print("Data saved to database.")

def get_tour(db_session):
    api_url = "http://api.kcisa.kr/openapi/API_CNV_061/request"
    serviceKey = env_vars["CNV_SERVICE_KEY"]
    query_params = {
        "serviceKey": serviceKey,
        "numOfRows": 20,  # 한 페이지당 가져올 데이터 수
        "pageNo": 1       # 초기 페이지 번호
    }

    while True:
        # API 요청
        api_response = requests.get(api_url, params=query_params)
        if api_response.status_code != 200:
            print(f"Failed to fetch data from API: {api_response.status_code}")
            break

        # XML 데이터 파싱
        import xml.etree.ElementTree as ET
        root = ET.fromstring(api_response.content)
        items = root.find('.//items')
        total_count_elem = root.find('.//totalCount')
        if items is None or total_count_elem is None:
            print("No items or total count found in XML data.")
            break

        total_count = int(total_count_elem.text)

        for item in items.findall('item'):
            title = item.find('title').text
            detail_url = item.find('url').text
            
            # 중복 확인
            if db_session.query(Tourlist).filter(Tourlist.url == detail_url).first():
                print(f"Duplicate found for {title}. Skipping.")
                continue

            description_raw = item.find('description').text  # HTML 포함된 텍스트
            description_clean = clean_html(description_raw)  # HTML 제거            
            spatialCoverage = item.find('spatialCoverage').text

            try:
                detail_response = requests.get(detail_url)
                soup = BeautifulSoup(detail_response.text, 'html.parser')

                # 이미지 태그 찾기
                image_div = soup.find('div', class_='culture_view_img')
                if image_div:
                    image_tag = image_div.find('img')
                    if image_tag and 'src' in image_tag.attrs:
                        image_url = urljoin(detail_url, image_tag['src'])  # 절대 경로 변환
                    else:
                        image_url = "No Image Found"
                else:
                    image_url = "No Image Found"

            except Exception as e:
                image_url = f"Error fetching image: {str(e)}"

            # DB에 저장
            db_tour_list = Tourlist(
                tour_name_kor=title,
                description=description_clean,  # HTML 제거된 텍스트
                url=detail_url,
                spatial_coverage=spatialCoverage,
                image_url=image_url
            )
            db_session.add(db_tour_list)

        # 페이지 증가 및 중단 조건 확인
        db_session.commit()
        print(f"Page {query_params['pageNo']} saved to database.")

        query_params["pageNo"] += 1
        if query_params["numOfRows"] * (query_params["pageNo"] - 1) >= total_count:
            print("All data fetched.")
            break

    print("Data fetching completed.")