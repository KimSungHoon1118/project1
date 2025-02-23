# itinerary_planner.py

from .travel_info import TravelInfo

def create_itinerary(travel_info: TravelInfo) -> str:
    """
    TravelInfo에 저장된 정보를 바탕으로
    간단한 텍스트 기반의 여행 일정을 생성하는 예시입니다.
    실제로는 지도 API, 거리/시간 계산 등이 들어가야 합니다.
    """
    region = travel_info.region
    days = travel_info.travel_days
    num_people = travel_info.num_people
    destinations = travel_info.selected_destinations
    restaurants = travel_info.selected_restaurants
    activities = travel_info.selected_activities

    itinerary_text = f"=== {region} 여행 일정표 ===\n"
    itinerary_text += f"여행 기간: {days}\n"
    itinerary_text += f"여행 인원: {num_people}명\n\n"

    # 예시로 1일차 / 2일차로 단순 분리
    itinerary_text += "1일차:\n"
    if destinations:
        # 절반을 첫째 날, 나머지를 둘째 날(매우 단순화)
        mid_point = len(destinations) // 2 if len(destinations) > 1 else len(destinations)
        day1_dest = destinations[:mid_point]
        day2_dest = destinations[mid_point:]

        if day1_dest:
            for d in day1_dest:
                itinerary_text += f" - {d}\n"
        else:
            itinerary_text += " - 방문할 여행지가 없습니다.\n"

        itinerary_text += "\n2일차:\n"
        if day2_dest:
            for d in day2_dest:
                itinerary_text += f" - {d}\n"
        else:
            itinerary_text += " - 방문할 여행지가 없습니다.\n"
    else:
        itinerary_text += " - 방문할 여행지가 없습니다.\n\n"

    itinerary_text += "\n[맛집 및 카페 방문]\n"
    if restaurants:
        for r in restaurants:
            itinerary_text += f" - {r}\n"
    else:
        itinerary_text += " - 방문할 예정인 맛집이 없습니다.\n"

    itinerary_text += "\n[추가 활동]\n"
    if activities:
        for a in activities:
            itinerary_text += f" - {a}\n"
    else:
        itinerary_text += " - 예정된 테마/활동이 없습니다.\n"

    itinerary_text += "\n즐거운 여행 되세요!\n"
    return itinerary_text