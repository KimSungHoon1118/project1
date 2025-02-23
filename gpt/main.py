# main.py

from fastapi import APIRouter
import os
from dotenv import load_dotenv
import logging  # 로깅 모듈 임포트

# Load environment variables


# 로깅 설정: WARNING 이상의 수준만 콘솔에 출력
logging.basicConfig(
    level=logging.WARNING,  # WARNING 이상만 표시
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

import requests
from .gpt_manager import GPTManager
from .conversation_manager import ConversationManager
from .travel_info import TravelInfo
from .naver_api import naver_local_search
from .itinerary_planner import create_itinerary

gpt = APIRouter()

@gpt.get("/api/gpt")
async def main():
    # GPT 매니저 생성
    system_role_text = (
        "당신은 여행 플래너 역할의 GPT입니다. "
        "사용자와 대화를 통해 여행 지역, 일정, 인원, 취향 등을 파악하고, "
        "사용자가 선택한 장소 주변의 맛집/카페 정보를 안내해주세요."
        "당신의 성격은 꼼꼼하고, 완벽한 성격이며 모르는게 없습니다."
        "당신은 모르는 내용에 대하여 절대 거짓말을 하지않습니다."
    )
    gpt_manager = GPTManager(system_role_content=system_role_text)

    # ConversationManager
    cm = ConversationManager(gpt_manager)

    # TravelInfo
    travel_info = TravelInfo()

    # 환영인사
    cm.show_message("안녕하세요! 저는 여행 플래너 GPT 챗봇입니다. 여행 계획을 도와드릴게요.", use_gpt=False)

    # 지역 입력
    region = cm.prompt_user("먼저, 여행하실 지역은 어디인가요?")
    travel_info.set_region(region)

    # 일정 입력
    days = cm.prompt_user("몇 박 몇 일로 여행하시나요? (예: 2박3일)")
    travel_info.set_travel_days(days)

    # 여행 인원
    num_str = cm.prompt_user("여행 인원은 총 몇 명인가요?")
    try:
        num_people = int(num_str)
    except ValueError:
        num_people = 1
    travel_info.set_num_people(num_people)

    # 1) 지역 대표 여행지 검색 & 선택
    cm.show_message(f"이제 '{region}' 지역의 대표 여행지를 검색합니다...")
    destination_results = naver_local_search(f"{region} 관광지", display=10)  # display=10으로 변경
    if destination_results:
        msg = "다음은 검색된 여행지 목록입니다:\n"
        for i, item in enumerate(destination_results, start=1):
            msg += f"{i}. {item['title']} - {item['address']}\n"
        cm.show_message(msg, use_gpt=False)

        sel = cm.prompt_user("가보고 싶은 여행지가 있으면 번호(쉼표 구분)로 입력해주세요. (예: 1,3)")
        if sel:
            try:
                indices = [int(x.strip()) for x in sel.split(",")]
                for i in indices:
                    if 1 <= i <= len(destination_results):
                        travel_info.add_destination(destination_results[i-1]['title'])
            except ValueError:
                cm.show_message("잘못된 입력입니다. 번호만 입력해주세요.", use_gpt=False)

    # 2) 테마/액티비티 선택 (사용자 요청에 따라)
    see_theme = cm.prompt_user("특별히 해보고 싶은 활동(테마)이 있나요? (예/아니오)")
    if see_theme.lower() in ["예", "네", "y", "yes"]:
        theme = cm.prompt_user("원하시는 테마/활동을 알려주세요:")
        travel_info.set_activity_theme(theme)

        # 검색
        cm.show_message(f"'{region}' 지역에서 '{theme}' 관련 장소를 검색합니다...", use_gpt=False)
        activity_results = naver_local_search(f"{region} {theme}", display=10)
        if activity_results:
            amsg = "다음은 활동/테마 장소 후보입니다:\n"
            for i, item in enumerate(activity_results, start=1):
                amsg += f"{i}. {item['title']} - {item['address']}\n"
            cm.show_message(amsg, use_gpt=False)

            sel_activity = cm.prompt_user("마음에 드는 곳이 있으면 번호(쉼표)로 선택해주세요.")
            if sel_activity:
                try:
                    a_indices = [int(x.strip()) for x in sel_activity.split(",")]
                    for i in a_indices:
                        if 1 <= i <= len(activity_results):
                            travel_info.add_activity(activity_results[i-1]['title'])
                except ValueError:
                    cm.show_message("잘못된 입력입니다. 번호만 입력해주세요.", use_gpt=False)
    else:
        cm.show_message("추가 테마/활동은 없다고 하셨습니다.", use_gpt=False)

    # === 여기서부터가 **중요**: 각 장소별 맛집/카페 검색 ===

    # (A) 사용자에게 음식 선호도 및 "각 장소 주변 맛집/카페를 보고 싶으신가요?" 질문
    see_nearby_food = cm.prompt_user("선택하신 장소 주변의 맛집/카페 정보를 확인하시겠습니까? (예/아니오)")
    if see_nearby_food.lower() in ["예", "네", "y", "yes"]:
        # 음식 선호도 입력
        food_preference = cm.prompt_user("원하시는 음식 종류나 분위기가 있으신가요? (예: 한식, 양식, 중식, 일식, 디저트 등) Enter를 누르면 생략됩니다:")
        if food_preference:
            travel_info.set_restaurant_preference(food_preference)
            cm.show_message(f"선호도에 따라 '{food_preference}' 관련 장소를 우선적으로 검색합니다.", use_gpt=False)
        else:
            cm.show_message("특별한 음식 선호도는 없다고 하셨습니다.", use_gpt=False)

        # 검색 및 추천 함수 정의
        def search_and_recommend(cm, travel_info, location, preference):
            recommended = set()

            # 1. 선호도에 맞는 식당 4곳 검색
            if preference:
                pref_query = f"{location} {preference}"
                pref_results = naver_local_search(pref_query, display=10)  # 충분히 많은 결과를 가져와서 중복 제거
                pref_restaurants = pref_results[:4] if len(pref_results) >=4 else pref_results
            else:
                pref_restaurants = []

            # 2. 일반 맛집 6곳 검색
            general_query = f"{location} 맛집"
            general_results = naver_local_search(general_query, display=15)  # 충분히 많은 결과를 가져와서 중복 제거
            general_restaurants = []
            for res in general_results:
                if res['title'] not in [r['title'] for r in pref_restaurants]:
                    general_restaurants.append(res)
                if len(general_restaurants) >=6:
                    break

            # 합친 리스트
            combined_restaurants = pref_restaurants + general_restaurants

            # 중복 제거 (이미 추가된 식당은 제외)
            unique_restaurants = []
            for res in combined_restaurants:
                if res['title'] not in recommended:
                    unique_restaurants.append(res)
                    recommended.add(res['title'])

            # 식당 출력
            if unique_restaurants:
                msg_rest = f"\n[ {location} 주변 추천 식당 ]\n"
                for idx, item in enumerate(unique_restaurants, start=1):
                    msg_rest += f"{idx}. {item['title']} - {item['address']}\n"
                cm.show_message(msg_rest, use_gpt=False)

                # 사용자 선택
                sel_rest = cm.prompt_user("가고 싶은 식당이 있으면 번호(쉼표)로 선택해주세요. Enter면 넘어갑니다:")
                if sel_rest:
                    try:
                        r_indices = [int(x.strip()) for x in sel_rest.split(",")]
                        for ri in r_indices:
                            if 1 <= ri <= len(unique_restaurants):
                                travel_info.add_restaurant(unique_restaurants[ri-1]['title'])
                    except ValueError:
                        cm.show_message("잘못된 입력입니다. 번호만 입력해주세요.", use_gpt=False)

            # 3. 카페/베이커리 6곳 추천 (선호도 적용 가능)
            if preference:
                pref_cafe_query = f"{location} {preference} 카페"
                pref_cafe_results = naver_local_search(pref_cafe_query, display=10)
                pref_cafes = pref_cafe_results[:4] if len(pref_cafe_results) >=4 else pref_cafe_results
            else:
                pref_cafes = []

            general_cafe_query = f"{location} 카페 베이커리"
            general_cafe_results = naver_local_search(general_cafe_query, display=15)
            general_cafes = []
            for res in general_cafe_results:
                if res['title'] not in [c['title'] for c in pref_cafes]:
                    general_cafes.append(res)
                if len(general_cafes) >=6:
                    break

            combined_cafes = pref_cafes + general_cafes

            # 중복 제거
            unique_cafes = []
            for res in combined_cafes:
                if res['title'] not in recommended:
                    unique_cafes.append(res)
                    recommended.add(res['title'])

            # 카페 출력
            if unique_cafes:
                msg_cafe = f"\n[ {location} 주변 추천 카페·베이커리 ]\n"
                for idx, item in enumerate(unique_cafes, start=1):
                    msg_cafe += f"{idx}. {item['title']} - {item['address']}\n"
                cm.show_message(msg_cafe, use_gpt=False)

                # 사용자 선택
                sel_cafe = cm.prompt_user("가고 싶은 카페가 있으면 번호(쉼표)로 선택해주세요. Enter면 넘어갑니다:")
                if sel_cafe:
                    try:
                        c_indices = [int(x.strip()) for x in sel_cafe.split(",")]
                        for ci in c_indices:
                            if 1 <= ci <= len(unique_cafes):
                                travel_info.add_restaurant(unique_cafes[ci-1]['title'])
                    except ValueError:
                        cm.show_message("잘못된 입력입니다. 번호만 입력해주세요.", use_gpt=False)

        # (B) 'selected_destinations'에 대한 식당 및 카페 추천
        for destination in travel_info.selected_destinations:
            cm.show_message(f"\n[ {destination} 주변 맛집/카페 추천 ]", use_gpt=False)
            search_and_recommend(cm, travel_info, destination, travel_info.restaurant_preference)

        # (C) 'selected_activities'에 대한 식당 및 카페 추천
        for activity_place in travel_info.selected_activities:
            cm.show_message(f"\n[ {activity_place} 주변 맛집/카페 추천 ]", use_gpt=False)
            search_and_recommend(cm, travel_info, activity_place, travel_info.restaurant_preference)

    else:
        cm.show_message("각 장소 주변 맛집/카페 정보는 확인하지 않습니다.", use_gpt=False)

    # 이후 GPT에게 최종 요약/분석
    user_summary = (
        "지금까지 수집한 여행 정보는 다음과 같습니다.\n"
        f"{travel_info}\n"
        "이 정보를 바탕으로 여행 일정(코스)을 최적 코스로 제안해 주세요."
    )
    gpt_manager.add_user_message(user_summary)
    gpt_plan = gpt_manager.get_response_from_gpt()
    cm.show_message("[GPT의 여행 일정 제안]\n" + gpt_plan, use_gpt=False)

    # 로컬 일정 생성
    cm.show_message("\n--- 로컬 로직으로 생성한 간단 일정표 ---", use_gpt=False)
    local_plan = create_itinerary(travel_info)
    cm.show_message(local_plan, use_gpt=False)

    # 종료
    cm.show_message("이용해주셔서 감사합니다. 즐거운 여행 되세요!", use_gpt=False)

# if __name__ == "__main__":
#     main()


