import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_google_auth import Authenticate

# 1. PAGE SETUP
st.set_page_config(page_title="Satlex Feynman AI", layout="wide")

# 2. GOOGLE AUTHENTICATION SETUP
google_creds = {
    "web": {
        "client_id": st.secrets["GOOGLE_CLIENT_ID"],
        "project_id": st.secrets["firebase"]["project_id"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"]
    }
}

with open("google_credentials.json", "w") as f:
    json.dump(google_creds, f)

authenticator = Authenticate(
    secret_credentials_path="google_credentials.json",
    cookie_name="satlex_auth",
    cookie_key="random_secret_key_123",
    redirect_uri="https://faynman.streamlit.app",
)

# 3. FIREBASE DATABASE SETUP
# This if-statement prevents Streamlit from crashing by trying to initialize Firebase twice
if not firebase_admin._apps:
    cert = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cert)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 4. TRIGGER THE LOGIN UI
authenticator.check_authentification()
authenticator.login()

# ==========================================
# 5. THE MAIN APPLICATION (SECURE ZONE)
# ==========================================
if st.session_state.get('connected'):
    
    # Get user details from Google
    user_info = st.session_state['user_info']
    user_email = user_info.get('email')
    user_name = user_info.get('name', 'Student')

    # Fetch or Create User Wallet in Firestore
    user_ref = db.collection('students').document(user_email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        # First time login! Give them 0 coins to start.
        user_ref.set({'name': user_name, 'coins': 0})
        coins = 0
    else:
        # Returning user. Fetch their balance.
        coins = user_doc.to_dict().get('coins', 0)

    # --- SIDEBAR UI ---
    st.sidebar.title("🧠 Satlex Identity")
    st.sidebar.write(f"Welcome, **{user_name}**")
    st.sidebar.metric("Satlex Wallet", f"{coins} SC")
    
    if st.sidebar.button('Log out'):
        authenticator.logout()

    # --- ADMIN MARKETPLACE DASHBOARD ---
    # Put your exact Gmail address here to unlock God Mode
    ADMIN_EMAIL = "satviksinghalyt@gmail.com" 
    
    if user_email == ADMIN_EMAIL:
        st.sidebar.divider()
        st.sidebar.subheader("👑 Admin Panel")
        with st.sidebar.expander("Upload to Marketplace"):
            new_note_title = st.text_input("Note Title (e.g., Thermodynamics)")
            note_price = st.number_input("Price (SC)", min_value=0, step=10)
            note_link = st.text_input("Google Drive Link to PDF")
            
            if st.button("Publish Notes"):
                db.collection('marketplace').add({
                    'title': new_note_title,
                    'price': note_price,
                    'link': note_link,
                    'author': 'Satvik (Admin)'
                })
                st.sidebar.success("Published to Marketplace!")

    # --- MAIN AI STUDIO UI ---
    st.title("Feynman AI Studio")
    st.write("Explain a JEE concept to the AI. Score an 8/10 or higher to earn Satlex Coins!")

    # Place your Groq AI text area or audio uploader here
    concept_explanation = st.text_area("Explain your concept:")
    
    if st.button("Submit to AI"):
        # Placeholder for your Groq AI evaluation logic
        st.info("Sending to Groq AI for evaluation...")
        
        # Example of how you will add coins once Groq gives a good score:
        # user_ref.update({'coins': firestore.Increment(10)})
        # st.success("You earned 10 SC!")
        # st.rerun()

# ==========================================
# 6. THE LOGGED-OUT STATE
# ==========================================
else:
    st.info("Please log in securely with your Google account to access your JEE workspace.")
                
