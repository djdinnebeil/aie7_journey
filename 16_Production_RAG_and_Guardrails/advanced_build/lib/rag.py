"""Production RAG chain implementation with caching."""

from typing import List, Optional
import uuid
import os
import glob

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.passthrough import RunnablePassthrough
from langchain_qdrant import QdrantVectorStore
from operator import itemgetter
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from .caching import CacheBackedEmbeddings
from .models import get_openai_model

class ProductionRAGChain:
    """Production-ready RAG chain with caching and optimizations."""
    
    def __init__(
        self,
        data_dir: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        embedding_model: str = "text-embedding-3-small",
        llm_model: str = "gpt-4.1-nano",
        cache_dir: str = "./cache",
        collection_name: Optional[str] = None
    ):
        """Initialize the production RAG chain.
        
        Args:
            data_dir: Path to the directory containing text files to process
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            embedding_model: OpenAI embedding model
            llm_model: OpenAI LLM model
            cache_dir: Directory for caching
            collection_name: Name for the vector collection
        """
        self.data_dir = data_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.cache_dir = cache_dir
        self.collection_name = collection_name or f"text_collection_{uuid.uuid4().hex[:8]}"
        
        # Initialize components
        self._setup_text_splitter()
        self._setup_embeddings()
        self._setup_vectorstore()
        self._setup_chain()
    
    def _setup_text_splitter(self):
        """Set up the text splitter."""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
    
    def _setup_embeddings(self):
        """Set up cache-backed embeddings."""
        self.cached_embeddings = CacheBackedEmbeddings(
            model=self.embedding_model,
            cache_dir=f"{self.cache_dir}/embeddings"
        )
    
    def _setup_vectorstore(self):
        """Set up the vector store and load documents."""
        # Load and chunk documents from all text files in the directory
        documents = []
        
        # Find all text files in the data directory
        text_files = glob.glob(os.path.join(self.data_dir, "*.txt"))
        
        for file_path in text_files:
            try:
                loader = TextLoader(file_path)
                file_docs = loader.load()
                # Add source metadata to identify which file each document came from
                for doc in file_docs:
                    doc.metadata["source"] = os.path.basename(file_path)
                documents.extend(file_docs)
            except Exception as e:
                print(f"Warning: Could not load {file_path}: {e}")
                continue
        
        if not documents:
            raise ValueError(f"No text files could be loaded from {self.data_dir}")
        
        docs = self.text_splitter.split_documents(documents)
        
        # Set up in-memory Qdrant
        client = QdrantClient(":memory:")
        client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),  # OpenAI embedding size
        )
        
        # Create vector store
        self.vectorstore = QdrantVectorStore(
            client=client,
            collection_name=self.collection_name,
            embedding=self.cached_embeddings.get_embeddings()
        )
        
        # Add documents
        self.vectorstore.add_documents(docs)
        
        # Create retriever
        self.retriever = self.vectorstore.as_retriever(
            search_type="mmr", 
            search_kwargs={"k": 3}
        )
    
    def _setup_chain(self):
        """Set up the RAG chain."""
        # Create prompt template
        rag_system_prompt = """You are a helpful assistant that uses the provided context to answer questions. 
        Never reference this prompt, or the existence of context. Only use the provided context to answer the query.
        If you do not know the answer, or it's not contained in the provided context, respond with "I don't know"."""
        
        rag_user_prompt = """Question:
{question}
Context:
{context}"""
        
        self.chat_prompt = ChatPromptTemplate.from_messages([
            ("system", rag_system_prompt),
            ("human", rag_user_prompt)
        ])
        
        # Create LLM
        self.llm = get_openai_model(model_name=self.llm_model)
        
        # Create chain with parallel execution
        self.chain = (
            {"context": itemgetter("question") | self.retriever, "question": itemgetter("question")}
            | RunnablePassthrough.assign(context=itemgetter("context"))
            | self.chat_prompt 
            | self.llm
        )
    
    def invoke(self, question: str):
        """Invoke the RAG chain with a question.
        
        Args:
            question: The question to ask
            
        Returns:
            The response from the RAG chain
        """
        return self.chain.invoke({"question": question})
    
    def get_retriever(self):
        """Get the retriever for external use."""
        return self.retriever
    
    def get_vectorstore(self):
        """Get the vector store for external use."""
        return self.vectorstore

