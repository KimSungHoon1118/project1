# naver_api.py

import os
import requests
import logging
from typing import List, Dict

# 모듈별 로거 생성
logger = logging.getLogger(__name__)

# 환경 변수에서 API 자격 증명 불러오기
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
    logger.error("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 환경 변수가 설정되지 않았습니다.")
    raise EnvironmentError("Missing NAVER_CLIENT_ID or NAVER_CLIENT_SECRET in environment variables.")

def naver_local_search(query: str, display: int = 10) -> List[Dict]:
    """
    네이버 지역 검색 API에 query를 전달해 결과를 리스트로 반환한다.
    display: 검색 결과 개수 (최대 10)
    """
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
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