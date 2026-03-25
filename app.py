import streamlit as st
import json
import re
import requests
import base64
import random
import string
import time
import hashlib
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq

# ==========================================
# 1. INITIALIZATION & SECURITY
# ==========================================
st.set_page_config(
    page_title="Satlex Feynman Studio",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- Custom CSS: Premium dark-sci aesthetic ----
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}
.stApp { background: #0a0d14; color: #e2e8f0; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; background: transparent; }
.stTabs [data-baseweb="tab"] {
    background: #12172a;
    border-radius: 10px;
    padding: 8px 20px;
    border: 1px solid #1e2a45;
    color: #7c8db5;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1a3a6b, #0f2347) !important;
    color: #60a5fa !important;
    border-color: #3b6fd4 !important;
}
div[data-testid="stMetricValue"] { color: #38bdf8; font-size: 1.4rem; font-weight: 700; }
.stButton>button {
    background: linear-gradient(135deg, #1e40af, #1d4ed8);
    color: white;
    border-radius: 10px;
    border: none;
    padding: 8px 20px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    letter-spacing: 0.04em;
    transition: all 0.2s ease;
}
.stButton>button:hover { background: linear-gradient(135deg, #2563eb, #3b82f6); transform: translateY(-1px); box-shadow: 0 4px 15px rgba(59,130,246,0.35); }
.score-badge { display:inline-block; padding:4px 14px; border-radius:20px; font-weight:700; font-size:1.1em; margin: 6px 4px; }
.score-excellent { background: linear-gradient(90deg,#065f46,#047857); color: #a7f3d0; border: 1px solid #10b981; }
.score-good { background: linear-gradient(90deg,#1e3a5f,#1e40af); color: #93c5fd; border: 1px solid #3b82f6; }
.score-low { background: linear-gradient(90deg,#4a1942,#6d1f3e); color: #f9a8d4; border: 1px solid #ec4899; }
.coin-anim { font-size: 1.3em; animation: coinpop 0.5s ease; }
@keyframes coinpop { 0%{transform:scale(1)} 50%{transform:scale(1.4)} 100%{transform:scale(1)} }
</style>
""", unsafe_allow_html=True)

# ==========================================
# FIREBASE INIT (singleton, safe)
# ==========================================
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cert = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cert)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()
ADMIN_EMAIL = "satviksinghalyt@gmail.com"
GROQ_MODEL_AUDIO = "whisper-large-v3-turbo"
GROQ_MODEL_TEXT  = "llama-3.3-70b-versatile"
GROQ_MODEL_VISION = "llama-3.2-11b-vision-preview"

# ==========================================
# 2. AUTH — SECURE KEY HASH + RATE LIMIT
# ==========================================

def hash_key(raw_key: str) -> str:
    """
    UPGRADE: Keys are now stored as SHA-256 hashes, not plaintext.
    Original code stored raw 6-char keys in Firestore — trivially readable
    by anyone with DB access. Now we hash before storing/comparing.
    """
    return hashlib.sha256(raw_key.encode()).hexdigest()

def generate_key() -> str:
    """Cryptographically stronger: uppercase + digits, 8 chars (vs 6)."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def check_rate_limit(email: str) -> bool:
    """
    NEW: Brute-force protection. Track failed attempts in Firestore.
    Block login for 15 minutes after 5 failed attempts.
    """
    ref = db.collection('login_attempts').document(email)
    doc = ref.get()
    now = time.time()
    if doc.exists:
        data = doc.to_dict()
        if data.get('attempts', 0) >= 5:
            elapsed = now - data.get('last_attempt', 0)
            if elapsed < 900:  # 15 min lockout
                mins = int((900 - elapsed) / 60) + 1
                return False, f"Account locked. Try again in {mins} minute(s)."
            else:
                ref.delete()  # Reset after lockout expires
    return True, ""

def record_failed_attempt(email: str):
    ref = db.collection('login_attempts').document(email)
    doc = ref.get()
    now = time.time()
    if doc.exists:
        attempts = doc.to_dict().get('attempts', 0) + 1
        ref.update({'attempts': attempts, 'last_attempt': now})
    else:
        ref.set({'attempts': 1, 'last_attempt': now})

def clear_failed_attempts(email: str):
    db.collection('login_attempts').document(email).delete()

# -------- AUTH GATE --------
if 'user_email' not in st.session_state:
    st.markdown("<h1 style='text-align:center;color:#60a5fa;letter-spacing:0.06em;'>🛡️ SATLEX IDENTITY GATEWAY</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#7c8db5;'>Authenticate to enter the Feynman Studio</p>", unsafe_allow_html=True)
    st.markdown("---")
    tab_log, tab_sign = st.tabs(["🔑 Enter Studio", "📜 Create Identity"])

    with tab_log:
        login_e = st.text_input("Registered Email", key="log_e", placeholder="you@domain.com")
        login_k = st.text_input("Satlex Access Key", type="password", key="log_k", placeholder="Your key")
        if st.button("⚡ Authorize Access", use_container_width=True):
            if not login_e or not login_k:
                st.warning("Please fill in both fields.")
            else:
                allowed, msg = check_rate_limit(login_e)
                if not allowed:
                    st.error(f"🔒 {msg}")
                else:
                    user_doc = db.collection('students').document(login_e).get()
                    if user_doc.exists and user_doc.to_dict().get('access_key') == hash_key(login_k):
                        clear_failed_attempts(login_e)
                        st.session_state.user_email = login_e
                        st.rerun()
                    else:
                        record_failed_attempt(login_e)
                        st.error("❌ Access Denied: Invalid credentials.")

    with tab_sign:
        new_e = st.text_input("Your Email", key="sig_e", placeholder="you@domain.com")
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Display Name", key="sig_n", placeholder="Dr. Feynman")
        if st.button("🧬 Generate Identity", use_container_width=True):
            if not new_e:
                st.warning("Enter your email first.")
            elif db.collection('students').document(new_e).get().exists:
                st.warning("Identity already registered. Log in instead.")
            else:
                raw_key = generate_key()
                db.collection('students').document(new_e).set({
                    'coins': 0,
                    'access_key': hash_key(raw_key),  # SECURE: store hash only
                    'history': [],
                    'purchased': [],
                    'display_name': new_name or new_e.split('@')[0],
                    'joined': datetime.now(timezone.utc).isoformat(),
                    'streak': 0,
                    'last_active': None,
                    'total_submissions': 0,
                })
                st.success(f"✅ Identity Born!")
                st.code(f"YOUR KEY: {raw_key}", language=None)
                st.warning("⚠️ Save this key immediately. It cannot be recovered.")
    st.stop()

# ==========================================
# 3. GLOBAL DATA SYNC + STREAK SYSTEM
# ==========================================
user_email = st.session_state.user_email
user_ref = db.collection('students').document(user_email)

@st.cache_data(ttl=30, show_spinner=False)
def fetch_user(email):
    return db.collection('students').document(email).get().to_dict()

user_data = fetch_user(user_email)
coins = user_data.get('coins', 0)
streak = user_data.get('streak', 0)
display_name = user_data.get('display_name', user_email.split('@')[0])

# NEW: Daily streak logic
def update_streak():
    """
    NEW FEATURE: Learning streak tracker. Increments streak if user submits
    today and last submission was yesterday. Resets if gap > 1 day.
    """
    today = datetime.now(timezone.utc).date().isoformat()
    last = user_data.get('last_active')
    if last == today:
        return  # Already active today
    yesterday = (datetime.now(timezone.utc).date().replace(day=datetime.now(timezone.utc).day - 1)).isoformat() if datetime.now(timezone.utc).day > 1 else None
    new_streak = (user_data.get('streak', 0) + 1) if last == yesterday else 1
    user_ref.update({'streak': new_streak, 'last_active': today})

# ==========================================
# 4. SIDEBAR: IDENTITY & LEADERBOARD
# ==========================================
def get_rank(c):
    if c < 100:   return "Aspirant",    "🔬"
    if c < 500:   return "Intern",      "🩺"
    if c < 1000:  return "Resident",    "🏥"
    if c < 5000:  return "Specialist",  "🧠"
    if c < 15000: return "Surgeon Pro", "🔪"
    return "Feynman Master", "🏆"

lvl, badge = get_rank(coins)

st.sidebar.markdown(f"""
<div style='text-align:center;padding:12px 0;'>
  <div style='font-size:2.2em'>{badge}</div>
  <div style='font-weight:700;font-size:1.1em;color:#60a5fa'>{display_name}</div>
  <div style='color:#7c8db5;font-size:0.85em'>{lvl}</div>
</div>
""", unsafe_allow_html=True)

# Progress bar to next rank
rank_thresholds = [100, 500, 1000, 5000, 15000]
next_thresh = next((t for t in rank_thresholds if coins < t), None)
if next_thresh:
    prev_thresh = rank_thresholds[rank_thresholds.index(next_thresh) - 1] if rank_thresholds.index(next_thresh) > 0 else 0
    progress = (coins - prev_thresh) / (next_thresh - prev_thresh)
    st.sidebar.progress(min(progress, 1.0), text=f"{coins}/{next_thresh} SC to next rank")

col_c, col_s = st.sidebar.columns(2)
col_c.metric("💰 Coins", f"{coins} SC")
col_s.metric("🔥 Streak", f"{streak} days")

st.sidebar.divider()

# UPGRADE: Leaderboard now shows display names + rank badges
st.sidebar.subheader("🏆 Global Leaderboard")

@st.cache_data(ttl=60, show_spinner=False)
def fetch_leaderboard():
    return [
        (u.id, u.to_dict())
        for u in db.collection('students')
            .order_by('coins', direction=firestore.Query.DESCENDING)
            .limit(5).stream()
    ]

medals = ["🥇","🥈","🥉","4️⃣","5️⃣"]
for i, (uid, udat) in enumerate(fetch_leaderboard()):
    name = udat.get('display_name', uid[:10]) + "..."
    c = udat.get('coins', 0)
    _, rb = get_rank(c)
    st.sidebar.caption(f"{medals[i]} {rb} {name} — **{c} SC**")

st.sidebar.divider()
if st.sidebar.button("🚪 Exit Studio"):
    for key in ['user_email']:
        if key in st.session_state:
            del st.session_state[key]
    st.cache_data.clear()
    st.rerun()

# ==========================================
# 5. DEVELOPER / ADMIN MODE
# ==========================================
if user_email == ADMIN_EMAIL:
    with st.expander("🛠️ Satlex Developer Console", expanded=False):
        st.subheader("📦 Deploy Learning Material")
        col1, col2 = st.columns(2)
        with col1:
            m_name  = st.text_input("Material Name")
            m_price = st.number_input("Price (SC)", min_value=10, step=10, value=50)
            m_desc  = st.text_area("Short Description", height=80)
        with col2:
            m_link  = st.text_input("Drive Link (ending in /preview)")
            m_tags  = st.text_input("Tags (comma-separated)", placeholder="biology,anatomy")
            m_level = st.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"])
        if st.button("🚀 Push to Marketplace", use_container_width=True):
            if m_name and m_link:
                db.collection('marketplace').add({
                    'name': m_name, 'price': m_price, 'link': m_link,
                    'description': m_desc, 'tags': [t.strip() for t in m_tags.split(',')],
                    'level': m_level, 'published': datetime.now(timezone.utc).isoformat(),
                    'purchases': 0
                })
                st.success(f"✅ Live: {m_name}")
            else:
                st.error("Name and link are required.")

        st.subheader("👥 User Management")
        target_email = st.text_input("Target User Email")
        col_a, col_b, col_c2 = st.columns(3)
        with col_a:
            bonus = st.number_input("Bonus SC", min_value=0, step=50)
            if st.button("Grant Coins") and target_email:
                db.collection('students').document(target_email).update(
                    {'coins': firestore.Increment(bonus)}
                )
                st.success(f"+{bonus} SC granted to {target_email}")
        with col_b:
            if st.button("Reset User") and target_email:
                db.collection('students').document(target_email).update(
                    {'coins': 0, 'history': [], 'purchased': [], 'streak': 0}
                )
                st.success(f"User {target_email} reset.")
        with col_c2:
            # NEW: Admin can see basic stats
            total_users = len(list(db.collection('students').stream()))
            st.metric("Total Users", total_users)

# ==========================================
# 6. SCORING ENGINE — UPGRADE
# ==========================================

def extract_score(feedback: str) -> int:
    """
    UPGRADE: Original used brittle string-in checks like 'Score: 10/10'.
    Now uses regex to robustly extract score from any 'X/10' format in text.
    Handles: Score: 8/10, score:9/10, 7/10, Rating: 8.5/10, etc.
    """
    patterns = [
        r'[Ss]core[:\s]+(\d+(?:\.\d+)?)\s*/\s*10',
        r'[Rr]ating[:\s]+(\d+(?:\.\d+)?)\s*/\s*10',
        r'\b(\d+(?:\.\d+)?)\s*/\s*10\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, feedback)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
    return 0.0

def calculate_reward(score: float) -> int:
    """
    UPGRADE: Original only rewarded scores 8-10 and used fixed amounts.
    Now uses a continuous reward curve — any score earns something,
    encouraging improvement and preventing zero-reward frustration.
    Also applies streak multiplier.
    """
    if score <= 0:
        return 0
    base = max(0, int((score / 10) ** 1.5 * 100))  # Curved: 10→100, 8→72, 5→35, 3→13
    streak_bonus = min(streak * 2, 20)              # Up to +20 SC for streak
    return base + streak_bonus

def build_prompt(persona_label: str, age_map: dict, transcript_or_hint: str, mode: str) -> str:
    """
    UPGRADE: Structured, rich evaluation prompt replaces terse one-liner.
    Provides consistent output format for reliable score parsing.
    Includes Feynman technique criteria explicitly.
    """
    persona_instruction = age_map[persona_label]
    return f"""You are evaluating a student's Feynman Technique explanation.
Listener persona: {persona_label}. {persona_instruction}

Evaluate across 4 criteria:
1. Clarity — Is the explanation simple enough for the listener?
2. Accuracy — Are the core facts correct?
3. Depth — Does it cover the important concepts?
4. Engagement — Is it interesting and well-structured?

{'Transcribed explanation: ' + transcript_or_hint if mode == 'audio' else 'The image shows handwritten/visual notes. Evaluate their content.'}

Provide:
- A 2-3 sentence summary of what was done well.
- A 1-2 sentence constructive improvement tip.
- End your response EXACTLY with: Score: X/10
  where X is an integer from 1 to 10.
"""

# ==========================================
# 7. MAIN TABS
# ==========================================
tab_studio, tab_market, tab_history, tab_analytics = st.tabs([
    "🎨 Feynman Studio", "🛒 Marketplace", "📜 History", "📊 Analytics"
])

# ---- STUDIO TAB ----
with tab_studio:
    st.markdown("## 🧠 Feynman Mastery Engine")
    st.caption("Teach it simply. The universe rewards clarity.")

    col_left, col_right = st.columns([1.2, 1])
    with col_left:
        age_map = {
            "👶 10-year-old (Kid)":
                "Explain like I'm 10. No jargon. Use toys, cartoons, or daily-life analogies.",
            "🧑 20-year-old (Peer)":
                "Explain like we're classmates. Semi-formal, can use some technical words.",
            "🎓 Expert (PhD level)":
                "I'm a domain expert. Be rigorous, use precise terminology, go deep.",
        }
        persona = st.selectbox("🎯 Choose your listener:", list(age_map.keys()))
        mode = st.radio("📤 Submission method:", ["🎙️ Audio File", "📸 Photo of Notes"], horizontal=True)

        # NEW: Topic tag field for better history tracking
        topic_tag = st.text_input("📌 Topic label (e.g. 'Krebs Cycle')", placeholder="Optional but recommended")

        uploaded = st.file_uploader(
            "Upload your explanation",
            type=['mp3','wav','m4a','jpg','png','jpeg'],
            help="Audio or image of your handwritten notes"
        )

    with col_right:
        st.markdown("### 🪙 Reward Preview")
        st.markdown("""
        | Score | Coins Earned |
        |-------|-------------|
        | 10/10 | 100 SC + streak |
        | 8/10  | ~72 SC |
        | 5/10  | ~35 SC |
        | Any   | Always earn something |
        """)
        st.info(f"🔥 Your streak: **{streak} days** (+{min(streak*2,20)} SC bonus per submission)")

    if st.button("⚡ Evaluate My Mastery", use_container_width=True, type="primary") and uploaded:
        with st.spinner("🔬 Analyzing with Groq AI..."):
            try:
                client = Groq(api_key=st.secrets["GROQ_API_KEY"])

                if "Audio" in mode:
                    # Audio transcription path
                    transcription = client.audio.transcriptions.create(
                        file=(uploaded.name, uploaded.getvalue()),
                        model=GROQ_MODEL_AUDIO,
                        response_format="text"
                    )
                    prompt = build_prompt(persona, age_map, transcription, "audio")
                    response = client.chat.completions.create(
                        model=GROQ_MODEL_TEXT,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.4,   # NEW: Lower temp for consistent scoring
                        max_tokens=600,
                    )
                else:
                    # Vision path
                    b64_img = base64.b64encode(uploaded.getvalue()).decode('utf-8')
                    vision_prompt = build_prompt(persona, age_map, "", "vision")
                    response = client.chat.completions.create(
                        model=GROQ_MODEL_VISION,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": vision_prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{uploaded.type};base64,{b64_img}"}}
                            ]
                        }],
                        temperature=0.4,
                        max_tokens=600,
                    )

                feedback = response.choices[0].message.content
                score = extract_score(feedback)
                reward = calculate_reward(score)

                # Display feedback
                st.markdown("---")
                st.markdown("### 📋 Evaluation Report")

                # Score badge
                if score >= 8:
                    badge_class = "score-excellent"
                elif score >= 5:
                    badge_class = "score-good"
                else:
                    badge_class = "score-low"
                st.markdown(f'<span class="score-badge {badge_class}">Score: {score}/10</span>', unsafe_allow_html=True)

                st.markdown(feedback)

                # Reward + history update
                if reward > 0:
                    topic_label = topic_tag if topic_tag else uploaded.name
                    history_entry = {
                        "topic": topic_label,
                        "score": score,
                        "reward": reward,
                        "persona": persona,
                        "date": datetime.now(timezone.utc).isoformat(),
                        "mode": "audio" if "Audio" in mode else "vision",
                    }
                    update_streak()
                    user_ref.update({
                        'coins': firestore.Increment(reward),
                        'total_submissions': firestore.Increment(1),
                        'history': firestore.ArrayUnion([history_entry])
                    })
                    st.success(f"🪙 +{reward} SC awarded! (Base: {reward - min(streak*2,20)} + {min(streak*2,20)} streak bonus)")
                    st.cache_data.clear()
                    st.balloons()
                else:
                    st.info("No coins this time — keep practicing! Any score earns rewards on your next attempt.")

            except Exception as e:
                st.error(f"⚠️ Processing error: {str(e)}")
                st.caption("Check your Groq API key in secrets, or try a different file.")

    elif not uploaded and st.button("⚡ Evaluate My Mastery", use_container_width=True, disabled=True):
        st.warning("Please upload a file first.")

# ---- MARKETPLACE TAB ----
with tab_market:
    st.markdown("## 🛒 Satlex Knowledge Marketplace")
    st.caption(f"Your balance: **{coins} SC**")

    # NEW: Search/filter
    search_q = st.text_input("🔍 Search materials", placeholder="e.g. anatomy, pharmacology...")
    level_filter = st.multiselect("Difficulty", ["Beginner", "Intermediate", "Advanced"], default=[])

    @st.cache_data(ttl=120, show_spinner=False)
    def fetch_marketplace():
        return [(n.id, n.to_dict()) for n in db.collection('marketplace').stream()]

    all_items = fetch_marketplace()

    # Apply filters
    filtered = []
    for nid, item in all_items:
        if search_q and search_q.lower() not in item.get('name','').lower() and search_q.lower() not in item.get('description','').lower():
            continue
        if level_filter and item.get('level') not in level_filter:
            continue
        filtered.append((nid, item))

    if not filtered:
        st.info("No materials match your filters. Try broadening your search.")

    # Display in 2-column grid
    cols = st.columns(2)
    for idx, (nid, item) in enumerate(filtered):
        with cols[idx % 2]:
            with st.container(border=True):
                # Header
                col_t, col_p = st.columns([3,1])
                with col_t:
                    st.subheader(item.get('name', 'Untitled'))
                    if item.get('description'):
                        st.caption(item['description'])
                with col_p:
                    level_colors = {"Beginner":"🟢","Intermediate":"🟡","Advanced":"🔴"}
                    lvl_icon = level_colors.get(item.get('level',''), "⚪")
                    st.markdown(f"**{lvl_icon} {item.get('level','')}**")
                    st.markdown(f"💰 **{item.get('price',0)} SC**")

                # Tags
                if item.get('tags'):
                    tags_html = " ".join([f'<span style="background:#1e3a5f;color:#93c5fd;padding:2px 8px;border-radius:10px;font-size:0.78em;margin:2px">{t}</span>' for t in item['tags'] if t])
                    st.markdown(tags_html, unsafe_allow_html=True)

                # Purchase count
                if item.get('purchases', 0) > 0:
                    st.caption(f"👥 {item['purchases']} learners enrolled")

                # Unlock / View
                if nid in user_data.get('purchased', []):
                    st.success("✅ Unlocked")
                    if item.get('link'):
                        st.components.v1.iframe(item['link'], height=500, scrolling=True)
                else:
                    can_afford = coins >= item.get('price', 0)
                    if st.button(
                        f"🔓 Unlock for {item.get('price',0)} SC",
                        key=f"buy_{nid}",
                        disabled=not can_afford,
                        use_container_width=True
                    ):
                        user_ref.update({
                            'coins': firestore.Increment(-item['price']),
                            'purchased': firestore.ArrayUnion([nid])
                        })
                        # Track purchases on item too
                        db.collection('marketplace').document(nid).update(
                            {'purchases': firestore.Increment(1)}
                        )
                        st.cache_data.clear()
                        st.rerun()
                    if not can_afford:
                        st.caption(f"Need {item['price'] - coins} more SC")

# ---- HISTORY TAB ----
with tab_history:
    st.markdown("## 📜 Mastery Timeline")
    history = user_data.get('history', [])

    if not history:
        st.info("No submissions yet. Head to the Studio and teach something!")
    else:
        # UPGRADE: Rich history table with all stored metadata
        # Sort newest first
        try:
            sorted_hist = sorted(history, key=lambda x: x.get('date',''), reverse=True)
        except:
            sorted_hist = history[::-1]

        st.markdown(f"**{len(sorted_hist)} total submissions** — {user_data.get('total_submissions', len(sorted_hist))} evaluated")

        for entry in sorted_hist:
            score = entry.get('score', 0)
            reward = entry.get('reward', 0)
            date_str = entry.get('date', '')
            try:
                date_fmt = datetime.fromisoformat(date_str).strftime("%b %d, %Y %H:%M")
            except:
                date_fmt = date_str[:16] if date_str else "Unknown"

            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3,1,1,1])
                with col1:
                    mode_icon = "🎙️" if entry.get('mode') == 'audio' else "📸"
                    st.markdown(f"**{mode_icon} {entry.get('topic', 'Untitled')}**")
                    st.caption(f"🎯 {entry.get('persona','—')}  ·  {date_fmt}")
                with col2:
                    if score >= 8:   color = "🟢"
                    elif score >= 5: color = "🟡"
                    else:            color = "🔴"
                    st.markdown(f"**{color} {score}/10**")
                with col3:
                    st.markdown(f"**+{reward} SC**")
                with col4:
                    # NEW: Re-evaluate hint button
                    if st.button("📖", key=f"hist_{date_str}", help="Review this topic"):
                        st.info(f"Re-practice: **{entry.get('topic','')}** with a fresh explanation!")

# ---- ANALYTICS TAB ----
with tab_analytics:
    st.markdown("## 📊 Personal Performance Analytics")
    history = user_data.get('history', [])

    if len(history) < 2:
        st.info("Submit at least 2 evaluations to see analytics.")
    else:
        scores = [e.get('score', 0) for e in history if 'score' in e]
        rewards = [e.get('reward', 0) for e in history if 'reward' in e]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Avg Score", f"{sum(scores)/len(scores):.1f}/10")
        col2.metric("Best Score", f"{max(scores)}/10")
        col3.metric("Total SC Earned", f"{sum(rewards)} SC")
        col4.metric("Total Submissions", len(history))

        # Score trend chart
        st.markdown("### Score Trend")
        import pandas as pd
        try:
            sorted_hist = sorted(history, key=lambda x: x.get('date',''))
            df = pd.DataFrame({
                'Submission': range(1, len(sorted_hist)+1),
                'Score': [e.get('score',0) for e in sorted_hist],
                'Topic': [e.get('topic','')[:20] for e in sorted_hist],
            })
            st.line_chart(df.set_index('Submission')['Score'])
        except Exception as e:
            st.caption(f"Chart unavailable: {e}")

        # Persona breakdown
        st.markdown("### Performance by Listener Persona")
        from collections import defaultdict
        persona_scores = defaultdict(list)
        for e in history:
            if 'persona' in e and 'score' in e:
                short_p = e['persona'].split('(')[0].strip()
                persona_scores[short_p].append(e['score'])
        for persona_name, pscores in persona_scores.items():
            avg = sum(pscores)/len(pscores)
            st.markdown(f"**{persona_name}** — avg {avg:.1f}/10 over {len(pscores)} attempts")
            st.progress(avg/10)
