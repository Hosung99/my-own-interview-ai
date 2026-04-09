import json
import os
from datetime import datetime
from dotenv import load_dotenv
from litellm import completion
from core import CLAUDE_CLI_MODEL, CODEX_CLI_MODEL, _run_cli

load_dotenv()

WIKI_PATH = "./data/interview_wiki.json"

SESSION_KEYS = ["경험", "기술스택", "강점", "약점_모순", "미커버_토픽"]


def load_wiki() -> dict:
    """wiki 전체 로드. 구조: {"sessions": [...]}"""
    if os.path.exists(WIKI_PATH):
        with open(WIKI_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 구버전 호환: 세션 구조가 아니면 마이그레이션
            if "sessions" not in data:
                session = {k: data.get(k, []) for k in SESSION_KEYS}
                session["date"] = data.get("_updated_at", "")
                session["id"] = 1
                return {"sessions": [session]}
            return data
    return {"sessions": []}


def save_wiki(wiki: dict) -> None:
    os.makedirs("./data", exist_ok=True)
    with open(WIKI_PATH, "w", encoding="utf-8") as f:
        json.dump(wiki, f, ensure_ascii=False, indent=2)


def reset_wiki() -> None:
    save_wiki({"sessions": []})


def delete_session(session_id: int) -> None:
    """특정 세션을 삭제하고 나머지 세션의 id를 재정렬합니다."""
    wiki = load_wiki()
    sessions = [s for s in wiki["sessions"] if s["id"] != session_id]
    for i, session in enumerate(sessions, start=1):
        session["id"] = i
    wiki["sessions"] = sessions
    save_wiki(wiki)


def _parse_json_response(content: str) -> dict:
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)


def build_wiki_from_conversation(model_name: str, messages: list) -> tuple[dict | None, str]:
    """
    면접 대화를 분석해서 새 세션으로 wiki에 추가합니다.
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
  "미커버_토픽": ["아직 다루지 않은 중요한 면접 토픽들"],
  "평점": {{
    "점수": 3.5,
    "총평": "전반적인 면접 평가 한 줄 요약"
  }}
}}"""

    try:
        if model_name in (CLAUDE_CLI_MODEL, CODEX_CLI_MODEL):
            cli = "claude" if model_name == CLAUDE_CLI_MODEL else "codex"
            flag = "-p" if model_name == CLAUDE_CLI_MODEL else "-q"
            raw = _run_cli([cli, flag, prompt])
        else:
            response = completion(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content

        new_data = _parse_json_response(raw)

        wiki = load_wiki()
        session_id = len(wiki["sessions"]) + 1
        new_session = {
            "id": session_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        for key in SESSION_KEYS:
            new_session[key] = new_data.get(key, []) if isinstance(new_data.get(key), list) else []
        rating = new_data.get("평점", {})
        new_session["평점"] = {
            "점수": float(rating.get("점수", 0)) if rating else 0,
            "총평": rating.get("총평", "") if rating else "",
        }

        wiki["sessions"].append(new_session)
        save_wiki(wiki)
        return wiki, ""

    except json.JSONDecodeError as e:
        return None, f"Wiki 파싱 실패 (JSON 오류): {e}"
    except Exception as e:
        return None, f"Wiki 생성 실패: {e}"


def wiki_to_context_string(wiki: dict) -> str:
    """모든 세션을 합산해 system prompt에 주입할 텍스트로 변환합니다."""
    sessions = wiki.get("sessions", [])
    if not sessions:
        return ""

    # 전체 세션에서 항목 누적 (중복 제거)
    aggregated = {key: [] for key in SESSION_KEYS}
    for session in sessions:
        for key in SESSION_KEYS:
            for item in session.get(key, []):
                if item not in aggregated[key]:
                    aggregated[key].append(item)

    if not any(aggregated.values()):
        return ""

    lines = [f"[지원자 Wiki - {len(sessions)}회 면접 누적 정보]"]
    label_map = {
        "경험": "경험/프로젝트",
        "기술스택": "기술스택",
        "강점": "강점",
        "약점_모순": "약점/모순 (집중 공략 필요)",
        "미커버_토픽": "미커버 토픽 (반드시 질문할 것)",
    }
    for key, label in label_map.items():
        items = aggregated[key]
        if items:
            lines.append(f"\n{label}:")
            lines.extend(f"  - {item}" for item in items)

    return "\n".join(lines)
