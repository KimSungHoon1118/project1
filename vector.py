from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings
from fastapi import FastAPI
from dotenv import load_dotenv
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
import requests
from env import get_env_vars

load_dotenv()
env_vars = get_env_vars()
KAKAO_API_KEY = env_vars["KAKAO_API_KEY"]
app = FastAPI()

regions_list = ["서울", "부산", "대구","춘천","강릉","공주","전주","경주","통영","제주특별자치도"]

def extract_tourist_spot_metadata(content):
    """
    PDF 텍스트에서 관광지명, 주소, 이미지 및 개요 정보를 추출
    :param content: 텍스트 내용 (page_content)
    :return: 메타데이터 리스트 (각 관광지 정보를 개별적으로 반환)
    """
    metadata_list = []
    
    # 관광지 정보 패턴
    pattern = re.compile(r'-\s*(.+?)\s*주소:\s*(.+?)\s*이미지:\s*(.+?)\s*개요:\s*(.+?)(?=-\s|\Z)', re.DOTALL)
    matches = pattern.findall(content)

    for match in matches:
        metadata = {
            "관광지명": match[0].strip(),
            "주소": match[1].strip(),
            "이미지": match[2].strip(),
            "개요": match[3].strip()
        }
        metadata_list.append(metadata)

    return metadata_list


def extract_tourist_spot_metadata_with_pages(documents):
    """
    PDF 페이지별로 처리하면서 개요가 여러 페이지에 걸친 경우 병합
    :param documents: 페이지별 문서 리스트
    :return: 관광지 메타데이터 리스트
    """
    full_text = "\n".join([doc.page_content for doc in documents])  # 모든 페이지 병합
    metadata_list = extract_tourist_spot_metadata(full_text)  # 기존 메타데이터 추출 함수 재활용
    return metadata_list

def vectorize_pdf_with_metadata(pdf_path, vectorstore_path, regions_list):
    """
    PDF 데이터를 벡터화하고 텍스트에서 지역명과 관광지 정보를 추출하여 메타데이터에 추가
    :param pdf_path: PDF 파일 경로
    :param vectorstore_path: 저장할 벡터 저장소 경로
    :param regions_list: 지역 리스트
    """
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    # 개요 병합 및 메타데이터 추출
    spot_metadata_list = extract_tourist_spot_metadata_with_pages(documents)

    all_documents = []

    for metadata in spot_metadata_list:
        matched_region = next((region for region in regions_list if region in metadata["개요"]), "기타")

        # Splitter로 개요를 분리
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, add_start_index=True
        )
        split_texts = text_splitter.split_text(metadata["개요"])

        # 분리된 텍스트를 개별 문서로 변환
        for i, chunk in enumerate(split_texts):
            doc_metadata = metadata.copy()  # 메타데이터 복사
            doc_metadata["chunk_id"] = i  # 각 chunk에 ID 부여
            doc_metadata["지역"] = matched_region

            new_doc = Document(
                page_content=chunk,
                metadata=doc_metadata
            )
            all_documents.append(new_doc)

    # 벡터화 및 저장
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vectorstore = FAISS.from_documents(all_documents, embeddings)
    vectorstore.save_local(vectorstore_path)
    print(f"벡터 저장 완료: {vectorstore_path}")

# PDF 벡터화 및 저장 실행
# vectorize_pdf_with_metadata("tourist_spots.pdf", "vectorstore", regions_list)

from langchain.vectorstores import FAISS

# 메타데이터 기반 검색
def search_tourist_spots_with_metadata(query, vectorstore_path, keyword, k=35):
    """
    메타데이터를 활용한 유사 검색
    :param query: 검색어
    :param vectorstore_path: 벡터 저장소 경로
    :param region: 지역 필터 (예: "서울")
    :param k: 반환할 검색 결과 개수
    :return: 검색 결과 리스트
    """
    # 저장된 벡터 저장소 로드
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vectorstore = FAISS.load_local(vectorstore_path, embeddings, allow_dangerous_deserialization=True)

    # 검색 실행
    results_with_scores = vectorstore.similarity_search_with_score(query, k=k)
    
    # # 메타데이터 필터링 (지역 기반)
    # filtered_results = [
    #     (result, score) for result, score in results_with_scores
    #     if result.metadata.get("지역") == region
    # ]
    # 메타데이터 필터링 (지역 또는 주소에 키워드 포함)
    filtered_results = [
        (result, score) for result, score in results_with_scores
        if keyword.lower() in result.metadata.get("지역", "").lower() or keyword.lower() in result.metadata.get("주소", "").lower()
    ]
    # filtered_results = sorted(filtered_results, key=lambda x: x[1], reverse=True)[:5]
     # 결과 포맷팅
    formatted_results = [
        {
            "지역": result.metadata.get("지역"),
            "관광지명": result.metadata.get("관광지명", "알 수 없음"),
            "주소": result.metadata.get("주소", "알 수 없음"),
            "이미지": result.metadata.get("이미지", "알 수 없음"),
            "개요": result.metadata.get("개요", "알 수 없음"),
            "점수": score,
        }
        for result, score in filtered_results
    ]
            
    return formatted_results

# # 검색 테스트
# query = "서울 관광 명소"
# keyword = "서울"  # 검색할 지역
# results = search_tourist_spots_with_metadata(query, "vectorstore", keyword, k=30)

# # 결과 출력
# for i, res in enumerate(results):
#     print(f"결과 {i+1}:")
#     print(f"지역: {res['지역']}")
#     print(f"관광지명: {res['관광지명']}")
#     print(f"주소: {res['주소']}")
#     print(f"이미지: {res['이미지']}")
#     print(f"개요: {res['개요']}")
#     print(f"점수: {res['점수']}\n")

# api로 장소이름으로 좌표 가져오기
def get_coordinates_by_name(name):
    """
    Kakao Maps API를 사용하여 장소 이름으로 좌표를 가져옴
    :param name: 장소 이름
    :return: (위도, 경도) 또는 None
    """
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": name}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data["documents"]:
            # 첫 번째 결과의 좌표 반환
            return data["documents"][0]["y"], data["documents"][0]["x"]
    except Exception as e:
        print(f"Error fetching coordinates for {name}: {e}")
    return None, None


@app.get("/search_spots")
def search_spots(query: str):
    results = search_tourist_spots_with_metadata(query, "vectorstore")
    return {"results": [res.page_content for res in results]}



def load_vectorstore(vectorstore_path):
    """
    저장된 FAISS 벡터 저장소 로드
    :param vectorstore_path: 벡터 저장소 경로
    :return: 로드된 FAISS 객체
    """
    # OpenAI 임베딩 모델 초기화
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    # FAISS 저장소 로드
    vectorstore = FAISS.load_local(vectorstore_path, embeddings, allow_dangerous_deserialization=True)
    return vectorstore



# # 벡터 저장소 로드
# vectorstore_path = "vectorstore"
# vectorstore = load_vectorstore(vectorstore_path)

# # 특정 조건(예: 지역)으로 검색
# desired_region = "서울"  # 원하는 조건
# docstore_dict = vectorstore.docstore._dict
# count = 0
# for doc_id, doc in docstore_dict.items():
#     if doc.metadata.get("지역") == desired_region:  # 조건에 맞는 문서만 출력
#         print(f"문서 ID: {doc_id}")
#         print(f"내용: {doc.page_content}")
#         print(f"메타데이터: {doc.metadata}")
#         count+=1
#         if count == 10:
#             break

def generate_travel_plan(location, duration, search_results):
    """
    OpenAI 모델을 사용하여 여행 계획 생성
    :param location: 여행지
    :param duration: 여행 기간
    :param search_results: 검색된 관광지 메타데이터 리스트
    :return: 생성된 여행 계획 (JSON 형식)
    """
    travel_plan = {"location": f"{location} ({duration})", "여행코스": {}}
    
    try:
        day = 1
        daily_plan = []

        for spot in search_results:
            # 좌표 가져오기
            lat, lng = get_coordinates_by_name(spot["관광지명"])
            
            # JSON 데이터에 추가
            daily_plan.append({
                "여행지": spot["관광지명"],
                "설명": spot["개요"],
                "주소": spot["주소"],
                "좌표": f"{lat}, {lng}" if lat and lng else "좌표 정보 없음"
            })

            # 하루에 5개씩 채우고 다음 날로 넘김
            if len(daily_plan) == 5:
                travel_plan["여행코스"][f"{day}일"] = daily_plan
                daily_plan = []
                day += 1

        # 남은 일정 추가
        if daily_plan:
            travel_plan["여행코스"][f"{day}일"] = daily_plan

        return travel_plan
    except Exception as e:
        print(f"Error: {e}")
        return None
    
