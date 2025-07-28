import streamlit as st
import sqlite3
import hashlib
import re
from datetime import datetime

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

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

def create_user(username, email, password):
    """Create new user in database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    password_hash = hash_password(password)
    c.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)', 
              (username, email, password_hash))
    conn.commit()
    conn.close()

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
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="signup-container">', unsafe_allow_html=True)
    st.markdown('<div class="signup-header"><h2>📝 Sign Up</h2><p>Create your AI Chat Assistant account</p></div>', unsafe_allow_html=True)
    
    with st.form("signup_form"):
        username = st.text_input("👤 Username", placeholder="Choose a username")
        email = st.text_input("📧 Email", placeholder="Enter your email")
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
            st.error("❌ Please fill in all fields")
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
                    create_user(username, email, password)
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

if __name__ == "__main__":
    signup_page() 