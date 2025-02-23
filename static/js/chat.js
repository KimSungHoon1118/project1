// 메시지 전송 처리
const sendButton = document.getElementById("sendBtn");
const messageInput = document.getElementById("messageInput");
const messagesContainer = document.getElementById("messages");

// 메시지 전송 함수
async function sendMessage() {
        const messageText = messageInput.value.trim();
    if (messageText !== "") {
        // 사용자 메시지
        const userMessage = document.createElement("div");
        userMessage.classList.add("chat-message", "user");
        userMessage.innerHTML = `<div class="message-bubble">${messageText}</div>`;
        messagesContainer.appendChild(userMessage);
        messageInput.value = ""; // 입력창 초기화
        // 자동 스크롤
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        console.log(messageText)
        // 상대방의 답변을 자동으로 추가 (예시)
        try {
            const botMessage = document.createElement("div");
            botMessage.classList.add("chat-message", "bot");
            botMessage.innerHTML = `<div class="message-bubble">잠시만 기다려주세요.. 답변을 가져오는 중입니다.</div>`;
            messagesContainer.appendChild(botMessage);
            // AI 응답 가져오기
            // 로그인 상태 확인 및 thread_id 설정
            const statusResponse = await fetch("/auth/status");
            const statusData = await statusResponse.json();
            console.log(statusData)
            let thread_id = statusData.logged_in ? statusData.google_user_id : statusData.uuid;
            console.log("사용할 thread_id:", thread_id);
            console.log("messageText",messageText)
            const config = {"configurable": {"thread_id": String(thread_id)}}
            // messageTrim = messageText.trim()
            const response = await fetch(`/api/workflow`,{
                method : "POST",
                headers: {
                    'Content-Type': 'application/json'
                },            
                // config = google user id 받기
                body: JSON.stringify({
                    config : config,
                    user_input: messageText,
                })
            })
            // console.log("response:", response)
            const data = await response.json();
            console.log("data:", data)
            // console.log("data.messages:", data.messages)
            // AI 응답 메시지 필터링
            // const count = data.messages.length -1; // 배열의 마지막 인덱스 계산
            // let messages = data.messages.at(-1) || [];
            // console.log("messages:", messages)
            // const aiResponseMessage = messages.find(msg => msg.role === "assistant" && msg.content);
            
            let messages = data.ai_response
            // let messages = data.messages.at(-1).content

            console.log("messages:", messages)
            if (messages) {
            messages = messages.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

            // const aiMessage = aiResponseMessage.content;
            const aiMessage = messages.replace(/\n/g, "<br>"); // 개행을 <br>로 변환
            // AI 답변을 화면에 표시
            // const botMessage = document.createElement("div");
            // botMessage.classList.add("chat-message", "bot");
            botMessage.innerHTML = `<div class="message-bubble">${aiMessage}</div>`;
            messagesContainer.appendChild(botMessage);

            // 자동 스크롤
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            } else {
            console.error("No valid AI response found in messages.");
            }
        } catch (error) {
            console.error("Error fetching AI response:", error);

            // 에러 메시지를 화면에 표시 (선택 사항)
            const errorMessage = document.createElement("div");
            errorMessage.classList.add("chat-message", "bot");
            errorMessage.innerHTML = `<div class="message-bubble">오류가 발생했습니다. 잠시 후 다시 시도해주세요.</div>`;
            messagesContainer.appendChild(errorMessage);

            // 자동 스크롤
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
}
    

    



// Enter 키로 메시지 전송
messageInput.addEventListener("keydown", function(event) {
if (event.key === "Enter") {
    sendMessage();
}
});

// 전송 버튼 클릭 시 메시지 전송
sendButton.addEventListener("click", sendMessage);