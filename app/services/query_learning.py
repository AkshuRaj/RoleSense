"""
Query Learning Module - Tracks and analyzes queries for continuous improvement
Helps identify patterns, improve relevance, and detect common questions
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)

# Query log file path
QUERY_LOG_FILE = Path("logs/query_analytics.json")
QUERY_STATS_FILE = Path("logs/query_stats.json")


def ensure_log_directory():
    """Create logs directory if it doesn't exist."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)


def log_query_interaction(
    username: str,
    role: str,
    query: str,
    response: str,
    query_classification: Dict,
    docs_used: int,
    relevance_score: float = None
) -> None:
    """
    Log a query interaction for analytics and learning.
    
    Args:
        username: User's name
        role: User's role/department
        query: Original query
        response: Generated response
        query_classification: Query classification data
        docs_used: Number of documents used
        relevance_score: Optional relevance score (0-1)
    """
    ensure_log_directory()
    
    interaction = {
        "timestamp": datetime.now().isoformat(),
        "username": username,
        "role": role,
        "query": query,
        "response_preview": response[:200],  # First 200 chars for privacy
        "query_type": query_classification.get("type", "unknown"),
        "is_greeting": query_classification.get("is_greeting", False),
        "is_offtopic": query_classification.get("is_offtopic", False),
        "is_company_related": query_classification.get("is_company_related", False),
        "keywords_found": query_classification.get("keywords_found", []),
        "docs_used": docs_used,
        "relevance_score": relevance_score or 0.0,
        "response_length": len(response)
    }
    
    try:
        # Append to query log
        logs = []
        if QUERY_LOG_FILE.exists():
            with open(QUERY_LOG_FILE, 'r') as f:
                logs = json.load(f)
        
        logs.append(interaction)
        
        # Keep only last 10000 entries to prevent file size explosion
        if len(logs) > 10000:
            logs = logs[-10000:]
        
        with open(QUERY_LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)
        
        # Update statistics
        _update_query_statistics(interaction)
        
    except Exception as e:
        logger.error(f"Error logging query interaction: {str(e)}")


def _update_query_statistics(interaction: Dict) -> None:
    """Update running statistics about queries."""
    try:
        stats = {}
        if QUERY_STATS_FILE.exists():
            with open(QUERY_STATS_FILE, 'r') as f:
                stats = json.load(f)
        
        # Initialize counters if needed
        if "total_queries" not in stats:
            stats = {
                "total_queries": 0,
                "greetings": 0,
                "offtopic_questions": 0,
                "company_questions": 0,
                "by_role": defaultdict(int),
                "query_types": defaultdict(int),
                "average_docs_used": 0,
                "average_response_length": 0,
                "common_keywords": defaultdict(int)
            }
        
        # Update counts
        stats["total_queries"] += 1
        if interaction["is_greeting"]:
            stats["greetings"] += 1
        if interaction["is_offtopic"]:
            stats["offtopic_questions"] += 1
        if interaction["is_company_related"]:
            stats["company_questions"] += 1
        
        # Track by role
        if interaction["role"] not in stats["by_role"]:
            stats["by_role"][interaction["role"]] = 0
        stats["by_role"][interaction["role"]] += 1
        
        # Track query types
        query_type = interaction["query_type"]
        if query_type not in stats["query_types"]:
            stats["query_types"][query_type] = 0
        stats["query_types"][query_type] += 1
        
        # Track common keywords
        for keyword in interaction.get("keywords_found", []):
            if keyword not in stats["common_keywords"]:
                stats["common_keywords"][keyword] = 0
            stats["common_keywords"][keyword] += 1
        
        # Calculate rolling averages
        total = stats["total_queries"]
        prev_avg_docs = stats.get("average_docs_used", 0)
        prev_avg_response = stats.get("average_response_length", 0)
        
        stats["average_docs_used"] = ((prev_avg_docs * (total - 1)) + interaction["docs_used"]) / total
        stats["average_response_length"] = ((prev_avg_response * (total - 1)) + interaction["response_length"]) / total
        
        # Convert defaultdict to regular dict for JSON serialization
        stats["by_role"] = dict(stats["by_role"])
        stats["query_types"] = dict(stats["query_types"])
        stats["common_keywords"] = dict(stats["common_keywords"])
        
        with open(QUERY_STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error updating query statistics: {str(e)}")


def get_query_insights() -> Dict:
    """Get insights from query analytics."""
    ensure_log_directory()
    
    try:
        if not QUERY_STATS_FILE.exists():
            return {"status": "No data available yet"}
        
        with open(QUERY_STATS_FILE, 'r') as f:
            stats = json.load(f)
        
        return {
            "status": "success",
            "total_queries": stats.get("total_queries", 0),
            "greetings_percentage": f"{(stats.get('greetings', 0) / max(stats.get('total_queries', 1), 1) * 100):.1f}%",
            "offtopic_percentage": f"{(stats.get('offtopic_questions', 0) / max(stats.get('total_queries', 1), 1) * 100):.1f}%",
            "company_related_percentage": f"{(stats.get('company_questions', 0) / max(stats.get('total_queries', 1), 1) * 100):.1f}%",
            "by_role": stats.get("by_role", {}),
            "query_types": stats.get("query_types", {}),
            "top_keywords": sorted(
                stats.get("common_keywords", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "average_docs_used": f"{stats.get('average_docs_used', 0):.2f}",
            "average_response_length": f"{stats.get('average_response_length', 0):.0f} chars"
        }
        
    except Exception as e:
        logger.error(f"Error getting query insights: {str(e)}")
        return {"status": "error", "message": str(e)}


def get_common_questions_by_role(role: str, limit: int = 5) -> List[Dict]:
    """Get most common questions asked by a specific role."""
    ensure_log_directory()
    
    try:
        if not QUERY_LOG_FILE.exists():
            return []
        
        with open(QUERY_LOG_FILE, 'r') as f:
            logs = json.load(f)
        
        # Filter by role and count unique queries
        role_queries = defaultdict(int)
        for log in logs:
            if log.get("role") == role and log.get("is_company_related"):
                role_queries[log.get("query", "").lower()] += 1
        
        # Sort by frequency
        top_questions = sorted(
            role_queries.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [{"query": q, "count": c} for q, c in top_questions]
        
    except Exception as e:
        logger.error(f"Error getting common questions: {str(e)}")
        return []


def calculate_relevance_score(
    query: str,
    response: str,
    context_docs: List[str],
    was_offtopic: bool,
    was_greeting: bool
) -> float:
    """
    Calculate relevance score for query-response pair.
    
    This helps identify when responses might not match queries well.
    
    Args:
        query: Original query
        response: Generated response
        context_docs: Context documents used
        was_offtopic: Whether query was off-topic
        was_greeting: Whether query was greeting
        
    Returns:
        float: Relevance score (0-1)
    """
    # Special cases
    if was_greeting:
        return 0.95  # Greetings should always get high relevance
    
    if was_offtopic:
        # Off-topic should have professional response (not data retrieval)
        if "outside my scope" in response or "don't have access" in response:
            return 0.90
        else:
            return 0.5  # Lower if we tried to answer off-topic
    
    # For company questions, check if response contains data
    score = 0.5  # Base score
    
    # Presence of numbers/dates suggests real data
    if any(char.isdigit() for char in response):
        score += 0.2
    
    # Check for quantitative statements
    if any(keyword in response.lower() for keyword in ["$", "%", "increase", "decrease", "million"]):
        score += 0.15
    
    # Check response length (not too short, not too long)
    if 100 <= len(response) <= 500:
        score += 0.15
    
    # Penalty for uncertainty markers
    if any(marker in response.lower() for marker in ["i don't know", "unclear", "not sure"]):
        score = max(score - 0.2, 0.3)
    
    return min(score, 1.0)
