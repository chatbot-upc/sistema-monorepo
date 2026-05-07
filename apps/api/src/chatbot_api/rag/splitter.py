"""Text splitter para chunking de documentos."""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from chatbot_api.core.settings import get_settings


def get_splitter() -> RecursiveCharacterTextSplitter:
    s = get_settings()
    return RecursiveCharacterTextSplitter(
        chunk_size=s.rag_chunk_size,
        chunk_overlap=s.rag_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
