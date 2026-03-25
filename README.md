# 🎓 Feynman Listener

A multimodal AI tool built to help students master complex topics using the Feynman Technique. Explain a concept via audio recording or handwritten notes, and an AI listener will evaluate your clarity, point out logical gaps, and provide actionable feedback.

## Features
* **Select Your Audience:** Choose between explaining to a 10-year-old, a college peer, or a rigorous PhD expert.
* **Audio Mode:** Upload voice recordings to be transcribed and evaluated.
* **Vision Mode:** Upload photos of your handwritten notes or mathematical diagrams for direct analysis.

## Tech Stack
* **Frontend:** Streamlit
* **LLM Engine:** Groq API
* **Audio Processing:** Whisper Large V3 Turbo
* **Vision Processing:** Llama 4 Scout (17B)
* **Text Processing:** Llama 3.3 (70B)

## Deployment
This app is designed to be deployed directly on **Streamlit Community Cloud**. 
To run it yourself:
1. Fork or clone this repository.
2. Deploy the `app.py` file to Streamlit.
3. Add your `GROQ_API_KEY` to the Streamlit App Secrets dashboard.
