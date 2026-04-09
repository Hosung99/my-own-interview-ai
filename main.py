import os
import streamlit as st
from dotenv import load_dotenv
from core import get_interview_response
from rag_engine import RAGEngine
from wiki_builder import build_wiki_from_conversation, load_wiki, reset_wiki, wiki_to_context_string

load_dotenv()

# 앱 시작 시 data/ 디렉토리 보장
os.makedirs("./data", exist_ok=True)

# 페이지 설정
st.set_page_config(page_title="LLM OS Interviewer", layout="wide")
st.title("🤖 나만의 로컬 면접 AI")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "rag" not in st.session_state:
    st.session_state.rag = RAGEngine()
if "wiki" not in st.session_state:
    st.session_state.wiki = load_wiki()

# 사이드바: 설정
with st.sidebar:
    st.header("⚙️ 설정")
    model_provider = st.selectbox(
        "모델 선택",
        ["openai/gpt-4o", "anthropic/claude-3-5-sonnet-20240620", "google/gemini-1.5-pro"]
    )

    # 로드된 API Key 상태 표시
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GEMINI_API_KEY",
    }
    provider = model_provider.split("/")[0]
    env_key = key_map.get(provider, "")
    if os.environ.get(env_key):
        st.success(f"✅ {env_key} 로드됨")
    else:
        st.error(f"❌ {env_key} 없음 — .env 파일을 확인하세요")

    st.divider()

    st.header("📄 자료 업로드")
    uploaded_file = st.file_uploader("이력서나 회사 위키(PDF)를 올려주세요", type="pdf")
    if uploaded_file:
        with open(f"./data/{uploaded_file.name}", "wb") as f:
            f.write(uploaded_file.getbuffer())
        with st.spinner("파일 분석 중..."):
            msg = st.session_state.rag.process_pdf(f"./data/{uploaded_file.name}")
            st.success(msg)

    st.divider()

    # 면접 종료 & Wiki 생성
    st.header("📖 Interview Wiki")
    if st.button("🔚 면접 종료 & Wiki 생성", type="primary", use_container_width=True):
        if not st.session_state.messages:
            st.warning("면접 대화가 없습니다.")
        else:
            with st.spinner("Wiki 생성 중..."):
                wiki, error = build_wiki_from_conversation(
                    model_provider, st.session_state.messages
                )
            if error:
                st.error(error)
            else:
                st.session_state.wiki = wiki
                st.success("Wiki 업데이트 완료!")

    if st.button("🗑️ Wiki 초기화", use_container_width=True):
        reset_wiki()
        st.session_state.wiki = load_wiki()
        st.info("Wiki가 초기화되었습니다.")

    # Wiki 내용 표시
    wiki = st.session_state.wiki
    if any(wiki.get(k) for k in ["경험", "기술스택", "강점", "약점_모순", "미커버_토픽"]):
        label_map = {
            "경험": "💼 경험/프로젝트",
            "기술스택": "🛠️ 기술스택",
            "강점": "✅ 강점",
            "약점_모순": "⚠️ 약점/모순",
            "미커버_토픽": "📌 미커버 토픽",
        }
        for key, label in label_map.items():
            items = wiki.get(key, [])
            if items:
                st.markdown(f"**{label}**")
                for item in items:
                    st.markdown(f"- {item}")
        updated_at = wiki.get("_updated_at", "")
        if updated_at:
            st.caption(f"마지막 업데이트: {updated_at}")
    else:
        st.caption("면접 종료 후 Wiki가 생성됩니다.")


# 채팅 UI
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("답변을 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not os.environ.get(env_key):
            st.warning(f"{env_key}가 설정되지 않았습니다. .env 파일을 확인하세요.")
        else:
            with st.spinner("생각 중..."):
                resume_context = st.session_state.rag.get_relevant_context(prompt)
                wiki_context = wiki_to_context_string(st.session_state.wiki)

                system_instruction = f"""너는 날카롭고 경험 많은 기술 면접관이야.
아래 제공된 [이력서 Context]와 [지원자 Wiki]를 바탕으로 면접을 진행해.

규칙:
- 질문은 한 번에 하나씩만 해라.
- 지원자의 답변에서 모순이나 부족한 점이 있으면 꼬리 질문을 던져라.
- Wiki의 [미커버 토픽]은 반드시 다뤄라.
- Wiki의 [약점/모순]은 집중적으로 파고들어라.
- 이미 충분히 다룬 주제는 반복하지 마라.

[이력서 Context]:
{resume_context}

{wiki_context}"""

                full_messages = [{"role": "system", "content": system_instruction}] + st.session_state.messages

                response = get_interview_response(model_provider, full_messages)
                st.markdown(response)

                st.session_state.messages.append({"role": "assistant", "content": response})
