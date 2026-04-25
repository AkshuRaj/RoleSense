"""
LangChain RAG Integration Service
- Custom Groq LLM wrapper
- ChromaDB retriever with RBAC
- Direct RAG chain implementation
"""

import os
import logging
from typing import List, Optional, Tuple, Any
from dotenv import load_dotenv

import chromadb
from groq import Groq as GroqClient
from langchain_core.language_models import LLM
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_classic.chains import RetrievalQA

load_dotenv()
logger = logging.getLogger(__name__)


class GroqLLM(LLM):
    """
    Custom LangChain LLM wrapper for Groq API
    Maintains anti-hallucination constraints
    """
    
    model: str = "llama-3.1-8b-instant"
    temperature: float = 0.1
    max_tokens: int = 500
    top_p: float = 0.3
    api_key: Optional[str] = None
    client: Any = None
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.client = GroqClient(api_key=self.api_key)
    
    @property
    def _llm_type(self) -> str:
        return "groq"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> str:
        """Call method for LLM interface"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a factual, security-conscious enterprise assistant. "
                        "Under NO circumstances create, guess, or hallucinate information. "
                        "Only provide what is explicitly stated in the context. "
                        "If information is not available, clearly state that. "
                        "DO NOT mention sources, sections, or where information comes from. "
                        "Present all information as direct facts."
                    )
                },
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                stop=stop,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")
            raise


def create_langchain_rag_chain(role: str):
    """
    Create a production-ready RAG chain with RBAC
    Returns a callable that executes the RAG flow
    """
    # Initialize LLM with custom Groq wrapper
    llm = GroqLLM()
    
    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Initialize Chroma vectorstore
    vectorstore = Chroma(
        persist_directory="./chroma_db",
        embedding_function=embeddings,
        collection_name="company_data"
    )
    
    # Configure exact RBAC metadata filter
    if role == "c_level":
        filter_dict = None
    else:
        filter_dict = {"department": {"$in": [role, "general"]}}
        
    # Setup Langchain retriever with RBAC filter
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 6,
            "filter": filter_dict
        }
    )
    
    # Create prompt template
    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template="""You are a helpful answering assistant.
If the context provided below is empty, you must say exactly: "No relevant information found in your department data."

Otherwise, answer the question comprehensively using ONLY the provided context. 
Do NOT generate fake policy-based denial responses. DO NOT mention where information comes from.
Provide a detailed, well-structured, multi-sentence explanation. Use bullet points if helpful. Do NOT give simple one-sentence answers if more details exist in the context.

CONTEXT:
{context}

QUESTION: {question}

DETAILED ANSWER:"""
    )
    
    # Initialize standard RetrievalQA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={
            "prompt": prompt_template,
        }
    )
    
    return qa_chain


def query_with_rag(
    query: str,
    role: str,
    username: Optional[str] = None
) -> Tuple[str, List[str]]:
    """
    Execute query through LangChain RAG chain
    """
    try:
        # Create chain for this specific role
        qa_chain = create_langchain_rag_chain(role)
        
        # Execute query
        result = qa_chain({"query": query})
        
        response = result["result"]
        source_docs = result.get("source_documents", [])
        
        # Extract text from documents for compatibility
        doc_texts = [doc.page_content for doc in source_docs]
        
        # Debug safety: print retrieved documents
        print(f"--- DEBUG: RETRIEVED DOCS ({len(source_docs)}) ---")
        for i, doc in enumerate(source_docs):
            print(f"Doc {i+1}: {doc.page_content[:100]}...\n")
        print("---------------------------------------")
        
        logger.info(f"Query processed: user={username}, role={role}, docs_retrieved={len(source_docs)}")
        
        return response.strip(), doc_texts
        
    except Exception as e:
        logger.error(f"RAG Chain Error: {str(e)}")
        return (
            "⚠️ An error occurred while processing your request. "
            "Please try again or contact support if the issue persists."
        ), []


def handle_greeting(username: Optional[str] = None) -> str:
    """Generate personalized greeting"""
    if username:
        return (
            f"👋 Hello {username}! Welcome to FinSolve's Enterprise Chatbot. "
            "I'm here to help you with company-related information. "
            "Feel free to ask me anything about your department or company policies!"
        )
    return (
        "👋 Hello! I'm here to help you with company-related information. "
        "What can I assist you with today?"
    )


def handle_offtopic() -> str:
    """Handle off-topic queries"""
    return (
        "🤔 I appreciate the question, but that's outside my scope. I'm specifically designed to provide information "
        "about FinSolve Technologies — including company policies, HR guidelines, financial data, engineering documentation, "
        "and marketing insights relevant to your role.\n\n"
        "Would you like to ask me something about the company instead? For example:\n"
        "• 'What are the leave policies?'\n"
        "• 'Tell me about the engineering architecture'\n"
        "• 'What were the Q4 2024 financial results?'\n"
        "• 'How can I request a transfer?'"
    )


def handle_no_access(role: str) -> str:
    """Handle when no documents are accessible"""
    return (
        f"I don't have access to information about this topic in your authorized departments. "
        f"As a {role} team member, you can only access {role} and general information. "
        f"Contact your manager for cross-department access requests."
    )
