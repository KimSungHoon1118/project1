# travel_info.py

class TravelInfo:
    def __init__(self):
        self.region = None           # 여행 지역
        self.travel_days = None      # 여행 일정(며칠짜리)
        self.num_people = None       # 여행 인원
        self.selected_destinations = []  # 선택한 여행지 목록
        self.restaurant_preference = None  # 선호 음식 종류 또는 분위기
        self.selected_restaurants = []     # 선택한 맛집(식당, 카페, 베이커리 등)
        self.activity_theme = None         # 선호 테마/활동(예: 액티비티, 전시 등)
        self.selected_activities = []      # 실제 선택한 활동/장소

    def set_region(self, region: str):
        self.region = region

    def set_travel_days(self, days: str):
        self.travel_days = days

    def set_num_people(self, num: int):
        self.num_people = num

    def add_destination(self, destination: str):
        self.selected_destinations.append(destination)

    def set_restaurant_preference(self, preference: str):
        self.restaurant_preference = preference

    def add_restaurant(self, restaurant: str):
        if restaurant not in self.selected_restaurants:
            self.selected_restaurants.append(restaurant)

    def set_activity_theme(self, theme: str):
        self.activity_theme = theme

    def add_activity(self, activity: str):
        self.selected_activities.append(activity)

    def __str__(self):
        """
        디버깅이나 요약을 위해, 현재 TravelInfo 내용을 문자열로 반환
        """
        info = (
            f"여행 지역: {self.region}\n"
            f"여행 일정: {self.travel_days}\n"
            f"여행 인원: {self.num_people}\n"
            f"선택한 여행지: {self.selected_destinations}\n"
            f"음식 선호도: {self.restaurant_preference}\n"
            f"선택한 맛집: {self.selected_restaurants}\n"
            f"선택한 테마/활동: {self.selected_activities}\n"
        )
        return info