import requests, json
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import os, urllib.request
import urllib.parse
from fastapi.staticfiles import StaticFiles
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
from datetime import datetime

class TLSAdapter(HTTPAdapter):
    def __init__(self, ssl_version=None, **kwargs):
        self.ssl_version = ssl_version
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_version'] = self.ssl_version
        return PoolManager(*args, **kwargs)

app = FastAPI()
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=templates_dir)
SERVICE_KEY = os.getenv("SERVICE_KEY")
REST_API_KEY = os.getenv("REST_API_KEY")

# 정적 파일 마운트
static_dir = Path(__file__).parent.parent / "static"
app.mount("/backend/static", StaticFiles(directory=static_dir), name="static")

import requests

# 공공데이터포털 축제,행사 정보 API 호출 함수
def fetch_event_data(region: str = None, date: str = None):
    api_url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/searchFestival"    

    # 기본값: 오늘 날짜
    if not date:
        date = datetime.now().strftime("%Y%m%d")

    params = {
        "serviceKey": SERVICE_KEY,
        "numOfRows": 20,
        "pageNo": 1,
        "arrange": "O",  # 정렬 기준: A=제목순
        "listYN": "Y",
        "MobileOS": "ETC",
        "MobileApp": "AppTest",
        "eventStartDate": date,  # 시작 날짜
        "_type" : "json",
    }

    # API 요청
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()  # JSON 응답 파싱

        # 응답 데이터에서 필요한 정보만 추출
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        events = []
        url = "https://korean.visitkorea.or.kr/kfes/detail/fstvlDetail.do?cmsCntntsId="
        for item in items:
            event = {
                "title": item.get("title"),
                "address": item.get("addr1"),
                "start_date": item.get("eventstartdate"),
                "end_date": item.get("eventenddate"),
                "thumbnail": item.get("firstimage"),
                "url": url+item.get("contentid"),
            }

            # 지역 필터링
            if region and region not in event["address"]:
                continue

            events.append(event)

        return events

    return {"error": f"Failed to fetch data from API. Status code: {response.status_code}"}


@app.get("/proxy-image/")
def proxy_image(url: str):
    try:
        encoded_url = quote(url, safe=":/?=&")  # URL 인코딩
        response = requests.get(encoded_url, stream=True)
        if response.status_code == 200:
            return StreamingResponse(response.raw, media_type="image/jpeg")
        return JSONResponse(content={"error": "Failed to fetch the image"}, status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": f"Error occurred: {str(e)}"}, status_code=500)

# 지역 조회 엔드포인트
@app.get("/api/regions")
def get_regions():
    url = "http://apis.data.go.kr/B551011/KorService1/areaCode1"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "AppTest",
        "_type": "json",
        "numOfRows": 20,
        "pageNo": 1,
    }

    try:
        response = requests.get(url, params=params, verify=False)
        print(f"Final URL: {response.url}")  # 최종 URL 출력
        print(f"Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")

        if response.status_code != 200:
            return JSONResponse(content={
                "error": "Request failed",
                "status_code": response.status_code,
                "response_text": response.text
            }, status_code=response.status_code)

        data = response.json()
        regions = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return JSONResponse(content=regions)

    except ValueError as e:
        return JSONResponse(content={
            "error": "Invalid JSON response",
            "exception": str(e),
            "response_text": response.text
        }, status_code=500)
    except Exception as e:
        return JSONResponse(content={
            "error": "Unexpected error occurred",
            "exception": str(e)
        }, status_code=500)
    

# 도시 조회 엔드포인트
@app.get("/api/cities/{region_code}")
def get_cities(region_code: str):
    url = "http://apis.data.go.kr/B551011/KorService1/areaCode1"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "App",
        "_type": "json",
        "numOfRows": 31,
        "pageNo": 1,
        "areaCode": region_code,
    }
    response = requests.get(url, params=params)
    data = response.json()
    cities = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    return JSONResponse(content=cities)

# 키워드 검색 엔드포인트
@app.get("/api/keyword_search")
def keyword_search( keyword: str = Query(...)):
    print(f"Received keyword: {keyword}")
    url = "http://apis.data.go.kr/B551011/KorService1/searchKeyword1"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "App",
        "_type": "json",
        "numOfRows": 20,
        "listYN": "Y",
        "pageNo": 1,
        "arrange": "A",
        "contentTypeId" : 12,
        "keyword": keyword,
    }
    # URL 인코딩
    encoded_keyword = quote(keyword)
    print(f"Encoded keyword: {encoded_keyword}")

    # 수동 URL 구성
    query_string = "&".join([f"{key}={quote(str(value))}" for key, value in params.items()])
    full_url = f"{url}?{query_string}"
    print(f"Request URL: {full_url}")

    response = requests.get(full_url, params=params)
    if response.status_code != 200:
        return JSONResponse(
            content={"error": "Failed to fetch data from the API", "status": response.status_code},
            status_code=response.status_code,
        )

    try:
        data = response.json()
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        return JSONResponse(content=items)
    except ValueError as e:
        return JSONResponse(
            content={"error": "Failed to parse JSON response", "exception": str(e)},
            status_code=500,
        )

# 이미지 검색 엔드포인트
@app.get("/api/img_search")
def search_img(query: str = Query(...)):
   
    # KA 헤더 설정
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")     
    
    params = urllib.parse.quote(query)
    print(params)
    url = "https://openapi.naver.com/v1/search/image?query=" + params
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


@app.get("/events")
def get_events(
    region: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1)
):
    """
    특정 지역을 기준으로 관광 이벤트 정보를 반환하며 페이지네이션을 지원
    """
    all_events = fetch_event_data(region=region)
    if "error" in all_events:
        return {"error": all_events["error"]}

    # 페이지네이션 처리
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_events = all_events[start_idx:end_idx]

    return {
        "region": region,
        "total_events": len(all_events),
        "page": page,
        "per_page": per_page,
        "events": paginated_events
    }


# 상세정보 조회 엔드포인트
@app.get("/api/detail_view")
def detail_view(content_id: str):
    url = "http://apis.data.go.kr/B551011/KorService1/detailCommon1"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "App",
        "_type": "json",
        "contentId": content_id,
        "contentTypeId": "12",
        "defaultYN": "Y",
        "firstImageYN": "Y",
        "areacodeYN": "N",
        "catcodeYN": "N",
        "addrinfoYN": "Y",
        "mapinfoYN": "N",
        "overviewYN": "Y",
        "numOfRows": 1,
        "pageNo": 1,
    }
    response = requests.get(url, params=params)
    data = response.json()
    detail = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    return JSONResponse(content=detail)

# # HTML 폼 페이지
# @app.get("/", response_class=JSONResponse)
# async def form_page(request: Request):
#     return templates.TemplateResponse("form.html", {"request": request})

@app.get("/", response_class=JSONResponse)
async def form_page(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

# FastAPI 애플리케이션 실행
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="localhost", port=5000)