import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document


def _ocr_pdf(file_path: str) -> list[Document]:
    """이미지 기반 PDF를 OCR로 텍스트 추출합니다."""
    try:
        import pytesseract
        from pdf2image import convert_from_path

        images = convert_from_path(file_path)
        docs = []
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image, lang="kor+eng")
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={"source": file_path, "page": i}
                ))
        return docs
    except ImportError:
        return []


class RAGEngine:
    def __init__(self, db_path="./chroma_db"):
        self.db_path = db_path
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_store = None

    def process_pdf(self, file_path: str) -> str:
        """PDF를 읽어서 벡터 DB에 저장합니다. 이미지 PDF는 OCR로 처리합니다."""
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        # 텍스트 추출이 안 된 경우 OCR 폴백
        text_extracted = [d for d in documents if d.page_content.strip()]
        if not text_extracted:
            documents = _ocr_pdf(file_path)
            if not documents:
                return "❌ 텍스트 추출 실패. Tesseract가 설치됐는지 확인해주세요: brew install tesseract tesseract-lang"
            method = "OCR"
        else:
            documents = text_extracted
            method = "텍스트"

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_documents(documents)
        chunks = [c for c in chunks if c.page_content.strip()]

        if not chunks:
            return "❌ PDF에서 유효한 내용을 찾을 수 없습니다."

        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.db_path
        )
        return f"✅ 파일 분석 완료 ({method}, {len(chunks)}개 청크 저장)"

    def get_relevant_context(self, query):
        """질문과 관련된 이력서/위키 내용을 찾아옵니다."""
        if not self.vector_store:
            if os.path.exists(self.db_path):
                self.vector_store = Chroma(persist_directory=self.db_path, embedding_function=self.embeddings)
            else:
                return ""

        docs = self.vector_store.similarity_search(query, k=3)
        return "\n".join([doc.page_content for doc in docs])