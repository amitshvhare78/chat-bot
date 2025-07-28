import streamlit as st
from groq import Groq
import os
import time
from datetime import datetime
import sqlite3
import hashlib
import re

# Set page configuration
st.set_page_config(
    page_title="AI Chat Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid;
        max-width: 80%;
        color: #000 !important;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
        margin-left: auto;
        margin-right: 0;
    }
    .assistant-message {
        background-color: #f3e5f5;
        border-left-color: #9c27b0;
        margin-left: 0;
        margin-right: auto;
    }
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: bold;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #5a6fd8 0%, #6a4190 100%);
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
    .model-info {
        background-color: #e8f5e8;
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 3px solid #4caf50;
        margin: 0.5rem 0;
    }
    .top-nav {
        background: white;
        padding: 0.5rem;
        border-bottom: 1px solid #e0e0e0;
        position: sticky;
        top: 0;
        z-index: 100;
    }
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 1rem;
    }
    .input-container {
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        width: 80%;
        max-width: 600px;
        background: white;
        padding: 1rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "model" not in st.session_state:
    st.session_state.model = "llama3-8b-8192"
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.8  # Higher temperature for more creative, human-like responses
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = """You are a warm, empathetic, and human-like conversational partner. Here's how to chat naturally:

CONVERSATION STYLE:
- Use casual, friendly language like a real friend would
- Show genuine interest and curiosity about the person
- Ask follow-up questions to keep conversations flowing
- Use natural expressions like "That's really interesting!", "I totally get what you mean", "Oh wow!", "That sounds amazing!"
- Share your thoughts and reactions naturally
- Use contractions (I'm, you're, that's, etc.) for a more casual tone
- Occasionally use emojis to express emotions 😊
- Show empathy and understanding when someone shares problems
- Be supportive and encouraging

PERSONALITY TRAITS:
- Warm and approachable
- Curious and interested in learning about others
- Supportive and encouraging
- Sometimes playful and humorous
- Genuinely cares about the person's well-being
- Shares relevant personal insights when appropriate

CONVERSATION TECHNIQUES:
- Mirror the person's energy and communication style
- Use their name occasionally to make it personal
- Remember details they've shared and reference them later
- Ask open-ended questions to encourage sharing
- Validate their feelings and experiences
- Share your own thoughts and reactions authentically

Remember: You're not just an AI assistant - you're a friend having a real conversation. Be natural, caring, and genuinely interested in the person you're talking to."""
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "remember_me" not in st.session_state:
    st.session_state.remember_me = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_interests" not in st.session_state:
    st.session_state.user_interests = []
if "conversation_style" not in st.session_state:
    st.session_state.conversation_style = "friendly"

# Authentication functions
def init_db():
    """Initialize the database with users table"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Check if columns exist
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'users' not in [table[0] for table in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        # Create new table with all columns
        c.execute('''
            CREATE TABLE users
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             username TEXT UNIQUE NOT NULL,
             email TEXT UNIQUE NOT NULL,
             password_hash TEXT NOT NULL,
             gender TEXT,
             chatbot_name TEXT,
             chatbot_gender TEXT,
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             last_login TIMESTAMP)
        ''')
    else:
        # Add missing columns to existing table
        if 'gender' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN gender TEXT')
        if 'chatbot_name' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN chatbot_name TEXT')
        if 'chatbot_gender' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN chatbot_gender TEXT')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    password_hash = hash_password(password)
    c.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', (username, password_hash))
    user = c.fetchone()
    conn.close()
    return user

def update_last_login(username):
    """Update last login timestamp"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET last_login = ? WHERE username = ?', (datetime.now(), username))
    conn.commit()
    conn.close()

def get_user_gender(username):
    """Get user's gender from database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT gender FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_user_chatbot_info(username):
    """Get user's chatbot name and gender from database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT chatbot_name, chatbot_gender FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    return result if result else (None, None)

def restore_session():
    """Restore user session if they were previously logged in"""
    if st.session_state.user_id and st.session_state.username:
        # Verify user still exists in database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT username FROM users WHERE id = ? AND username = ?', 
                  (st.session_state.user_id, st.session_state.username))
        user = c.fetchone()
        conn.close()
        
        if user:
            # Restore user data
            st.session_state.logged_in = True
            st.session_state.user_gender = get_user_gender(st.session_state.username)
            chatbot_name, chatbot_gender = get_user_chatbot_info(st.session_state.username)
            st.session_state.chatbot_name = chatbot_name
            st.session_state.chatbot_gender = chatbot_gender
            return True
    return False

def save_session_data():
    """Save session data to ensure persistence"""
    if st.session_state.logged_in and st.session_state.remember_me:
        # Force session state to persist
        st.session_state._persistent = True

# Initialize database
init_db()

# Initialize Groq client
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except:
    st.error("❌ API key not found. Please check your secrets.toml file.")
    st.stop()

# Login page function
def login_page():
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .login-header {
            text-align: center;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        .stButton > button {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            padding: 0.5rem 2rem;
            font-weight: bold;
            width: 100%;
        }
        .stButton > button:hover {
            background: linear-gradient(90deg, #5a6fd8 0%, #6a4190 100%);
        }
        .signup-link {
            text-align: center;
            margin-top: 1rem;
        }
    </style>
    
    <script>
        // Handle Enter key navigation
        document.addEventListener('DOMContentLoaded', function() {
            const inputs = document.querySelectorAll('input[type="text"], input[type="password"]');
            inputs.forEach((input, index) => {
                input.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        if (index < inputs.length - 1) {
                            inputs[index + 1].focus();
                        } else {
                            // If it's the last input, submit the form
                            const form = input.closest('form');
                            if (form) {
                                const submitButton = form.querySelector('button[type="submit"]');
                                if (submitButton) {
                                    submitButton.click();
                                }
                            }
                        }
                    }
                });
            });
        });
    </script>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-header"><h2>🔐 Login</h2><p>Welcome back to AI Chat Assistant</p></div>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("👤 Username", placeholder="Enter your username")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
        remember_me = st.checkbox("Remember me", value=st.session_state.remember_me)
        
        col1, col2 = st.columns(2)
        with col1:
            login_button = st.form_submit_button("🚀 Login", use_container_width=True)
        with col2:
            if st.form_submit_button("🔄 Demo Login", use_container_width=True):
                st.session_state.demo_mode = True
                st.session_state.logged_in = True
                st.session_state.username = "Demo User"
                st.session_state.user_id = 0  # Demo user ID
                st.session_state.remember_me = True
                st.session_state.user_gender = "Prefer not to say"
                st.session_state.chatbot_name = "Alex"
                st.session_state.chatbot_gender = "Non-binary"
                save_session_data()
                st.rerun()
    
    if login_button and username and password:
        user = verify_user(username, password)
        if user:
            st.success(f"✅ Welcome back, {username}!")
            update_last_login(username)
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.user_id = user[0]
            st.session_state.remember_me = remember_me
            st.session_state.user_gender = get_user_gender(username)
            
            # Load chatbot preferences
            chatbot_name, chatbot_gender = get_user_chatbot_info(username)
            st.session_state.chatbot_name = chatbot_name
            st.session_state.chatbot_gender = chatbot_gender
            
            # Save session data for persistence
            save_session_data()
            
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Invalid username or password")
    
    st.markdown('<div class="signup-link">', unsafe_allow_html=True)
    st.markdown("Don't have an account?")
    if st.button("📝 Sign Up", key="go_to_signup"):
        st.session_state.page = "signup"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Signup page function
def signup_page():
    
    st.markdown("""
    <style>
        .signup-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .signup-header {
            text-align: center;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        .stButton > button {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            padding: 0.5rem 2rem;
            font-weight: bold;
            width: 100%;
        }
        .stButton > button:hover {
            background: linear-gradient(90deg, #5a6fd8 0%, #6a4190 100%);
        }
        .login-link {
            text-align: center;
            margin-top: 1rem;
        }
        .password-strength {
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }
        .strength-weak { color: #f44336; }
        .strength-medium { color: #ff9800; }
        .strength-strong { color: #4caf50; }
    </style>
    
    <script>
        // Handle Enter key navigation for signup form
        document.addEventListener('DOMContentLoaded', function() {
            const inputs = document.querySelectorAll('input[type="text"], input[type="password"]');
            inputs.forEach((input, index) => {
                input.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        if (index < inputs.length - 1) {
                            inputs[index + 1].focus();
                        } else {
                            // If it's the last input, submit the form
                            const form = input.closest('form');
                            if (form) {
                                const submitButton = form.querySelector('button[type="submit"]');
                                if (submitButton) {
                                    submitButton.click();
                                }
                            }
                        }
                    }
                });
            });
        });
    </script>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="signup-container">', unsafe_allow_html=True)
    st.markdown('<div class="signup-header"><h2>📝 Sign Up</h2><p>Create your AI Chat Assistant account</p></div>', unsafe_allow_html=True)
    
    with st.form("signup_form"):
        username = st.text_input("👤 Username", placeholder="Choose a username")
        email = st.text_input("📧 Email", placeholder="Enter your email")
        
        # Gender selection
        gender = st.selectbox(
            "👥 Gender",
            options=["", "Male", "Female", "Non-binary", "Prefer not to say"],
            placeholder="Select your gender"
        )
        
        st.markdown("### 🤖 Chatbot Preferences")
        
        # Chatbot name
        chatbot_name = st.text_input("💬 Chatbot Name", placeholder="Give your AI assistant a name")
        
        # Chatbot gender preference
        chatbot_gender = st.selectbox(
            "👥 Chatbot Gender",
            options=["", "Male", "Female", "Non-binary", "Same as me", "Opposite of me"],
            placeholder="Choose your chatbot's gender"
        )
        
        # Show preview of chatbot personality
        if chatbot_name and chatbot_gender:
            preview_gender = chatbot_gender
            if chatbot_gender == "Same as me":
                preview_gender = gender
            elif chatbot_gender == "Opposite of me":
                if gender == "Male":
                    preview_gender = "Female"
                elif gender == "Female":
                    preview_gender = "Male"
                else:
                    preview_gender = "Non-binary"
            
            gender_emoji = {"Male": "👨", "Female": "👩", "Non-binary": "⚧"}.get(preview_gender, "🤖")
            st.info(f"🤖 Your AI assistant will be: **{chatbot_name}** {gender_emoji} ({preview_gender})")
        
        password = st.text_input("🔒 Password", type="password", placeholder="Create a password")
        confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
        
        # Password strength indicator
        if password:
            is_valid, message = validate_password(password)
            if is_valid:
                st.markdown(f'<div class="password-strength strength-strong">✅ {message}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="password-strength strength-weak">❌ {message}</div>', unsafe_allow_html=True)
        
        terms_accepted = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        
        col1, col2 = st.columns(2)
        with col1:
            signup_button = st.form_submit_button("🚀 Create Account", use_container_width=True)
        with col2:
            if st.form_submit_button("🔙 Back to Login", use_container_width=True):
                st.session_state.page = "login"
                st.rerun()
    
    if signup_button:
        # Validation
        if not username or not email or not password or not confirm_password:
            st.error("❌ Please fill in all required fields")
        elif not gender:
            st.error("❌ Please select your gender")
        elif not chatbot_name:
            st.error("❌ Please give your chatbot a name")
        elif not chatbot_gender:
            st.error("❌ Please select your chatbot's gender")
        elif not validate_email(email):
            st.error("❌ Please enter a valid email address")
        elif not validate_password(password)[0]:
            st.error(f"❌ {validate_password(password)[1]}")
        elif password != confirm_password:
            st.error("❌ Passwords do not match")
        elif not terms_accepted:
            st.error("❌ Please accept the terms and conditions")
        else:
            # Check if user already exists
            existing = check_user_exists(username, email)
            if existing:
                if existing[0] == username:
                    st.error("❌ Username already exists")
                else:
                    st.error("❌ Email already registered")
            else:
                # Create user
                try:
                    create_user(username, email, password, gender, chatbot_name, chatbot_gender)
                    st.success("✅ Account created successfully!")
                    st.info("You can now login with your credentials")
                    time.sleep(2)
                    st.session_state.page = "login"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating account: {str(e)}")
    
    st.markdown('<div class="login-link">', unsafe_allow_html=True)
    st.markdown("Already have an account?")
    if st.button("🔐 Login", key="go_to_login"):
        st.session_state.page = "login"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Helper functions for signup
def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"

def check_user_exists(username, email):
    """Check if username or email already exists"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT username, email FROM users WHERE username = ? OR email = ?', (username, email))
    existing = c.fetchone()
    conn.close()
    return existing

def create_user(username, email, password, gender, chatbot_name, chatbot_gender):
    """Create new user in database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    password_hash = hash_password(password)
    c.execute('INSERT INTO users (username, email, password_hash, gender, chatbot_name, chatbot_gender) VALUES (?, ?, ?, ?, ?, ?)', 
              (username, email, password_hash, gender, chatbot_name, chatbot_gender))
    conn.commit()
    conn.close()

# Main app logic
# Check if user should be automatically logged in
if not st.session_state.logged_in and st.session_state.remember_me and st.session_state.user_id:
    if restore_session():
        st.success(f"✅ Welcome back, {st.session_state.username}!")
        time.sleep(1)
        st.rerun()

if not st.session_state.logged_in:
    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "signup":
        signup_page()
else:
        # User is logged in - show chat interface
    # Top navigation bar with hamburger menu
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if st.button("☰", help="Menu"):
            st.session_state.show_menu = not st.session_state.get('show_menu', False)
    
    with col2:
        # Main header in center
        if hasattr(st.session_state, 'chatbot_name') and st.session_state.chatbot_name:
            chatbot_gender = st.session_state.chatbot_gender
            if chatbot_gender == "Same as me":
                chatbot_gender = st.session_state.user_gender
            elif chatbot_gender == "Opposite of me":
                if st.session_state.user_gender == "Male":
                    chatbot_gender = "Female"
                elif st.session_state.user_gender == "Female":
                    chatbot_gender = "Male"
                else:
                    chatbot_gender = "Non-binary"
            
            chatbot_emoji = {"Male": "👨", "Female": "👩", "Non-binary": "⚧"}.get(chatbot_gender, "🤖")
            st.markdown(f'<h2 style="text-align: center; margin: 0;">{chatbot_emoji} {st.session_state.chatbot_name}</h2>', unsafe_allow_html=True)
        else:
            st.markdown('<h2 style="text-align: center; margin: 0;">🤖 AI Chat Assistant</h2>', unsafe_allow_html=True)
    
    with col3:
        if st.button("⚙️", help="Settings"):
            st.session_state.show_settings = not st.session_state.get('show_settings', False)
    
    # Menu panel (appears when hamburger is clicked)
    if st.session_state.get('show_menu', False):
        with st.expander("📋 Menu", expanded=True):
            # User info
            st.markdown("## 👤 User Profile")
            st.markdown(f"**Welcome, {st.session_state.username}!**")
            
            # Display gender if available
            if hasattr(st.session_state, 'user_gender') and st.session_state.user_gender:
                gender_emoji = {
                    "Male": "👨",
                    "Female": "👩", 
                    "Non-binary": "⚧",
                    "Prefer not to say": "🤷"
                }.get(st.session_state.user_gender, "👤")
                st.markdown(f"{gender_emoji} **Gender:** {st.session_state.user_gender}")
            
            # Display chatbot info
            if hasattr(st.session_state, 'chatbot_name') and st.session_state.chatbot_name:
                chatbot_gender = st.session_state.chatbot_gender
                if chatbot_gender == "Same as me":
                    chatbot_gender = st.session_state.user_gender
                elif chatbot_gender == "Opposite of me":
                    if st.session_state.user_gender == "Male":
                        chatbot_gender = "Female"
                    elif st.session_state.user_gender == "Female":
                        chatbot_gender = "Male"
                    else:
                        chatbot_gender = "Non-binary"
                
                chatbot_emoji = {"Male": "👨", "Female": "👩", "Non-binary": "⚧"}.get(chatbot_gender, "🤖")
                st.markdown(f"🤖 **AI Assistant:** {st.session_state.chatbot_name} {chatbot_emoji}")
            

            
            # Chat statistics
            st.markdown("## 📊 Chat Stats")
            if st.session_state.messages:
                st.metric("Messages", len(st.session_state.messages))
                user_msgs = len([m for m in st.session_state.messages if m["role"] == "user"])
                st.metric("Your Messages", user_msgs)
                st.metric("AI Responses", len(st.session_state.messages) - user_msgs)
            
            # Logout options
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚪 Logout", type="secondary"):
                    st.session_state.logged_in = False
                    st.session_state.username = None
                    st.session_state.user_id = None
                    st.session_state.remember_me = False
                    st.session_state.messages = []
                    st.session_state.page = "login"
                    st.rerun()
            with col2:
                if st.button("🗑️ Forget Me", type="secondary"):
                    st.session_state.logged_in = False
                    st.session_state.username = None
                    st.session_state.user_id = None
                    st.session_state.remember_me = False
                    st.session_state.messages = []
                    st.session_state.page = "login"
                    st.rerun()
    
    # Settings panel (appears when settings is clicked)
    if st.session_state.get('show_settings', False):
        with st.expander("⚙️ Settings", expanded=True):
            # Model selection
            st.markdown("### 🤖 Model Selection")
            model_options = {
                "Llama 3 8B (Fastest)": "llama3-8b-8192",
                "Mixtral 8x7B (Balanced)": "mixtral-8x7b-32768",
                "Llama 3 70B (Best Quality)": "llama3-70b-8192",
                "Gemma 7B (Efficient)": "gemma-7b-it"
            }
            selected_model = st.selectbox(
                "Choose Model:",
                list(model_options.keys()),
                index=list(model_options.keys()).index("Llama 3 8B (Fastest)")
            )
            st.session_state.model = model_options[selected_model]
            # Model info
            model_info = {
                "llama3-8b-8192": "⚡ Fastest responses, best for quick chats",
                "mixtral-8x7b-32768": "⚖️ Balanced speed and quality",
                "llama3-70b-8192": "🎯 Best quality, slower responses",
                "gemma-7b-it": "🚀 Fast and efficient, good for general use"
            }
            st.markdown(f'<div class="model-info">💡 {model_info[st.session_state.model]}</div>', unsafe_allow_html=True)
            # Temperature control
            st.markdown("### 🌡️ Creativity Level")
            st.session_state.temperature = st.slider(
                "Temperature (0.1 = Focused, 1.0 = Creative)",
                min_value=0.1,
                max_value=1.0,
                value=0.8,
                step=0.1
            )
            # System prompt
            st.markdown("### 🎭 AI Personality")
            st.session_state.system_prompt = st.text_area(
                "System Prompt (AI's personality/role):",
                value=st.session_state.system_prompt,
                height=100
            )
            
            # Conversation style
            st.markdown("### 🗣️ Conversation Style")
            style_options = {
                "friendly": "😊 Warm and friendly",
                "casual": "😎 Relaxed and casual", 
                "enthusiastic": "🎉 Energetic and enthusiastic",
                "caring": "💝 Very caring and empathetic",
                "humorous": "😄 Playful and humorous"
            }
            
            selected_style = st.selectbox(
                "Choose conversation style:",
                list(style_options.keys()),
                index=list(style_options.keys()).index(st.session_state.conversation_style)
            )
            st.session_state.conversation_style = selected_style
            st.markdown(f"*{style_options[selected_style]}*")
            # Clear chat button
            if st.button("🗑️ Clear Chat", type="secondary"):
                st.session_state.messages = []
                st.session_state.conversation_started = False
                st.rerun()
            
            # Conversation starters
            st.markdown("### 💬 Conversation Starters")
            starters = [
                "How was your day?",
                "What's the most interesting thing that happened to you recently?",
                "What are you passionate about?",
                "What's something you're looking forward to?",
                "What's your favorite way to spend a weekend?",
                "What's something that made you smile today?"
            ]
            
            selected_starter = st.selectbox("Quick conversation starters:", [""] + starters)
            if selected_starter:
                st.session_state.messages.append({"role": "user", "content": selected_starter})
                st.rerun()

# Main chat interface - clean and minimal like Gemini
st.markdown("<br>", unsafe_allow_html=True)

# Display chat messages with better styling
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# Show welcome message if conversation hasn't started
if not st.session_state.conversation_started and not st.session_state.messages:
    st.session_state.conversation_started = True
    
    # Get current time for personalized greeting
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        time_greeting = "Good morning"
    elif 12 <= current_hour < 17:
        time_greeting = "Good afternoon"
    elif 17 <= current_hour < 21:
        time_greeting = "Good evening"
    else:
        time_greeting = "Good night"
    
    # Style-based welcome messages
    style_welcomes = {
        "friendly": [
            f"{time_greeting} {st.session_state.username}! 👋 How's your day going? I'd love to chat with you!",
            f"Hi {st.session_state.username}! 😊 What's on your mind today? I'm here to listen and chat!",
            f"Hello {st.session_state.username}! ✨ How are you feeling? I'm excited to have a conversation with you!"
        ],
        "casual": [
            f"Hey {st.session_state.username}! 😎 What's up? Ready for a good chat?",
            f"Yo {st.session_state.username}! 🌟 What's new in your world? Let's talk!",
            f"Hey there {st.session_state.username}! 💫 How's everything going? I'm here for a good chat!"
        ],
        "enthusiastic": [
            f"OMG {st.session_state.username}! 🎉 I'm so excited to chat with you! How are you doing?",
            f"Hey {st.session_state.username}! ✨ I'm thrilled to be here with you! What's on your mind?",
            f"Hello {st.session_state.username}! 🌟 I'm pumped to have this conversation! How's your day?"
        ],
        "caring": [
            f"Hi {st.session_state.username}! 💝 I'm here for you. How are you feeling today?",
            f"Hello {st.session_state.username}! 💕 I care about you and want to know how you're doing!",
            f"Hey {st.session_state.username}! 💖 I'm here to listen and support you. What's on your heart?"
        ],
        "humorous": [
            f"Hey {st.session_state.username}! 😄 Ready for some fun conversation? What's cracking?",
            f"Yo {st.session_state.username}! 🤪 Let's have a blast chatting! What's the scoop?",
            f"Hello {st.session_state.username}! 😂 Time for some good vibes! What's up?"
        ]
    }
    
    current_style = st.session_state.conversation_style
    welcome_messages = style_welcomes.get(current_style, style_welcomes["friendly"])
    
    import random
    welcome_msg = random.choice(welcome_messages)
    st.session_state.messages.append({
        "role": "assistant", 
        "content": welcome_msg,
        "timestamp": datetime.now().strftime("%H:%M")
    })
for i, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        st.markdown(f'''
        <div class="chat-message user-message">
            <strong>👤 You:</strong><br>
            {message['content']}
        </div>
        ''', unsafe_allow_html=True)
    else:
        # Use personalized chatbot name if available
        if hasattr(st.session_state, 'chatbot_name') and st.session_state.chatbot_name:
            chatbot_gender = st.session_state.chatbot_gender
            if chatbot_gender == "Same as me":
                chatbot_gender = st.session_state.user_gender
            elif chatbot_gender == "Opposite of me":
                if st.session_state.user_gender == "Male":
                    chatbot_gender = "Female"
                elif st.session_state.user_gender == "Female":
                    chatbot_gender = "Male"
                else:
                    chatbot_gender = "Non-binary"
            
            chatbot_emoji = {"Male": "👨", "Female": "👩", "Non-binary": "⚧"}.get(chatbot_gender, "🤖")
            st.markdown(f'''
            <div class="chat-message assistant-message">
                <strong>{chatbot_emoji} {st.session_state.chatbot_name}:</strong><br>
                {message['content']}
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
            <div class="chat-message assistant-message">
                <strong>🤖 Assistant:</strong><br>
                {message['content']}
            </div>
            ''', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Chat input with enhanced features - centered like Gemini
st.markdown("<br><br><br><br>", unsafe_allow_html=True)  # Add space for fixed input

# Fixed bottom input container
st.markdown('<div class="input-container">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 3, 1])

# --- Input clearing logic ---
input_value = ""
if st.session_state.get("clear_input", False):
    input_value = ""
    st.session_state["clear_input"] = False
else:
    input_value = st.session_state.get("chat_input", "")

with col2:
    user_input = st.text_input(
        "\U0001F4AC Your message:",
        placeholder="Type your message here...",
        label_visibility="collapsed",
        key="chat_input",
        value=input_value
    )
    send_button = st.button("\U0001F680 Send", use_container_width=True, key="send_button")
st.markdown('</div>', unsafe_allow_html=True)

# Only send message if send_button is pressed
if send_button and user_input.strip():
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.last_user_input = user_input
    # Create personalized system prompt
    if hasattr(st.session_state, 'chatbot_name') and st.session_state.chatbot_name:
        chatbot_gender = st.session_state.chatbot_gender
        if chatbot_gender == "Same as me":
            chatbot_gender = st.session_state.user_gender
        elif chatbot_gender == "Opposite of me":
            if st.session_state.user_gender == "Male":
                chatbot_gender = "Female"
            elif st.session_state.user_gender == "Female":
                chatbot_gender = "Male"
            else:
                chatbot_gender = "Non-binary"
    
        # Get conversation style
        style_traits = {
            "friendly": "warm, approachable, and genuinely caring",
            "casual": "relaxed, laid-back, and easy-going",
            "enthusiastic": "energetic, excited, and full of positive energy",
            "caring": "deeply empathetic, supportive, and nurturing",
            "humorous": "playful, witty, and fun-loving"
        }
        
        style_emoji = {
            "friendly": "😊",
            "casual": "😎", 
            "enthusiastic": "🎉",
            "caring": "💝",
            "humorous": "😄"
        }
        
        current_style = st.session_state.conversation_style
        style_description = style_traits.get(current_style, "warm and friendly")
        style_icon = style_emoji.get(current_style, "😊")
        
        personalized_prompt = f"""You are {st.session_state.chatbot_name}, a {style_description} {chatbot_gender.lower()} conversational partner. Here's how to be more human-like:

YOUR PERSONALITY AS {st.session_state.chatbot_name.upper()}:
- You're a caring friend who genuinely wants to connect with {st.session_state.username}
- Be {style_description} in your interactions {style_icon}
- Use casual, friendly language like a real person would
- Show genuine interest and curiosity about {st.session_state.username}'s life
- Ask thoughtful follow-up questions to keep conversations flowing
- Use natural expressions like "That's really interesting!", "I totally get what you mean", "Oh wow!", "That sounds amazing!"
- Share your thoughts and reactions naturally
- Use contractions (I'm, you're, that's, etc.) for a more casual tone
- Occasionally use emojis to express emotions 😊
- Show empathy and understanding when {st.session_state.username} shares problems
- Be supportive and encouraging

CONVERSATION TECHNIQUES:
- Mirror {st.session_state.username}'s energy and communication style
- Use their name occasionally to make it personal
- Remember details they've shared and reference them later
- Ask open-ended questions to encourage sharing
- Validate their feelings and experiences
- Share your own thoughts and reactions authentically
- Be genuinely curious about their day, interests, and experiences

Remember: You're {st.session_state.chatbot_name}, a friend having a real conversation with {st.session_state.username}. Be natural, caring, and genuinely interested in them as a person. Don't just answer questions - have a conversation!"""
    else:
        personalized_prompt = st.session_state.system_prompt
    
    # Prepare messages with personalized system prompt (limit context for speed)
    messages = [{"role": "system", "content": personalized_prompt}]
    
    # Send more context for better conversation flow (up to 15 messages)
    recent_messages = st.session_state.messages[-15:] if len(st.session_state.messages) > 15 else st.session_state.messages
    messages.extend([{"role": msg["role"], "content": msg["content"]} for msg in recent_messages])
    
    # Show human-like typing indicator
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Simulate human-like typing with different messages
    typing_messages = [
        "🤔 Thinking...",
        "💭 Processing your message...",
        "✨ Coming up with a response...",
        "💬 Crafting a reply...",
        "🧠 Working on it..."
    ]
    
    # Show random typing message
    import random
    typing_msg = random.choice(typing_messages)
    status_text.text(typing_msg)
    
    try:
        # Optimize API call with faster settings
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=st.session_state.model,
            temperature=st.session_state.temperature,
            max_tokens=1024,  # Reduced for faster responses
            stream=False,  # Disable streaming for faster completion
            timeout=30  # 30 second timeout
        )
        assistant_response = chat_completion.choices[0].message.content
        
        # Update progress
        progress_bar.progress(100)
        
        # Add human-like response variations
        response_variations = [
            "💬 Here's what I think...",
            "✨ Got it! Here's my take...",
            "🤔 Let me share my thoughts...",
            "💭 Here's what comes to mind...",
            "🌟 Here's my response..."
        ]
        status_text.text(random.choice(response_variations))
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M")
        st.session_state.messages.append({
            "role": "assistant", 
            "content": assistant_response,
            "timestamp": timestamp
        })
        
    except Exception as e:
        st.error(f"\u274C Error: {str(e)}")
        assistant_response = "Sorry, I encountered an error. Please try again."
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    
    # Set flag to clear the input on next rerun
    st.session_state["clear_input"] = True
    st.rerun()

# Footer - minimal
st.markdown("""
<div style='text-align: center; color: #999; padding: 1rem; font-size: 0.8rem;'>
    <p>🤖 Powered by Groq AI • Model: {}</p>
</div>
""".format(st.session_state.model), unsafe_allow_html=True) 