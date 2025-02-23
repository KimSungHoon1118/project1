# Set up the state
from langgraph.graph import MessagesState, START, END, StateGraph
from langgraph.graph.message import add_messages
from difflib import SequenceMatcher
# Set up the tool
# We will have one real tool - a search tool
# We'll also have one "fake" tool - a "ask_human" tool
# Here we define any ACTUAL tools
from langchain_core.tools import tool
from langchain.prompts import PromptTemplate
# from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.schema import AIMessage, SystemMessage, HumanMessage
load_dotenv()
import requests
from env import get_env_vars
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from langgraph.checkpoint.memory import MemorySaver
import uuid, json, re
from rich import print as rprint
from langgraph.prebuilt import create_react_agent, tools_condition
from pymongo import MongoClient
from db.mongodb import get_chat_history, save_chat_message, session_manager
from typing import Annotated, TypedDict, List, Tuple
import os
import logging as logger
import operator



# if not os.environ.get("TAVILY_API_KEY"):
#     os.environ("TAVILY_API_KEY") == os.getenv("TAVILY_API_KEY")

db = MongoClient("localhost",27017)
mongo_uri = os.getenv("MONGODB_URL")

tourg = APIRouter()

env_vars = get_env_vars()

CLIENT_ID = env_vars["NAVER_CLIENT_ID"]
CLIENT_SECRET = env_vars["NAVER_CLIENT_SECRET"]

@tool
def naver_local_search(query: str, display: int = 10) -> list[dict]:
    """
    네이버 지역 검색 API에 query를 전달해 결과를 리스트로 반환한다.    
    display: 검색 결과 개수 (최대 10)
    처음 반환하는 결과는 {지역} 관광지로 찾아온 결과중에 title, address, link를 반환한다.
    example 서울 관광지 일때-
    1. 롯데월드 어드벤처, 서울특별시 송파구 잠실동 40-1, http://www.lotteworld.com
    2. 롯데월드 아쿠아리움, 서울특별시 송파구 신천동 29 롯데월드몰 B1, https://www.lotteworld.com/aquarium
    3. 서울식물원, 서울특별시 강서구 마곡동 812 서울식물원, http://botanicpark.seoul.go.kr/
    4. 경복궁, 서울특별시 종로구 세종로 1-91 경복궁, https://royal.khs.go.kr/gbg
    5. 서울스카이, 서울특별시 송파구 신천동 29 117~123층, http://seoulsky.lotteworld.com/main/index.do
    관광지 중에서 가고 싶은 곳을 선택해 주세요.: (예: 1,2,4)
    사용자가 관광지 목록을 선택하면 선택한 장소들을 history에 저장
    사용자에게 특별히 해보고 싶은 활동(테마)이 있나요? (예/아니오) 로 입력받아서
    {지역} 지역에서 {테마} 관련 장소를 검색해서 
    1. 테마관련1
    2. 테마관련2
    3. 테마관련3
    4. 테마관련4
    5. 테마관련5
    마음에 드는 곳이 있으면 번호(쉼표)로 선택해주세요. (예: 1,3,5)
    숫자로 선택한 곳들 출력하고 history에 저장
    """
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {
        "query": query,
        "display": display
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])

        results = []
        for item in items:
            title = item.get("title", "").replace("<b>", "").replace("</b>", "")
            category = item.get("category", "")
            address = item.get("address", "")
            telephone = item.get("telephone", "")
            link = item.get("link", "")

            results.append({
                "title": title,
                "category": category,
                "address": address,
                "telephone": telephone,
                "link": link
            })
        logger.info(f"API 호출 성공: {len(results)}개 결과 반환")
        return results
    else:
        # 에러 처리 (로깅을 사용하는 것이 좋습니다)
        logger.error(f"Error({response.status_code}): {response.text}")
        return []


def naver_blog_search(query: str, display: int = 10, start: int = 1):
    """네이버 블로그 검색 API를 사용하여 정보를 검색."""

    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    params = {
        "query": query,
        "display": display,  # 검색 결과 개수
        "start": start,      # 시작점
        "sort": "sim"        # 유사도 순 정렬
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.status_code}

from langchain_community.tools import TavilySearchResults, Tool


# tavily_tool = [TavilySearchResults(max_results=3, include_answer=True,
#             include_raw_content=True,
#             include_images=True,)]

# OpenAI LLM 설정
llm = ChatOpenAI(model="gpt-4o-mini" ,temperature=0.2)



# system_message ="너는 10년 이상 경력의 여행플래너로 사용자가 원하는 여행 정보를 틀림없이 알맞게 줄 수 있다. 지역과 장소를 사용자가 입력한 지역의 주소 기반으로 찾아서 정확하게 찾아오고 "\
# "여행 경비 예산에 따라서 사용자가 원하는 여행코스에 예산에 알맞는 장소를 추천하고 사용자가 여행지에 갈 때 무엇을 타고 갈지에 따라 '대중교통(택시, 버스), 자가용"\
# "비행기, 렌터카 등' 그에 알맞는 정보 즉, 대중교통이면 어떤 경로로 타고 가야하는지와 소모요금, 자가용이면 여행지까지 가는 고속도로나 톨게이트 등의 경로정보와 유류비 등"\
# "을 알려준다. 여행 테마는 사용자의 입력에 따라 숙박, 관광지 ,문화관광, 호캉스, 레포츠, 드라마촬영지, 영화촬영지 등의 테마를 서로 연계하여 알려주고 주소 기반으로 알려준다. "\
# "사용자의 입력에 따라 생성된 여행코스에서 식당이면 금연시설 여부, 키즈존 여부, 네이버에서 평점이 몇점인지와 메뉴 사진이 있으면 메뉴 사진을 보여주고  대표 메뉴와 가격을 알려준다."\

from langchain_core.prompts import ChatPromptTemplate

from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from langgraph.prebuilt import ToolNode
from typing import Union
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_teddynote.tools.tavily import TavilySearch
from langchain_core.runnables import RunnableWithMessageHistory


class Location(TypedDict):
    """사용자에게 지역을 입력받고, 몇박 몇일 여행할지 입력받고,
    여행 인원이 총 몇명인지 입력받고 네이버 지역 api tool에 연결 해준다.
    """
    messages: Annotated[list, add_messages]
    location: str
    travel_days: str
    travel_num: int
    selected_places: Annotated[list, "선택한 관광지 목록"]
    theme_results: Annotated[list, "선택한 테마 관광지 목록"]
    food_results: Annotated[list, "선택한 식당/카페 목록"]

# 사용자 입력 데이터 스키마 정의
class UserInput(BaseModel):
    user_input: str
    config: Dict[str, Dict[str, str]]

# tavily_tool = TavilySearchResults(max_results=3)

tools = [naver_local_search]

# LLM 모델 정의
llm_with_tools = llm.bind_tools(tools)

location_prompt_template = ChatPromptTemplate.from_template("""
사용자의 입력에서 여행 지역, 일정(예: 1박 2일), 그리고 인원을 추출하세요.    
여행 일정은 숫자로 변환하지 말고 원래 입력된 형식(예: "1박 2일") 그대로 반환하세요.
인원이 없거나 비어 있으면 1명으로 입력한 걸로 간주한다.               

응답 형식은 JSON으로 제공하세요:
{
    "location": "<지역>",
    "travel_days": "<여행 일정 (예: 1박 2일)>",
    "travel_num": <인원 수>
}

사용자 입력: {user_input}
""")


selection_prompt_template = ChatPromptTemplate.from_template("""
사용자의 입력이 하나 또는 여러 개의 숫자(쉼표 포함)일 경우, 이를 사용자가 아래 목록 중에서 선택한 것으로 간주한다.

아래는 사용자가 이전 질문에서 받은 관광지 목록입니다:

{place_list}

사용자가 선택한 번호를 기반으로 관광지를 반환하세요.

응답 형식은 JSON으로 제공하세요:
{{
    "selected_places": ["<선택한 장소1>", "<선택한 장소2>", "<선택한 장소3>"]
}}

사용자 입력: {user_input}
""")


# 프롬프트 템플릿 정의
prompt_template = PromptTemplate(
    input_variables=["user_input"],
    template="""
    AiMessage가 선택해 주세요로 질문했을때 지역, 여행기간, 인원추출을 하지않고 사용자의 입력이 하나또는 여러개의 숫자 일때
    질문내용의 번호를 선택한 것으로 간주한다.
    AiMessage에 답변할때는 사용자 입력을 그대로 받고 아래는 무시한다. 
    선택해 주세요가 아닐때는 사용자의 입력에서 지역, 여행 기간(며칠), 그리고 인원을 추출하세요.    
    인원이 없거나 비어 있으면 1명으로 입력한걸로 간주한다.               
    응답 형식은 JSON으로 제공하세요:
    {{
        "location": "<지역>",
        "travel_days": "<며칠>",
        "travel_num": <인원 수>
    }}
    사용자 입력: {user_input}
    """
)
state = StateGraph(Location)

def dummy(state:Location):
    """초기 입력값 설정"""
    return {"messages": []}

def extract_location(user_input: str)-> Location:
    """LLM을 이용해 사용자 입력에서 Location 정보를 추출"""
    prompt = prompt_template.format(user_input=user_input)
    response = llm.invoke(prompt)  # LLM으로부터 응답 받기

    return {"messages": [response]}

# 상태를 처리하는 함수 정의
def process(state: Location):
    print(f"{state.location}에서 {state.travel_days} 동안 {state.travel_num}명이 여행합니다.")

def chatbot(state: Location):
    """
    상태에 따라 다른 프롬프트를 적용하여 LLM 도구 호출.
    """
    
    # LLM 도구 호출을 통한 응답 생성
    response = llm_with_tools.invoke(state["messages"])


    # 메시지와 ask_human 상태 반환
    return {"messages": [response]}
    


# 노드 추가: 사용자 입력을 받아 상태 생성
def input_processing(state: dict):     
    """
    Location 객체가 비어있을때만
    사용자의 입력에서 지역, 여행 기간(며칠), 그리고 인원을 추출하세요.
    인원이 없거나 비어 있으면 1명으로 입력한걸로 간주한다.
    """
    message = state.get("messages")
    print(f"message:{message}")
    user_input = [msg for msg in message if isinstance(msg, HumanMessage)][-1]
    print(user_input)
    return extract_location(user_input)

# 노드 추가: 상태를 처리
def process_location(state: dict) -> dict:
    """
    상태를 업데이트하여 location이 설정되면 여행 일정이 올바르게 유지되도록 수정.
    """
    if state is None:
        state = {}

    response = [item.content for item in state.get("messages", []) if isinstance(item, AIMessage)]
   
    
    if response:
        try:
            clean_content = response[0].strip("```json").strip("```").strip()
            parsed_data = json.loads(clean_content)

            # ✅ 안전한 데이터 접근 방식 적용
            location = parsed_data.get("location", "").strip()
            travel_days = parsed_data.get("travel_days", "").strip()
            travel_num = parsed_data.get("travel_num", 1)

            if not location:
                raise ValueError("❌ Location 값이 없습니다.")
            if not travel_days:
                travel_days = "1박 2일"  # 기본값 설정
            if not travel_num:
                travel_num = 1  # 기본값 설정

            # ✅ 상태 업데이트
            updated_state = {
                "location": location,
                "travel_days": travel_days,
                "travel_num": travel_num,
                "selected_places": state.get("selected_places", []),  # 기존 선택 목록 유지
                "messages": state.get("messages", []) + [response[0]]
            }

            print(f"✅ 여행 정보 설정 완료: {updated_state}")

            return updated_state

        except json.JSONDecodeError as e:
            print(f"❌ JSON 변환 오류: {e}")
        except ValueError as e:
            print(f"❌ 값 오류: {e}")

    return {"messages": [AIMessage(content="오류가 발생했습니다. 여행 정보를 다시 입력해주세요.")]}





# LangGraph 워크플로우 정의
workflow = StateGraph(Location)



workflow.add_node("dummy", dummy)
workflow.add_node("chatbot", chatbot)
workflow.add_node("input_processing", input_processing)
workflow.add_node("process_location", process_location)
workflow.add_node("tools", ToolNode(tools=tools))

# 두 노드를 연결
workflow.add_edge(START, "dummy")
workflow.add_edge("dummy", "input_processing" )
workflow.add_edge("input_processing", "process_location")
workflow.add_edge("process_location", "chatbot")
workflow.add_edge("tools", "chatbot")
# workflow.add_edge("chatbot", END)
# workflow.add_edge("input_processing", END)
# workflow.add_edge("process_location", END)

# # 조건부 엣지를 정의하는 함수
# def conditional_edge_logic(state: Location) -> str:
#     """
#     Location이 설정되면 chatbot으로 이동, 아니면 input_processing을 유지
#     """
#     if state.get("location") and state.get("travel_days") and state.get("travel_num"):
#         print(state.get("location"))
#         print(state.get("travel_days"))
#         return "chatbot"  # ✅ Location이 있으면 바로 chatbot 실행
#     else:
#         return "input_processing"  # ✅ Location이 없으면 계속 input_processing 실행

# workflow.add_conditional_edges(
#     "dummy",
#     conditional_edge_logic,
#     {"input_processing": "input_processing","chatbot": "chatbot"}
# )

# 조건부 엣지 추가
workflow.add_conditional_edges(
    "chatbot",  # 현재 노드 이름
    tools_condition,  # 조건부 엣지 정의
)
search_subgraph = StateGraph(Location)


def search_tourist_spots(state: Location):
    """
    🔹 네이버 API를 이용하여 사용자의 여행 지역에 맞는 관광지 검색
    """
    location = state["location"]
    print(f"📍 관광지 검색: {location}")

    # 네이버 API 호출
    places = naver_local_search.invoke({"query": f"{location} 관광지"})

    if not places:
        return {"messages": [AIMessage(content=f"{location}에서 관광지를 찾을 수 없습니다.")]}

    # 검색된 관광지 저장
    state["selected_places"] = places

    # 검색된 관광지 목록 표시
    place_list = "\n".join(
        [f"{i+1}. [{place['title']}]({place['link']}) - {place['address']} ({place['category']})"
         for i, place in enumerate(places)]
    )

    ai_response = f"✅ {location}에서 추천하는 관광지 목록입니다:\n\n{place_list}\n\n가고 싶은 곳을 선택해 주세요. (예: 1,2,4)"
    return {"messages": [AIMessage(content=ai_response)]}


### ✅ 1️⃣ 테마 검색 여부 확인 (`예/아니오`)
def ask_theme_search(state: Location):
    """사용자에게 테마 검색 여부를 물어본다."""
    return {"messages": [AIMessage(content="🎭 원하는 여행지 테마(문화 체험, 역사 탐방, 액티비티 등)가 있나요? (예/아니오)")]}


def search_theme_spots(state: Location):
    """
    🔹 사용자가 원하는 테마를 입력받아 검색 실행, 네이버 API에서 테마별 관광지 검색
    """
    user_input = state["messages"][-1].content.strip()

    # 사용자가 '아니오'라고 하면 바로 음식점 검색 단계로 이동
    if user_input.lower() in ["아니오", "아니요", "건너뛰기","ㄴ"]:
        return {"messages": [AIMessage(content="⏭ 테마 검색을 건너뛰고, 음식점 검색 여부를 확인합니다.")], "skip_theme": True}

    # 테마 검색 실행
    theme_query = f"{state['location']} {user_input} 관련 장소"
    print(f"🎭 테마 검색 실행: {theme_query}")
    # 네이버 API 호출
    theme_results = naver_local_search.invoke({"query": theme_query})

    if not theme_results:
        return {"messages": [AIMessage(content="❌ 해당 테마에 대한 장소를 찾을 수 없습니다.")], "skip_theme": True}

    # 테마 목록 출력
    theme_list = "\n".join([
        f"{i+1}. [{place['title']}]({place['link']}) - {place['address']} ({place['category']})"
        for i, place in enumerate(theme_results)
    ])

    ai_response = f"🎭 {user_input} 관련 장소 목록입니다:\n\n{theme_list}\n\n마음에 드는 곳이 있으면 번호(쉼표)로 선택해주세요. (예: 1,3,5)"
    return {"messages": [AIMessage(content=ai_response)], "theme_results": theme_results}

### ✅ 3️⃣ 음식점 검색 여부 확인 (`예/아니오`)
def ask_food_search(state: Location):
    """사용자에게 음식점 검색 여부를 물어본다."""
    return {"messages": [AIMessage(content="🍽 주변의 맛집/카페 정보를 검색할까요? (예/아니오)")]}


### ✅ 4️⃣ 음식점/카페 검색 실행
def search_food(state: Location):
    """사용자가 원하는 음식 카테고리를 입력받아 검색 실행"""
    user_input = state["messages"][-1].content.strip()

    # 사용자가 '아니오'라고 하면 바로 일정 생성 단계로 이동
    if user_input.lower() in ["아니오", "아니요", "건너뛰기","ㄴ"]:
        return {"messages": [AIMessage(content="⏭ 음식점 검색을 건너뛰고, 최종 일정을 생성합니다.")], "skip_food": True}

    # 음식 검색 실행
    if user_input.lower() in ["없음", "모름", "아무거나"]:
        food_query = f"{state['location']} 맛집"
    else:
        food_query = f"{state['location']} {user_input} 맛집"

    print(f"🍽 음식점 검색 실행: {food_query}")

    food_results = naver_local_search.invoke({"query": food_query})

    if not food_results:
        return {"messages": [AIMessage(content="❌ 해당 카테고리의 맛집을 찾을 수 없습니다.")], "skip_food": True}

    # 음식점 목록 출력
    food_list = "\n".join([
        f"{i+1}. [{place['title']}]({place['link']}) - {place['address']} ({place['category']})"
        for i, place in enumerate(food_results)
    ])

    ai_response = f"🍽 추천 맛집 목록입니다:\n\n{food_list}\n\n마음에 드는 곳이 있으면 번호(쉼표)로 선택해주세요. (예: 1,3,5)"
    return {"messages": [AIMessage(content=ai_response)], "food_results": food_results}


def finalize_trip_plan(state: Location):
    """
    🔹 사용자가 선택한 관광지, 테마, 식당을 기반으로 최적 여행 일정 제공
    """
    selected_places = state.get("selected_places", [])

    if not selected_places:
        return {"messages": [AIMessage(content="선택된 관광지가 없습니다. 다시 검색해 주세요.")]}

    # 일정 정리
    plan = "\n".join(
        [f"- {place['title']} ({place['address']})" for place in selected_places]
    )

    ai_response = f"✅ 최적화된 여행 일정:\n\n{plan}\n\n즐거운 여행 되세요! 🚀"
    return {"messages": [AIMessage(content=ai_response)]}

# search_subgraph.add_node("search_tourist_spots", search_tourist_spots)
# search_subgraph.add_node("search_theme_spots", search_theme_spots)
# search_subgraph.add_node("search_food_places", search_food)
# search_subgraph.add_node("finalize_trip_plan", finalize_trip_plan)
# search_subgraph.add_node("ask_theme_search", ask_theme_search)
# search_subgraph.add_node("ask_food_search", ask_food_search)
# search_subgraph.add_node("search_food", search_food)

# search_subgraph.add_edge(START, "search_tourist_spots")
# search_subgraph.add_edge("search_tourist_spots", "ask_theme_search")
# search_subgraph.add_edge("ask_theme_search", "search_theme_spots")
# search_subgraph.add_edge("search_theme_spots", "ask_food_search")
# search_subgraph.add_edge("ask_food_search", "search_food_places")
# search_subgraph.add_edge("search_food_places", "finalize_trip_plan")
# search_subgraph.add_edge("finalize_trip_plan", END)

# sub_grpah = search_subgraph.compile(MemorySaver(), interrupt_before=["search_theme_spots", "ask_food_search", "search_food_places"])

# workflow.add_node("search_subgraph", sub_grpah)

# workflow.add_edge("process_location", "search_subgraph")

graph = workflow.compile(checkpointer=MemorySaver())

# user_input = input("지역, 일정, 인원을 입력해주세요 (서울 1박2일 3명)")

# config = {"configurable": {"thread_id": "2"}}

config = {"configurable": {"thread_id": uuid.uuid4()}}
# 워크플로우 실행
# graph.invoke({"messages": user_input} ,config, stream_mode="values")
# print(graph)
import asyncio

# @tourg.post("/api/workflow")
# def tour_work(input_data: UserInput):
#     print(input_data.user_input)
#     print(input_data.config)
#     user_input=input_data.user_input
#     config = input_data.config
#     # 비동기 값일 경우 await로 처리
#     # if asyncio.iscoroutine(user_input):
#     #     user_input = await user_input

#     print(f"user_input: {user_input}", f"config: {config}")

    
#     response = graph.invoke({"messages": [user_input]} ,config, stream_mode="values")
#     print(f"response:{response}")
#     return response

# 🔹 user_id별 Lock을 저장할 Dictionary
user_locks = {}
active_requests = set()  # 현재 실행 중인 요청 기록

@tourg.post("/api/workflow")
async def tour_work(input_data: UserInput):
    print(input_data.user_input)
    print(input_data.config)
    user_input=input_data.user_input
    config = input_data.config
    user_id = config.get("thread_id", str(uuid.uuid4()))  # user_id 없으면 랜덤 생성

    # 비동기 값일 경우 await로 처리
    # if asyncio.iscoroutine(user_input):
    #     user_input = await user_input

    print(f"user_input: {user_input}", f"config: {config}")

     # 🔹 user_id 별로 Lock이 없으면 생성
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Semaphore(1)  # 동시에 하나의 요청만 처리
    
      # 🔹 중복 요청 방지 (현재 실행 중인 요청이 있으면 즉시 반환)
    if user_id in active_requests:
        return {"ai_response": "현재 요청을 처리 중입니다. 잠시 후 다시 시도해주세요."}


    async def agent_task(checkpointer):
        async with user_locks[user_id]:  # 🔹 하나의 요청만 실행되도록 제한
            try:
                active_requests.add(user_id)  # 현재 요청 기록
                # await user_locks[user_id].acquire()
                # 1. 이전 대화 기록 불러오기
                history = await get_chat_history(checkpointer, user_id)
                print("[INFO] Loaded history:", history)

                system_message = (
                    "당신은 여행 플래너 역할의 GPT입니다. "
                    "사용자가 여행 지역, 일정, 인원, 취향 등을 입력하면 tools을 통해 지역 관광지를 검색하여, "
                    "관광지 목록을 번호를 붙여서 사용자에게 보여주고 사용자가 선택하는 관광지 목록을 저장하고 나중에 여행 일정을 작성할때 반드시 넣는다."
                    "활동/테마로 찾아오는 관광지는 반드시 앞에 저장한 관광지에 덮어쓰지 말고 이후에 추가한다."
                    "사용자의 선택에 따른 저장 목록을 절대 임의로 누락시키지 않는다."
                    "활동/테마나 기존 관광지에서 예약이 필요하면 예약이 필요한 장소라고 알려준다."
                    "사용자에게 특별히 해보고 싶은 활동(테마)이 있나요? (예/아니오) 물어보고 입력이 없거나 아니오면 건너뛰고"
                    "입력이 있으면 원하시는 테마/활동을 알려주세요(예: 문화 체험, 역사 탐방, 자연 탐방, 액티비티 등)로 입력받아서 tools로 지역 입력받은(테마/활동)으로 검색하여"
                    "테마/활동 목록을 번호를 붙여서 사용자에게 보여주고 사용자가 선택하는 테마/활동을 저장한다. 저장할때 반드시 이전 관광지에 덮어씌우지 않고"
                    "이전 관광지 + 테마 관광지로 전부 저장해서 최적 코스 짤때 사용한다."
                    "건너뛰었거나 테마/활동을 저장한 후에 선택하신 장소 주변의 맛집/카페 정보를 확인하시겠습니까? (예/아니오)로 질문하고"
                    "입력이 없거나 아니오면 건너뛴다."
                    "입력이 있으면 원하시는 음식 종류나 분위기가 있으신가요? (예: 한식, 양식, 중식, 일식, 디저트 등) 선호하는 음식이 없으면 아니오"
                    "입력받아서 선호하는 음식 종류가 있으면 선호하는 종류로 검색하고 없음이나 아니오를 입력 받았으면 식당으로 검색"
                    "지역 선호하는종류 / 선호하는 종류가 없으면 지역 식당 으로 tools을 통해 검색해서 결과를 번호를 붙여서 보여주고"
                    "사용자가 선택한 식당을 저장한다."            
                    "식당이랑 카페 한번에 보여줄때는 식당1~5번 이후에 카페 6~10번 이런식으로 번호를 부여해서 보여준다."
                    "사용자의 입력을 받아서 사용자가 선택하는 번호의 식당이나 카페만 저장해서 일정에 포함시킨다."
                    "지금까지 저장한 정보들을 사용자에게 보여줄때 여행 일정에 따라 최적 코스로 일정을 짜준다."
                    "여행 일정을 짜줄때 위에서 선택한 내용들을 절대 누락시키지 않고 최종 일정에 포함시킨다."
                    "최종 일정을 토대로 최적 코스로 사용자에게 여행 코스를 만들어 준다."                    
                    "여행일정을 짜줄 수 없을만큼 정보가 부족하면 tavily_search tool을 사용해 추가적으로 보완한다."
                )


                # 2. 대화 이력 메시지 리스트 생성
                messages = [SystemMessage(content=system_message)]
                for session in history:
                    for msg in session["messages"]:
                        if msg["role"] == "user":
                            messages.append(HumanMessage(content=msg["content"]))
                        elif msg["role"] == "assistant":
                            messages.append(AIMessage(content=msg["content"]))

                # 3. 요청 수행
                response = await graph.ainvoke(
                    {"messages": messages + [{"role": "user", "content": user_input}]},
                    config,
                    stream_mode="values"
                )

                # 4. AI 응답 처리
                # ai_response = response.get("messages", [])[-1].get("content", "AI 응답이 없습니다.")
                # 4. AI 응답에서 툴 호출 확인
                tool_calls = [msg for msg in response["messages"] if isinstance("tool_calls", AIMessage)]
                if tool_calls:
                    print("[INFO] AI가 툴을 호출했습니다.")
                    
                    tool_responses = []
                    for tool_call in tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        tool_call_id = tool_call["id"]

                        # 🔹 호출된 툴 실행
                        if tool_name == "naver_local_search":
                            tool_result = naver_local_search(**tool_args)
                        # elif tool_name == "TavilySearchResults":
                        #     tool_result = tavily_tool.invoke(tool_args["query"])
                        else:
                            tool_result = {"error": f"Unknown tool: {tool_name}"}

                        # 🔹 툴 응답을 messages 리스트에 추가
                        tool_responses.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": str(tool_result)
                        })

                    # 🔹 툴 응답을 포함한 메시지로 다시 LLM 요청
                    response = await graph.ainvoke(
                        {"messages": messages + tool_responses},
                        config,
                        stream_mode="values"
                    )

                # 5. 응답에서 AIMessage 가져오기
                ai_response = [
                    msg for msg in response["messages"] if isinstance(msg, AIMessage)
                ][-1].content if response else "AI 응답이 없습니다."
                # 5. 대화 저장
                await save_chat_message(checkpointer, user_id, user_input, ai_response)

                return  ai_response
            
            except Exception as e:
                print("[ERROR] Agent Task Exception:", str(e))
                return "오류가 발생했습니다."
            
            finally:
            # 🔹 Lock 해제 (작업이 끝난 후 새로운 요청을 받을 수 있도록)
                # user_locks[user_id].release()
                active_requests.discard(user_id)  # 실행 중인 요청 제거

    # MongoDB 세션 실행
    try:
        response = await session_manager(mongo_uri, agent_task)
        return {"ai_response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


# from langchain_teddynote.graphs import visualize_graph

# visualize_graph(graph, xray=True)
# # graph.get_graph().print_ascii()
# # user_input = input("지역, 일정, 인원을 입력해주세요 (서울 1박2일 3명)")

# config = {"configurable": {"thread_id": "2"}}
# # 워크플로우 실행
# # graph.invoke({"messages": user_input} ,config, stream_mode="values")
# # print(graph)







@tool
def search_naver_blog(query: str):
    """네이버 블로그 검색 API를 통해 여행지 정보를 검색."""
    results = naver_blog_search(query)
    # rprint(results)
    if "error" in results:
        return f"Error: {results['error']}"
    
    # return filter_and_deduplicate_results(results)


    return filter_and_deduplicate_results(results)

# tools = [toolaa]


@tourg.get("/api/tour/agent")
async def tour_get_tavily(query: str, user_id: str):
    """
    FastAPI 엔드포인트: MongoDBSaver를 사용하여 agent와 연동
    """
    async def agent_task(checkpointer):
        # 1. 이전 대화 기록 로드
        history = await get_chat_history(checkpointer, user_id)
        print("[INFO] Loaded history:", history)


        system_message =(
            "당신은 여행 플래너 역할의 GPT입니다. "
            "사용자가 여행 지역, 일정, 인원, 취향 등을 입력하면 최적의 여행 일정을 생성하고, "
            "맛집/카페 정보와 교통 정보를 포함해 완벽하게 제공해야 합니다."
        )

        # 2. 이전 기록을 agent 초기 상태로 설정
        messages = [SystemMessage(content=system_message)]  # 시스템 메시지
        for session in history:
            for msg in session["messages"]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        # 3. agent 생성
        agent = create_react_agent(
            # llm, tools, checkpointer=checkpointer  # MongoDBSaver를 연결
        )
        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4()),
                "checkpoint_ns": "tour_guide",
                "checkpoint_id": str(uuid.uuid4())
            }
        }

        # 4. 새로운 요청 처리
        response = await agent.ainvoke(
            {"messages": messages + [{"role": "user", "content": query}]},
            config=config
        )

        # 5. 응답에서 AIMessage 가져오기
        ai_response = [
            msg for msg in response["messages"] if isinstance(msg, AIMessage)
        ][-1].content if response else "AI 응답이 없습니다."

        # 6. 대화 저장
        await save_chat_message(checkpointer, user_id, query, ai_response)

        return ai_response

    # MongoDB 세션 관리
    try:
        response = await session_manager(mongo_uri, agent_task)
        return {"ai_response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")





# The thread id is a unique key that identifies
# this particular conversation.
# We'll just generate a random uuid here.
# thread_id  설정 
thread_id = uuid.uuid4()
config = {"configurable": {"thread_id": thread_id}}


def remove_duplicates(results, similarity_threshold=0.8):
    """
    검색 결과에서 중복된 항목 제거.
    - similarity_threshold: 제목 또는 내용의 유사도를 판단하는 기준 (0.8 = 80%)
    """
    unique_results = []
    seen_links = set()

    for item in results.get("items", []):
        title = item["title"].replace("<b>", "").replace("</b>", "").strip()
        link = item["link"].strip()
        description = item["description"].replace("<b>", "").replace("</b>", "").strip()

        # URL 중복 제거
        if link in seen_links:
            continue

        # 제목과 설명 유사도 비교
        is_duplicate = False
        for unique_item in unique_results:
            title_similarity = SequenceMatcher(None, title, unique_item["title"]).ratio()
            desc_similarity = SequenceMatcher(None, description, unique_item["description"]).ratio()

            # 중복 조건: 제목 또는 설명이 유사하거나 링크가 동일
            if title_similarity > similarity_threshold or desc_similarity > similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_links.add(link)
            unique_results.append({
                "title": title,
                "link": link,
                "description": description
            })

    return unique_results


def filter_and_deduplicate_results(results, max_results=15):
    """검색 결과를 필터링하고 중복 제거."""
    deduplicated_results = remove_duplicates(results)

    # 상위 max_results만 반환
    return deduplicated_results[:max_results]


