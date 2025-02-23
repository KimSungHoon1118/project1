from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from pymongo import MongoClient
from langgraph.graph import StateGraph
load_dotenv()
from rich import print as rprint
from datetime import datetime
from langchain_community.tools import TavilySearchResults


builder = StateGraph(str, "A description for the state")
# ... define the graph
# checkpointer = # mongodb checkpointer (see examples below)
# graph = builder.compile(checkpointer=checkpointer)


from typing import Literal

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from pinecone import Pinecone, ServerlessSpec
import os
PINECONE_API_KEY = os.getenv("API_KEY")
PINECONE_ENV = "us-east-1" # Pinecone 환경 설정 (api 환경 확인 필요)
# print(PINECONE_API_KEY)
# Pinecone 초기화
pc = Pinecone(api_key=PINECONE_API_KEY)



index_name = "keyword-vector"
index = pc.Index(index_name)

from langchain_openai import OpenAIEmbeddings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=OPENAI_API_KEY)

# async def get_user_metadata(user_id):
#     response = index.query(
#         # vector=embeddings.embed_query(user_id),  # 검색 기준 텍스트
#         top_k=2,  # 가장 유사한 하나의 결과
#         include_metadata=True,
#         id= user_id
#         # filter={"ID": user_id}
#     )
#     print(response)  # 전체 응답 확인
#     if response["matches"]:
#         return response["matches"]
#     return {}

# import asyncio
# asyncio.run(get_user_metadata("user223_1"))


@tool
def get_weather(city: Literal["nyc", "sf"]):
    """Use this to get weather information."""
    if city == "nyc":
        return "It might be cloudy in nyc"
    elif city == "sf":
        return "It's always sunny in sf"
    else:
        raise AssertionError("Unknown city")

@tool
def get_time():
    """년,월,일 오늘의 시간 정보를 주는 tool"""
    return datetime.now()


toolaa = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=True,
    # include_domains=[...],
    # exclude_domains=[...],
    # name="...",            # overwrite default tool name
    # description="...",     # overwrite default tool description
    # args_schema=...,       # overwrite default args_schema: BaseModel
)
import asyncio

# result = toolaa.invoke({"query": "서울의 유명한 관광지는 뭐지"})
# rprint(result)

tools = [get_weather, get_time, toolaa]
model = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.6)
# response = model.invoke("서울 자연 관광지")
config = {"configurable": {"thread_id:": "1"}}
graphs = create_react_agent(model, [toolaa])
# response = graphs.invoke({
#     "messages": [
#         {"role": "user", "content": "한국에서 추천하는 관광지는 어디인가요?"},
#     ],
#     "configurable": {"thread_id": "1"}
# })
# rprint(response)

MONGODB_URI = "localhost:27017"  # replace this with your connection string

# with AsyncMongoDBSaver.from_conn_string(MONGODB_URI) as checkpointer:
#     config = {"configurable": {"thread_id": "1"}}
#     graphs = create_react_agent(model,tools =[toolaa], checkpointer=checkpointer)
#     response = graphs.ainvoke({
#         "messages": [
#             {"role": "user", "content": "한국에서 추천하는 관광지는 어디인가요?"},
#         ],
#         "configurable": {"thread_id": "1"}
#     })
#     rprint(response)
    # a = checkpointer.get(config)
#     human_message_content = [message.content for message in a.get("channel_values").get("messages") if isinstance(message, HumanMessage)][-5:-1]
#     ai_message_content = [message.content for message in a.get("channel_values").get("messages") if isinstance(message, AIMessage) and message.content != ''][-5:-1]
    
#     rprint(a.get("ts"), "human:",human_message_content, "AI:", ai_message_content)

#     # 두 리스트의 길이를 맞추고 순서대로 출력
#     pairs = zip(human_message_content, ai_message_content)
#     # 순서대로 출력
#     for i, (h, a) in enumerate(pairs, start=1):
#         print(f"h{i}: {h}")
#         print(f"a{i}: {a}")

    

# prompt = "python의 datatime.now()의 시간을 기준으로 알려줘"

# def print_stream(stream):
#     for s in stream:
#         message = s["messages"][-1]
#         if isinstance(message, tuple):
#             print(message)
#         else:
#             message.pretty_print()


# # text_input = input("질문을 입력해주세요.: ")
# with MongoDBSaver.from_conn_string(MONGODB_URI) as checkpointer:
#     graph = create_react_agent(model, tools=tools, state_modifier=prompt)
#     # graph = create_react_agent(model, tools=tools, checkpointer=checkpointer, state_modifier=prompt)
#     config = {"configurable": {"thread_id": "2"}}
#     # response = graph.invoke(
#     #     {"messages": [("human", text_input)]}, config
#     # )
#     inputs = {"messages": [("user", "오늘이 몇월 몇일이야?")]}
#     print_stream(graph.stream(inputs, stream_mode="values"))

    # print([message.content for message in response.get("messages") if isinstance(message, AIMessage)][-1])
    

