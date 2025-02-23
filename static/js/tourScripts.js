const locations = ["강릉", "서울", "부산", "대구", "춘천", "공주", "전주", "경주", "통영", "제주특별자치도", "충주"]; // 지역 리스트
const durations = ["당일치기", "1박2일", "2박3일"]; // 기간 리스트




async function fetchSpots(location, duration) {
    // 지역과 기간으로 데이터를 가져오는 API 호출
    const response = await fetch(`/api/tour/spot?location=${location}&duration=${duration}`);
    if (!response.ok) throw new Error(`Failed to fetch data for ${location} ${duration}`);
    return await response.json(); // 데이터 반환
  }
  
  function createSwiperHTML(location, duration) {
    // Swiper 컨테이너 생성
    const containerId = `swiper-container-${location}-${duration}`;
    return `
      <div class="swiper-container ${containerId}">
        <div class="swiper-wrapper"></div>
        <div class="swiper-button-prev"></div>
        <div class="swiper-button-next"></div>
        <div class="swiper-pagination"></div>
      </div>
    `;
  }
  
  function initializeSwiperClickEvents() {
    document.querySelectorAll('.swiper-slide').forEach(slide => {
      slide.addEventListener('click', function () {
        const spotsData = JSON.parse(this.dataset.spots); // 슬라이드의 데이터 가져오기
        localStorage.setItem("selectedSpots", JSON.stringify(spotsData)); // 로컬스토리지 저장
        window.location.href = "/spot-details"; // 상세 페이지로 이동
      });
    });
  }

  function createDaySlide(day, spots) {
    // 각 일차(day)별 슬라이드 생성
    let imagesHTML = "";
    console.log(spots)
    let namesHTML = ""; // 장소 이름 HTML

    spots.slice(0, 5).forEach(spot => {
      const imageUrl = spot.image_url || '/static/images/default.jpg';
      const spotName = spot.name || 'No Name';      
      imagesHTML += `
        <img src="${imageUrl}" alt="${spotName}" style="width: 150px; height: 150px; object-fit: cover; margin: 5px;">
        `;
      // 장소 이름 HTML 추가
      namesHTML += `
      <span style="flex: 1; text-align: center;">${spotName}</span>
        `;
    });
  
    return `
      <div class="swiper-slide">
        <p>여행 Day ${day}</p>
        <div style="display: flex; justify-content: center; flex-wrap: wrap;">${imagesHTML}</div>
        <p style="display: flex; justify-content: space-between; width: 100%; max-width: 1500px; margin: 0 auto; margin-top: 10px;">
          ${namesHTML}
        </p>
      </div>
    `;
  }
  
  async function initializeSwipers() {    
  
    const durationToContainer = {
        "당일치기": "swiper-day-trip",
        "1박2일": "swiper-overnight",
        "2박3일": "swiper-two-nights",
      };
    
      for (const duration of durations) {
        const containerId = durationToContainer[duration];
        const swiperWrapper = document.querySelector(`#${containerId} .swiper-wrapper`);
    
        if (!swiperWrapper) {
          console.error(`Container for ${duration} not found.`);
          continue;
        }
    
        for (const location of locations) {
          const schedules = await fetchSpots(location, duration);
          if (schedules && schedules.length > 0) {
            let groupSize = duration === "1박2일" ? 2 : duration === "2박3일" ? 3 : 1; // 1박2일 → 2개, 2박3일 → 3개
                let groupedSchedules = [];

                // 일정 데이터를 groupSize만큼 묶기
                for (let i = 0; i < schedules.length; i += groupSize) {
                    groupedSchedules.push(schedules.slice(i, i + groupSize));
                }

                groupedSchedules.forEach((group) => {
                    const spotData = JSON.stringify(group.flatMap(schedule => schedule.spots.slice(0, 5))); // JSON 데이터 저장

                    const slideHTML = `
                        <div class="swiper-slide" data-spots='${spotData}'>
                            <p>${location} - ${duration}</p>
                            <div style="display: flex; justify-content: center; flex-wrap: wrap;">
                                ${group
                                    .flatMap(schedule => schedule.spots.slice(0, 5))
                                    .map(
                                        (spot) => `
                                            <div style="text-align: center; margin: 5px;">
                                                <img src="${spot.image_url || '/static/images/default.jpg'}" 
                                                    alt="${spot.name || 'No Name'}" 
                                                    style="width: 250px; height: 250px; object-fit: cover; margin-bottom: 5px;">
                                                <p style="margin: 0; font-size: 20px;">${spot.name || 'No Name'}</p>
                                            </div>
                                        `
                                    )
                                    .join("")}
                            </div>
                        </div>
                    `;
                    swiperWrapper.innerHTML += slideHTML;
                });
            // schedules.forEach(({ spots }) => {
            //   if (spots.length > 0) {
            //     const spotData = JSON.stringify(spots.slice(0, 5)); // JSON 데이터 저장

            //     const slideHTML = `
            //       <div class="swiper-slide"  data-spots='${spotData}'>
            //         <p>${location} - ${duration}</p>
            //         <div style="display: flex; justify-content: center; flex-wrap: wrap;">
            //           ${spots
            //             .slice(0, 5)
            //             .map(
            //               (spot) => `
            //                 <div style="text-align: center; margin: 5px;">
            //                 <img src="${spot.image_url || '/static/images/default.jpg'}" 
            //                     alt="${spot.name || 'No Name'}" 
            //                     style="width: 250px; height: 250px; object-fit: cover; margin-bottom: 5px;">
            //                 <p style="margin: 0; font-size: 20px;">${spot.name || 'No Name'}</p>
            //                 </div>
            //               `
            //             )
            //             .join("")}
            //         </div>
            //       </div>
            //     `;
            //     swiperWrapper.innerHTML += slideHTML;
            //   }
            // });
          }
        }
    
        // Swiper 초기화
        new Swiper(`#${containerId}`, {
          loop: false,
          slidesPerView: 1,
          spaceBetween: 20,
          navigation: {
            nextEl: `#${containerId} .swiper-button-next`,
            prevEl: `#${containerId} .swiper-button-prev`,
          },
          pagination: {
            el: `#${containerId} .swiper-pagination`,
            clickable: true,
          },
          autoplay: {
            delay: 3000,
            disableOnInteraction: false,
          },
        });
        // 클릭 이벤트 추가
        initializeSwiperClickEvents();
    }
  }
  
  document.addEventListener("DOMContentLoaded", initializeSwipers);