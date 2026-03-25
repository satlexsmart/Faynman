import streamlit as st
import json
import requests
import base64
import random
import string
import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq

# ==========================================
# 1. INITIALIZATION & SECURITY
# ==========================================
st.set_page_config(page_title="Satlex Feynman Studio", page_icon="🧬", layout="wide")

# Firebase setup from Secrets
if not firebase_admin._apps:
    cert = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cert)
    firebase_admin.initialize_app(cred)

db = firestore.client()
ADMIN_EMAIL = "satviksinghalyt@gmail.com"

# ==========================================
# 2. PASS-LESS AUTH LOGIC
# ==========================================
def generate_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

if 'user_email' not in st.session_state:
    st.title("🛡️ Satlex Identity Gateway")
    st.markdown("---")
    tab_log, tab_sign = st.tabs(["🔑 Enter Studio", "📜 Create Identity"])
    
    with tab_log:
        login_e = st.text_input("Registered Email", key="log_e")
        login_k = st.text_input("6-Digit Satlex Key", type="password", key="log_k")
        if st.button("Authorize Access"):
            user_doc = db.collection('students').document(login_e).get()
            if user_doc.exists and user_doc.to_dict().get('access_key') == login_k:
                st.session_state.user_email = login_e
                st.rerun()
            else: st.error("Access Denied: Check credentials or contact Admin.")

    with tab_sign:
        new_e = st.text_input("Best Email", key="sig_e")
        if st.button("Generate Identity"):
            if db.collection('students').document(new_e).get().exists:
                st.warning("Identity already exists. Log in instead.")
            else:
                new_k = generate_key()
                db.collection('students').document(new_e).set({
                    'coins': 0, 'access_key': new_k, 'history': [], 'purchased': []
                })
                st.success(f"Identity Born! YOUR KEY: **{new_k}**")
                st.warning("Save this key. It is your only way to return.")
    st.stop()

# ==========================================
# 3. GLOBAL DATA SYNC
# ==========================================
user_email = st.session_state.user_email
user_ref = db.collection('students').document(user_email)
user_data = user_ref.get().to_dict()
coins = user_data.get('coins', 0)

# ==========================================
# 4. SIDEBAR: IDENTITY & RANKINGS
# ==========================================
if coins < 100: lvl, b = "Aspirant", "📝"
elif coins < 500: lvl, b = "Intern", "🩺"
elif coins < 1000: lvl, b = "Resident", "🏥"
elif coins < 5000: lvl, b = "Specialist", "🧠"
else: lvl, b = "Surgeon Pro", "🔪"

st.sidebar.title(f"{b} {lvl}")
st.sidebar.write(f"**ID:** {user_email}")
st.sidebar.metric("Satlex Wallet", f"{coins} SC")

st.sidebar.divider()
st.sidebar.subheader("🏆 Global Leaderboard")
rankings = db.collection('students').order_by('coins', direction=firestore.Query.DESCENDING).limit(5).stream()
for i, u in enumerate(rankings):
    u_data = u.to_dict()
    st.sidebar.caption(f"{i+1}. {u.id[:10]}... — {u_data.get('coins',0)} SC")

if st.sidebar.button("Exit Studio"):
    del st.session_state.user_email
    st.rerun()

# ==========================================
# 5. DEVELOPER MODE (ADMIN)
# ==========================================
if user_email == ADMIN_EMAIL:
    with st.expander("🛠️ Satlex Developer Mode"):
        st.subheader("Deploy Learning Material")
        m_name = st.text_input("Name")
        m_price = st.number_input("Price (SC)", min_value=10, step=10)
        m_link = st.text_input("Drive Link (ending in /preview)")
        if st.button("Push to Marketplace"):
            db.collection('marketplace').add({'name': m_name, 'price': m_price, 'link': m_link})
            st.success(f"Live: {m_name}")

# ==========================================
# 6. MAIN HUB (STUDIO / MARKET / HISTORY)
# ==========================================
tab_studio, tab_market, tab_history = st.tabs(["🎨 Feynman Studio", "🛒 Marketplace", "📜 History"])

with tab_studio:
    st.header("Feynman AI Mastery")
    age_map = {
        "10 yr (Kid)": "Explain like I'm 10. Use analogies.",
        "20 yr (Peer)": "Explain like we're classmates.",
        "Professional (Expert)": "I'm a PhD expert. Be rigorous and technical."
    }
    persona = st.selectbox("Choose your listener:", list(age_map.keys()))
    mode = st.radio("Method:", ["🎙️ Audio File", "📸 Photo of Notes"])
    uploaded = st.file_uploader("Upload Explanation", type=['mp3','wav','m4a','jpg','png','jpeg'])

    if st.button("Evaluate Mastery") and uploaded:
        with st.spinner("Analyzing..."):
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            if mode == "🎙️ Audio File":
                trans = client.audio.transcriptions.create(file=(uploaded.name, uploaded.getvalue()), model="whisper-large-v3-turbo", response_format="text")
                prompt = f"You are a {persona}. {age_map[persona]}\nTranscript: {trans}\nRate 1-10. End with 'Score: X/10'."
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            else:
                b64_img = base64.b64encode(uploaded.getvalue()).decode('utf-8')
                res = client.chat.completions.create(model="llama-3.2-11b-vision-preview",
                    messages=[{"role": "user", "content": [{"type": "text", "text": f"You are a {persona}. {age_map[persona]} Rate 1-10. End with 'Score: X/10'."}, {"type": "image_url", "image_url": {"url": f"data:{uploaded.type};base64,{b64_img}"}}]}]
                )
            
            feedback = res.choices[0].message.content
            st.markdown(feedback)
            
            # Reward Engine
            score = 50 if "Score: 10/10" in feedback else 20 if "Score: 9/10" in feedback else 10 if "Score: 8/10" in feedback else 0
            if score > 0:
                user_ref.update({'coins': firestore.Increment(score), 'history': firestore.ArrayUnion([{"topic": uploaded.name, "result": feedback[-8:]}])})
                st.success(f"+{score} SC Awarded!")
                st.rerun()

with tab_market:
    st.header("🛒 Satlex Marketplace")
    notes = db.collection('marketplace').stream()
    for n in notes:
        item = n.to_dict()
        with st.container(border=True):
            st.subheader(f"{item['name']}")
            st.caption(f"Cost: {item['price']} SC")
            if n.id in user_data.get('purchased', []):
                st.success("Unlocked ✅")
                st.components.v1.iframe(item['link'], height=600)
            elif st.button(f"Unlock Material", key=n.id):
                if coins >= item['price']:
                    user_ref.update({'coins': firestore.Increment(-item['price']), 'purchased': firestore.ArrayUnion([n.id])})
                    st.rerun()
                else: st.error("Insufficient Coins")

with tab_history:
    st.header("Mastery History")
    for h in user_data.get('history', []):
        st.write(f"🔹 **{h['topic']}** — {h['result']}")
