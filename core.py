import os
from litellm import completion
from dotenv import load_dotenv

load_dotenv() # load from .env

def get_interview_response(model_name, api_key, messages):
    """
    선택된 모델로부터 면접 질문/답변을 받아옵니다.
    model_name 예시: 'anthropic/claude-3-5-sonnet-20240620', 'openai/gpt-4o'
    """
    try:
        if "anthropic" in model_name:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        elif "openai" in model_name:
            os.environ["OPENAI_API_KEY"] = api_key
        elif "gemini" in model_name:
            os.environ["GEMINI_API_KEY"] = api_key

        response = completion(
            model=model_name,
            messages=messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"