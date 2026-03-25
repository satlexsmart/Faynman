import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_google_auth import Authenticate
from groq import Groq

# ==========================================
# 1. PAGE SETUP & CONFIG
# ==========================================
st.set_page_config(page_title="Satlex Feynman AI", page_icon="🧠", layout="wide")

# ==========================================
# 2. GOOGLE AUTHENTICATION SETUP
# ==========================================
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

# ==========================================
# 3. FIREBASE DATABASE SETUP
# ==========================================
if not firebase_admin._apps:
    cert = dict(st.secrets["firebase"])
    cred = credentials.Certificate(cert)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================================
# 4. TRIGGER THE LOGIN UI
# ==========================================
authenticator.check_authentification()
authenticator.login()

# ==========================================
# 5. THE MAIN APPLICATION (SECURE ZONE)
# ==========================================
if st.session_state.get('connected'):
    
    # --- USER DATA FETCH ---
    user_info = st.session_state['user_info']
    user_email = user_info.get('email')
    user_name = user_info.get('name', 'Student')

    user_ref = db.collection('students').document(user_email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        user_ref.set({'name': user_name, 'coins': 0})
        coins = 0
    else:
        coins = user_doc.to_dict().get('coins', 0)

    # --- LEVEL LOGIC ---
    if coins < 100:
        level = "Aspirant 📝"
        next_lvl = 100 - coins
    elif coins < 500:
        level = "Intern 🩺"
        next_lvl = 500 - coins
    elif coins < 1000:
        level = "Resident 🏥"
        next_lvl = 1000 - coins
    elif coins < 5000:
        level = "Specialist 🧠"
        next_lvl = 5000 - coins
    else:
        level = "Surgeon Pro 🔪"
        next_lvl = 0

    # --- SIDEBAR UI ---
    st.sidebar.title("🧠 Satlex Identity")
    st.sidebar.subheader(f"Level: {level}")
    st.sidebar.write(f"Welcome, **{user_name}**")
    st.sidebar.metric("Satlex Wallet", f"{coins} SC")
    
    if next_lvl > 0:
        st.sidebar.progress(min(coins / (coins + next_lvl), 1.0))
        st.sidebar.caption(f"{next_lvl} SC until next level")

    if st.sidebar.button('Log out'):
        authenticator.logout()

    # --- ADMIN MARKETPLACE DASHBOARD ---
    ADMIN_EMAIL = "satviksinghalyt@gmail.com" 
    
    if user_email == ADMIN_EMAIL:
        st.sidebar.divider()
        st.sidebar.subheader("👑 Admin Panel")
        with st.sidebar.expander("Upload to Marketplace"):
            new_note_title = st.text_input("Note Title (e.g., Thermodynamics)")
            note_price = st.number_input("Price (SC)", min_value=0, step=10)
            note_link = st.text_input("Google Drive Link to PDF")
            
            if st.button("Publish Notes"):
                if new_note_title and note_link:
                    db.collection('marketplace').add({
                        'title': new_note_title,
                        'price': note_price,
                        'link': note_link,
                        'author': 'Satvik (Admin)'
                    })
                    st.sidebar.success("Published to Marketplace!")
                else:
                    st.sidebar.error("Fill all fields.")

    # --- THE CORE FEYNMAN AI STUDIO ---
    st.title("Feynman AI Studio ⚛️")
    st.write("Explain a concept simply. Earn Satlex Coins to unlock premium notes!")

    # --- THE TOPIC TYPER ---
    st.subheader("Step 1: What are we mastering today?")
    selected_topic = st.text_input("Enter Topic (e.g., Gauss's Law, SN2 Reaction):", 
                                  placeholder="Type your target topic here...")

    if selected_topic:
        st.write(f"### Target: **{selected_topic}**")
        
        # --- THE INPUT TABS (Voice or Text) ---
        tab1, tab2 = st.tabs(["🎤 Record Explanation", "✍️ Write Explanation"])
        
        concept_explanation = ""

        with tab1:
            audio_file = st.audio_input("Record your explanation:")
            if audio_file:
                with st.spinner("Transcribing your voice..."):
                    try:
                        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                        transcription = client.audio.transcriptions.create(
                            file=("recorded_audio.wav", audio_file.read()),
                            model="whisper-large-v3",
                            response_format="text",
                        )
                        concept_explanation = transcription
                        st.success("Transcription Complete!")
                        st.info(f"Your Words: {concept_explanation}")
                    except Exception as e:
                        st.error(f"Transcription Error: {e}")

        with tab2:
            text_input = st.text_area("Type your explanation here:", height=150)
            if text_input:
                concept_explanation = text_input

        # --- THE FEYNMAN EVALUATOR ---
        if st.button("Submit to Feynman"):
            if concept_explanation:
                with st.spinner("Feynman is analyzing your logic..."):
                    try:
                        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
                        
                        system_prompt = f"""You are Richard Feynman. Evaluate the user's explanation of the topic: '{selected_topic}'. 
                        Be brutally honest but encouraging. Point out any jargon that hides a lack of understanding.
                        You MUST end your response with a final score on its own line in this exact format: 'Score: X/10'"""
                        
                        chat_completion = client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": concept_explanation}
                            ],
                            model="llama3-8b-8192", 
                        )
                        
                        feedback = chat_completion.choices[0].message.content
                        st.markdown("### Feedback")
                        st.write(feedback)
                        
                        # --- SCALED ECONOMY LOGIC ---
                        reward = 0
                        if "Score: 10/10" in feedback:
                            reward = 50
                            st.success("💎 MASTERPIECE! You earned 50 SC!")
                        elif "Score: 9/10" in feedback:
                            reward = 20
                            st.success("🌟 EXCELLENT! You earned 20 SC!")
                        elif "Score: 8/10" in feedback:
                            reward = 10
                            st.success("✅ GOOD JOB! You earned 10 SC!")
                        else:
                            st.warning("Needs more clarity. No coins this time. Try again!")

                        if reward > 0:
                            user_ref.update({'coins': firestore.Increment(reward)})
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Groq API Error: {e}")
            else:
                st.error("Please provide an explanation first!")

# ==========================================
# 6. THE LOGGED-OUT STATE
# ==========================================
else:
    st.info("Please log in securely with your Google account to access the Feynman AI Studio.")
