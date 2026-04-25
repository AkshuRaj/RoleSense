"""
Audit Logging System
Tracks all API access attempts with security alerts for suspicious activity
"""

from datetime import datetime
from collections import defaultdict
import os

# In-memory tracker for DENIED requests (per user per session)
_denied_attempts = defaultdict(int)
LOG_FILE = "logs.txt"


def log_access(username: str, role: str, query: str, status: str, departments_accessed: str):
    """
    Log API access attempt to audit file.
    
    Args:
        username: User who made the request
        role: User's role (engineering, finance, hr, marketing, c_level)
        query: The question/query asked
        status: "ALLOWED" or "DENIED"
        departments_accessed: Department name or "ALL" for c_level
    
    Returns:
        bool: True if logged successfully, False otherwise
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create log entry
        log_entry = (
            f"[{timestamp}] | User: {username} | Role: {role} | "
            f"Status: {status} | Query: {query[:50]}... | Dept: {departments_accessed}\n"
        )
        
        # Append to log file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        # 🚨 SECURITY ALERT: Track DENIED attempts
        if status == "DENIED":
            _denied_attempts[username] += 1
            
            # Alert if suspicious activity detected (3+ DENIED requests)
            if _denied_attempts[username] >= 3:
                alert_entry = (
                    f"[{timestamp}] | ⚠️  ALERT: Suspicious activity detected for {username} "
                    f"({_denied_attempts[username]} failed access attempts)\n"
                )
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(alert_entry)
                
                return True
        
        return True
    
    except Exception as e:
        print(f"❌ Logging error: {e}")
        return False


def get_departments_accessed(metadatas: list) -> str:
    """
    Extract and format departments from metadata.
    
    Args:
        metadatas: List of metadata dictionaries from vector store
    
    Returns:
        str: Comma-separated department names or "ALL" for c_level unrestricted
    """
    if not metadatas:
        return "NONE"
    
    depts = set(meta.get("department", "unknown") for meta in metadatas)
    return ", ".join(sorted(depts))


def reset_session():
    """Reset denied attempts tracker (call on app restart or session end)"""
    global _denied_attempts
    _denied_attempts.clear()


def get_denied_count(username: str) -> int:
    """Get current DENIED attempt count for a user"""
    return _denied_attempts.get(username, 0)
