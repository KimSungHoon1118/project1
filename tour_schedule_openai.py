from vector import search_tourist_spots_with_metadata
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from db.db import SessionLocal
from db.models import TourSpot, Schedule
from sqlalchemy.orm import Session
import json
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from rich import print as rprint
# map.py의 search_location 함수를 가져온다고 가정
from api.map import search_location, get_route_info

from dotenv import load_dotenv
load_dotenv()

## 여행지 목록 pdf 임베딩해서 openai로 추천 여행지 뽑기 위한 py


@tool("get_coordinates")
def get_coordinates(place_name: str) -> dict:
    """
    주어진 장소 이름으로 Kakao맵 API를 통해 좌표를 조회한다.
    """
    return search_location(query=place_name)


@tool("generate_travel_plan")
def generate_travel_plan_with_search(query: str, keyword: str, duration: str):
    """
    OpenAI와 통합된 여행 계획 생성 Tool.
    :param query: 검색어
    :param keyword: 지역 필터 키워드
    :param duration: 여행 기간
    :return: JSON 형식의 여행 계획
    """
    # 1. 벡터스토어 검색
    vectorstore_path = "vectorstore"
    search_results = search_tourist_spots_with_metadata(query, vectorstore_path, keyword)

    if not search_results:
        return f"Error: {keyword}에 대한 검색 결과가 없습니다."

    # 2. 각 장소 좌표 구하기 (카카오맵 API)
    for spot in search_results:
        location_data = search_location(query=spot["관광지명"])
        if "lat" in location_data and "lng" in location_data:
            spot["lat"] = float(location_data["lat"])
            spot["lng"] = float(location_data["lng"])
        else:
            # 좌표가 없으면 제외하거나, skip
            spot["lat"] = None
            spot["lng"] = None
    
     # 유효한 좌표만 필터
    valid_spots = [s for s in search_results if s["lat"] is not None and s["lng"] is not None]
    if not valid_spots:
        return "Error: 모든 관광지 좌표를 찾지 못했습니다."

    # 3. (예시) 첫 번째 장소를 기준점으로 하여, 나머지 장소까지의 거리/시간 계산
    base_spot = valid_spots[0]
    base_lat, base_lng = base_spot["lat"], base_spot["lng"]
    
    # 거리 계산 결과를 담을 리스트
    results_with_distance = []
    
    for spot in valid_spots:
        if spot == base_spot:
            spot["distance"] = 0
            spot["duration"] = 0
        else:
            route_info = get_route_info(base_lat, base_lng, spot["lat"], spot["lng"])
            if route_info is None:
                # 경로 정보가 없을 때의 처리 (skip, 로그 출력, 오류 반환 등)
                continue
            if "error" not in route_info:
                spot["distance"] = route_info["distance"]   # 미터 단위
                spot["duration"] = route_info["duration"]   # 초 단위
            else:
                spot["distance"] = 9999999  # 엄청 큰 값으로 처리
                spot["duration"] = 9999999
        
        results_with_distance.append(spot)
    
    # 4. 거리 기준으로 정렬
    results_with_distance.sort(key=lambda x: x["distance"])  # 오름차순
    
    # (옵션) 너무 먼 곳은 제외하거나, 일정에 넣지 않을 수도 있음
    # 예: distance가 30000(30km) 넘으면 제외하기 등등
    
    # 5. 정렬된 결과를 프롬프트용 문자열로 변환
    spots_info = "\n".join(
        f"- {spot['관광지명']} (주소: {spot['주소']}, 거리: {spot['distance']}m, "
        f"시간: {spot['duration']}초, 위도/경도: {spot['lat']}, {spot['lng']}, "
        f"설명: {spot['개요'][:80]}...)" 
        for spot in results_with_distance
    )

    # 6. ChatGPT에 넘길 프롬프트 작성
    prompt = f"""
    {keyword}를(을) 여행할 계획입니다. {duration} 일정으로 여행 코스를 생성해 주세요.
    다음은 {keyword}의 주요 관광지 정보(카카오 경로조회로 정렬된 순서)입니다:
    {spots_info}

    - 이미 {keyword} 내에서 첫 번째 장소를 기준으로 가까운 순으로 정렬했습니다.
    - {duration}에 해당하는 여행 코스만 작성해 주세요. 다른 일정(예: 1박2일, 2박3일 등)은 포함하지 마세요.
    - 일정이 당일치기면 중복되지 않는 5개코스
    - 일정이 1박 2일이면 중복되지 않는 1일 4-5개 코스, 2일 4-5개 코스
    - 일정이 2박 3일이면 중복되지 않는 1일 4-5개 코스, 2일 4-5개 코스, 3일 4-5개코스로 짜줘
    - 여행지는 카카오 map API에서 찾을 수 있는 지명으로 적어줘, 지도에서 찾을 수 없는 곳은 제외해줘.
    - 각 코스는 주요 관광지와 활동을 포함하고 아래 포맷으로만 생성해줘. 간단한 설명을 추가하고 언어는 한글로만 해줘.
    - 대답은 json 형식으로 작성해줘.

    포맷:
    {{
      "location": "{keyword} ({duration})",
      "여행코스": {{
        "1일": [
          {{
            "여행지": "(여행지 이름)",
            "설명": "(간단한 설명)",
            "주소": "(주소)",
            "좌표": "위도, 경도"
          }},
          ...
        ]
      }}
    }}
    """

    # 7. ChatGPT 호출
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        if response and response.content:
            print(f"OpenAI 응답: {response.content}")
            return response.content.strip()
        else:
            return "Error: OpenAI 응답이 비어 있습니다."
    except Exception as e:
        return f"Error: OpenAI 호출 중 문제가 발생했습니다 - {e}"


tools = [get_coordinates]
tool_node = ToolNode(tools)
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7).bind_tools(tools)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
def parse_openai_json_response(response: str):
    """
    OpenAI의 ```로 감싸진 JSON 응답을 파싱
    :param response: OpenAI로부터 받은 문자열 응답
    :return: JSON 데이터 (dict 형태)
    """
    # ```json 또는 ``` 제거
    if response.startswith("```json"):
        response = response[7:].strip()
    elif response.startswith("```"):
        response = response[3:].strip()
    
    if response.endswith("```"):
        response = response[:-3].strip()

    # JSON 파싱
    try:
        parsed_data = json.loads(response)
        return parsed_data
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 에러: {e}")
        return None

def save_tour_spots_to_db(json_data, session: Session):
    """
    JSON 데이터에서 TourSpot 데이터를 추출하여 DB에 저장
    :param json_data: OpenAI로부터 받은 여행 코스 JSON 데이터
    :param session: SQLAlchemy 세션
    """
    if not json_data:
        print("Error: JSON 데이터가 없습니다.")
        return
    
    location = json_data.get("location").split(" (")[0]  # "서울 (1박2일)" → "서울"
    duration = json_data.get("location").split(" (")[1][:-1] if " (" in json_data.get("location", "") else ""
    travel_courses = json_data.get("여행코스", {})

    for day, spots in travel_courses.items():
        # 1. Schedule ID 조회
        schedule = (
            session.query(Schedule)
            .filter_by(location=location, duration=duration, day=int(day[0]))  # "1일" → 1
            .first()
        )

        if not schedule:
            print(f"Error: Schedule not found for {location}, {duration}, day {day}")
            continue

        for spot in spots:
            latitude, longitude = None, None
            if "좌표" in spot and "," in spot["좌표"]:
                try:
                    latitude, longitude = map(float, spot["좌표"].split(","))
                except ValueError:
                    print(f"Error: 좌표 변환 실패 - {spot['좌표']}")

            tour_spot = TourSpot(
                schedule_id=schedule.id,
                name=spot.get("여행지"),
                address=spot.get("주소"),
                description=spot.get("설명"),
                latitude=latitude,
                longitude=longitude,
            )
            session.add(tour_spot)

    session.commit()
    print("TourSpot 데이터가 성공적으로 저장되었습니다.")


# ChatPromptTemplate 정의
prompt_template = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=(
                "여행 계획을 작성하기 위해 필요한 정보를 입력해주세요.\n"
                "1. 여행 지역: (예: 경주, 강릉 등)\n"
                "2. 여행 일정: (예: 당일치기, 1박2일, 2박3일, 2월11일~13일 등)\n"
                "3. 원하는 여행 코스 유형: (예: 식당, 자연관광, 숙박, 관광지, 축제 등)\n"
                "위 정보를 입력받아 여행 코스를 짜주세요."
            )
        ),
        MessagesPlaceholder(variable_name="msgs"),  # 동적으로 메시지 삽입
    ]
)

def generate_travel_prompt(region: str, duration: str, course_type: str) -> HumanMessage:
    return HumanMessage(
        content=f"""
        여행 계획을 세우고 싶습니다.
        아래 정보를 기반으로 JSON 형식으로만 응답해주세요:
        
        지역: {region}
        일정: {duration}
        유형: {course_type}
        
        각 일정은 하루에 5~6개의 코스로 구성되어야 합니다.
        JSON 응답의 형식은 아래와 같아야 합니다:

        {{
          "location": "{region}",
          "duration": "{duration}",
          "여행코스": {{
            "1일차": [
              {{
                "여행지": "장소 이름",
                "설명": "장소에 대한 간단한 설명",
                "주소": "주소 정보",
                "좌표": "위도, 경도"
              }},
              ...
            ],
            ...
          }}
        }}
        """
    )

def refine_travel_schedule(json_data, selected_indexes):
    """
    JSON 데이터를 기반으로 사용자가 선택한 코스를 기준으로 일정 생성
    :param json_data: OpenAI에서 생성한 JSON 데이터
    :param selected_indexes: 사용자가 선택한 숫자 리스트 (예: [1, 3, 5])
    :return: 선택한 코스 기반의 여행 일정
    """
    refined_schedule = {"location": json_data["location"], "여행코스": {}}
    
    for day, spots in json_data["여행코스"].items():
        refined_schedule["여행코스"][day] = [
            spots[i - 1] for i in selected_indexes if i <= len(spots)
        ]

    return refined_schedule

def parse_openai_json_response(response):
    """
    OpenAI의 ```로 감싸진 JSON 응답을 파싱
    :param response: OpenAI로부터 받은 응답 객체 (AIMessage)
    :return: JSON 데이터 (dict 형태)
    """
    # response.content에서 텍스트를 추출
    content = response.content if hasattr(response, "content") else response

    # OpenAI 응답이 비어 있으면 None 반환
    if not content:
        print("Error: OpenAI 응답이 비어 있습니다.")
        return None

    # ```json 또는 ``` 제거
    if content.startswith("```json"):
        content = content[7:].strip()
    elif content.startswith("```"):
        content = content[3:].strip()

    if content.endswith("```"):
        content = content[:-3].strip()

    # JSON 파싱
    try:
        parsed_data = json.loads(content)
        return parsed_data
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 에러: {e}, 내용: {content}")
        return None


# tools = [get_coordinates]
# tool_node = ToolNode(tools)
# chat = ChatOpenAI(model="gpt-4o-mini", temperature=0.7).bind_tools(tools)


if __name__ == "__main__":

    # # 사용자 입력 처리
    # user_query = "경주에 자연관광지로 2박3일 여행가고 싶어."
    # response = chat.invoke(user_query)
    # rprint(response)

    # region = input("여행 지역을 입력하세요: (예: 경주, 서울, 부산) ")
    # duration = input("여행 일정을 입력하세요 (예: 당일치기, 1박2일): ")
    # course_type = input("원하는 여행 코스 유형을 입력하세요 (예: 자연관광, 숙박, 관광지, 문화시설): ")

    # prompt = generate_travel_prompt(region, duration, course_type)
    # templates = prompt_template.invoke([HumanMessage(content=prompt)])
    # response = chat.invoke(templates)
    # print("OpenAI 응답 내용:", response.content)
    # parsed_data = parse_openai_json_response(response)

    # if parsed_data:
    #     print("생성된 여행 코스:")
    #     for day, spots in parsed_data["여행코스"].items():
    #         print(f"\n{day}일차:")
    #         for i, spot in enumerate(spots, start=1):
    #             print(f"{i}. {spot['여행지']} ({spot['설명']})")
    # else:
    #     print("여행 코스 생성에 실패했습니다.")

    # selected_indexes = list(map(int, input("선택할 코스 번호를 입력하세요 (예: 1, 3, 5): ").split(",")))
    # refined_schedule = refine_travel_schedule(parsed_data, selected_indexes)

    # print("최종 여행 일정:")
    # rprint(json.dumps(refined_schedule, ensure_ascii=False, indent=2))

#  # 사용자 입력
#     region = input("여행 지역을 입력하세요: (예: 경주, 서울, 부산) ")
#     duration = input("여행 일정을 입력하세요 (예: 당일치기, 1박2일): ")
#     course_type = input("원하는 여행 코스 유형을 입력하세요 (예: 자연관광, 숙박, 관광지, 문화시설): ")

   
#     # 1. 여행 계획을 위한 프롬프트 생성
#     travel_prompt = generate_travel_prompt(region, duration, course_type)
#     print("\n[디버그] 생성된 프롬프트:\n", travel_prompt.content)

#     # 2. OpenAI 모델 호출
#     try:
#         response = llm.invoke([
#             HumanMessage(
#                 content=travel_prompt.content  # travel_prompt의 내용을 전달
#             )
#         ])
#         print("\n[디버그] OpenAI 응답 내용:\n", response.content)

#         # 3. JSON 파싱
#         parsed_data = parse_openai_json_response(response)
#         if parsed_data:
#             # 생성된 여행 코스 출력
#             print("\n생성된 여행 코스:")
#             for day, spots in parsed_data["여행코스"].items():
#                 print(f"\n{day}:")
#                 for i, spot in enumerate(spots, start=1):
#                     print(f"{i}. {spot['여행지']} ({spot['설명']})")

#             # 4. 사용자 선택
#             selected_indexes = list(map(int, input("\n선택할 코스 번호를 입력하세요 (예: 1, 3, 5): ").split(",")))
#             refined_schedule = refine_travel_schedule(parsed_data, selected_indexes)

#             # 5. 최종 일정 출력
#             print("\n최종 여행 일정:")
#             rprint(json.dumps(refined_schedule, ensure_ascii=False, indent=2))
#         else:
#             print("여행 코스 생성에 실패했습니다.")
#     except Exception as e:
#         print(f"오류 발생: {e}")


    db = SessionLocal()
    regions_list = ["강릉", "대구", "춘천", "부산"]
    durations = ["당일치기", "1박2일", "2박3일"]

    for region in regions_list:
        for duration in durations:
            result = generate_travel_plan_with_search.invoke({
                "query": region,
                "keyword": region,
                "duration": duration
            })
            print(f"지역: {region}, 기간: {duration}")
            parsed_data = parse_openai_json_response(result)

            if parsed_data:
                save_tour_spots_to_db(parsed_data, db)
            else:
                print("JSON 데이터 파싱 실패")        
    print("완료")
    result = generate_travel_plan_with_search.invoke({"query": "관광", "keyword": "서울", "duration": "당일치기"})

    parsed_data = parse_openai_json_response(result)

    if parsed_data:
        save_tour_spots_to_db(parsed_data, db)
    else:
        print("JSON 데이터 파싱 실패")        

    db.close() 
