from groq import Groq
from dotenv import load_dotenv
from app.services.query_classifier import classify_query, is_greeting, is_offtopic
import os
import logging
import re

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
logger = logging.getLogger(__name__)


def generate_answer(query: str, context_docs: list, username: str = None, role: str = None) -> str:
    """
    Generate answer with improved hallucination prevention and user personalization.
    
    Args:
        query: User query
        context_docs: Retrieved documents from vector store
        username: User's name for personalization
        role: User's role for context
        
    Returns:
        str: Generated response
    """
    
    # 1️⃣ GREETING DETECTION - Personalized greeting with username
    if is_greeting(query):
        if username:
            return f"👋 Hello {username}! Welcome to FinSolve's Enterprise Chatbot. I'm here to help you with company-related information. Feel free to ask me anything about your department or company policies!"
        else:
            return "👋 Hello! I'm here to help you with company-related information. What can I assist you with today?"
    
    # 2️⃣ OFF-TOPIC DETECTION - Professional handling of non-company questions
    if is_offtopic(query):
        professional_response = (
            "🤔 I appreciate the question, but that's outside my scope. I'm specifically designed to provide information "
            "about FinSolve Technologies — including company policies, HR guidelines, financial data, engineering documentation, "
            "and marketing insights relevant to your role.\n\n"
            "Would you like to ask me something about the company instead? For example:\n"
            "• 'What are the leave policies?'\n"
            "• 'Tell me about the engineering architecture'\n"
            "• 'What were the Q4 2024 financial results?'\n"
            "• 'How can I request a transfer?'"
        )
        return professional_response
    
    # 3️⃣ NO CONTEXT AVAILABLE - Secure response with no data leakage
    if not context_docs or len(context_docs) == 0:
        return (
            "❌ I don't have access to information about this topic in the company database. "
            "This could be because:\n"
            "• The information isn't available in your accessible departments\n"
            "• You may not have permission to access this information\n"
            "• The information hasn't been documented yet\n\n"
            "Please contact your HR manager or department lead for more details."
        )
    
    # 4️⃣ CONTEXT AVAILABLE - Generate answer with strict hallucination prevention
    context = "\n---\n".join(context_docs[:3])  # Use only top 3 results for clarity
    
    # Create role-aware system prompt (WITHOUT citing sources)
    role_context = f"The user is in the {role} department" if role else "The user is accessing this system"
    
    prompt = f"""
    You are a professional, factual enterprise assistant for FinSolve Technologies.
    {role_context} and can only access information relevant to their role.
    
    ═══════════════════════════════════════════════════════════
    🚫 CRITICAL ANTI-HALLUCINATION RULES (MANDATORY):
    ═══════════════════════════════════════════════════════════
    
    FORBIDDEN BEHAVIORS:
    ✗ DO NOT create, invent, or fabricate information
    ✗ DO NOT add examples not in the context
    ✗ DO NOT guess numbers, dates, or percentages
    ✗ DO NOT hypothesize about policies or procedures
    ✗ DO NOT continue incomplete sentences with made-up content
    ✗ DO NOT mention departments or information you weren't given
    ✗ DO NOT apologize and then provide incorrect information
    ✗ DO NOT cite sources or mention "section 2.3.5" or similar references
    ✗ DO NOT mention where information comes from
    
    REQUIRED BEHAVIORS:
    ✓ ONLY answer using the provided context below
    ✓ State facts directly without mentioning sources
    ✓ Quote exact sections when helpful (but don't cite them)
    ✓ Be specific and factual
    ✓ If uncertain, say: "This information is not available in the company database."
    ✓ Maintain confidentiality - do not reference other departments
    ✓ Keep responses concise (3-4 sentences maximum unless detailed explanation requested)
    ✓ Provide information as fact, not as coming from a document
    
    ═══════════════════════════════════════════════════════════
    📋 AVAILABLE INFORMATION (ONLY SOURCE OF TRUTH):
    ═══════════════════════════════════════════════════════════
    {context}
    
    ═══════════════════════════════════════════════════════════
    ❓ USER QUESTION: {query}
    ═══════════════════════════════════════════════════════════
    
    RESPONSE (FACTUAL, FROM CONTEXT ONLY - NO SOURCE CITATIONS):
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
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
            ],
            temperature=0.1,  # Extremely low for maximum factuality
            max_tokens=500,   # Reasonable limit to prevent rambling
            top_p=0.3         # Restrict to most probable tokens
        )
        
        answer = response.choices[0].message.content.strip()
        
        # 5️⃣ POST-GENERATION VALIDATION - Remove any citations that slipped through
        answer = _validate_and_sanitize_response(answer, context_docs)
        
        logger.info(f"Query processed for user: {username}, Role: {role}")
        
        return answer
        
    except Exception as e:
        logger.error(f"LLM Error: {str(e)}")
        return (
            "⚠️ An error occurred while processing your request. "
            "Please try again or contact support if the issue persists."
        )


def _validate_and_sanitize_response(response: str, context_docs: list) -> str:
    """
    Post-generation validation to catch potential hallucinations and remove citations.
    
    Args:
        response: Generated response from LLM
        context_docs: Original context documents
        
    Returns:
        str: Validated/sanitized response
    """
    import re
    
    # Check for common hallucination patterns
    hallucination_indicators = [
        "for example",  # Often followed by made-up examples
        "such as",      # Similar issue
        "specifically",  # Often leads to specifics not in context
        "in particular", # Same as above
    ]
    
    response_lower = response.lower()
    
    # Remove citation patterns that might have slipped through
    citation_patterns = [
        r"(?:in section|section|from section)\s+[\d\.\w\s]+",  # "in section 2.3.5"
        r"(?:in document|document|from document)\s+[\w\s]+",    # "in document..."
        r"(?:according to|as stated in|the document|the context|this information)\s+\w+",  # "according to..."
        r"\([^)]*section[^)]*\)",  # "(section 2.3)"
        r"stated in [\w\s]+:",     # "stated in engineering_master_doc:"
        r"provided (?:context|information)",  # "provided information"
        r"This is stated in",
        r"According to",
        r"From the provided information",
    ]
    
    for pattern in citation_patterns:
        response = re.sub(pattern, "", response, flags=re.IGNORECASE)
    
    # Clean up multiple spaces
    response = re.sub(r'\s+', ' ', response)
    response = response.strip()
    
    # Check for "I apologize but..." pattern
    if response_lower.startswith("i apologize") and len(response.split(".")) > 1:
        lines = response.split(".")
        if any(kw in lines[1].lower() for kw in ["however", "but", "instead"]):
            return "This specific information is not available in the company database. Please check with your department lead or HR for more details."
    
    return response


def get_response_with_learning(query: str, context_docs: list, username: str = None, role: str = None) -> dict:
    """
    Generate answer and log for continuous learning/improvement.
    
    Args:
        query: User query
        context_docs: Retrieved documents
        username: User's name
        role: User's role
        
    Returns:
        dict: Response with metadata for learning
    """
    # Classify query
    classification = classify_query(query)
    
    # Generate answer
    answer = generate_answer(query, context_docs, username, role)
    
    # Return with metadata for learning/analytics
    return {
        "response": answer,
        "query_classification": classification,
        "username": username,
        "role": role,
        "docs_used": len(context_docs),
        "was_offtopic": classification["is_offtopic"],
        "was_greeting": classification["is_greeting"]
    }