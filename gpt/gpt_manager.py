from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from dotenv import load_dotenv
import os
load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")

class GPTManager:
    def __init__(self, system_role_content: str = None):
        """
        GPTManager: LangChain 및 ChatOpenAI 기반의 대화 매니저 클래스.
        
        Args:
            system_role_content (str): GPT의 역할을 정의하는 시스템 메시지.
        """
        # 시스템 메시지 기본값 설정
        self.system_message = system_role_content or (
            "당신은 여행 플래너 역할의 GPT입니다. "
            "사용자의 질문에 친절하게 답변하고, 대화를 통해 "
            "최적의 여행 계획을 제안해주세요."
        )

        # 대화 히스토리 관리 객체 생성
        self.message_history = ChatMessageHistory()

        # LLM 설정 (ChatOpenAI 인스턴스 생성)
        self.llm = ChatOpenAI(
            temperature=0.7,
            api_key = OPENAI_KEY,
            model="gpt-4o-mini"
        )

        # 세션 히스토리를 반환하는 함수 정의
        def get_session_history():
            return self.message_history

        # RunnableWithMessageHistory 초기화
        self.chain = RunnableWithMessageHistory(
            runnable=self.llm,
            get_session_history=get_session_history
        )

    def add_user_message(self, user_message: str):
        """
        사용자 메시지를 대화 히스토리에 추가.
        
        Args:
            user_message (str): 사용자 입력 메시지.
        """
        self.message_history.add_user_message(user_message)

    def add_assistant_message(self, assistant_message: str):
        """
        GPT 응답 메시지를 대화 히스토리에 추가.
        
        Args:
            assistant_message (str): GPT가 생성한 메시지.
        """
        self.message_history.add_ai_message(assistant_message)

    def get_response_from_gpt(self):
        """
        GPT로부터 응답을 생성하여 반환.
        
        Returns:
            str: GPT가 생성한 응답 메시지 (문자열).
        """
        # 시스템 메시지로 프롬프트 템플릿 생성
        prompt = PromptTemplate.from_template(self.system_message)

        # 프롬프트 텍스트 생성
        prompt_text = prompt.format()

        # GPT 응답 생성
        response = self.chain.invoke({"input": prompt_text})

        # 응답을 대화 히스토리에 추가
        self.add_assistant_message(response)

        # 문자열로 반환
        return response.content
