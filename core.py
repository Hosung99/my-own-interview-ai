import os
from litellm import completion
from dotenv import load_dotenv

load_dotenv()


def get_interview_response(model_name: str, messages: list) -> str:
    """
    선택된 모델로부터 면접 질문/답변을 받아옵니다.
    API Key는 .env 파일에서 자동으로 로드됩니다.
    model_name 예시: 'anthropic/claude-3-5-sonnet-20240620', 'openai/gpt-4o'
    """
    try:
        response = completion(
            model=model_name,
            messages=messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"
