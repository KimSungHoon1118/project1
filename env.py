from dotenv import load_dotenv
import os

load_dotenv()

def get_env_vars(key=None):
    env_vars = {
        "KAKAO_API_KEY": os.getenv("KAKAO_API_KEY"),
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
        "NAVER_CLIENT_ID": os.getenv("NAVER_CLIENT_ID"),
        "NAVER_CLIENT_SECRET": os.getenv("NAVER_CLIENT_SECRET"),
        "REST_API_KEY": os.getenv("REST_API_KEY"),
        "SERVICE_KEY": os.getenv("SERVICE_KEY"),
        "REDIRECT_URI": os.getenv("REDIRECT_URI"),
    }
    if key:
        return env_vars.get(key)  # 특정 키 반환
    return env_vars  # 모든 키 반환