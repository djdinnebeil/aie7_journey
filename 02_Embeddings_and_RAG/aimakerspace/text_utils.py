import os
from typing import List
import PyPDF2
from pdf2image import convert_from_path
import pytesseract
from docx import Document
import textract


class BaseFileLoader:
    def __init__(self, path: str):
        self.documents = []
        self.path = path

    def load(self):
        if os.path.isdir(self.path):
            self.load_directory()
        elif os.path.isfile(self.path) and self.is_valid_file(self.path):
            self.load_file(self.path)
        else:
            raise ValueError(
                f"Provided path is neither a valid directory nor a {self.file_extension()} file."
            )

    def load_directory(self):
        for root, _, files in os.walk(self.path):
            for file in files:
                if self.is_valid_file(file):
                    self.load_file(os.path.join(root, file))

    def load_documents(self):
        self.load()
        return self.documents

    def is_valid_file(self, file_path: str) -> bool:
        return file_path.endswith(self.file_extension())

    def file_extension(self) -> str:
        raise NotImplementedError

    def load_file(self, file_path: str):
        raise NotImplementedError


class TextFileLoader(BaseFileLoader):
    def __init__(self, path: str, encoding: str = "utf-8"):
        super().__init__(path)
        self.encoding = encoding

    def file_extension(self) -> str:
        return ".txt"

    def load_file(self, file_path: str):
        with open(file_path, "r", encoding=self.encoding) as f:
            self.documents.append(f.read())


class CharacterTextSplitter:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        assert (
            chunk_size > chunk_overlap
        ), "Chunk size must be greater than chunk overlap"

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str) -> List[str]:
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunks.append(text[i : i + self.chunk_size])
        return chunks

    def split_texts(self, texts: List[str]) -> List[str]:
        chunks = []
        for text in texts:
            chunks.extend(self.split(text))
        return chunks


class PDFFileLoader(BaseFileLoader):
    def __init__(self, path: str, poppler_path: str = None):
        super().__init__(path)
        self.poppler_path = poppler_path

    def file_extension(self) -> str:
        return ".pdf"

    def extract_text_from_page(self, page, pdf_path, page_number):
        text = page.extract_text() or ""
        if text.strip():
            return text
        try:
            images = convert_from_path(pdf_path, first_page=page_number+1, last_page=page_number+1, poppler_path=self.poppler_path)
            if images:
                ocr_text = pytesseract.image_to_string(images[0])
                return ocr_text
        except Exception as e:
            print(f"OCR failed for page {page_number+1}: {e}")
        return ""

    def load_file(self, file_path: str):
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for i, page in enumerate(reader.pages):
                page_text = self.extract_text_from_page(page, file_path, i)
                text += page_text
            self.documents.append(text)


class DocxFileLoader(BaseFileLoader):
    def file_extension(self) -> str:
        return ".docx"

    def load_file(self, file_path: str):
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        self.documents.append(text)


class DocFileLoader(BaseFileLoader):
    def file_extension(self) -> str:
        return ".doc"

    def load_file(self, file_path: str):
        try:
            text = textract.process(file_path).decode("utf-8")
            self.documents.append(text)
        except Exception as e:
            print(f"Failed to extract text from {file_path}: {e}")


class UniversalFileLoader:
    _registry = {}

    @classmethod
    def register_loader(cls, extension: str, loader_cls):
        cls._registry[extension.lower()] = loader_cls

    def __init__(self, path: str, **kwargs):
        self.path = path
        self.documents = []
        self.loader_kwargs = kwargs

    def load(self):
        if os.path.isdir(self.path):
            self._load_directory(self.path)
        elif os.path.isfile(self.path):
            self._load_file(self.path)
        else:
            raise ValueError("Provided path is neither a valid directory nor a file.")
        return self.documents

    def _get_loader(self, file_path: str):
        for ext, loader_cls in self._registry.items():
            if file_path.lower().endswith(ext):
                return loader_cls(file_path, **self.loader_kwargs)
        return None

    def _load_file(self, file_path: str):
        loader = self._get_loader(file_path)
        if loader is not None:
            self.documents.extend(loader.load_documents())
        else:
            print(f"No loader registered for file: {file_path}")

    def _load_directory(self, dir_path: str):
        for root, _, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                self._load_file(file_path)

# Register default loaders
UniversalFileLoader.register_loader('.txt', TextFileLoader)
UniversalFileLoader.register_loader('.pdf', PDFFileLoader)
UniversalFileLoader.register_loader('.docx', DocxFileLoader)
UniversalFileLoader.register_loader('.doc', DocFileLoader)

if __name__ == "__main__":
    loader = UniversalFileLoader("../data")
    loader.load()
    splitter = CharacterTextSplitter()
    chunks = splitter.split_texts(loader.documents)
    print(len(chunks))
    print(chunks[0])
    print("--------")
    print(chunks[1])
    print("--------")
    print(chunks[-2])
    print("--------")
    print(chunks[-1])
