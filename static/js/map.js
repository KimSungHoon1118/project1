var selectedSpots = JSON.parse(localStorage.getItem('selectedSpots')) || [];

function initMap() {
    kakao.maps.load(function() {
        if (selectedSpots.length === 0) {
            console.log("저장된 위치 데이터가 없습니다.");
            return;
        }

        var map = new kakao.maps.Map(document.getElementById('map'), {
            center: new kakao.maps.LatLng(selectedSpots[0].latitude, selectedSpots[0].longitude),
            level: 5
        });

        var bounds = new kakao.maps.LatLngBounds();
        var spotListContainer = document.getElementById("spot-list");
        spotListContainer.innerHTML = "";

        selectedSpots.forEach(function(spot, index) {
            var position = new kakao.maps.LatLng(spot.latitude, spot.longitude);
            var marker = new kakao.maps.Marker({
                position: position,
                map: map,
                title: spot.name
            });

            var infowindow = new kakao.maps.InfoWindow({
                content: `<div style="padding:5px;font-size:12px;">${spot.name}</div>`
            });
            kakao.maps.event.addListener(marker, 'mouseover', function() {
                infowindow.open(map, marker);
            });
            kakao.maps.event.addListener(marker, 'mouseout', function() {
                infowindow.close();
            });
            
            kakao.maps.event.addListener(marker, 'click', function() {
                document.getElementById("spot-" + index).scrollIntoView({ behavior: 'smooth' });
            });

            bounds.extend(position);

            var spotItem = document.createElement("div");
            spotItem.className = "spot-item";
            spotItem.id = "spot-" + index;
            spotItem.innerHTML = `
                <img src="${spot.image_url}" alt="${spot.name}">
                <div>
                    <h3><a href="#" onclick="openPopup('${spot.name}'); return false;">${spot.name}</a></h3>
                    <p><strong>주소:</strong> ${spot.address}</p>
                    <p>${spot.description}</p>
                </div>
            `;
            spotListContainer.appendChild(spotItem);
        });

        map.setBounds(bounds);
    });
}
// window.onload = function() {
//     if (window.kakao && kakao.maps) {
//         initMap();
//     } else {
//         setTimeout(initMap, 500);
//     }
// };

async function openPopup(name) {
    document.getElementById("popup-title").innerText = name;
    document.getElementById("popup-content").innerText = name + "에 대한 상세 정보 검색 중...";
    document.getElementById("popup-overlay").style.display = "block";
    document.getElementById("popup").style.display = "block";
    try {
        let response = await fetch(`/api/tour/detail?name=${name}`);
        let data = await response.json();
        console.log("API 응답:", data);
        if (Array.isArray(data) && data.length > 0) {
            document.getElementById("popup-content").innerHTML = `
                <img src="${data[0].image_url}" alt="${data[0].name}" style="width:100%; max-height:300px; object-fit:cover; border-radius:10px;">
                <h3>${data[0].name}</h3>
                <p><strong>주소:</strong> ${data[0].address}</p>
                <p>${data[0].description}</p>
            `;
        } else {
            document.getElementById("popup-content").innerText = "상세 정보를 찾을 수 없습니다.";
        }
    } catch (error) {
        console.error("API 호출 오류:", error);
        document.getElementById("popup-content").innerText = "정보를 가져오는 데 실패했습니다.";
    }
}

function closePopup() {
    document.getElementById("popup-overlay").style.display = "none";
    document.getElementById("popup").style.display = "none";
}

window.onload = function() {
    if (window.kakao && kakao.maps) {
        initMap();
    } else {
        setTimeout(initMap, 500);
    }
};