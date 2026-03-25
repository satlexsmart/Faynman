import streamlit as st
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(page_title="Satlex Feynman AI", page_icon="🧠", layout="wide")

# ==========================================
# 2. FIREBASE & AUTH FUNCTIONS
# ==========================================
# Initialize Firebase Admin for Database
if not firebase_admin._apps:
    cert = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cert)
    firebase_admin.initialize_app(cred)

db = firestore.client()
API_KEY = st.secrets["FIREBASE_API_KEY"]

def login_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    r = requests.post(url, data=payload)
    return r.json()

def signup_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    r = requests.post(url, data=payload)
    return r.json()

# ==========================================
# 3. THE LOGIN SCREEN
# ==========================================
if 'user' not in st.session_state:
    st.title("🛡️ Satlex Feynman AI: Secure Entry")
    
    auth_mode = st.radio("Choose Mode:", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Enter Studio"):
        if auth_mode == "Login":
            res = login_user(email, password)
            if 'email' in res:
                st.session_state.user = res
                st.rerun()
            else:
                st.error("Invalid Login. Try again!")
        else:
            res = signup_user(email, password)
            if 'email' in res:
                st.session_state.user = res
                st.success("Account Created! Redirecting...")
                st.rerun()
            else:
                st.error("Sign-up failed. Check email format!")
    st.stop() # Stop the app here if not logged in

# ==========================================
# 4. MAIN APP (ONLY SHOWS IF LOGGED IN)
# ==========================================
user_email = st.session_state.user['email']

# --- DATABASE FETCH ---
user_ref = db.collection('students').document(user_email)
user_doc = user_ref.get()

if not user_doc.exists:
    user_ref.set({'coins': 0})
    coins = 0
else:
    coins = user_doc.to_dict().get('coins', 0)

# --- LEVEL LOGIC ---
if coins < 100: level = "Aspirant 📝"
elif coins < 500: level = "Intern 🩺"
elif coins < 1000: level = "Resident 🏥"
else: level = "Specialist 🧠"

# --- SIDEBAR ---
st.sidebar.title("🧠 Satlex Identity")
st.sidebar.subheader(f"Level: {level}")
st.sidebar.write(f"Logged in: **{user_email}**")
st.sidebar.metric("Satlex Wallet", f"{coins} SC")

if st.sidebar.button("Logout"):
    del st.session_state.user
    st.rerun()

# --- ADMIN PANEL ---
if user_email == "satviksinghalyt@gmail.com":
    st.sidebar.divider()
    st.sidebar.subheader("👑 Admin Panel")
    with st.sidebar.expander("Upload to Marketplace"):
        title = st.text_input("Note Title")
        price = st.number_input("Price (SC)", min_value=0)
        link = st.text_input("Link")
        if st.button("Publish"):
            db.collection('marketplace').add({'title': title, 'price': price, 'link': link})
            st.sidebar.success("Note Published!")

# --- FEYNMAN STUDIO ---
st.title("Feynman AI Studio ⚛️")
topic = st.text_input("What are we mastering today?")

if topic:
    st.write(f"### Target: **{topic}**")
    tab1, tab2 = st.tabs(["🎤 Voice", "✍️ Text"])
    explanation = ""

    with tab1:
        audio = st.audio_input("Record your explanation:")
        if audio:
            with st.spinner("Whisper is listening..."):
                client = Groq(api_key=st.secrets["groq"]["api_key"])
                explanation = client.audio.transcriptions.create(
                    file=("recorded.wav", audio.read()), 
                    model="whisper-large-v3", 
                    response_format="text"
                )
                st.info(f"Transcribed: {explanation}")

    with tab2:
        text_in = st.text_area("Type your explanation:")
        if text_in: explanation = text_in

    if st.button("Submit to Feynman"):
        if explanation:
            with st.spinner("Feynman is analyzing..."):
                client = Groq(api_key=st.secrets["groq"]["api_key"])
                prompt = f"As Richard Feynman, grade the user's explanation of '{topic}'. Point out jargon. End with 'Score: X/10'."
                res = client.chat.completions.create(
                    messages=[{"role": "system", "content": prompt}, {"role": "user", "content": explanation}],
                    model="llama3-8b-8192"
                )
                feedback = res.choices[0].message.content
                st.markdown(feedback)
                
                # Award Coins
                if any(f"Score: {s}/10" in feedback for s in ["8", "9", "10"]):
                    user_ref.update({'coins': firestore.Increment(10)})
                    st.success("🎉 +10 SC Awarded!")
                    st.rerun()
        else:
            st.error("Provide an explanation first!")
