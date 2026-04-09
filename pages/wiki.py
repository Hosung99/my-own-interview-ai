import streamlit as st
from wiki_builder import load_wiki, reset_wiki

st.set_page_config(page_title="Interview Wiki", layout="wide")

LABEL_MAP = {
    "경험": "💼 경험/프로젝트",
    "기술스택": "🛠️ 기술스택",
    "강점": "✅ 강점",
    "약점_모순": "⚠️ 약점/모순",
    "미커버_토픽": "📌 미커버 토픽",
}


def render_stars(score: float) -> str:
    full = int(score)
    half = 1 if score - full >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + "½" * half + "☆" * empty


wiki = load_wiki()
sessions = wiki.get("sessions", [])

st.title("📖 Interview Wiki")
st.caption(f"총 {len(sessions)}회 면접 기록")

if not sessions:
    st.info("아직 생성된 Wiki가 없습니다. 면접을 완료하고 '면접 종료 & Wiki 생성'을 눌러주세요.")
    st.page_link("main.py", label="← 면접으로 돌아가기")
else:
    # 레이아웃: 왼쪽 세션 목록 / 오른쪽 상세
    col_list, col_detail = st.columns([1, 2.5])

    if "selected_session_id" not in st.session_state:
        st.session_state.selected_session_id = sessions[-1]["id"]

    with col_list:
        st.subheader("세션 목록")
        for session in reversed(sessions):
            score = session.get("평점", {}).get("점수", 0)
            stars = render_stars(score)
            label = f"세션 {session['id']}\n{session.get('date', '')}\n{stars} {score}/5"
            is_selected = st.session_state.selected_session_id == session["id"]
            if st.button(label, key=f"sess_{session['id']}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                st.session_state.selected_session_id = session["id"]
                st.rerun()

    with col_detail:
        selected = next(
            (s for s in sessions if s["id"] == st.session_state.selected_session_id), None
        )
        if selected:
            score = selected.get("평점", {}).get("점수", 0)
            review = selected.get("평점", {}).get("총평", "")

            st.subheader(f"세션 {selected['id']} 상세 — {selected.get('date', '')}")

            # 평점
            st.markdown("### 평점")
            stars_display = render_stars(score)
            st.markdown(f"## {stars_display}  **{score} / 5**")
            if review:
                st.info(review)

            st.divider()

            # 각 항목
            for key, label in LABEL_MAP.items():
                items = selected.get(key, [])
                if items:
                    st.markdown(f"### {label}")
                    for item in items:
                        st.markdown(f"- {item}")

    st.divider()
    col1, col2 = st.columns([1, 5])
    with col1:
        st.page_link("main.py", label="← 면접으로 돌아가기")
    with col2:
        if st.button("🗑️ 전체 Wiki 초기화", type="secondary"):
            reset_wiki()
            st.session_state.selected_session_id = None
            st.success("Wiki가 초기화되었습니다.")
            st.rerun()
