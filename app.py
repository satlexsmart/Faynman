"""
╔══════════════════════════════════════════════════════════════════════╗
║         SATLEX COMMUNITY PLATFORM  — v3.0 DECENTRALIZED             ║
║  Architecture: Peer-to-peer knowledge economy. No admin gatekeeping. ║
║  Anyone learns → earns SC → uploads knowledge → others buy → cycle  ║
╚══════════════════════════════════════════════════════════════════════╝

DECENTRALIZED MODEL (like open-source biology):
  - Any student can upload materials (pending community moderation)
  - Any student with enough SC can buy materials
  - Uploaders earn SC royalties when their material is purchased
  - Community votes on quality (upvote/downvote/report)
  - Admin role reduced to: ban appeals, dispute resolution only
  - Material quality self-regulates via ratings + SC incentives

NEW vs v2:
  + Student uploader system with 30% royalty engine
  + Community moderation pipeline (pending → approved/rejected)
  + Uploader creator dashboard with earnings metrics
  + File hash deduplication (anti-coin-farming)
  + OTP key recovery via email
  + Live Whisper transcription preview before scoring
  + Structured feedback (Strengths / Improvements / Score blocks)
  + Related topic suggestions after evaluation
  + Free preview link support on marketplace cards
  + Star ratings & text reviews system
  + Refund/dispute mechanism with admin resolution
  + Weekly SC goal system with progress bar
  + Achievement badge unlocks with toast notifications
  + "You are here" leaderboard rank even outside top 10
  + Bulk CSV upload with per-row validation
  + Smart URL type detection (Drive / YouTube / PDF / custom)
  + Edit/archive own uploaded materials
  + Welcome SC bonus on signup
"""

import streamlit as st
import hashlib, re, random, string, time, io, csv as csv_mod
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq

# ══════════════════════════════════════════
# 1.  PAGE CONFIG & GLOBAL STYLES
# ══════════════════════════════════════════
st.set_page_config(
    page_title="Satlex Community",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
.stApp { background: #080b12; color: #e2e8f0; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; background: transparent; flex-wrap: wrap; }
.stTabs [data-baseweb="tab"] {
    background: #10172a; border-radius: 10px; padding: 6px 16px;
    border: 1px solid #1e2d4a; color: #6b7fa3;
    font-weight: 600; font-family: 'Space Grotesk', sans-serif; font-size: .88rem;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg,#0f3460,#1a4980) !important;
    color: #60a5fa !important; border-color: #2563eb !important;
}
.stButton>button {
    background: linear-gradient(135deg,#1e40af,#2563eb); color: white;
    border-radius: 10px; border: none;
    font-family: 'Space Grotesk', sans-serif; font-weight: 600; transition: all .2s;
}
.stButton>button:hover {
    background: linear-gradient(135deg,#2563eb,#3b82f6);
    transform: translateY(-1px); box-shadow: 0 4px 14px rgba(59,130,246,.4);
}
div[data-testid="stMetricValue"] { color: #38bdf8; font-size: 1.3rem; font-weight: 700; }
.uploader-badge {
    display:inline-block; padding:2px 10px; border-radius:20px;
    font-size:.75rem; font-weight:600;
    background:#0c2340; color:#60a5fa; border:1px solid #1e4080;
}
.royalty-badge {
    display:inline-block; padding:2px 10px; border-radius:20px;
    font-size:.75rem; font-weight:600;
    background:#0c2e1a; color:#34d399; border:1px solid #064e2e;
}
.score-badge { display:inline-block; padding:3px 12px; border-radius:20px; font-weight:700; font-size:1em; margin:4px 2px; }
.score-excellent { background:linear-gradient(90deg,#065f46,#047857); color:#a7f3d0; border:1px solid #10b981; }
.score-good      { background:linear-gradient(90deg,#1e3a5f,#1e40af); color:#93c5fd; border:1px solid #3b82f6; }
.score-low       { background:linear-gradient(90deg,#4a1942,#6d1f3e); color:#f9a8d4; border:1px solid #ec4899; }
.feedback-block  { border-left:3px solid; border-radius:0 8px 8px 0; padding:.7rem 1rem; margin:.4rem 0; background:#0d1525; }
.fb-strength { border-color:#10b981; }
.fb-improve  { border-color:#f59e0b; }
.fb-score    { border-color:#3b82f6; }
.achievement { display:inline-block; padding:3px 10px; border-radius:20px; font-size:.78rem; font-weight:600; margin:2px; }
.ach-gold    { background:#3b2a0f; color:#fcd34d; border:1px solid #b45309; }
.ach-silver  { background:#1a2030; color:#94a3b8; border:1px solid #475569; }
.ach-bronze  { background:#2d1a0f; color:#fdba74; border:1px solid #92400e; }
.rank-row    { padding:.4rem .6rem; border-radius:8px; font-size:.85rem; margin-bottom:3px; }
.rank-self   { background:#0f2347; border:1px solid #1e3a6e; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════
# 2.  FIREBASE INIT
# ══════════════════════════════════════════
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()

db         = init_firebase()
ADMIN_EMAIL = "satviksinghalyt@gmail.com"
WHISPER    = "whisper-large-v3-turbo"
LLM        = "llama-3.3-70b-versatile"
VISION     = "llama-3.2-11b-vision-preview"

# ══════════════════════════════════════════
# 3.  UTILITIES
# ══════════════════════════════════════════
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def md5_bytes(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()

def gen_key(n=8) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()

def detect_url(url: str):
    """Returns (label, embed_url)"""
    if "drive.google.com" in url:
        e = re.sub(r'/view.*$', '/preview', url)
        if '/preview' not in e:
            e = url.rstrip('/') + '/preview'
        return "Google Drive", e
    if "youtube.com" in url or "youtu.be" in url:
        m = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})', url)
        return "YouTube", (f"https://www.youtube.com/embed/{m.group(1)}" if m else url)
    if url.lower().endswith('.pdf'):
        return "PDF", url
    return "Web URL", url

def extract_score(text: str) -> float:
    for p in [r'[Ss]core[:\s]+(\d+(?:\.\d+)?)\s*/\s*10',
              r'[Rr]ating[:\s]+(\d+(?:\.\d+)?)\s*/\s*10',
              r'\b(\d+(?:\.\d+)?)\s*/\s*10\b']:
        m = re.search(p, text)
        if m:
            try: return float(m.group(1))
            except: pass
    return 0.0

def calc_reward(score: float, streak: int) -> int:
    if score <= 0: return 0
    base = max(0, int((score / 10) ** 1.5 * 100))
    return base + min(streak * 2, 20)

def get_rank(coins: int):
    if coins < 100:   return "Aspirant",     "🔬"
    if coins < 500:   return "Intern",        "🩺"
    if coins < 1000:  return "Resident",      "🏥"
    if coins < 5000:  return "Specialist",    "🧠"
    if coins < 15000: return "Surgeon Pro",   "🔪"
    return "Feynman Master", "🏆"

RANK_THRESH = [100, 500, 1000, 5000, 15000]

ACHIEVEMENTS = [
    ('first_perfect',  '🌟 First Perfect',   'ach-gold',   lambda d,h,s: any(x.get('score',0)==10 for x in h)),
    ('seven_streak',   '🔥 7-Day Streak',     'ach-gold',   lambda d,h,s: s >= 7),
    ('first_upload',   '📤 First Upload',     'ach-silver', lambda d,h,s: d.get('total_uploads',0) >= 1),
    ('first_sale',     '💰 First Sale',       'ach-gold',   lambda d,h,s: d.get('total_royalties',0) > 0),
    ('ten_evals',      '🧪 10 Evaluations',   'ach-silver', lambda d,h,s: len(h) >= 10),
    ('scholar',        '🎓 Scholar (1k SC)',  'ach-gold',   lambda d,h,s: d.get('coins',0) >= 1000),
    ('contributor',    '🤝 Contributor x3',   'ach-bronze', lambda d,h,s: d.get('total_uploads',0) >= 3),
]

def check_achievements(user_data, history, streak):
    existing = set(user_data.get('achievements', []))
    new = []
    for key, name, cls, cond in ACHIEVEMENTS:
        if key not in existing:
            try:
                if cond(user_data, history, streak):
                    new.append({'key': key, 'name': name, 'class': cls})
            except: pass
    return new

def rate_limit_ok(email: str):
    ref = db.collection('login_attempts').document(email)
    doc = ref.get()
    now = time.time()
    if doc.exists:
        d = doc.to_dict()
        if d.get('attempts', 0) >= 5:
            elapsed = now - d.get('last_attempt', 0)
            if elapsed < 900:
                return False, f"Locked {int((900-elapsed)/60)+1} min"
            ref.delete()
    return True, ""

def record_fail(email):
    ref = db.collection('login_attempts').document(email)
    doc = ref.get()
    if doc.exists:
        ref.update({'attempts': firestore.Increment(1), 'last_attempt': time.time()})
    else:
        ref.set({'attempts': 1, 'last_attempt': time.time()})

def clear_fails(email):
    db.collection('login_attempts').document(email).delete()

# ══════════════════════════════════════════
# 4.  CACHED DATA FETCHERS
# ══════════════════════════════════════════
@st.cache_data(ttl=20, show_spinner=False)
def fetch_user(email):
    d = db.collection('students').document(email).get()
    return d.to_dict() if d.exists else {}

@st.cache_data(ttl=60, show_spinner=False)
def fetch_leaderboard():
    return [(u.id, u.to_dict()) for u in
            db.collection('students').order_by('coins', direction=firestore.Query.DESCENDING).limit(10).stream()]

@st.cache_data(ttl=30, show_spinner=False)
def fetch_marketplace():
    return [(d.id, d.to_dict()) for d in
            db.collection('community_materials').where('status','==','approved').stream()]

@st.cache_data(ttl=30, show_spinner=False)
def fetch_pending():
    return [(d.id, d.to_dict()) for d in
            db.collection('community_materials').where('status','==','pending').stream()]

@st.cache_data(ttl=30, show_spinner=False)
def fetch_my_uploads(email):
    return [(d.id, d.to_dict()) for d in
            db.collection('community_materials').where('uploader','==',email).stream()]

# ══════════════════════════════════════════
# 5.  AUTH GATE
# ══════════════════════════════════════════
if 'user_email' not in st.session_state:
    st.markdown("""
    <div style='text-align:center;padding:2rem 0 1rem'>
      <div style='font-size:3rem'>🧬</div>
      <h1 style='color:#60a5fa;letter-spacing:.04em;margin:.4rem 0'>SATLEX COMMUNITY</h1>
      <p style='color:#6b7fa3;font-size:1rem'>A living knowledge ecosystem — grown by students, for students</p>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    t_in, t_up, t_rec = st.tabs(["🔑 Sign In", "📜 Join Community", "🔓 Recover Key"])

    with t_in:
        em = st.text_input("Email", key="li_e", placeholder="you@domain.com")
        ky = st.text_input("Access Key", type="password", key="li_k")
        if st.button("⚡ Enter Studio", use_container_width=True):
            ok, msg = rate_limit_ok(em)
            if not ok:
                st.error(f"🔒 {msg}")
            elif not em or not ky:
                st.warning("Fill both fields.")
            else:
                doc = db.collection('students').document(em).get()
                if doc.exists and doc.to_dict().get('access_key') == sha256(ky):
                    clear_fails(em)
                    st.session_state.user_email = em
                    st.rerun()
                else:
                    record_fail(em)
                    st.error("❌ Invalid credentials.")

    with t_up:
        ne = st.text_input("Email", key="su_e")
        nn = st.text_input("Display Name", key="su_n")
        if st.button("🧬 Create Identity", use_container_width=True):
            if not ne:
                st.warning("Enter email.")
            elif not re.match(r'^[\w.+-]+@[\w-]+\.[a-z]{2,}$', ne, re.I):
                st.error("Invalid email format.")
            elif db.collection('students').document(ne).get().exists:
                st.warning("Already registered. Sign in instead.")
            else:
                raw = gen_key()
                db.collection('students').document(ne).set({
                    'coins': 50, 'access_key': sha256(raw),
                    'history': [], 'purchased': [],
                    'display_name': nn or ne.split('@')[0],
                    'joined': now_iso(), 'streak': 0,
                    'last_active': None, 'total_submissions': 0,
                    'total_uploads': 0, 'total_royalties': 0,
                    'achievements': [], 'weekly_sc': 0,
                    'week_start': today(), 'submitted_hashes': [],
                })
                st.success("✅ Welcome to the community! +50 SC joining bonus.")
                st.code(f"YOUR KEY: {raw}", language=None)
                st.warning("⚠️ Save this key. Email OTP recovery is available if lost.")

    with t_rec:
        re_em = st.text_input("Registered Email", key="rec_e")
        if st.button("📧 Send OTP Code", use_container_width=True):
            if not re_em:
                st.warning("Enter email.")
            elif not db.collection('students').document(re_em).get().exists:
                st.error("No account found.")
            else:
                otp = gen_key(6)
                exp = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
                db.collection('otp_recovery').document(re_em).set({'otp': sha256(otp), 'expires': exp})
                st.info(f"🔐 OTP (demo — production sends via email): **{otp}**")

        otp_in = st.text_input("OTP Code", key="otp_i")
        nk_in  = st.text_input("New Key (blank = auto-generate)", key="nk_i")
        if st.button("✅ Reset Key", use_container_width=True):
            if not re_em or not otp_in:
                st.warning("Fill email and OTP.")
            else:
                rec = db.collection('otp_recovery').document(re_em).get()
                if not rec.exists:
                    st.error("No active OTP. Request one first.")
                else:
                    rd  = rec.to_dict()
                    exp = datetime.fromisoformat(rd['expires'])
                    if datetime.now(timezone.utc) > exp:
                        st.error("OTP expired.")
                    elif rd['otp'] != sha256(otp_in):
                        st.error("Wrong OTP.")
                    else:
                        fk = nk_in if nk_in else gen_key()
                        db.collection('students').document(re_em).update({'access_key': sha256(fk)})
                        db.collection('otp_recovery').document(re_em).delete()
                        st.success(f"✅ Key reset! New key: **{fk}**")
    st.stop()

# ══════════════════════════════════════════
# 6.  LOAD USER STATE
# ══════════════════════════════════════════
user_email = st.session_state.user_email
user_ref   = db.collection('students').document(user_email)
user_data  = fetch_user(user_email)
coins      = user_data.get('coins', 0)
streak     = user_data.get('streak', 0)
dname      = user_data.get('display_name', user_email.split('@')[0])
is_admin   = (user_email == ADMIN_EMAIL)

# Weekly goal reset
try:
    ws = user_data.get('week_start', today())
    ws_date = datetime.strptime(ws[:10], '%Y-%m-%d').date()
    if (datetime.now(timezone.utc).date() - ws_date).days >= 7:
        user_ref.update({'weekly_sc': 0, 'week_start': today()})
        user_data['weekly_sc'] = 0
except: pass
weekly_sc   = user_data.get('weekly_sc', 0)
WEEKLY_GOAL = 300

def tick_streak():
    td   = today()
    last = user_data.get('last_active')
    if last == td: return
    try:
        yest  = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        new_s = (user_data.get('streak', 0) + 1) if last == yest else 1
    except:
        new_s = 1
    user_ref.update({'streak': new_s, 'last_active': td})

# ══════════════════════════════════════════
# 7.  SIDEBAR
# ══════════════════════════════════════════
lvl, badge_icon = get_rank(coins)
st.sidebar.markdown(f"""
<div style='text-align:center;padding:10px 0 6px'>
  <div style='font-size:2rem'>{badge_icon}</div>
  <div style='font-weight:700;font-size:1.05rem;color:#60a5fa'>{dname}</div>
  <div style='color:#6b7fa3;font-size:.82rem'>{lvl}</div>
</div>""", unsafe_allow_html=True)

nt = next((t for t in RANK_THRESH if coins < t), None)
if nt:
    pt = RANK_THRESH[RANK_THRESH.index(nt)-1] if RANK_THRESH.index(nt) > 0 else 0
    st.sidebar.progress((coins - pt) / (nt - pt), text=f"{coins}/{nt} SC to next rank")

c1, c2 = st.sidebar.columns(2)
c1.metric("💰 SC", f"{coins}")
c2.metric("🔥 Streak", f"{streak}d")
st.sidebar.progress(min(weekly_sc / WEEKLY_GOAL, 1.0), text=f"Weekly: {weekly_sc}/{WEEKLY_GOAL} SC")

achs = user_data.get('achievements', [])
if achs:
    st.sidebar.markdown("<div style='font-size:.78rem;color:#6b7fa3;margin:.4rem 0'>Achievements</div>", unsafe_allow_html=True)
    st.sidebar.markdown(" ".join(f'<span class="achievement ach-gold">{a}</span>' for a in achs[:4]), unsafe_allow_html=True)

st.sidebar.divider()
st.sidebar.subheader("🏆 Leaderboard")
medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
lb = fetch_leaderboard()
user_in_top = False
for i, (uid, ud) in enumerate(lb):
    is_me = uid == user_email
    if is_me: user_in_top = True
    name  = ud.get('display_name', uid[:10])
    cv    = ud.get('coins', 0)
    _, rb = get_rank(cv)
    cls   = "rank-row rank-self" if is_me else "rank-row"
    st.sidebar.markdown(f'<div class="{cls}">{medals[i]} {rb} {name[:14]} — <b>{cv} SC</b></div>', unsafe_allow_html=True)

if not user_in_top:
    all_u = list(db.collection('students').order_by('coins', direction=firestore.Query.DESCENDING).stream())
    for i, u in enumerate(all_u):
        if u.id == user_email:
            st.sidebar.markdown(f'<div class="rank-row rank-self">📍 You: #{i+1} — {coins} SC</div>', unsafe_allow_html=True)
            break

st.sidebar.divider()
if st.sidebar.button("🚪 Exit"):
    st.session_state.pop('user_email', None)
    st.cache_data.clear()
    st.rerun()

# ══════════════════════════════════════════
# 8.  MAIN TABS
# ══════════════════════════════════════════
tab_names = ["🎨 Studio", "🌐 Community Market", "📤 My Uploads", "📜 History", "📊 Analytics"]
if is_admin: tab_names.append("🛠️ Admin")
tabs = st.tabs(tab_names)

# ─────────────────────────────────────────
# TAB 0: FEYNMAN STUDIO
# ─────────────────────────────────────────
with tabs[0]:
    st.markdown("## 🧠 Feynman Mastery Studio")
    st.caption("Teach it simply. The universe taxes confusion and rewards clarity.")

    col_l, col_r = st.columns([1.3, 1])
    with col_l:
        age_map = {
            "👶 Kid (10 yr)":  "Explain like I'm 10. No jargon. Use toys or daily-life analogies.",
            "🧑 Peer (20 yr)": "Explain like we're classmates. Semi-formal, some technical words OK.",
            "🎓 Expert (PhD)": "I'm a domain expert. Be rigorous, precise, technically deep.",
        }
        persona   = st.selectbox("🎯 Listener persona", list(age_map.keys()))
        mode      = st.radio("📤 Method", ["🎙️ Audio", "📸 Photo of Notes"], horizontal=True)
        topic_tag = st.text_input("📌 Topic (e.g. 'Krebs Cycle')", placeholder="Helps track your progress")
        uploaded  = st.file_uploader("Upload your explanation", type=['mp3','wav','m4a','jpg','png','jpeg'])

    with col_r:
        st.markdown("### 🪙 Reward Table")
        st.markdown("""
| Score | Coins |
|-------|-------|
| 10/10 | 100 SC + streak |
| 8/10  | ~72 SC + streak |
| 5/10  | ~35 SC |
| Any   | Always > 0 SC |
        """)
        st.info(f"🔥 Streak bonus: +{min(streak*2,20)} SC/submission")
        st.info(f"📅 Weekly goal: {weekly_sc}/{WEEKLY_GOAL} SC")

    if st.button("⚡ Evaluate Mastery", use_container_width=True, type="primary") and uploaded:
        if len(uploaded.getvalue()) > 25 * 1024 * 1024:
            st.error("File too large. Max 25 MB.")
            st.stop()

        file_hash = md5_bytes(uploaded.getvalue())
        if file_hash in user_data.get('submitted_hashes', []):
            st.warning("⚠️ Identical file already submitted. Upload a fresh recording!")
            st.stop()

        with st.spinner("🔬 Analyzing..."):
            try:
                client = Groq(api_key=st.secrets["GROQ_API_KEY"])

                if "Audio" in mode:
                    transcription = client.audio.transcriptions.create(
                        file=(uploaded.name, uploaded.getvalue()),
                        model=WHISPER, response_format="text"
                    )
                    st.markdown("---")
                    st.markdown("#### 📝 What the AI heard")
                    with st.expander("Review transcription", expanded=True):
                        st.write(transcription)

                    prompt = f"""Evaluate this Feynman Technique explanation.
Listener: {persona}. {age_map[persona]}

Criteria: Clarity, Accuracy, Depth, Engagement.

Transcript: {transcription}

Reply in EXACTLY this format:
STRENGTHS: [2-3 sentences on what was done well]
IMPROVEMENTS: [1-2 sentences on what to fix next time]
Score: X/10"""
                    resp = client.chat.completions.create(
                        model=LLM,
                        messages=[{"role":"user","content":prompt}],
                        temperature=0.35, max_tokens=500
                    )

                else:
                    import base64
                    b64 = base64.b64encode(uploaded.getvalue()).decode()
                    prompt_v = f"""Evaluate these study notes using Feynman Technique criteria.
Listener: {persona}. {age_map[persona]}
Criteria: Clarity, Accuracy, Depth, Engagement.

Reply in EXACTLY this format:
STRENGTHS: [2-3 sentences]
IMPROVEMENTS: [1-2 sentences]
Score: X/10"""
                    resp = client.chat.completions.create(
                        model=VISION,
                        messages=[{"role":"user","content":[
                            {"type":"text","text":prompt_v},
                            {"type":"image_url","image_url":{"url":f"data:{uploaded.type};base64,{b64}"}}
                        ]}],
                        temperature=0.35, max_tokens=500
                    )

                feedback = resp.choices[0].message.content
                score    = extract_score(feedback)
                reward   = calc_reward(score, streak)

                st.markdown("---")
                st.markdown("### 📋 Evaluation Report")

                if score >= 8:   bc = "score-excellent"
                elif score >= 5: bc = "score-good"
                else:            bc = "score-low"
                st.markdown(f'<span class="score-badge {bc}">Score: {score}/10</span>', unsafe_allow_html=True)

                sm = re.search(r'STRENGTHS:\s*(.*?)(?=IMPROVEMENTS:|Score:|$)', feedback, re.S)
                im = re.search(r'IMPROVEMENTS:\s*(.*?)(?=Score:|$)', feedback, re.S)
                if sm:
                    st.markdown(f'<div class="feedback-block fb-strength">✅ <b>Strengths</b><br>{sm.group(1).strip()}</div>', unsafe_allow_html=True)
                if im:
                    st.markdown(f'<div class="feedback-block fb-improve">💡 <b>Improvements</b><br>{im.group(1).strip()}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="feedback-block fb-score">📊 <b>Final Score: {score}/10  →  +{reward} SC</b></div>', unsafe_allow_html=True)

                if reward > 0:
                    tick_streak()
                    topic_label = topic_tag or uploaded.name
                    h_entry = {
                        "topic": topic_label, "score": score, "reward": reward,
                        "persona": persona, "date": now_iso(),
                        "mode": "audio" if "Audio" in mode else "vision",
                    }
                    new_hist  = user_data.get('history', []) + [h_entry]
                    new_achs  = check_achievements(
                        {**user_data, 'coins': coins + reward},
                        new_hist, streak + 1
                    )
                    updates = {
                        'coins':            firestore.Increment(reward),
                        'weekly_sc':        firestore.Increment(reward),
                        'total_submissions':firestore.Increment(1),
                        'history':          firestore.ArrayUnion([h_entry]),
                        'submitted_hashes': firestore.ArrayUnion([file_hash]),
                    }
                    if new_achs:
                        updates['achievements'] = firestore.ArrayUnion([a['name'] for a in new_achs])
                    user_ref.update(updates)
                    st.cache_data.clear()
                    st.success(f"🪙 +{reward} SC awarded!")
                    for a in new_achs:
                        st.toast(f"🏅 Achievement unlocked: {a['name']}", icon="🏆")
                    st.balloons()

                # Topic suggestions
                if topic_tag:
                    st.markdown("---")
                    st.markdown("### 🔭 What to study next?")
                    try:
                        sg = client.chat.completions.create(
                            model=LLM,
                            messages=[{"role":"user","content":
                                f"Suggest 3 related topics to learn after studying '{topic_tag}'. "
                                f"Numbered list only. Max 6 words each."}],
                            temperature=0.7, max_tokens=80
                        )
                        st.markdown(sg.choices[0].message.content)
                    except: pass

            except Exception as e:
                st.error(f"⚠️ Error: {e}")

# ─────────────────────────────────────────
# TAB 1: COMMUNITY MARKETPLACE
# ─────────────────────────────────────────
with tabs[1]:
    st.markdown("## 🌐 Community Knowledge Market")
    st.caption("Uploaded by students. Bought with SC. Creators earn 30% royalty on every sale.")

    c_s, c_f1, c_f2 = st.columns([2,1,1])
    with c_s: sq = st.text_input("🔍 Search", placeholder="anatomy, ECG, pharmacology...")
    with c_f1: lf = st.multiselect("Level", ["Beginner","Intermediate","Advanced"])
    with c_f2: sb = st.selectbox("Sort", ["Newest","Popular","Top Rated","Price: Low","Price: High"])

    items = fetch_marketplace()
    filtered = [
        (nid, itm) for nid, itm in items
        if (not sq or sq.lower() in f"{itm.get('name','')} {itm.get('description','')} {' '.join(itm.get('tags',[]))}".lower())
        and (not lf or itm.get('level') in lf)
    ]
    if sb == "Popular":      filtered.sort(key=lambda x: x[1].get('purchases',0),   reverse=True)
    elif sb == "Top Rated":  filtered.sort(key=lambda x: x[1].get('avg_rating',0),  reverse=True)
    elif sb == "Price: Low": filtered.sort(key=lambda x: x[1].get('price',0))
    elif sb == "Price: High":filtered.sort(key=lambda x: x[1].get('price',0),       reverse=True)
    else:                    filtered.sort(key=lambda x: x[1].get('published',''),   reverse=True)

    if not filtered:
        st.info("No materials yet — be the first to upload something valuable!")

    for nid, itm in filtered:
        with st.container(border=True):
            ca, cb, cc = st.columns([3,1,1])
            with ca:
                st.markdown(f"### {itm.get('name','Untitled')}")
                st.caption(itm.get('description',''))
                if itm.get('tags'):
                    st.markdown(" ".join(
                        f'<span style="background:#0c2340;color:#60a5fa;padding:2px 8px;border-radius:10px;font-size:.76em">{t}</span>'
                        for t in itm.get('tags',[]) if t
                    ), unsafe_allow_html=True)
                uname = itm.get('uploader_name', 'Community')
                st.markdown(
                    f'<span class="uploader-badge">👤 {uname}</span>  '
                    f'<span class="royalty-badge">💸 Creator earns 30% royalty</span>',
                    unsafe_allow_html=True
                )
            with cb:
                lvl_icons = {"Beginner":"🟢","Intermediate":"🟡","Advanced":"🔴"}
                st.markdown(f"**{lvl_icons.get(itm.get('level',''),'⚪')} {itm.get('level','')}**")
                ar = itm.get('avg_rating', 0)
                st.markdown(f"⭐ {ar:.1f} ({itm.get('review_count',0)})")
                st.caption(f"👥 {itm.get('purchases',0)} bought")
            with cc:
                st.markdown(f"## {itm.get('price',0)} SC")
                purchased = nid in user_data.get('purchased', [])
                is_mine   = itm.get('uploader') == user_email
                if is_mine:
                    st.caption("📤 Your upload")
                elif purchased:
                    st.success("✅ Owned")
                else:
                    can_afford = coins >= itm.get('price', 0)
                    if st.button(f"🔓 Buy", key=f"buy_{nid}", disabled=not can_afford, use_container_width=True):
                        user_ref.update({
                            'coins': firestore.Increment(-itm['price']),
                            'purchased': firestore.ArrayUnion([nid]),
                        })
                        royalty = max(1, int(itm['price'] * 0.30))
                        if itm.get('uploader'):
                            db.collection('students').document(itm['uploader']).update({
                                'coins': firestore.Increment(royalty),
                                'total_royalties': firestore.Increment(royalty),
                            })
                        db.collection('community_materials').document(nid).update(
                            {'purchases': firestore.Increment(1)}
                        )
                        st.cache_data.clear()
                        st.rerun()
                    if not can_afford:
                        st.caption(f"Need {itm['price']-coins} more SC")

            # Content viewer
            if purchased or is_mine:
                with st.expander("📖 View Content"):
                    utype, eurl = detect_url(itm.get('link',''))
                    if utype == "YouTube":
                        st.video(eurl)
                    else:
                        st.components.v1.iframe(eurl, height=520, scrolling=True)

                    # Rating
                    if not is_mine:
                        existing_rev = next((r for r in itm.get('reviews',[]) if r.get('reviewer')==user_email), None)
                        if not existing_rev:
                            st.markdown("**Rate this material**")
                            rating = st.slider("Stars", 1, 5, 4, key=f"rat_{nid}")
                            rtext  = st.text_input("Review (optional)", key=f"rtxt_{nid}", max_chars=120)
                            if st.button("Submit Rating", key=f"srat_{nid}"):
                                nr      = {'reviewer':user_email,'reviewer_name':dname,'rating':rating,'text':rtext,'date':now_iso()}
                                all_r   = itm.get('reviews',[]) + [nr]
                                avg_r   = sum(x['rating'] for x in all_r) / len(all_r)
                                db.collection('community_materials').document(nid).update({
                                    'reviews': firestore.ArrayUnion([nr]),
                                    'avg_rating': round(avg_r, 2),
                                    'review_count': len(all_r),
                                })
                                st.cache_data.clear()
                                st.rerun()
                        else:
                            st.caption(f"Your rating: {'⭐'*existing_rev.get('rating',0)}")

            elif itm.get('preview_link'):
                with st.expander("👁️ Free Preview"):
                    _, pe = detect_url(itm['preview_link'])
                    st.components.v1.iframe(pe, height=280, scrolling=True)

            if itm.get('reviews'):
                with st.expander(f"💬 Reviews ({itm.get('review_count',0)})"):
                    for rv in itm.get('reviews',[])[-5:]:
                        st.markdown(f"**{'⭐'*rv.get('rating',0)}** — {rv.get('reviewer_name','?')} · *{rv.get('text','')}*")

            if purchased and not is_mine:
                with st.expander("🚩 Report Issue"):
                    issue = st.text_input("Describe the problem", key=f"iss_{nid}")
                    if st.button("Submit Report", key=f"rep_{nid}"):
                        db.collection('reports').add({
                            'material_id': nid, 'material_name': itm.get('name'),
                            'reporter': user_email, 'issue': issue,
                            'date': now_iso(), 'resolved': False,
                        })
                        st.success("Reported. Admin will review and may refund.")

# ─────────────────────────────────────────
# TAB 2: MY UPLOADS / CREATOR DASHBOARD
# ─────────────────────────────────────────
with tabs[2]:
    st.markdown("## 📤 Creator Dashboard")
    st.caption("Upload knowledge. Earn 30% royalty on every sale. Community votes on quality.")

    my_ups    = fetch_my_uploads(user_email)
    t_sales   = sum(d.get('purchases',0) for _,d in my_ups)
    t_royal   = user_data.get('total_royalties', 0)
    avg_rat   = (sum(d.get('avg_rating',0) for _,d in my_ups) / max(len(my_ups),1))

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("📦 Uploads",    len(my_ups))
    c2.metric("💸 Sales",       t_sales)
    c3.metric("💰 Royalties",  f"{t_royal} SC")
    c4.metric("⭐ Avg Rating",  f"{avg_rat:.1f}/5")

    st.markdown("---")
    ut1, ut2, ut3 = st.tabs(["➕ New Upload", "📋 Manage My Materials", "📄 Bulk CSV"])

    # ── New Upload ──
    with ut1:
        url_in = st.text_input("🔗 Content URL", placeholder="Google Drive, YouTube, or PDF URL...")
        if url_in:
            utype, eurl = detect_url(url_in)
            st.markdown(f'<span class="uploader-badge">{utype} detected</span>', unsafe_allow_html=True)
            with st.expander("👁️ Live Preview before submitting"):
                if utype == "YouTube":
                    st.video(eurl)
                else:
                    st.components.v1.iframe(eurl, height=300, scrolling=True)

        ca2, cb2 = st.columns(2)
        with ca2:
            mn  = st.text_input("Material Title")
            mpr = st.number_input("Price (SC)", min_value=10, max_value=1000, step=10, value=50)
            md  = st.text_area("Description (max 150 chars)", max_chars=150)
        with cb2:
            ml  = st.selectbox("Difficulty", ["Beginner","Intermediate","Advanced"])
            ms  = st.selectbox("Subject", ["Anatomy","Physiology","Pharmacology","Pathology","Biochemistry","Microbiology","Other"])
            mta = st.text_input("Tags (comma-separated)")
            mpv = st.text_input("Free Preview URL (optional)", placeholder="First page/section only")

        st.info("📋 All uploads go to community review before going live. Usually within 24 hours.")
        if st.button("🚀 Submit for Community Review", use_container_width=True):
            if not url_in or not mn:
                st.error("URL and title are required.")
            else:
                _, final_embed = detect_url(url_in)
                db.collection('community_materials').add({
                    'name': mn, 'price': mpr, 'link': final_embed,
                    'original_url': url_in, 'description': md,
                    'level': ml, 'subject': ms,
                    'tags': [t.strip() for t in mta.split(',') if t.strip()],
                    'preview_link': mpv, 'uploader': user_email,
                    'uploader_name': dname, 'status': 'pending',
                    'published': now_iso(), 'purchases': 0,
                    'avg_rating': 0, 'review_count': 0, 'reviews': [],
                    'votes_up': 0, 'votes_down': 0,
                    'url_type': detect_url(url_in)[0],
                })
                user_ref.update({'total_uploads': firestore.Increment(1)})
                st.cache_data.clear()
                st.success("✅ Submitted! Community will review within 24 hours.")

    # ── Manage ──
    with ut2:
        if not my_ups:
            st.info("No uploads yet. Use 'New Upload' tab to get started.")
        for nid, itm in my_ups:
            with st.container(border=True):
                ca3, cb3, cc3 = st.columns([3,1.5,1.2])
                with ca3:
                    sc_map = {'approved':'🟢','pending':'🟡','rejected':'🔴','archived':'⚫'}
                    st.markdown(f"**{itm.get('name','?')}** {sc_map.get(itm.get('status',''),'⚪')} {itm.get('status','').capitalize()}")
                    st.caption(f"{itm.get('level','')} · {itm.get('subject','')} · {itm.get('price',0)} SC")
                with cb3:
                    earned = int(itm.get('purchases',0) * itm.get('price',0) * 0.3)
                    st.markdown(f"💸 {itm.get('purchases',0)} sales · **+{earned} SC** earned")
                    st.markdown(f"⭐ {itm.get('avg_rating',0):.1f} ({itm.get('review_count',0)} reviews)")
                with cc3:
                    if st.button("✏️ Edit", key=f"ed_{nid}"):
                        st.session_state[f"editing_{nid}"] = True
                    if st.button("🗑️ Archive", key=f"ar_{nid}"):
                        db.collection('community_materials').document(nid).update({'status':'archived'})
                        st.cache_data.clear(); st.rerun()

                if st.session_state.get(f"editing_{nid}"):
                    with st.form(key=f"ef_{nid}"):
                        en  = st.text_input("Title",       value=itm.get('name',''))
                        ep  = st.number_input("Price",     value=itm.get('price',50), min_value=10, step=10)
                        ede = st.text_area("Description",  value=itm.get('description',''))
                        epv = st.text_input("Preview URL", value=itm.get('preview_link',''))
                        if st.form_submit_button("💾 Save Changes"):
                            db.collection('community_materials').document(nid).update(
                                {'name':en,'price':ep,'description':ede,'preview_link':epv}
                            )
                            st.session_state.pop(f"editing_{nid}", None)
                            st.cache_data.clear(); st.rerun()

    # ── Bulk CSV ──
    with ut3:
        st.markdown("### Bulk Upload via CSV")
        st.markdown("""**Columns:** `name, price, url, description, level, subject, tags, preview_url`

```
Cardiac Anatomy,200,https://drive.google.com/...,Deep heart anatomy,Advanced,Anatomy,heart;cardiology,
ECG Basics,75,https://youtu.be/...,Beginner ECG,Beginner,Cardiology,ECG;basics,https://...
```""")
        csv_file = st.file_uploader("Upload CSV", type=['csv'])
        if csv_file:
            try:
                reader = csv_mod.DictReader(io.StringIO(csv_file.getvalue().decode()))
                rows   = list(reader)
                valid, errors = [], []
                for i, row in enumerate(rows):
                    if not row.get('name') or not row.get('url'):
                        errors.append(f"Row {i+1}: missing name or URL")
                    else:
                        valid.append(row)
                st.markdown(f"**{len(valid)} valid / {len(errors)} errors**")
                for v in valid[:3]:
                    st.markdown(f"✅ **{v.get('name')}** — {v.get('url','')[:50]}...")
                for e in errors:
                    st.markdown(f"❌ {e}")
                if valid and st.button(f"🚀 Submit {len(valid)} valid rows"):
                    for row in valid:
                        _, embed = detect_url(row.get('url',''))
                        db.collection('community_materials').add({
                            'name':         row.get('name',''),
                            'price':        int(row.get('price',50)),
                            'link':         embed,
                            'original_url': row.get('url',''),
                            'description':  row.get('description',''),
                            'level':        row.get('level','Intermediate'),
                            'subject':      row.get('subject','Other'),
                            'tags':         [t.strip() for t in row.get('tags','').split(';') if t.strip()],
                            'preview_link': row.get('preview_url',''),
                            'uploader':     user_email,
                            'uploader_name': dname,
                            'status':       'pending',
                            'published':    now_iso(),
                            'purchases':    0, 'avg_rating':0,
                            'review_count': 0, 'reviews': [],
                        })
                    user_ref.update({'total_uploads': firestore.Increment(len(valid))})
                    st.cache_data.clear()
                    st.success(f"✅ {len(valid)} materials submitted for review!")
            except Exception as e:
                st.error(f"CSV parse error: {e}")

# ─────────────────────────────────────────
# TAB 3: HISTORY
# ─────────────────────────────────────────
with tabs[3]:
    st.markdown("## 📜 Mastery Timeline")
    history = user_data.get('history', [])
    if not history:
        st.info("No submissions yet. Head to the Studio!")
    else:
        try: hist_s = sorted(history, key=lambda x: x.get('date',''), reverse=True)
        except: hist_s = history[::-1]
        st.caption(f"{len(hist_s)} total submissions")
        for entry in hist_s:
            sc = entry.get('score', 0)
            rw = entry.get('reward', 0)
            try: df2 = datetime.fromisoformat(entry.get('date','')).strftime("%b %d, %Y %H:%M")
            except: df2 = entry.get('date','')[:16]
            with st.container(border=True):
                c1,c2,c3,c4 = st.columns([3,1,1,1])
                with c1:
                    ic = "🎙️" if entry.get('mode')=='audio' else "📸"
                    st.markdown(f"**{ic} {entry.get('topic','Untitled')}**")
                    st.caption(f"{entry.get('persona','—')}  ·  {df2}")
                with c2:
                    cl = "🟢" if sc>=8 else "🟡" if sc>=5 else "🔴"
                    st.markdown(f"**{cl} {sc}/10**")
                with c3:
                    st.markdown(f"**+{rw} SC**")
                with c4:
                    if st.button("🔁", key=f"re_{entry.get('date',sc)}", help="Practice again"):
                        st.info(f"Re-practice: **{entry.get('topic','')}**")

# ─────────────────────────────────────────
# TAB 4: ANALYTICS
# ─────────────────────────────────────────
with tabs[4]:
    st.markdown("## 📊 Personal Analytics")
    history = user_data.get('history', [])
    if len(history) < 2:
        st.info("Submit at least 2 evaluations to unlock analytics.")
    else:
        import pandas as pd
        scores  = [e.get('score',0)  for e in history if 'score'  in e]
        rewards = [e.get('reward',0) for e in history if 'reward' in e]

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Avg Score",   f"{sum(scores)/len(scores):.1f}/10")
        c2.metric("Best Score",  f"{max(scores)}/10")
        c3.metric("Total SC",    f"{sum(rewards)} SC")
        c4.metric("Submissions", len(history))
        c5.metric("This Week",   f"{weekly_sc} SC")

        try:
            sh = sorted(history, key=lambda x: x.get('date',''))
            df3 = pd.DataFrame({'Sub': range(1,len(sh)+1), 'Score': [e.get('score',0) for e in sh]})
            st.markdown("### Score Trajectory")
            st.line_chart(df3.set_index('Sub')['Score'])
        except: pass

        st.markdown("### Performance by Persona")
        ps = defaultdict(list)
        for e in history:
            if 'persona' in e and 'score' in e:
                ps[e['persona'].split('(')[0].strip()].append(e['score'])
        for p, s in ps.items():
            avg2 = sum(s)/len(s)
            st.markdown(f"**{p}** — {avg2:.1f}/10 over {len(s)} attempts")
            st.progress(avg2/10)

        st.markdown("### Topics Practiced")
        tc = defaultdict(int)
        for e in history:
            if e.get('topic'): tc[e['topic']] += 1
        if tc:
            top = sorted(tc.items(), key=lambda x: x[1], reverse=True)[:8]
            df4 = pd.DataFrame(top, columns=['Topic','Count'])
            st.bar_chart(df4.set_index('Topic'))

# ─────────────────────────────────────────
# TAB 5: ADMIN (admin only)
# ─────────────────────────────────────────
if is_admin:
    with tabs[5]:
        st.markdown("## 🛠️ Admin Console")
        st.caption("Reduced role: moderation queue, dispute resolution, user management only.")

        at1, at2, at3 = st.tabs(["📋 Review Queue", "🚩 Reports", "👥 Users"])

        with at1:
            pending = fetch_pending()
            st.markdown(f"**{len(pending)} materials awaiting review**")
            if not pending: st.success("All clear!")
            for pid, pitm in pending:
                with st.container(border=True):
                    st.markdown(f"**{pitm.get('name')}** — by *{pitm.get('uploader_name','?')}*")
                    st.caption(f"{pitm.get('level','')} · {pitm.get('subject','')} · {pitm.get('price',0)} SC")
                    st.write(pitm.get('description',''))
                    if pitm.get('link'):
                        with st.expander("Preview"):
                            _, pe2 = detect_url(pitm['link'])
                            st.components.v1.iframe(pe2, height=280, scrolling=True)
                    ca4,cb4,cc4 = st.columns(3)
                    with ca4:
                        if st.button("✅ Approve", key=f"ap_{pid}"):
                            db.collection('community_materials').document(pid).update({'status':'approved'})
                            st.cache_data.clear(); st.rerun()
                    with cb4:
                        if st.button("❌ Reject", key=f"rj_{pid}"):
                            db.collection('community_materials').document(pid).update({'status':'rejected'})
                            st.cache_data.clear(); st.rerun()
                    with cc4:
                        if st.button("🗑️ Delete", key=f"dl_{pid}"):
                            db.collection('community_materials').document(pid).delete()
                            st.cache_data.clear(); st.rerun()

        with at2:
            reps = [(r.id, r.to_dict()) for r in db.collection('reports').where('resolved','==',False).stream()]
            st.markdown(f"**{len(reps)} unresolved reports**")
            for rid, rep in reps:
                with st.container(border=True):
                    st.markdown(f"**{rep.get('material_name','?')}** — reported by {rep.get('reporter','?')}")
                    st.write(rep.get('issue',''))
                    ca5, cb5 = st.columns(2)
                    with ca5:
                        if st.button("✅ Resolve + Refund buyer", key=f"res_{rid}"):
                            mat = db.collection('community_materials').document(rep.get('material_id','')).get()
                            if mat.exists:
                                price = mat.to_dict().get('price', 0)
                                db.collection('students').document(rep['reporter']).update(
                                    {'coins': firestore.Increment(price)}
                                )
                            db.collection('reports').document(rid).update({'resolved': True})
                            st.cache_data.clear(); st.rerun()
                    with cb5:
                        if st.button("❌ Dismiss", key=f"dis_{rid}"):
                            db.collection('reports').document(rid).update({'resolved': True})
                            st.cache_data.clear(); st.rerun()

        with at3:
            total_members = len(list(db.collection('students').stream()))
            st.metric("Total Community Members", total_members)
            tgt = st.text_input("Target user email")
            c1,c2,c3 = st.columns(3)
            with c1:
                bonus2 = st.number_input("Grant SC", min_value=0, step=50)
                if st.button("Grant") and tgt:
                    db.collection('students').document(tgt).update({'coins': firestore.Increment(bonus2)})
                    st.success(f"+{bonus2} SC granted.")
            with c2:
                if st.button("Reset User") and tgt:
                    db.collection('students').document(tgt).update(
                        {'coins':0,'history':[],'purchased':[],'streak':0}
                    )
                    st.success("Reset done.")
            with c3:
                if st.button("Ban User") and tgt:
                    db.collection('students').document(tgt).update({'banned': True})
                    st.warning(f"Banned: {tgt}")
