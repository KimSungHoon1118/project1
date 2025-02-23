from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain.schema import HumanMessage, AIMessage

from langchain.chains import retrieval_qa
from langchain.vectorstores import PGVector
from langchain.prompts import PromptTemplate

from langgraph.graph import StateGraph
from dotenv import load_dotenv
load_dotenv()
from rich import print as rprint
from typing import Literal
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

@tool
def get_weather(city: Literal["nyc", "sf"]):
    """Use this to get weather information."""
    if city == "nyc":
        return "It might be cloudy in nyc"
    elif city == "sf":
        return "It's always sunny in sf"
    else:
        raise AssertionError("Unknown city")


tools = [get_weather]
model = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

builder = StateGraph(...)



DB_URI = "postgresql://postgres:1234@localhost/postgres?sslmode=disable"

connection_kwargs = {
    "autocommit": True,
    "prepare_threshold":0,
}

from psycopg import Connection

with Connection.connect(DB_URI, **connection_kwargs) as conn:
    checkpointer = PostgresSaver(conn)
    print(checkpointer)
    # checkpointer.setup()
    config = {"configurable": {"thread_id": "1"}}
    check = checkpointer.get(config)
    rprint(check)
    # rprint(check.get("channel_values").get("messages"))

    # # 데이터에서 HumanMessage만 추출
    # human_messages = [message.content for message in check.get("channel_values").get("messages") if isinstance(message, HumanMessage)]

    # # 데이터에서 AIMessage만 추출
    # ai_messages = [message.content for message in check.get("channel_values").get("messages") if isinstance(message, AIMessage)]

    # # 결과 출력
    # print("Human Messages:")
    # for msg in human_messages:
    #     print(msg)

    # print("\nAI Messages:")
    # for msg in ai_messages:
    #     print(msg)

# from psycopg_pool import ConnectionPool

# with ConnectionPool(
#     conninfo=DB_URI,
#     max_size=20,
#     kwargs=connection_kwargs,
# ) as pool:
#     checkpointer = PostgresSaver(pool)

#     # NOTE: you need to call .setup() the first time you're using your checkpointer
#     checkpointer.setup()

#     graph = create_react_agent(model, tools=tools, checkpointer=checkpointer)
#     config = {"configurable": {"thread_id": "1"}}
#     res = graph.invoke({"messages": [("human", "what's the weather in sf")]}, config)
#     # print("res:",res)
#     checkpoint = checkpointer.get(config)
    
   

# graph = builder.compile(checkpointer=checkpointer)

# from psycopg import Connection

# with Connection.connect(DB_URI, **connection_kwargs) as conn:
#     checkpointer = PostgresSaver(conn)
#     checkpointer.setup()
#     graph = create_react_agent(model, tools=tools, checkpointer=checkpointer)
#     config = {"configurable": {"thread_id": "2"}}
#     res = graph.invoke({"messages": [("human", "whats's the weather in sf")]}, config)

#     checkpoint_tuple = checkpointer.get_tuple(config)