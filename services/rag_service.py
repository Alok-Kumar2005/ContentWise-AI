import chromadb
from chromadb.config import Settings
import logging
import tempfile
import shutil
import os
import asyncio
import threading
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma
from langchain.schema import Document
from config import Config
from core.templates import Template
import uuid
import sqlite3
import time

class RAGService:
    def __init__(self):
        self.temp_dir = None
        self.client = None
        self.embedding_model = None
        self.llm = None
        self.text_splitter = None
        self.vectorstore = None
        self.retrieval_qa_chain = None
        self.session_id = str(uuid.uuid4())
        self.collection = None
        
        try:
            try:
                asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            self.temp_dir = tempfile.mkdtemp(prefix=f"rag_chroma_{self.session_id[:8]}_")
            self.client = chromadb.PersistentClient(
                path=self.temp_dir,
                settings=Settings(
                    allow_reset=True,
                    anonymized_telemetry=False,
                    is_persistent=True,
                    persist_directory=self.temp_dir
                )
            )
            self.embedding_model = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001", 
                google_api_key=Config.GOOGLE_API_KEY
            )
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=Config.GOOGLE_API_KEY,
                temperature=0.7
            )
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
            )
            
            logging.info(f"RAG Service initialized with session ID: {self.session_id}")
            
        except Exception as e:
            logging.error(f"Error initializing RAG Service: {e}")
            self.cleanup_safely()
    
    def create_vector_database(self, transcript, video_title=""):
        """Create vector database from video transcript and setup RetrievalQA chain"""
        try:
            collection_name = f"video_transcript_{self.session_id.replace('-', '_')}"
            chunks = self.text_splitter.split_text(transcript)
            if not chunks:
                logging.warning("No chunks created from transcript")
                return False
            documents = [
                Document(
                    page_content=chunk,
                    metadata={
                        "chunk_index": i,
                        "video_title": video_title,
                        "session_id": self.session_id
                    }
                )
                for i, chunk in enumerate(chunks)
            ]
            try:
                self.vectorstore = Chroma.from_documents(
                    documents=documents,
                    embedding=self.embedding_model,
                    collection_name=collection_name,
                    persist_directory=self.temp_dir,
                    client=self.client
                )
                self.vectorstore.persist()
                
            except Exception as e:
                logging.error(f"Error creating Chroma vectorstore: {e}")
                self.vectorstore = Chroma.from_documents(
                    documents=documents,
                    embedding=self.embedding_model,
                    collection_name=collection_name,
                    persist_directory=self.temp_dir
                )
            
            custom_prompt = PromptTemplate(
                input_variables=["context", "question"],
                template= Template.rag_template
            )
            
            self.retrieval_qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 5}
                ),
                chain_type_kwargs={"prompt": custom_prompt},
                return_source_documents=True
            )
            
            logging.info(f"Created vector database with {len(chunks)} chunks and RetrievalQA chain")
            return True
            
        except Exception as e:
            logging.error(f"Error creating vector database: {e}")
            return False
    
    def query_video_content(self, query, return_sources=False):
        """Query the video transcript using RetrievalQA chain"""
        try:
            if not hasattr(self, 'retrieval_qa_chain') or not self.retrieval_qa_chain:
                return "No video content available for querying. Please analyze a video first."
            result = self.retrieval_qa_chain({"query": query})
            
            response = result["result"]
            if return_sources and "source_documents" in result:
                sources_info = self._format_source_documents(result["source_documents"])
                response += f"\n\n**Sources:**\n{sources_info}"
            
            return response
            
        except Exception as e:
            logging.error(f"Error querying video content: {e}")
            return f"Error processing your query: {str(e)}"
    
    def query_with_custom_retriever_params(self, query, k=5, search_type="similarity"):
        """Query with custom retriever parameters"""
        try:
            if not hasattr(self, 'vectorstore') or not self.vectorstore:
                return "No video content available for querying. Please analyze a video first."
            custom_retriever = self.vectorstore.as_retriever(
                search_type=search_type,
                search_kwargs={"k": k}
            )
            custom_qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=custom_retriever,
                return_source_documents=True
            )
            
            result = custom_qa_chain({"query": query})
            return result["result"]
            
        except Exception as e:
            logging.error(f"Error with custom retriever query: {e}")
            return f"Error processing your query: {str(e)}"
    
    def _format_source_documents(self, source_docs):
        """Format source documents for display"""
        if not source_docs:
            return "No source documents found."
        
        formatted_sources = []
        for i, doc in enumerate(source_docs, 1):
            chunk_info = doc.metadata.get("chunk_index", "unknown")
            video_title = doc.metadata.get("video_title", "Unknown Video")
            content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            
            formatted_sources.append(
                f"Source {i} (Chunk {chunk_info} from '{video_title}'):\n{content_preview}\n"
            )
        
        return "\n".join(formatted_sources)
    
    def get_similar_chunks(self, query, k=3):
        """Get similar chunks without generating an answer"""
        try:
            if not hasattr(self, 'vectorstore') or not self.vectorstore:
                return "No video content available for similarity search."
            similar_docs = self.vectorstore.similarity_search(query, k=k)
            
            if not similar_docs:
                return "No similar content found."
            
            formatted_chunks = []
            for i, doc in enumerate(similar_docs, 1):
                chunk_index = doc.metadata.get("chunk_index", "unknown")
                formatted_chunks.append(f"Chunk {i} (Index: {chunk_index}):\n{doc.page_content}\n")
            
            return "\n".join(formatted_chunks)
            
        except Exception as e:
            logging.error(f"Error getting similar chunks: {e}")
            return f"Error in similarity search: {str(e)}"
    
    def get_database_stats(self):
        """Get statistics about the vector database"""
        try:
            if not hasattr(self, 'vectorstore') or not self.vectorstore:
                return {"status": "No database created", "chunks": 0}
            try:
                if hasattr(self.vectorstore, '_collection') and self.vectorstore._collection:
                    count = self.vectorstore._collection.count()
                else:
                    count = len(self.vectorstore.similarity_search("test", k=1000))
            except Exception as e:
                logging.warning(f"Could not get exact count: {e}")
                count = "Unknown"
            
            return {
                "status": "Active",
                "chunks": count,
                "session_id": getattr(self, 'session_id', 'unknown'),
                "has_retrieval_chain": hasattr(self, 'retrieval_qa_chain') and self.retrieval_qa_chain is not None
            }
        except Exception as e:
            logging.error(f"Error getting database stats: {e}")
            return {"status": "Error", "chunks": 0}
    
    def update_chain_parameters(self, temperature=None, chain_type=None, k=None):
        """Update RetrievalQA chain parameters"""
        try:
            if not hasattr(self, 'vectorstore') or not self.vectorstore:
                return False
            if temperature is not None:
                self.llm.temperature = temperature
            retriever_kwargs = {"search_type": "similarity"}
            if k is not None:
                retriever_kwargs["search_kwargs"] = {"k": k}
            else:
                retriever_kwargs["search_kwargs"] = {"k": 5}
            chain_type = chain_type or "stuff"
            self.retrieval_qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type=chain_type,
                retriever=self.vectorstore.as_retriever(**retriever_kwargs),
                return_source_documents=True
            )
            
            logging.info(f"Updated RetrievalQA chain parameters: temp={temperature}, chain_type={chain_type}, k={k}")
            return True
            
        except Exception as e:
            logging.error(f"Error updating chain parameters: {e}")
            return False
    
    def cleanup_safely(self):
        """Safely clean up the vector database and temporary files"""
        try:
            if hasattr(self, 'vectorstore') and self.vectorstore:
                try:
                    if hasattr(self.vectorstore, '_collection') and self.vectorstore._collection:
                        collection_name = getattr(self.vectorstore._collection, 'name', None)
                        if collection_name and hasattr(self, 'client') and self.client:
                            try:
                                self.client.delete_collection(collection_name)
                                logging.info(f"Deleted collection: {collection_name}")
                            except Exception as e:
                                logging.warning(f"Could not delete collection: {e}")
                    self.vectorstore = None
                    
                except Exception as e:
                    logging.warning(f"Error cleaning vectorstore: {e}")
            
            if hasattr(self, 'client') and self.client:
                try:
                    if hasattr(self.client, 'reset'):
                        self.client.reset()
                except Exception as e:
                    logging.warning(f"Could not reset client: {e}")
                finally:
                    self.client = None
            self._force_close_sqlite_connections()
            if hasattr(self, 'temp_dir') and self.temp_dir and os.path.exists(self.temp_dir):
                self._cleanup_temp_dir_with_retry()
            self.vectorstore = None
            self.retrieval_qa_chain = None
            self.client = None
            self.collection = None
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
    
    def _force_close_sqlite_connections(self):
        """Force close any open SQLite connections"""
        try:
            import gc
            gc.collect() 
            if hasattr(self, 'temp_dir') and self.temp_dir:
                sqlite_path = os.path.join(self.temp_dir, 'chroma.sqlite3')
                if os.path.exists(sqlite_path):
                    try:
                        conn = sqlite3.connect(sqlite_path)
                        conn.close()
                    except Exception as e:
                        logging.debug(f"SQLite cleanup attempt: {e}")
        except Exception as e:
            logging.warning(f"Error forcing SQLite cleanup: {e}")
    
    def _cleanup_temp_dir_with_retry(self, max_retries=3, delay=1):
        """Clean up temporary directory with retry mechanism"""
        for attempt in range(max_retries):
            try:
                time.sleep(delay * (attempt + 1))
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                if not os.path.exists(self.temp_dir):
                    logging.info(f"Successfully cleaned up temporary directory: {self.temp_dir}")
                    self.temp_dir = None
                    return True
                    
            except Exception as e:
                logging.warning(f"Cleanup attempt {attempt + 1} failed: {e}")
                
                if attempt == max_retries - 1:
                    try:
                        if os.name == 'nt': 
                            import win32api
                            import win32con
                            win32api.MoveFileEx(self.temp_dir, None, win32con.MOVEFILE_DELAY_UNTIL_REBOOT)
                            logging.info(f"Marked directory for deletion on reboot: {self.temp_dir}")
                    except ImportError:
                        logging.warning("Could not mark for deletion on reboot (win32api not available)")
                    except Exception as e:
                        logging.warning(f"Could not mark for deletion on reboot: {e}")
        
        return False
    
    def cleanup(self):
        """Main cleanup method (alias for cleanup_safely)"""
        self.cleanup_safely()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup_safely()
        except Exception as e:
            logging.error(f"Error in destructor: {e}")