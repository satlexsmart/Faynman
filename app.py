import streamlit as st
import base64
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib
from groq import Groq
from datetime import datetime
import re

# --- 1. PAGE CONFIG & AESTHETIC CSS ---
st.set_page_config(page_title="Satlex Feynman Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    /* Modern, clean aesthetic overrides */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; padding-top: 10px; padding-bottom: 10px; font-weight: 600; }
    .stTabs [aria-selected="true"] { border-bottom-color: #FF4B4B !important; color: #FF4B4B !important; }
    div[data-testid="metric-container"] { background-color: #1E1E1E; border: 1px solid #333; padding: 15px; border-radius: 10px; color: white; }
    .success-coin { font-size: 20px; font-weight: bold; color: #FFD700; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SECURE INITIALIZATION ---
# Initialize Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("⚠️ Groq API Key missing in Secrets!")
    st.stop()

# Initialize Firebase
if not firebase_admin._apps:
    try:
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("⚠️ Firebase credentials missing in Secrets!")
        st.stop()

db = firestore.client()

# --- 3. AUTH & SATLEX ECONOMY ---
def get_user_id(name):
    return hashlib.sha256(name.strip().lower().encode()).hexdigest()[:10]

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png", width=50)
    st.title("Satlex Identity")
    user_name = st.text_input("Student Name", value="Satvik", help="Used to securely save your progress.")
    
    user_id = get_user_id(user_name)
    user_ref = db.collection("students").document(user_id)
    user_doc = user_ref.get()

    # Load or Create User
    if not user_doc.exists:
        user_ref.set({"name": user_name, "coins": 0, "history": []})
        coins = 0
        history = []
    else:
        data = user_doc.to_dict()
        coins = data.get("coins", 0)
        history = data.get("history", [])

    st.markdown("---")
    st.metric(label="💰 Satlex Wallet", value=f"{coins} SC", delta="Active")
    st.markdown("[📂 GitHub Source](https://github.com/satlexsmart/faynman)")

# --- 4. MAIN DASHBOARD ---
st.title("🚀 Satlex Feynman AI")
st.markdown("Master complex engineering concepts by teaching them to a multimodal AI.")

# Create aesthetic tabs
tab1, tab2, tab3 = st.tabs(["🎙️ Practice Studio", "📊 My Progression", "🛒 Marketplace"])

# ==========================================
# TAB 1: PRACTICE STUDIO
# ==========================================
with tab1:
    col1, col2 = st.columns([1, 1.2], gap="large")
    
    with col1:
        st.subheader("1. Setup Your Lesson")
        topic_name = st.text_input("Target Topic", "Rotational Mechanics")
        
        age_map = {
            "10 yr (Beginner)": "Explain this like I am 10. Point out confusing jargon.",
            "20 yr (Peer)": "Explain like a classmate. Keep it clear but technical.",
            "JEE Advanced Expert": "I am a strict JEE Advanced examiner. Be mathematically rigorous, look for flaws in my logic, and point out standard traps."
        }
        age_choice = st.selectbox("Listener Persona:", list(age_map.keys()))
        
        mode = st.radio("Input Mode:", ["🎙️ Audio", "📸 Image/Notes"], horizontal=True)
        if mode == "🎙️ Audio":
            uploaded_file = st.file_uploader("Upload Voice Explanation", type=['mp3', 'wav', 'm4a'])
        else:
            uploaded_file = st.file_uploader("Upload Derivation/Notes", type=['jpg', 'png', 'jpeg'])

    with col2:
        st.subheader("2. Evaluation Panel")
        if st.button("Submit to AI Listener", type="primary", use_container_width=True):
            if uploaded_file:
                with st.spinner("Processing through Groq AI..."):
                    try:
                        # Process based on mode
                        if mode == "🎙️ Audio":
                            transcription = client.audio.transcriptions.create(
                                file=(uploaded_file.name, uploaded_file.getvalue()),
                                model="whisper-large-v3-turbo", response_format="text"
                            )
                            # Text AI Call
                            sys_prompt = f"You are a {age_choice} listener. {age_map[age_choice]}\nCRITICAL: At the very end of your feedback, you MUST include a score formatted exactly like this: 'FINAL_SCORE: X/10'."
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[
                                    {"role": "system", "content": sys_prompt},
                                    {"role": "user", "content": f"Topic: {topic_name}. Explanation: {transcription}"}
                                ]
                            )
                            feedback = response.choices[0].message.content
                            
                        else:
                            img_bytes = uploaded_file.getvalue()
                            base64_img = base64.b64encode(img_bytes).decode('utf-8')
                            img_url = f"data:{uploaded_file.type};base64,{base64_img}"
                            
                            # Vision AI Call
                            sys_prompt = f"You are a {age_choice} listener. {age_map[age_choice]}\nAnalyze these notes for the topic: {topic_name}. CRITICAL: At the very end of your feedback, you MUST include a score formatted exactly like this: 'FINAL_SCORE: X/10'."
                            response = client.chat.completions.create(
                                model="meta-llama/llama-4-scout-17b-16e-instruct",
                                messages=[{
                                    "role": "user", 
                                    "content": [
                                        {"type": "text", "text": sys_prompt},
                                        {"type": "image_url", "image_url": {"url": img_url}}
                                    ]
                                }]
                            )
                            feedback = response.choices[0].message.content

                        # --- Extract Score & Award Coins ---
                        score_match = re.search(r"FINAL_SCORE:\s*(\d+)/10", feedback)
                        earned_coins = 0
                        score_val = 0
                        if score_match:
                            score_val = int(score_match.group(1))
                            if score_val == 10:
                                earned_coins = 10
                                st.balloons()
                            elif score_val >= 8:
                                earned_coins = 1
                        
                        # Update Firebase
                        new_coins = coins + earned_coins
                        new_entry = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "topic": topic_name, "score": score_val}
                        history.append(new_entry)
                        user_ref.update({"coins": new_coins, "history": history})
                        
                        # Display Results
                        if earned_coins > 0:
                            st.success(f"🎉 Awesome! You earned +{earned_coins} Satlex Coins!")
                        st.markdown(feedback.replace(f"FINAL_SCORE: {score_val}/10", "")) # Hide the raw tag
                        
                    except Exception as e:
                        st.error(f"API Error: {e}")
            else:
                st.warning("Please upload a file first!")

# ==========================================
# TAB 2: MY PROGRESSION
# ==========================================
with tab2:
    st.subheader(f"Data for {user_name}")
    if history:
        df = pd.DataFrame(history)
        # Display a clean chart of scores
        st.line_chart(df.set_index('date')['score'])
        # Display the raw data table
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No practice sessions recorded yet. Head to the Practice Studio to begin!")

# ==========================================
# TAB 3: MARKETPLACE (Coming Soon)
# ==========================================
with tab3:
    st.subheader("🛒 Satlex Marketplace")
    st.info("Spend your Satlex Coins on verified community notes.")
    
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.container(border=True).markdown("### 📘 Organic Chem\n**Cost:** 50 SC\n*Author: Topper2025*\n\n[Unlock Button Locked]")
    with m_col2:
        st.container(border=True).markdown("### 📕 Calculus Tricks\n**Cost:** 30 SC\n*Author: Satvik*\n\n[Unlock Button Locked]")
    with m_col3:
        st.container(border=True).markdown("### 📗 Ray Optics\n**Cost:** 40 SC\n*Author: PhysicsPro*\n\n[Unlock Button Locked]")
