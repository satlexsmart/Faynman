import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import json
import datetime

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Satlex Feynman AI", page_icon="🧠", layout="wide")

# --- 2. FIREBASE & SECRETS SETUP ---
FIREBASE_API_KEY = st.secrets["FIREBASE_API_KEY"]
ADMIN_EMAIL = "satviksinghalyt@gmail.com" # 👑 MASTER ADMIN SET

# Initialize Firebase Admin (Database)
if not firebase_admin._apps:
    cred_dict = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 3. AUTHENTICATION FUNCTIONS (Email/Password) ---
def sign_up_with_email(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=payload)
    return response.json()

def sign_in_with_email(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=payload)
    return response.json()

# --- 4. SESSION STATE MANAGEMENT ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# --- 5. THE LOGIN SCREEN (GATEKEEPER) ---
if not st.session_state.logged_in:
    st.title("Welcome to Satlex Feynman AI 🧠")
    st.write("Master your concepts. Earn Satlex Coins. Buy premium notes.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Log In", "Sign Up"])
        
        with tab1:
            st.subheader("Student Login")
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            if st.button("Log In", use_container_width=True):
                result = sign_in_with_email(login_email, login_password)
                if "idToken" in result:
                    st.session_state.logged_in = True
                    st.session_state.user_email = result["email"]
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error(result.get("error", {}).get("message", "Login failed."))
                    
        with tab2:
            st.subheader("Create Account")
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input("Password (min 6 chars)", type="password", key="signup_password")
            if st.button("Sign Up", use_container_width=True):
                result = sign_up_with_email(signup_email, signup_password)
                if "idToken" in result:
                    db.collection("students").document(signup_email).set({"coins": 0, "joined": str(datetime.date.today())})
                    st.success("Account created! You can now log in.")
                else:
                    st.error(result.get("error", {}).get("message", "Signup failed."))
    
    st.stop()

# =====================================================================
# --- EVERYTHING BELOW THIS LINE ONLY SHOWS IF LOGGED IN ---
# =====================================================================

user_ref = db.collection("students").document(st.session_state.user_email)
user_doc = user_ref.get()

if not user_doc.exists:
    user_ref.set({"coins": 0})
    user_coins = 0
else:
    user_coins = user_doc.to_dict().get("coins", 0)

with st.sidebar:
    st.title("Satlex Identity")
    st.write(f"👤 **{st.session_state.user_email.split('@')[0]}**")
    st.metric(label="Satlex Wallet", value=f"{user_coins} SC")
    st.divider()
    app_mode = st.radio("Navigation", ["Feynman Studio", "Marketplace"])
    
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()

if st.session_state.user_email == ADMIN_EMAIL:
    with st.sidebar:
        st.divider()
        st.warning("👑 Admin Panel")
        if st.checkbox("Open Creator Dashboard"):
            app_mode = "Admin"

if app_mode == "Feynman Studio":
    st.header("The Feynman AI Studio 🎙️")
    st.info("Explain a concept like you are teaching it to a 5-year-old. The AI will grade you, and scores of 8+ earn Satlex Coins!")
    st.write("*(AI teaching interface loads here...)*")

elif app_mode == "Marketplace":
    st.header("Satlex Marketplace 🛒")
    st.write("Spend your hard-earned coins on premium notes.")
    
    notes = db.collection("marketplace").stream()
    col1, col2, col3 = st.columns(3)
    for idx, note in enumerate(notes):
        data = note.to_dict()
        with [col1, col2, col3][idx % 3]:
            with st.container(border=True):
                st.subheader(data.get("title", "Untitled"))
                st.write(f"💰 Price: {data.get('price', 0)} SC")
                if user_coins >= data.get('price', 0):
                    if st.button(f"Buy", key=f"buy_{note.id}"):
                        user_ref.update({"coins": user_coins - data.get('price', 0)})
                        st.success(f"Link unlocked: {data.get('link', '#')}")
                else:
                    st.button("Not enough SC", disabled=True, key=f"fail_{note.id}")

elif app_mode == "Admin":
    st.header("Creator Dashboard 👑")
    st.write("Upload new study materials and set their prices in Satlex Coins.")
    
    with st.form("new_note_form"):
        note_title = st.text_input("Note Title (e.g., Kinematics Master Sheet)")
        note_price = st.number_input("Price (SC)", min_value=1, value=50)
        note_link = st.text_input("Google Drive Link to PDF")
        
        if st.form_submit_button("Publish to Marketplace"):
            db.collection("marketplace").add({
                "title": note_title,
                "price": note_price,
                "link": note_link,
                "date_added": str(datetime.date.today())
            })
            st.success(f"Successfully published '{note_title}' to the Marketplace!")
