"""
Query Classification Module - Detects greeting, off-topic, and company-related queries
Helps reduce hallucinations and improves response relevance
"""

import re
from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)

# Greeting patterns
GREETING_PATTERNS = [
    r'^(h+i+|h+e+l+o+|h+e+y+|greetings?|good\s+(morning|afternoon|evening|night)|howdy)(\s|$)',
    r'^(what\'?s?\s+up|how\s+are\s+you|how\'?s\s+it\s+going)',
    r'^\s*(h+e+y+|h+e+l+o+|h+i+)\s+there',
]

# Off-topic patterns - Questions NOT related to company
OFFTOPIC_PATTERNS = [
    # Personal questions
    r'^(what\s+is\s+your\s+|do\s+you\s+have\s+a\s+)(favorite|name|age|birthday|appearance|hair|eyes|color)',
    r'^did\s+you\s+(eat|sleep|drink|watch|read)',
    r'^what\s+(color|food|music|movie|song)',
    r'^tell\s+me\s+(a\s+joke|a\s+story|about\s+yourself|your\s+opinion\s+on)',
    
    # General knowledge
    r'^(what\s+is\s+|who\s+is\s+|how\s+do\s+|explain\s+)(climate|weather|physics|math|history|geography|politics)',
    r'^(calculate|solve|find)\s+',
    r'^(what\s+time\s+is\s+it|what\s+date|when)',
    
    # Illegal/inappropriate
    r'^(how\s+do\s+i|help\s+me\s+)(hack|crack|bypass|break|cheat|steal)',
    
    # Spam/gibberish
    r'^(test|hello\s+world|asdf|qwerty|zzz|xxx)',
]

# Company-related keywords
COMPANY_KEYWORDS = {
    'company': ['finsol', 'company', 'organization', 'enterprise', 'business'],
    'finance': ['revenue', 'profit', 'salary', 'budget', 'cost', 'expense', 'financial', 'margin', 'roi', 'cash'],
    'hr': ['employee', 'leave', 'benefit', 'salary', 'hr', 'human resources', 'policy', 'onboard', 'hiring'],
    'engineering': ['architecture', 'system', 'microservice', 'database', 'kubernetes', 'aws', 'api', 'deployment', 'tech'],
    'marketing': ['campaign', 'marketing', 'customer', 'acquisition', 'roi', 'engagement', 'social', 'conversion'],
    'general': ['policy', 'handbook', 'code of conduct', 'values', 'mission', 'vision'],
}


def is_greeting(query: str) -> bool:
    """
    Detects if query is a greeting message.
    
    Args:
        query: User query string
        
    Returns:
        bool: True if query is a greeting
    """
    query_lower = query.strip().lower()
    
    # Check greeting patterns
    for pattern in GREETING_PATTERNS:
        if re.search(pattern, query_lower):
            return True
    
    # Check if it's just a single greeting word
    if query_lower in ['hi', 'hello', 'hey', 'thanks', 'thank you']:
        return True
    
    return False


def is_offtopic(query: str) -> bool:
    """
    Detects if query is off-topic (not related to company data).
    
    Args:
        query: User query string
        
    Returns:
        bool: True if query is off-topic
    """
    query_lower = query.strip().lower()
    
    # Check off-topic patterns
    for pattern in OFFTOPIC_PATTERNS:
        if re.search(pattern, query_lower):
            return True
    
    return False


def classify_query(query: str) -> Dict[str, any]:
    """
    Comprehensive query classification.
    
    Args:
        query: User query string
        
    Returns:
        dict: Classification result with type, confidence, and recommended_action
    """
    result = {
        "query": query,
        "type": None,
        "confidence": 0.0,
        "is_greeting": False,
        "is_offtopic": False,
        "is_company_related": False,
        "keywords_found": []
    }
    
    query_lower = query.strip().lower()
    
    # Check greeting
    if is_greeting(query):
        result["type"] = "greeting"
        result["is_greeting"] = True
        result["confidence"] = 0.95
        return result
    
    # Check off-topic
    if is_offtopic(query):
        result["type"] = "offtopic"
        result["is_offtopic"] = True
        result["confidence"] = 0.90
        return result
    
    # Check for company keywords
    found_keywords = []
    for category, keywords in COMPANY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query_lower:
                found_keywords.append(f"{category}:{keyword}")
    
    if found_keywords:
        result["type"] = "company_related"
        result["is_company_related"] = True
        result["keywords_found"] = found_keywords
        result["confidence"] = min(0.95, 0.5 + (len(found_keywords) * 0.15))
    else:
        # Ambiguous - could be company or general
        result["type"] = "ambiguous"
        result["confidence"] = 0.5
    
    return result


def get_query_intent(query: str) -> str:
    """
    Determine the main intent of the query.
    
    Args:
        query: User query string
        
    Returns:
        str: Intent category (greeting, question, search, command, etc.)
    """
    query_lower = query.strip().lower()
    
    if query_lower.endswith('?'):
        return "question"
    elif any(query_lower.startswith(cmd) for cmd in ['list', 'show', 'get', 'find']):
        return "search"
    elif any(query_lower.startswith(cmd) for cmd in ['what', 'how', 'explain', 'describe']):
        return "explanation"
    elif any(query_lower.startswith(greeting) for greeting in ['hi', 'hello', 'hey']):
        return "greeting"
    else:
        return "general"
