document.addEventListener("DOMContentLoaded", async () => {
  fetch("/auth/status")  // 로그인 상태 확인 API 호출
  .then(response => response.json())
  .then(data => {
      const loginDiv = document.getElementById("login");
      if (data.logged_in) {
          // 로그인한 경우, 로그아웃 버튼 표시
          loginDiv.innerHTML = `
              <span>${data.user.name}님, 환영합니다!</span>
              <a href="/auth/logout">로그아웃</a>
          `;
      } else {
          // 로그인하지 않은 경우, 로그인 버튼 유지
          loginDiv.innerHTML = `<a href="/auth/login">로그인</a>`;
      }
  })
  .catch(error => console.error("로그인 상태 확인 실패:", error));
});