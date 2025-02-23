document.addEventListener("DOMContentLoaded", () => {
    const timeFilter = document.getElementById("time-filter");
    const areaFilter = document.getElementById("area-filter");
    const festivalsContainer = document.getElementById("festivals-container");
    const paginationContainer = document.getElementById("pagination");

    let currentPage = 1;
    let initialLoad = true; // 초기 로드 여부 플래그

    // 필터 적용 함수
    const applyFilters = async () => {
        const time = timeFilter.value || null; // 기본값 설정
        const area = areaFilter.value || null; // 기본값 설정
        let apiUrl = `/api/festivals/${area}?page=${currentPage}&limit=9`

        // 필터 조건 추가
        if(time == "default" && area == "all") apiUrl = `/api/festivals?page=${currentPage}&limit=9`;

        if(time == "ongoing") apiUrl = `/api/festivals/ongoing?page=${currentPage}&limit=9`
        else if(time == "upcoming") apiUrl = `/api/festivals/upcoming?page=${currentPage}&limit=9`
        if(time != "default" && area != "all") apiUrl = `/api/festivals/filter/${area}?time=${time}&page=${currentPage}&limit=9`

        try {
            const response = await fetch(apiUrl);
            const data = await response.json();


            // 축제 목록 업데이트
            festivalsContainer.innerHTML = data.data
            .map(
                (festival) => `
                <div class="festival-box">
                            
                <img src="${festival.image_url}" alt="${festival.title}" class="festival-image" />
                <h2>${festival.title}</h2>
                <p>${festival.start_date} ~ ${festival.end_date}</p>
                <p>${festival.location}</p>
                <a href="${festival.detail_link}">상세 보기</a>
                </div>
            `
            )
            .join("");

            // 페이지네이션 업데이트
            paginationContainer.innerHTML = `
                ${data.page > 1
                    ? `<a href="#" class="pagination-button" data-page="${data.page - 1}">이전</a>`
                    : ""
                }
                <span>페이지 ${data.page} / ${data.total_pages}</span>
                ${data.page < data.total_pages
                    ? `<a href="#" class="pagination-button" data-page="${data.page + 1}">다음</a>`
                    : ""
                }
            `;

            // 페이지네이션 버튼 이벤트 추가
            document.querySelectorAll(".pagination-button").forEach((button) => {
                button.addEventListener("click", (event) => {
                    event.preventDefault();
                    currentPage = parseInt(button.dataset.page);
                    applyFilters();
                });
            });

      } catch (error) {
        console.error("Failed to fetch festivals:", error);
      }
    };

    // 이벤트 리스너 추가
    timeFilter.addEventListener("change", () => {
        currentPage = 1; // 페이지를 1로 초기화
        applyFilters();
    });

    areaFilter.addEventListener("change", () => {
        currentPage = 1; // 페이지를 1로 초기화
        applyFilters();
    });

    // 초기 데이터 로드 시 applyFilters 건너뛰기
    if (!initialLoad) {
        applyFilters();
    } else {
        initialLoad = false; // 초기 로드 후 플래그 변경
    }

    // 초기 데이터 로드
    applyFilters();
  });