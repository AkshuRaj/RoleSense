import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Page config
st.set_page_config(
    page_title="RoleSenseAI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark theme CSS with sticky input
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #0a0e27;
        color: #e0e0e0;
    }
    
    /* Main content container */
    .main {
        background-color: #0a0e27;
    }
    
    /* Sidebar */
    [data-testid="sidebar"] {
        background-color: #1a1f3a;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #e0e0e0;
    }
    
    h1 {
        font-size: 28px;
        margin-bottom: 24px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }
    
    h2 {
        font-size: 20px;
        margin-bottom: 12px;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #2d3748, transparent);
        margin: 16px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.auth = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000/chat"

# ============ SIDEBAR - LOGIN ============
with st.sidebar:
    st.markdown("### 🔐 Authentication")
    st.divider()
    
    if not st.session_state.authenticated:
        with st.form("login_form"):
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
                key="login_username"
            )
            password = st.text_input(
                "Password",
                placeholder="Enter your password",
                type="password",
                key="login_password"
            )
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                if not username or not password:
                    st.error("❌ Username and password required")
                else:
                    try:
                        # Test authentication
                        auth = HTTPBasicAuth(username, password)
                        response = requests.get(
                            "http://127.0.0.1:8000/test",
                            auth=auth,
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.authenticated = True
                            st.session_state.username = username
                            st.session_state.role = data.get("role", "unknown")
                            st.session_state.auth = auth
                            st.session_state.chat_history = []
                            st.success("✅ Login successful")
                            st.rerun()
                        else:
                            st.error("❌ Invalid credentials")
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")
    else:
        # User info display
        st.markdown("### 👤 User Information")
        st.divider()
        
        st.markdown(f"""
        <div class="info-box">
            <div class="info-label">Username</div>
            <div class="info-value">{st.session_state.username}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="info-box">
            <div class="info-label">Role</div>
            <div class="info-value">{st.session_state.role.upper()}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.auth = None
            st.session_state.chat_history = []
            st.rerun()

# Main chat area
if not st.session_state.authenticated:
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; height: 80vh;">
        <div style="text-align: center;">
            <h1>🤖 RoleSenseAI</h1>
            <p style="color: #9ca3af; font-size: 16px; margin-top: 20px;">
                Please log in with your credentials to start chatting
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Header
    st.markdown("## 💬 Chat Interface")
    st.divider()
    
    # Chat history display
    # Chat history display    
    if not st.session_state.chat_history:
        st.markdown("""
        <div style="text-align: center; color: #6b7280; padding: 60px 20px;">
            <p style="font-size: 18px;">👋 Start a conversation</p>
            <p style="font-size: 14px; margin-top: 8px;">Type a message below to begin chatting</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for message in st.session_state.chat_history:
            role = "assistant" if message["role"] == "bot" else message["role"]
            with st.chat_message(role):
                st.markdown(message["content"])
                if "timestamp" in message:
                    st.caption(message["timestamp"])
    
    # Process message via Streamlit Chat Input natively
    if user_input := st.chat_input("Ask me anything about the company..."):
        # Add user message to history
        timestamp = datetime.now().strftime("%H:%M")
        
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(user_input)
            
        # Get bot response
        try:
            with st.spinner("Thinking..."):
                response = requests.post(
                    BACKEND_URL,
                    params={"message": user_input},
                    auth=st.session_state.auth,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    bot_response = data.get("response", "Unable to get response")
                elif response.status_code == 401:
                    bot_response = "❌ Authentication failed. Please log in again."
                else:
                    bot_response = f"❌ Error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            bot_response = "⏱️ Request timed out. Please try again."
        except requests.exceptions.ConnectionError:
            bot_response = "🔌 Connection error. Is the backend running at http://127.0.0.1:8000?"
        except Exception as e:
            bot_response = f"❌ Error: {str(e)}"
        
        # Add bot response to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": bot_response,
            "timestamp": datetime.now().strftime("%H:%M")
        })
        
        st.rerun()
