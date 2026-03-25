import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_google_auth import Authenticate
import datetime
import re

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Satlex Feynman AI", page_icon="🧠", layout="wide")

# --- 2. SECRETS & ADMIN SETUP ---
ADMIN_EMAIL = "satviksinghalyt@gmail.com" # Your Master Key

# Initialize Firebase Admin (Database)
if not firebase_admin._apps:
    cred_dict = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 3. GOOGLE AUTHENTICATION ---
# This uses the Client ID and Secret you saved in Streamlit
authenticator = Authenticate(
    secret_credentials_path=None, # We use secrets directly below
    cookie_name='satlex_cookie',
    cookie_key='satlex_secure_key',
    redirect_uri='https://faynman.streamlit.app/',
)

# Manually inject the secrets for the authenticator
authenticator.client_id = st.secrets["GOOGLE_CLIENT_ID"]
authenticator.client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]

authenticator.check_authentification()

# --- 4. THE LOGIN GATE ---
if not st.session_state.get('connected'):
    st.title("Welcome to Satlex Feynman AI 🧠")
    st.markdown("### Master your JEE concepts. Earn Satlex Coins. Unlock premium notes.")
    st.write("To keep your wallet secure, please log in with your official Google account.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # This creates the "Sign in with Google" button
        authenticator.login()
        
    st.stop() # Stops the rest of the app from loading until logged in

# =====================================================================
# --- LOGGED IN AREA (Secure) ---
# =====================================================================

# Get the verified Google email
user_email = st.session_state['user_info'].get('email')
user_name = st.session_state['user_info'].get('name', 'Student')

# --- 5. USER WALLET SETUP ---
user_ref = db.collection("students").document(user_email)
user_doc = user_ref.get()

if not user_doc.exists:
    user_ref.set({"coins": 0, "name": user_name, "joined": str(datetime.date.today())})
    user_coins = 0
else:
    user_coins = user_doc.to_dict().get("coins", 0)

# --- 6. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("Satlex Identity")
    st.write(f"👤 **{user_name}**")
    st.metric(label="Satlex Wallet", value=f"{user_coins} SC")
    st.divider()
    
    app_mode = st.radio("Navigation", ["Feynman Studio", "Marketplace"])
    
    # 👑 ADMIN UNLOCK (Only visible to satviksinghalyt@gmail.com)
    if user_email == ADMIN_EMAIL:
        st.divider()
        st.warning("👑 Admin Panel")
        if st.checkbox("Open Creator Dashboard"):
            app_mode = "Admin"
            
    st.divider()
    authenticator.logout()

# --- 7. APP SCREENS ---

if app_mode == "Feynman Studio":
    st.header("The Feynman AI Studio 🎙️")
    st.info("Explain a concept clearly. The AI will grade you, and scores of 8+ earn 10 Satlex Coins!")
    
    # ==========================================
    # ⬇️ PASTE YOUR GROQ AI CODE BELOW HERE ⬇️
    # ==========================================
    
    st.write("*(AI audio recorder and Groq logic goes here)*")
    
    # Example of how you add coins once your AI gives a score:
    # if ai_score >= 8:
    #     user_ref.update({"coins": user_coins + 10})
    #     st.balloons()
    #     st.success("10 Coins Added!")

    # ==========================================
    # ⬆️ PASTE YOUR GROQ AI CODE ABOVE HERE ⬆️
    # ==========================================


elif app_mode == "Marketplace":
    st.header("Satlex Marketplace 🛒")
    st.write("Spend your hard-earned coins on premium resources.")
    
    notes = db.collection("marketplace").stream()
    for note in notes:
        data = note.to_dict()
        with st.container(border=True):
            st.subheader(data.get("title", "Untitled Resource"))
            st.write(f"💰 Price: **{data.get('price', 0)} SC**")
            
            # Check if user already bought it
            purchase_id = f"{user_email}_{note.id}"
            purchase_ref = db.collection("purchases").document(purchase_id)
            
            if purchase_ref.get().exists:
                st.success("✅ Purchased - Secure Viewer Unlocked")
                # Secure iframe viewer (Hides download button)
                embed_url = f"https://drive.google.com/file/d/{data['drive_id']}/preview?rm=minimal"
                st.components.v1.iframe(embed_url, height=600, scrolling=True)
            else:
                if st.button(f"Buy Resource", key=f"buy_{note.id}"):
                    if user_coins >= data.get('price', 0):
                        # Deduct coins and grant access
                        user_ref.update({"coins": user_coins - data.get('price', 0)})
                        purchase_ref.set({"unlocked_on": str(datetime.datetime.now())})
                        st.rerun()
                    else:
                        st.error("Not enough Satlex Coins. Go practice in the Feynman Studio!")

elif app_mode == "Admin":
    st.header("Creator Dashboard 👑")
    st.write("Upload your JEE videos or PDFs to Google Drive, set sharing to 'Anyone with link', and paste the link below.")
    
    with st.form("admin_upload", clear_on_submit=True):
        note_title = st.text_input("Resource Title (e.g., Kinematics One-Shot)")
        note_price = st.number_input("Price (Satlex Coins)", min_value=1, value=50)
        raw_drive_link = st.text_input("Google Drive 'Share' Link")
        
        if st.form_submit_button("🚀 Publish to Marketplace"):
            if "drive.google.com" in raw_drive_link:
                try:
                    # Automatically extract the secret file ID from the messy Drive link
                    file_id = re.search(r'/d/([a-zA-Z0-9_-]+)', raw_drive_link).group(1)
                    db.collection("marketplace").add({
                        "title": note_title,
                        "price": note_price,
                        "drive_id": file_id,
                        "date_added": str(datetime.date.today())
                    })
                    st.success(f"'{note_title}' is now live!")
                except Exception as e:
                    st.error("Could not read the link. Make sure it's a standard Drive share link.")
            else:
                st.error("Please paste a valid Google Drive link.")
