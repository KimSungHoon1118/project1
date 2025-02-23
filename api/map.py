from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import requests
from env import get_env_vars  # 종속성 가져오기
import platform
from pydantic import BaseModel
# 카카오 지도 api 한국의 상세 위치 보는용

# 라우터 객체 생성
kakaomap_router = APIRouter()

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="templates")
env_vars = get_env_vars()
REST_API_KEY = env_vars["REST_API_KEY"]
KAKAO_API_KEY = env_vars["KAKAO_API_KEY"]

@kakaomap_router.get("/map", response_class=HTMLResponse)
async def get_map(request: Request ):
    # KAKAO_API_KEY = env_vars["KAKAO_API_KEY"]
    # API 키를 템플릿으로 전달
    return templates.TemplateResponse("map.html", {"request": request, "kakao_api_key": KAKAO_API_KEY})

@kakaomap_router.get("/api/search_location")
def search_location(query: str = Query(...)) -> dict:
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    os_name = platform.system()
    ka_header = f"sdk/1.0 os/{os_name} lang/ko app/mapApi"
    headers = {
        "Authorization": f"KakaoAK {REST_API_KEY}",
        "KA": ka_header,
    }
    params = {"query": query}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("documents"):
            location = data["documents"][0]
            return {
                "status": "success",
                "name": location["place_name"],
                "lat": location["y"],
                "lng": location["x"]
            }
        else:
            return {"status": "error", "message": "Location not found"}
    else:
        return {"status": "error", "message": "Failed to connect to Kakao API"}


def get_route_info(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> dict:
    """
    카카오 경로조회 API 호출 예시. (실제 URL, 파라미터 등은 Kakao Developers 문서 참고)
    """
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    # KA 헤더 설정
    os_name = platform.system()  # 운영체제 이름 (예: 'Windows', 'Linux')
    ka_header = f"sdk/1.0 os/{os_name} lang/ko app/mapApi"
    # print(f"KA Header: {ka_header}")  # 디버깅 용도
    headers = {
        "Authorization": f"KakaoAK {REST_API_KEY}",
        "KA": ka_header ,
    }
    params = {
        "origin": f"{start_lng},{start_lat}",
        "destination": f"{end_lng},{end_lat}",
        "priority": "RECOMMEND",
        # ... 필요한 파라미터
    }
    # 요청
    response = requests.get(url, headers=headers, params=params)
    
    data = response.json()
       # 응답에서 "summary" 키가 있는지, 그리고 "routes"가 비어 있지 않은지 체크
    if "routes" in data and len(data["routes"]) > 0 and "summary" in data["routes"][0]:
        distance = data["routes"][0]["summary"].get("distance")
        duration = data["routes"][0]["summary"].get("duration")
        return {
            "distance": distance,
            "duration": duration
        }
    else:
        # 로그 출력 or None 리턴 등으로 에러 발생 상황을 알려주기
        print("경로 정보가 없습니다. (summary 없음)")
        return None

# 좌표로 주소 검색
@kakaomap_router.get("/api/coords-to-address")
async def coords_to_address(longitude: float = Query(...), latitude: float = Query(...) ):
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    # REST_API_KEY = env_vars["REST_API_KEY"]

    # KA 헤더 설정
    os_name = platform.system()  # 운영체제 이름 (예: 'Windows', 'Linux')
    ka_header = f"sdk/1.0 os/{os_name} lang/ko app/mapApi"
    # print(f"KA Header: {ka_header}")  # 디버깅 용도
    headers = {
        "Authorization": f"KakaoAK {REST_API_KEY}",
        "KA": ka_header ,
    }
    params = {"x": longitude, "y": latitude}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        result = response.json()
        if "documents" in result and len(result["documents"]) > 0:
            address_info = result["documents"][0]
            road_address = address_info.get("road_address", {}).get("address_name", "N/A")
            jibun_address = address_info.get("address", {}).get("address_name", "N/A")
            return {"road_address": road_address, "jibun_address": jibun_address}
        else:
            return {"road_address": "N/A", "jibun_address": "N/A"}
    else:
        return {"error": f"Failed to fetch address. Status: {response.status_code}"}
    
# @router.post("/api/shortest-path")
# async def get_shortest_path(start: str = Query(...), end: str = Query(...)):
#     """
#     Kakao Directions API를 사용하여 최단 경로를 계산하는 API
#     :param start: 시작 좌표 (위도, 경도)
#     :param end: 도착 좌표 (위도, 경도)
#     """
#     url = "https://apis-navi.kakaomobility.com/v1/directions"
#     headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
#     params = {"origin": start, "destination": end, "priority": "RECOMMEND"}

#     response = requests.get(url, headers=headers, params=params)
#     if response.status_code == 200:
#         return response.json()
#     else:
#         return {"error": response.json()}



# 좌표 데이터 모델
class Coordinates(BaseModel):
    coords: list[dict]  # [{"lat": 37.5665, "lng": 126.9780}, ...]

@kakaomap_router.post("/api/shortest-path")
async def calculate_shortest_path(coordinates: Coordinates):
    url = "https://apis-navi.kakaomobility.com/v1/waypoints/directions"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    # data = {
    #     "origin": f"{coords[0]['lng']},{coords[0]['lat']}",
    #     "destination": f"{coords[-1]['lng']},{coords[-1]['lat']}",
    #     "waypoints": [
    #         {"x": coord["lng"], "y": coord["lat"]} for coord in coords[1:-1]
    #     ],
    # }
    # 요청 데이터 확인
    print(coordinates)
    return {"status": "success", "path": coordinates.coords}
    # response = requests.post(url, headers=headers, json=data)
    # return response.json()