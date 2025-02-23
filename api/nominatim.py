import requests
#도시 이름으로 GPS X, Y 좌표 구하는 api

def get_coordinates(city_name):
    # API URL 구성
    url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
    
    try:
        # GET 요청 보내기
        response = requests.get(url)
        response.raise_for_status()  # HTTP 에러 발생 시 예외 발생
        
        # JSON 응답 파싱
        data = response.json()
        if data:
            location = data[0]
            print(f"위도: {location['lat']}, 경도: {location['lon']}")
        else:
            print("Geocoding 결과가 없습니다.")
    except requests.exceptions.RequestException as e:
        print(f"네트워크 에러: {e}")

# 예시: 'Seoul'로 좌표 구하기
get_coordinates("Seoul")