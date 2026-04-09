import json
import os
from datetime import datetime
from litellm import completion

WIKI_PATH = "./data/interview_wiki.json"

EMPTY_WIKI = {
    "경험": [],
    "기술스택": [],
    "강점": [],
    "약점_모순": [],
    "미커버_토픽": [],
    "_updated_at": ""
}


def load_wiki() -> dict:
    if os.path.exists(WIKI_PATH):
        with open(WIKI_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {k: list(v) for k, v in EMPTY_WIKI.items()}


def save_wiki(wiki: dict) -> None:
    os.makedirs("./data", exist_ok=True)
    with open(WIKI_PATH, "w", encoding="utf-8") as f:
        json.dump(wiki, f, ensure_ascii=False, indent=2)


def reset_wiki() -> None:
    save_wiki({k: list(v) for k, v in EMPTY_WIKI.items()})


def _set_api_key(model_name: str, api_key: str) -> None:
    if "anthropic" in model_name:
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif "openai" in model_name:
        os.environ["OPENAI_API_KEY"] = api_key
    elif "gemini" in model_name:
        os.environ["GEMINI_API_KEY"] = api_key


def _parse_json_response(content: str) -> dict:
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)


def build_wiki_from_conversation(model_name: str, api_key: str, messages: list) -> tuple[dict | None, str]:
    """
    면접 대화를 분석해서 interview wiki를 생성/업데이트합니다.
    Returns: (updated_wiki, error_message)
    """
    conversation_text = "\n".join(
        f"[{m['role']}]: {m['content']}"
        for m in messages
        if m["role"] != "system"
    )

    if not conversation_text.strip():
        return None, "대화 내용이 없습니다."

    prompt = f"""다음 면접 대화를 분석해서 아래 JSON 형식으로 정보를 추출해줘.
반드시 유효한 JSON만 출력하고 다른 텍스트는 절대 포함하지 마.

대화:
{conversation_text}

출력 형식:
{{
  "경험": ["지원자가 언급한 구체적인 경험/프로젝트 항목들"],
  "기술스택": ["지원자가 언급한 기술, 언어, 프레임워크들"],
  "강점": ["대화에서 드러난 지원자의 강점들"],
  "약점_모순": ["모호하게 답변하거나 부족해 보이는 부분들"],
  "미커버_토픽": ["아직 다루지 않은 중요한 면접 토픽들 (예: 시스템 디자인, 갈등 해결, 리더십 등)"]
}}"""

    try:
        _set_api_key(model_name, api_key)

        response = completion(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.choices[0].message.content
        new_data = _parse_json_response(raw)

        # 기존 wiki와 병합 (중복 제거)
        wiki = load_wiki()
        for key in EMPTY_WIKI:
            if key in new_data and isinstance(new_data[key], list):
                wiki[key] = list(dict.fromkeys(wiki[key] + new_data[key]))

        wiki["_updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_wiki(wiki)
        return wiki, ""

    except json.JSONDecodeError as e:
        return None, f"Wiki 파싱 실패 (JSON 오류): {e}"
    except Exception as e:
        return None, f"Wiki 생성 실패: {e}"


def wiki_to_context_string(wiki: dict) -> str:
    """Wiki를 system prompt에 주입할 텍스트로 변환합니다."""
    content_keys = [k for k in EMPTY_WIKI if k != "_updated_at"]
    if not any(wiki.get(k) for k in content_keys):
        return ""

    lines = ["[지원자 Wiki - 이전 면접에서 파악된 정보]"]

    label_map = {
        "경험": "경험/프로젝트",
        "기술스택": "기술스택",
        "강점": "강점",
        "약점_모순": "약점/모순 (집중 공략 필요)",
        "미커버_토픽": "미커버 토픽 (반드시 질문할 것)",
    }

    for key, label in label_map.items():
        items = wiki.get(key, [])
        if items:
            lines.append(f"\n{label}:")
            lines.extend(f"  - {item}" for item in items)

    return "\n".join(lines)
