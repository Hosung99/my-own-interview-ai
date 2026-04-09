import os
import re
import shutil
import streamlit as st
from dotenv import load_dotenv
from core import get_interview_response
from rag_engine import RAGEngine
from wiki_builder import build_wiki_from_conversation, load_wiki, reset_wiki, wiki_to_context_string
load_dotenv()

os.makedirs("./data", exist_ok=True)

st.set_page_config(page_title="LLM OS Interviewer", layout="wide")
st.title("🤖 나만의 로컬 면접 AI")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "rag" not in st.session_state:
    st.session_state.rag = RAGEngine()
st.session_state.wiki = load_wiki()
if "pdf_processed" not in st.session_state:
    st.session_state.pdf_processed = False
if "processed_filename" not in st.session_state:
    st.session_state.processed_filename = None
if "pending_pdf_path" not in st.session_state:
    st.session_state.pending_pdf_path = None
if "pending_wiki_build" not in st.session_state:
    st.session_state.pending_wiki_build = False
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False
if "awaiting_settings" not in st.session_state:
    st.session_state.awaiting_settings = False
if "difficulty" not in st.session_state:
    st.session_state.difficulty = None
if "field" not in st.session_state:
    st.session_state.field = None


def parse_settings(text: str) -> tuple[str, str]:
    """사용자 입력에서 경력과 분야를 추출합니다. 미매칭 시 기본값 반환."""
    difficulty = "5년차"
    field = "백엔드"

    if re.search(r"10년|시니어", text):
        difficulty = "10년차"
    elif re.search(r"3년|주니어", text):
        difficulty = "3년차"
    elif re.search(r"5년|미들", text):
        difficulty = "5년차"

    if re.search(r"프론트|frontend|front", text, re.IGNORECASE):
        field = "프론트엔드"
    elif re.search(r"풀스택|fullstack|full.stack", text, re.IGNORECASE):
        field = "풀스택"
    elif re.search(r"데이터|ai|머신|ML|딥러닝", text, re.IGNORECASE):
        field = "데이터/AI"
    elif re.search(r"백엔드|backend|back", text, re.IGNORECASE):
        field = "백엔드"

    return difficulty, field


# PDF 분석 대기 중인 파일 처리 (버튼 비활성화 상태에서 실행)
if st.session_state.pending_pdf_path:
    pdf_path = st.session_state.pending_pdf_path
    st.session_state.pending_pdf_path = None
    try:
        with st.spinner("파일 분석 중..."):
            msg = st.session_state.rag.process_pdf(pdf_path)
        if msg.startswith("✅"):
            filename = os.path.basename(pdf_path)
            st.session_state.processed_filename = filename
            st.session_state.pdf_processed = True
            st.session_state.awaiting_settings = True
            greeting = (
                "안녕하세요! 저는 오늘 면접을 진행할 AI 면접관입니다. 이력서를 검토했습니다.\n\n"
                "면접을 시작하기 전에 두 가지를 알려주세요:\n\n"
                "1. **원하시는 면접 난이도** (예: 3년차 / 5년차 / 10년차)\n"
                "2. **분야** (예: 백엔드 / 프론트엔드 / 풀스택 / 데이터·AI)\n\n"
                "예시: `5년차 백엔드`"
            )
            st.session_state.messages.append({"role": "assistant", "content": greeting})
        else:
            st.error(msg)
    finally:
        st.session_state.is_loading = False
elif st.session_state.pending_wiki_build:
    st.session_state.pending_wiki_build = False
    wiki_model = st.session_state.pop("pending_wiki_model", "claude-cli")
    try:
        with st.spinner("Wiki 생성 중..."):
            wiki, error = build_wiki_from_conversation(
                wiki_model, st.session_state.messages
            )
        if error:
            st.error(error)
        else:
            st.session_state.wiki = wiki
            st.success("Wiki 업데이트 완료!")
    finally:
        st.session_state.is_loading = False
else:
    # 처리 대기 중인 작업이 없으면 is_loading 초기화
    # (다른 페이지 이동 후 돌아올 때 stuck 방지)
    st.session_state.is_loading = False


# 사이드바: 설정
with st.sidebar:
    st.header("⚙️ 설정")

    CLI_LABELS = {
        "claude-cli": "Claude (구독 · API Key 불필요)",
        "codex-cli": "OpenAI Codex (구독 · API Key 불필요)",
    }

    model_provider = st.selectbox(
        "모델 선택",
        [
            "claude-cli",
            "codex-cli",
            "openai/gpt-4o",
            "anthropic/claude-3-5-sonnet-20240620",
            "google/gemini-1.5-pro",
        ],
        format_func=lambda m: CLI_LABELS.get(m, m),
    )

    if model_provider == "claude-cli":
        if shutil.which("claude"):
            st.success("✅ Claude Code 감지됨 — 구독 계정으로 실행")
        else:
            st.error("❌ claude CLI 없음 — Claude Code를 먼저 설치하세요")
        auth_ok = shutil.which("claude") is not None
    elif model_provider == "codex-cli":
        if shutil.which("codex"):
            st.success("✅ Codex CLI 감지됨 — 구독 계정으로 실행")
        else:
            st.error("❌ codex CLI 없음 — OpenAI Codex를 먼저 설치하세요 (npm install -g @openai/codex)")
        auth_ok = shutil.which("codex") is not None
    else:
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GEMINI_API_KEY",
        }
        provider = model_provider.split("/")[0]
        env_key = key_map.get(provider, "")
        auth_ok = bool(os.environ.get(env_key))
        if auth_ok:
            st.success(f"✅ {env_key} 로드됨")
        else:
            st.error(f"❌ {env_key} 없음 — .env 파일을 확인하세요")

    # 현재 면접 설정 표시
    if st.session_state.difficulty and st.session_state.field:
        st.divider()
        st.markdown("**🎯 현재 면접 설정**")
        st.markdown(f"- 경력: {st.session_state.difficulty}")
        st.markdown(f"- 분야: {st.session_state.field}")

    st.divider()

    st.header("📄 자료 업로드")
    uploaded_file = st.file_uploader(
        "이력서나 회사 위키(PDF)를 올려주세요",
        type="pdf",
        disabled=st.session_state.is_loading,
    )
    if uploaded_file:
        if st.session_state.processed_filename == uploaded_file.name:
            st.success(f"✅ {uploaded_file.name} 분석 완료")
        elif not st.session_state.is_loading:
            file_path = f"./data/{uploaded_file.name}"
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.pending_pdf_path = file_path
            st.session_state.is_loading = True
            st.rerun()

    st.divider()

    st.header("📖 Interview Wiki")
    btn_disabled = st.session_state.is_loading or not st.session_state.messages
    if st.button("🔚 면접 종료 & Wiki 생성", type="primary", use_container_width=True, disabled=btn_disabled):
        st.session_state.pending_wiki_build = True
        st.session_state.pending_wiki_model = model_provider
        st.session_state.is_loading = True
        st.rerun()

    if st.button("🗑️ Wiki 초기화", use_container_width=True, disabled=st.session_state.is_loading):
        reset_wiki()
        st.session_state.wiki = load_wiki()
        st.session_state.messages = []
        st.session_state.pdf_processed = False
        st.session_state.processed_filename = None
        st.session_state.awaiting_settings = False
        st.session_state.difficulty = None
        st.session_state.field = None
        st.info("Wiki와 대화가 초기화되었습니다.")

    sessions = st.session_state.wiki.get("sessions", [])
    if sessions:
        st.success(f"총 {len(sessions)}개 세션 저장됨")
        st.page_link("pages/wiki.py", label="📖 Wiki 상세 보기 →", use_container_width=True)
    else:
        st.caption("면접 종료 후 Wiki가 생성됩니다.")


# 채팅 UI
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("답변을 입력하세요...", disabled=st.session_state.is_loading):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not auth_ok:
            st.warning("인증 정보가 설정되지 않았습니다. 사이드바를 확인하세요.")
            st.stop()

        # 설정 수집 단계
        if st.session_state.awaiting_settings:
            difficulty, field = parse_settings(prompt)
            st.session_state.difficulty = difficulty
            st.session_state.field = field
            st.session_state.awaiting_settings = False

            confirm = (
                f"알겠습니다! **{difficulty} {field} 개발자** 기준으로 면접을 진행하겠습니다.\n\n"
                f"그럼 시작할게요. 간단하게 **자기소개**를 부탁드릴게요."
            )
            st.markdown(confirm)
            st.session_state.messages.append({"role": "assistant", "content": confirm})

        # 면접 진행 단계
        else:
            difficulty = st.session_state.difficulty or "5년차"
            field = st.session_state.field or "백엔드"

            st.session_state.is_loading = True
            with st.spinner("생각 중..."):
                resume_context = st.session_state.rag.get_relevant_context(prompt)
                wiki_context = wiki_to_context_string(st.session_state.wiki)

                system_instruction = f"""너는 {difficulty} {field} 개발자 출신의 날카로운 기술 면접관이야.
아래 제공된 [이력서 Context]와 [지원자 Wiki]를 바탕으로 면접을 진행해.

규칙:
- 질문은 한 번에 하나씩만 해라.
- 지원자의 답변에서 모순이나 부족한 점이 있으면 꼬리 질문을 던져라.
- Wiki의 [미커버 토픽]은 반드시 다뤄라.
- Wiki의 [약점/모순]은 집중적으로 파고들어라.
- 이미 충분히 다룬 주제는 반복하지 마라.
- {difficulty} 수준에 맞는 깊이로 질문해라.

[이력서 Context]:
{resume_context}

{wiki_context}"""

                full_messages = [{"role": "system", "content": system_instruction}] + st.session_state.messages
                response = get_interview_response(model_provider, full_messages)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.is_loading = False
