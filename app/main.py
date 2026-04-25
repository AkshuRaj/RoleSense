from typing import Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime
from app.services.langchain_service import (
    query_with_rag,
    handle_greeting,
    handle_offtopic,
    handle_no_access
)
from app.services.audit_logger import log_access, get_departments_accessed
from app.services.query_learning import log_query_interaction, calculate_relevance_score
from app.services.query_classifier import classify_query

app = FastAPI()
security = HTTPBasic()

# User database with role-based access
users_db: Dict[str, Dict[str, str]] = {
    "Tony": {"password": "password123", "role": "engineering"},
    "Bruce": {"password": "securepass", "role": "marketing"},
    "Sam": {"password": "financepass", "role": "finance"},
    "Peter": {"password": "pete123", "role": "engineering"},
    "Sid": {"password": "sidpass123", "role": "marketing"},
    "Natasha": {"password": "hrpass123", "role": "hr"},
    "CEO": {"password": "ceopass123", "role": "c_level"}  # C-level: full access
}


# Authentication dependency
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    user = users_db.get(username)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": username, "role": user["role"]}


# Login endpoint
@app.get("/login")
def login(user=Depends(authenticate)):
    return {"message": f"Welcome {user['username']}!", "role": user["role"]}


# Protected test endpoint
@app.get("/test")
def test(user=Depends(authenticate)):
    return {"message": f"Hello {user['username']}! You can now chat.", "role": user["role"]}


# Analytics endpoint (admin only)
@app.get("/analytics")
def get_analytics(user=Depends(authenticate)):
    """Get query analytics - admin/c-level users only."""
    if user["role"] != "c_level":
        raise HTTPException(status_code=403, detail="Only C-level users can access analytics")
    
    from app.services.query_learning import get_query_insights, get_common_questions_by_role
    
    insights = get_query_insights()
    
    return {
        "insights": insights,
        "timestamp": datetime.now().isoformat()
    }


# Protected chat endpoint
@app.post("/chat")
def query(user=Depends(authenticate), message: str = "Hello"):

    username = user["username"]
    role = user["role"]
    
    # 🔍 Step 1: Query classification (greeting, off-topic detection)
    classification = classify_query(message)
    
    # 1️⃣ GREETING DETECTION
    if classification.get("is_greeting", False):
        answer = handle_greeting(username)
        log_access(
            username=username,
            role=role,
            query=message,
            status="GREETING",
            departments_accessed="NONE"
        )
        return {
            "role": role,
            "query": message,
            "response": answer
        }
    
    # 2️⃣ OFF-TOPIC DETECTION
    if classification.get("is_offtopic", False):
        answer = handle_offtopic()
        log_access(
            username=username,
            role=role,
            query=message,
            status="OFFTOPIC",
            departments_accessed="NONE"
        )
        return {
            "role": role,
            "query": message,
            "response": answer
        }
    
    # 🤖 Step 2: LangChain RAG Query (with RBAC in retriever)
    answer, retrieved_docs = query_with_rag(
        query=message,
        role=role,
        username=username
    )
    
    # 🚫 Access DENIED: No documents available
    if not retrieved_docs:
        # Check strict RBAC cross-department inquiries
        found_keywords = classification.get("keywords_found", [])
        allowed_depts = [role, "general", "company"]
        asked_about_other_dept = False
        for kw in found_keywords:
            category = kw.split(":")[0]
            if category not in allowed_depts:
                asked_about_other_dept = True
                break
                
        if asked_about_other_dept and role != "c_level":
            answer = "I cannot provide the information of other departments."

        log_access(
            username=username,
            role=role,
            query=message,
            status="DENIED",
            departments_accessed="NONE"
        )
        return {
            "role": role,
            "query": message,
            "response": answer
        }
    
    # ✅ Access ALLOWED: Log successful retrieval
    # Extract metadata from documents for audit logging
    # (LangChain Document objects will have metadata attached)
    departments = "multiple"  # Default when using LangChain
    
    log_access(
        username=username,
        role=role,
        query=message,
        status="ALLOWED",
        departments_accessed=departments
    )
    
    # 📊 Step 3: Calculate relevance and log for learning
    relevance_score = calculate_relevance_score(
        query=message,
        response=answer,
        context_docs=retrieved_docs,
        was_offtopic=classification.get("is_offtopic", False),
        was_greeting=classification.get("is_greeting", False)
    )
    
    log_query_interaction(
        username=username,
        role=role,
        query=message,
        response=answer,
        query_classification=classification,
        docs_used=len(retrieved_docs),
        relevance_score=relevance_score
    )

    return {
        "role": role,
        "query": message,
        "response": answer
    }