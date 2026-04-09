# 나만의 로컬 면접 AI

Andrej Karpathy의 LLM OS 개념을 기반으로 한 **로컬 설치형 면접 AI**입니다.
이력서(PDF)를 업로드하면 AI 면접관이 이력서 내용을 바탕으로 질문을 생성하고, 면접 대화를 누적해 본인만의 **Interview Wiki**를 자동으로 만들어줍니다.

---

## 주요 기능

- **이력서 기반 면접 진행** — PDF를 업로드하면 RAG(검색 증강 생성)로 이력서 내용을 참조해 질문 생성
- **이미지 PDF OCR 지원** — 스캔/이미지 기반 PDF도 Tesseract OCR로 자동 처리
- **Interview Wiki 자동 생성** — 면접 대화를 LLM이 분석해 경험, 기술스택, 강점, 약점, 미커버 토픽을 구조화
- **Wiki 영구 저장** — 로컬 JSON 파일로 저장되어 앱을 재시작해도 이전 면접 내용 유지 및 누적
- **멀티 모델 지원** — OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Google Gemini 1.5 Pro 선택 가능
- **완전 로컬 처리** — API Key와 이력서 데이터는 외부 서버로 전송되지 않음

---

## 기술 스택

| 역할     | 라이브러리                               |
| -------- | ---------------------------------------- |
| UI       | Streamlit                                |
| LLM 연동 | LiteLLM                                  |
| PDF 로딩 | PyPDF, pdf2image                         |
| OCR      | Tesseract, pytesseract                   |
| 임베딩   | sentence-transformers (all-MiniLM-L6-v2) |
| 벡터 DB  | ChromaDB                                 |
| RAG      | LangChain                                |

---

## 설치 방법

### 1. 사전 요구사항

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (이미지 PDF 지원)
- [Poppler](https://poppler.freedesktop.org/) (PDF → 이미지 변환)

```bash
# macOS
brew install tesseract tesseract-lang poppler
```

### 2. 저장소 클론

```bash
git clone https://github.com/your-username/my-own-interview-ai.git
cd my-own-interview-ai
```

### 3. 가상환경 생성 및 활성화

```bash
# 생성
python -m venv venv

# 활성화 (macOS/Linux)
source venv/bin/activate

# 활성화 (Windows)
.\venv\Scripts\activate
```

### 4. 의존성 설치

```bash
pip install -r requirements.txt
```

### 5. 앱 실행

```bash
streamlit run main.py
```

브라우저에서 `http://localhost:8501`로 접속합니다.

---

## 사용 방법

1. **사이드바에서 모델 선택** — GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro 중 선택
2. **API Key 입력** — 선택한 모델의 API Key 입력 (로컬에서만 처리됨)
3. **이력서 업로드** — PDF 파일 업로드 (텍스트 PDF 및 이미지 PDF 모두 지원)
4. **면접 진행** — 채팅창에 답변 입력
5. **Wiki 생성** — "면접 종료 & Wiki 생성" 버튼 클릭 시 대화 내용을 분석해 Wiki 자동 생성
6. **연속 면접** — Wiki는 로컬에 저장되어 다음 실행 시 자동 로드 및 누적

---

## 프로젝트 구조

```
my-own-interview-ai/
├── main.py           # Streamlit UI 및 채팅 로직
├── core.py           # LiteLLM을 통한 LLM 호출
├── rag_engine.py     # PDF 처리, OCR, ChromaDB 벡터 저장
├── wiki_builder.py   # 면접 대화 분석 및 Interview Wiki 생성/관리
├── requirements.txt  # Python 의존성
├── data/             # 업로드된 PDF 및 interview_wiki.json 저장
└── chroma_db/        # ChromaDB 벡터 DB 저장
```

---

## API Key 발급

| 모델              | 발급처                                             |
| ----------------- | -------------------------------------------------- |
| GPT-4o            | [OpenAI Platform](https://platform.openai.com)     |
| Claude 3.5 Sonnet | [Anthropic Console](https://console.anthropic.com) |
| Gemini 1.5 Pro    | [Google AI Studio](https://aistudio.google.com)    |
