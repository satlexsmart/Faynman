import streamlit as st
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Satlex Feynman AI", page_icon="🧬", layout="wide")

# ==========================================
# 2. CORE INITIALIZATION
# ==========================================
if not firebase_admin._apps:
    cert = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cert)
    firebase_admin.initialize_app(cred)

db = firestore.client()
FB_API_KEY = st.secrets["FIREBASE_API_KEY"]
ADMIN_EMAIL = "satviksinghalyt@gmail.com"

# --- AUTH HELPERS ---
def auth_req(email, password, mode="signInWithPassword"):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:{mode}?key={FB_API_KEY}"
    r = requests.post(url, data={"email": email, "password": password, "returnSecureToken": True})
    return r.json()

# ==========================================
# 3. GATEKEEPER (LOGIN/SIGNUP)
# ==========================================
if 'user_email' not in st.session_state:
    st.title("🛡️ Satlex Identity Gateway")
    tab_log, tab_sign = st.tabs(["Existing Identity", "Create New Identity"])
    
    with tab_log:
        e_log = st.text_input("Email", key="l_email")
        p_log = st.text_input("Password", type="password", key="l_pass")
        if st.button("Authorize Entry"):
            res = auth_req(e_log, p_log)
            if 'email' in res:
                st.session_state.user_email = res['email']
                st.rerun()
            else:
                st.error("Access Denied: Invalid Credentials")

    with tab_sign:
        e_sig = st.text_input("New Email", key="s_email")
        p_sig = st.text_input("New Password", type="password", key="s_pass")
        if st.button("Establish Identity"):
            res = auth_req(e_sig, p_sig, "signUp")
            if 'email' in res:
                st.session_state.user_email = res['email']
                st.rerun()
            else:
                st.error("Identity Creation Failed")
    st.stop()

# ==========================================
# 4. DATA SYNCHRONIZATION
# ==========================================
user_email = st.session_state.user_email
user_ref = db.collection('students').document(user_email)
user_data = user_ref.get().to_dict() if user_ref.get().exists else None

if not user_data:
    user_data = {'coins': 0, 'history': [], 'purchased': []}
    user_ref.set(user_data)

coins = user_data.get('coins', 0)

# ==========================================
# 5. SIDEBAR: IDENTITY & LEADERBOARD
# ==========================================
# --- PROGRESS ---
if coins < 100: lvl, b = "Aspirant", "📝"
elif coins < 500: lvl, b = "Intern", "🩺"
elif coins < 1000: lvl, b = "Resident", "🏥"
else: lvl, b = "Specialist", "🧠"

st.sidebar.title(f"{b} {lvl}")
st.sidebar.write(f"ID: **{user_email}**")
st.sidebar.metric("Satlex Wallet", f"{coins} SC")

# --- GLOBAL LEADERBOARD ---
st.sidebar.divider()
st.sidebar.subheader("🏆 Global Rankings")
top_users = db.collection('students').order_by('coins', direction=firestore.Query.DESCENDING).limit(5).stream()
for i, user in enumerate(top_users):
    u_info = user.to_dict()
    st.sidebar.caption(f"{i+1}. {user.id[:10]}... — {u_info.get('coins', 0)} SC")

if st.sidebar.button("Logout"):
    del st.session_state.user_email
    st.rerun()

# ==========================================
# 6. DEVELOPER MODE (ADMIN PANEL)
# ==========================================
if user_email == ADMIN_EMAIL:
    st.divider()
    with st.expander("🛠️ Satlex Developer Mode"):
        st.subheader("Deploy New Learning Material")
        m_name = st.text_input("Material Name")
        m_price = st.number_input("Set Price (SC)", min_value=0, step=10)
        m_link = st.text_input("Google Drive Embed Link")
        m_type = st.selectbox("Content Type", ["PDF", "Video", "Audio", "Image"])
        
        if st.button("Publish to Marketplace"):
            if m_name and m_link:
                db.collection('marketplace').add({
                    'name': m_name, 'price': m_price, 'link': m_link, 'type': m_type
                })
                st.success(f"Deployed: {m_name}")
            else:
                st.error("Missing Metadata")

# ==========================================
# 7. MAIN HUB: STUDIO & MARKET
# ==========================================
hub_studio, hub_market, hub_history = st.tabs(["🎨 Feynman Studio", "🛒 Marketplace", "📜 Mastery History"])

# --- TAB: STUDIO (AI ENGINE) ---
with hub_studio:
    st.header("Feynman AI Mastery Studio")
    topic = st.text_input("Mastery Target", placeholder="e.g., Quantum Entanglement")
    
    if topic:
        in_v, in_t = st.tabs(["🎤 Voice", "✍️ Text"])
        explanation = ""
        
        with in_v:
            audio_data = st.audio_input("Explain your logic:")
            if audio_data:
                client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                explanation = client.audio.transcriptions.create(
                    file=("file.wav", audio_data.read()), model="whisper-large-v3", response_format="text"
                )
        with in_t:
            explanation_t = st.text_area("Write your logic:")
            if explanation_t: explanation = explanation_t

        if st.button("Finalize Submission"):
            if explanation:
                with st.spinner("AI Evaluating Logic..."):
                    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                    prompt = f"As Richard Feynman, grade the explanation of '{topic}'. Avoid jargon. End with 'Score: X/10'."
                    chat = client.chat.completions.create(
                        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": explanation}],
                        model="llama3-8b-8192"
                    )
                    feedback = chat.choices[0].message.content
                    st.info(feedback)
                    
                    # Reward Logic
                    reward = 50 if "Score: 10/10" in feedback else 20 if "Score: 9/10" in feedback else 10 if "Score: 8/10" in feedback else 0
                    if reward > 0:
                        user_ref.update({
                            'coins': firestore.Increment(reward),
                            'history': firestore.ArrayUnion([{"topic": topic, "score": feedback[-5:]}])
                        })
                        st.success(f"+{reward} SC Awarded!")
                        st.rerun()
            else:
                st.warning("Input required.")

# --- TAB: MARKETPLACE ---
with hub_market:
    st.header("Satlex Resources")
    items = db.collection('marketplace').stream()
    item_list = [{"id": i.id, **i.to_dict()} for i in items]
    
    if not item_list:
        st.info("Marketplace currently empty.")
    else:
        cols = st.columns(2)
        for idx, item in enumerate(item_list):
            with cols[idx % 2]:
                st.markdown(f"### {item['name']}")
                st.caption(f"Type: {item['type']} | Price: {item['price']} SC")
                
                if item['id'] in user_data.get('purchased', []):
                    st.success("Unlocked ✅")
                    # Drive Embed for "No Download" experience
                    # Requires Drive link to be /preview or /view with restricted permissions
                    st.components.v1.iframe(item['link'], height=500)
                else:
                    if st.button(f"Purchase for {item['price']} SC", key=item['id']):
                        if coins >= item['price']:
                            user_ref.update({
                                'coins': firestore.Increment(-item['price']),
                                'purchased': firestore.ArrayUnion([item['id']])
                            })
                            st.success("Transaction Successful!")
                            st.rerun()
                        else:
                            st.error("Insufficient Satlex Coins")

# --- TAB: HISTORY ---
with hub_history:
    st.header("Your Mastery Journey")
    for entry in user_data.get('history', []):
        st.write(f"🔹 **{entry['topic']}** — Result: {entry['score']}")
