import subprocess
from litellm import completion
from dotenv import load_dotenv

load_dotenv()

CLAUDE_CLI_MODEL = "claude-cli"
CODEX_CLI_MODEL = "codex-cli"


def _format_messages_for_cli(messages: list) -> tuple[str, str]:
    """메시지 리스트를 CLI용 system prompt와 대화 텍스트로 변환합니다."""
    system_prompt = ""
    conversation_lines = []

    for m in messages:
        if m["role"] == "system":
            system_prompt = m["content"]
        elif m["role"] == "user":
            conversation_lines.append(f"Human: {m['content']}")
        elif m["role"] == "assistant":
            conversation_lines.append(f"Assistant: {m['content']}")

    return system_prompt, "\n\n".join(conversation_lines)


def _run_cli(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()
    except FileNotFoundError:
        return f"Error: '{cmd[0]}' CLI가 설치되어 있지 않습니다."
    except subprocess.TimeoutExpired:
        return "Error: 응답 시간이 초과되었습니다."


def _get_response_via_claude_cli(messages: list) -> str:
    """claude CLI를 통해 응답을 받습니다 (Claude.ai 구독 사용)."""
    system_prompt, conversation = _format_messages_for_cli(messages)
    prompt = f"{system_prompt}\n\n{conversation}" if system_prompt else conversation
    return _run_cli(["claude", "-p", prompt])


def _get_response_via_codex_cli(messages: list) -> str:
    """codex CLI를 통해 응답을 받습니다 (ChatGPT Plus 구독 사용)."""
    system_prompt, conversation = _format_messages_for_cli(messages)
    prompt = f"{system_prompt}\n\n{conversation}" if system_prompt else conversation
    cmd = ["codex", "-a", "never", "exec", prompt]
    return _run_cli(cmd)


def get_interview_response(model_name: str, messages: list) -> str:
    """
    선택된 모델로부터 면접 응답을 받아옵니다.
    - claude-cli : Claude Code 구독 사용 (API Key 불필요)
    - codex-cli  : OpenAI Codex CLI 구독 사용 (API Key 불필요)
    - 그 외      : .env의 API Key 사용
    """
    if model_name == CLAUDE_CLI_MODEL:
        return _get_response_via_claude_cli(messages)
    if model_name == CODEX_CLI_MODEL:
        return _get_response_via_codex_cli(messages)

    try:
        response = completion(model=model_name, messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"
