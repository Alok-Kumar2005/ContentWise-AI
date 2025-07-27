import chromadb
from chromadb.config import Settings
import logging
import tempfile
import shutil
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma
from langchain.schema import Document
from config import Config
import uuid

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
        
        try:
            self.temp_dir = tempfile.mkdtemp()
            self.client = chromadb.PersistentClient(
                path=self.temp_dir,
                settings=Settings(
                    allow_reset=True,
                    anonymized_telemetry=False
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
            self.cleanup() 
    
    def create_vector_database(self, transcript, video_title=""):
        """Create vector database from video transcript and setup RetrievalQA chain"""
        try:
            collection_name = f"video_transcript_{self.session_id}"
            
            # Split transcript into chunks
            chunks = self.text_splitter.split_text(transcript)
            if not chunks:
                logging.warning("No chunks created from transcript")
                return False
            
            # Create Document objects for LangChain
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
            
            # Create Chroma vectorstore
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embedding_model,
                collection_name=collection_name,
                persist_directory=self.temp_dir
            )
            
            # Create custom prompt template for video content
            custom_prompt = PromptTemplate(
                input_variables=["context", "question"],
                template="""You are an AI assistant helping users understand video content. Based on the provided context from the video transcript, answer the user's question accurately and comprehensively.

Context from video transcript:
{context}

User Question: {question}

Instructions:
1. Answer based primarily on the provided context
2. Be specific and detailed in your response
3. If the context doesn't contain enough information, mention that clearly
4. Quote relevant parts from the transcript when appropriate
5. Keep your response focused and relevant to the question
6. If the question cannot be answered from the context, say so explicitly

Answer:"""
            )
            
            # Create RetrievalQA chain
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
            
            # Query using RetrievalQA chain
            result = self.retrieval_qa_chain({"query": query})
            
            response = result["result"]
            
            # Optionally include source information
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
            
            # Create a new retriever with custom parameters
            custom_retriever = self.vectorstore.as_retriever(
                search_type=search_type,
                search_kwargs={"k": k}
            )
            
            # Create a new RetrievalQA chain with custom retriever
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
            
            # Direct similarity search
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
            
            # Get collection count
            collection = self.vectorstore._collection
            count = collection.count() if collection else 0
            
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
            
            # Update LLM temperature if provided
            if temperature is not None:
                self.llm.temperature = temperature
            
            # Update retriever k if provided
            retriever_kwargs = {"search_type": "similarity"}
            if k is not None:
                retriever_kwargs["search_kwargs"] = {"k": k}
            else:
                retriever_kwargs["search_kwargs"] = {"k": 5}
            
            # Update chain type if provided
            chain_type = chain_type or "stuff"
            
            # Recreate the RetrievalQA chain with updated parameters
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
    
    def cleanup(self):
        """Clean up the vector database and temporary files"""
        try:
            # Clean up vectorstore
            if hasattr(self, 'vectorstore') and self.vectorstore:
                try:
                    # Delete the collection if it exists
                    if hasattr(self.vectorstore, '_collection'):
                        collection_name = getattr(self.vectorstore._collection, 'name', None)
                        if collection_name and hasattr(self, 'client') and self.client:
                            self.client.delete_collection(collection_name)
                            logging.info(f"Deleted collection: {collection_name}")
                except Exception as e:
                    logging.warning(f"Could not delete vectorstore collection: {e}")
            
            # Clean up temporary directory
            if hasattr(self, 'temp_dir') and self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                    logging.info(f"Cleaned up temporary directory: {self.temp_dir}")
                except Exception as e:
                    logging.warning(f"Could not clean up temp directory: {e}")
            
            # Reset attributes
            self.vectorstore = None
            self.retrieval_qa_chain = None
            self.client = None
            self.temp_dir = None
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception as e:
            logging.error(f"Error in destructor: {e}")