# conversation_manager.py
class ConversationManager:
    def __init__(self, gpt_manager):
        self.gpt_manager = gpt_manager

    def show_message(self, message, use_gpt=True):
        """사용자에게 메시지를 보여줍니다."""
        if use_gpt:
            print(f"GPT: {message}")
        else:
            print(message)

    def prompt_user(self, prompt):
        """사용자로부터 입력을 받습니다."""
        return input(prompt)
