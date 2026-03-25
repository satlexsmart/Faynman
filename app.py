import streamlit as st
import base64
from groq import Groq

# --- INITIALIZATION ---
# Securely grab the API key from Streamlit Secrets
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("⚠️ API Key missing! Please add GROQ_API_KEY to your Streamlit App Secrets.")
    st.stop()

st.set_page_config(page_title="Feynman Listener", page_icon="🎓")

# --- UI LAYOUT ---
st.title("🎓 Feynman Listener")
st.caption("Master any JEE or Coding concept by teaching it to an AI.")

# Panel 1: Listener Persona
age_map = {
    "10 yr (Kid)": "Explain this like I am 10 years old. Use simple analogies and point out if anything is too complex.",
    "20 yr (Peer)": "Explain this like we are classmates studying together. Keep it clear but use the right terminology.",
    "Professional (Expert)": "I am a PhD expert. Be highly technical, mathematically rigorous, and aggressively point out any logical gaps."
}
age_choice = st.selectbox("1. Choose your listener:", list(age_map.keys()))

# Panel 2: Input Mode
mode = st.radio("2. How do you want to teach?", ["🎙️ Audio File", "📸 Image of Notes"])

# Dynamically change accepted file types based on mode
if mode == "🎙️ Audio File":
    uploaded_file = st.file_uploader("Upload your audio explanation", type=['mp3', 'wav', 'm4a'])
else:
    uploaded_file = st.file_uploader("Upload a photo of your handwritten notes/diagrams", type=['jpg', 'png', 'jpeg'])

# --- CORE LOGIC & API CALLS ---
if st.button("Start Evaluation"):
    if uploaded_file:
        with st.spinner("Analyzing your explanation..."):
            try:
                
                # ==========================================
                # BRANCH 1: AUDIO PROCESSING (Whisper + Llama 3.3)
                # ==========================================
                if mode == "🎙️ Audio File":
                    # Step 1: Transcribe
                    transcription = client.audio.transcriptions.create(
                        file=(uploaded_file.name, uploaded_file.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                    
                    # Step 2: Evaluate Text
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": f"You are a {age_choice} listener. {age_map[age_choice]}"},
                            {"role": "user", "content": f"Here is the transcript of my explanation: '{transcription}'. Rate my clarity (1-10) and give 3 specific tips to improve."}
                        ]
                    )
                    final_feedback = response.choices[0].message.content


                # ==========================================
                # BRANCH 2: VISION PROCESSING (Llama 4 Scout)
                # ==========================================
                else:
                    # Step 1: Convert Image to Base64
                    img_bytes = uploaded_file.getvalue()
                    base64_img = base64.b64encode(img_bytes).decode('utf-8')
                    mime_type = uploaded_file.type 
                    image_url = f"data:{mime_type};base64,{base64_img}"
                    
                    # Step 2: Evaluate Image + Prompt directly in one shot
                    response = client.chat.completions.create(
                        model="meta-llama/llama-4-scout-17b-16e-instruct",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"You are a {age_choice} listener. {age_map[age_choice]}\n\nLook at these handwritten notes/diagrams of my explanation. Read them carefully. Rate my clarity and accuracy (1-10) and give 3 specific tips to improve the logic or presentation."},
                                    {"type": "image_url", "image_url": {"url": image_url}}
                                ]
                            }
                        ]
                    )
                    final_feedback = response.choices[0].message.content

                # --- OUTPUT RESULTS ---
                st.success("Analysis Complete!")
                st.markdown("### 📝 Feedback & Rating")
                st.write(final_feedback)

            except Exception as e:
                st.error(f"Execution Error: {e}")
    else:
        st.warning("Please upload a file first!")
