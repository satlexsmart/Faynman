"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         SATLEX COMMUNITY V4 — Decentralized Knowledge Economy               ║
║         Pure Mathematics • Cryptography • Community Consensus               ║
║         No Admins. No Passwords. No Central Authority.                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

Architecture inspired by:
  - Bitcoin's UTXO model (seed-phrase identity)
  - Uniswap's AMM (algorithmic treasury management)
  - Eigenlayer's restaking (reputation as economic stake)

Run:
    pip install streamlit firebase-admin mnemonic streamlit-webrtc aiortc
    streamlit run satlex_community_v4.py
"""

import streamlit as st
import hashlib
import hmac
import json
import time
import uuid
import random
import string
import base64
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# ── Groq AI Engine (Whisper + LLaMA + Vision) ─────────────────────────────────
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# ── Cryptographic identity layer ──────────────────────────────────────────────
try:
    from mnemonic import Mnemonic
    MNEMONIC_AVAILABLE = True
except ImportError:
    MNEMONIC_AVAILABLE = False

# ── Firebase / Firestore ───────────────────────────────────────────────────────
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# ── WebRTC for peer-to-peer video ─────────────────────────────────────────────
try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
    import av
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 0: PAGE CONFIG & GLOBAL CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Satlex Community V4",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Tokenomics constants — immutable once deployed (like Bitcoin's 21M cap)
HARD_CAP_SC          = 1_000_000      # Maximum Satlex Coins ever
JOINING_BONUS_SC     = 50             # Dispensed from Treasury on signup
CREATOR_SHARE_PCT    = 0.30           # 30% to creator on sale
TREASURY_SHARE_PCT   = 0.70           # 70% back to treasury
CONSENSUS_THRESHOLD  = 10             # Genuine User flags needed for takedown
GENUINE_DAILY_HELPS  = 10            # Minimum daily helps for Genuine User
GENUINE_STAR_RATIO   = 0.70          # 70% of answers must be 5-star
AI_REWARD_POOL_PCT   = 0.05          # Feynman AI draws from 5% of treasury

# ICE servers for WebRTC (STUN = like echolocation for finding your network path)
RTC_CONFIG = RTCConfiguration(
    iceServers=[
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
        {"urls": ["stun:stun2.l.google.com:19302"]},
    ]
)

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 1: CRYPTOGRAPHIC IDENTITY ENGINE
#  (The Bitcoin Model — your seed IS your key, your key IS your identity)
# ═══════════════════════════════════════════════════════════════════════════════

class CryptoIdentity:
    """
    Deterministic identity derived purely from entropy.
    
    Analogous to how a protein's entire 3D structure is determined by its
    amino acid sequence — your entire digital identity here is determined
    by 12 words chosen from 2048 possibilities (128 bits of entropy).
    """
    
    @staticmethod
    def generate_mnemonic() -> str:
        """Generate BIP-39 compatible 12-word mnemonic (128-bit entropy)."""
        if MNEMONIC_AVAILABLE:
            mnemo = Mnemonic("english")
            return mnemo.generate(strength=128)
        # Fallback: use cryptographically secure random words
        # (In production, use proper BIP-39 wordlist)
        wordlist = [
            "abandon", "ability", "able", "about", "above", "absent", "absorb",
            "abstract", "absurd", "abuse", "access", "accident", "account", "accuse",
            "achieve", "acid", "acoustic", "acquire", "across", "act", "action",
            "actor", "actress", "actual", "adapt", "add", "addict", "address",
            "adjust", "admit", "adult", "advance", "advice", "aerobic", "afford",
            "afraid", "again", "age", "agent", "agree", "ahead", "aim", "air",
            "airport", "aisle", "alarm", "album", "alcohol", "alert", "alien",
            "alley", "allow", "almost", "alone", "alpha", "already", "also",
            "alter", "always", "amateur", "amazing", "among", "amount", "amused",
            "analyst", "anchor", "ancient", "anger", "angle", "angry", "animal",
            "ankle", "announce", "annual", "another", "answer", "antenna", "antique",
            "anxiety", "any", "apart", "apology", "apple", "approve", "april",
            "arcade", "arctic", "argue", "arm", "armed", "armor", "army", "around",
            "arrange", "arrest", "arrive", "arrow", "art", "artefact", "artist",
            "artwork", "ask", "aspect", "assault", "asset", "assist", "assume",
            "asthma", "athlete", "atom", "attack", "attend", "attitude", "attract",
            "auction", "audit", "august", "aunt", "author", "auto", "autumn",
            "average", "avocado", "avoid", "awake", "aware", "away", "awesome",
            "awful", "awkward", "axis", "baby", "balance", "bamboo", "banana"
        ]
        import secrets
        return " ".join(secrets.choice(wordlist) for _ in range(12))
    
    @staticmethod
    def derive_room_id(seed_phrase: str) -> str:
        """
        Deterministic hash: seed → Room ID.
        Like SHA256 in Bitcoin: one-way, collision-resistant.
        The same 12 words always produce the same Room ID.
        """
        # Double SHA-256 (Bitcoin uses this for extra collision resistance)
        first_hash  = hashlib.sha256(seed_phrase.strip().lower().encode()).hexdigest()
        second_hash = hashlib.sha256(first_hash.encode()).hexdigest()
        # Take first 8 chars of hex → encode to base-36 style alphanumeric
        room_hex    = second_hash[:16].upper()
        return f"SAT-{room_hex[:4]}-{room_hex[4:8]}-{room_hex[8:12]}"
    
    @staticmethod
    def verify_seed(seed_phrase: str, room_id: str) -> bool:
        """Zero-knowledge style verification: prove you own the seed without revealing it."""
        return CryptoIdentity.derive_room_id(seed_phrase) == room_id


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 2: FIREBASE / FIRESTORE DATA LAYER
#  (Think of Firestore as the distributed ledger — shared state across all nodes)
# ═══════════════════════════════════════════════════════════════════════════════

class FirestoreDB:
    """
    Firestore wrapper. Each document is like a quantum state —
    it exists in superposition until observed (read) by a client.
    
    Collection schema:
      users/{room_id}           — User profiles & wallets
      marketplace/{item_id}     — Listed content
      doubts/{doubt_id}         — Questions & answers
      chats/{chat_id}           — DM threads
      messages/{msg_id}         — Individual messages
      system/treasury           — Global token supply ledger
    """
    
    _db = None  # Singleton connection
    
    @classmethod
    def get_db(cls):
        if cls._db is not None:
            return cls._db
        
        if not FIREBASE_AVAILABLE:
            return None
            
        if not firebase_admin._apps:
            # ── HOW TO CONFIGURE FIREBASE ────────────────────────────────────
            # Option A (Recommended): Store credentials in Streamlit Secrets
            #   In .streamlit/secrets.toml:
            #     [firebase]
            #     type = "service_account"
            #     project_id = "your-project-id"
            #     private_key_id = "..."
            #     private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
            #     client_email = "..."
            #     ... (rest of service account JSON fields)
            #
            # Option B: Point to a local service account JSON file:
            #   cred = credentials.Certificate("path/to/serviceAccountKey.json")
            # ────────────────────────────────────────────────────────────────
            try:
                if "firebase" in st.secrets:
                    firebase_config = dict(st.secrets["firebase"])
                    firebase_config["private_key"] = firebase_config["private_key"].replace("\\n", "\n")
                    cred = credentials.Certificate(firebase_config)
                else:
                    # Fallback: look for local file
                    import os
                    key_path = os.environ.get("FIREBASE_KEY_PATH", "serviceAccountKey.json")
                    cred = credentials.Certificate(key_path)
                
                firebase_admin.initialize_app(cred)
                cls._db = firestore.client()
                
                # Ensure treasury document exists (genesis block equivalent)
                cls._ensure_treasury(cls._db)
                
            except Exception as e:
                st.warning(f"⚠️ Firebase not configured. Running in Demo Mode. Error: {e}")
                return None
        else:
            cls._db = firestore.client()
        
        return cls._db
    
    @staticmethod
    def _ensure_treasury(db):
        """Create treasury document if it doesn't exist — like mining the genesis block."""
        treasury_ref = db.collection("system").document("treasury")
        if not treasury_ref.get().exists:
            treasury_ref.set({
                "total_supply": HARD_CAP_SC,
                "circulating": 0,
                "treasury_balance": HARD_CAP_SC,
                "total_transactions": 0,
                "created_at": firestore.SERVER_TIMESTAMP,
                "genesis_hash": hashlib.sha256(b"satlex_genesis_v4").hexdigest()
            })


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 3: IN-MEMORY DEMO STATE
#  (When Firebase is unavailable — a simulated blockchain in RAM)
# ═══════════════════════════════════════════════════════════════════════════════

def init_demo_state():
    """Initialize demo state — think of it as a local blockchain simulation."""
    if "demo_db" not in st.session_state:
        st.session_state.demo_db = {
            "users": {},
            "marketplace": {},
            "doubts": {},
            "chats": {},
            "messages": {},
            "treasury": {
                "total_supply": HARD_CAP_SC,
                "circulating": 1500,
                "treasury_balance": HARD_CAP_SC - 1500,
                "total_transactions": 30,
            }
        }
        # Seed some demo users (like pre-mined coins in testnet)
        _seed_demo_data()


def _seed_demo_data():
    """Populate demo environment with sample data."""
    db = st.session_state.demo_db
    
    demo_users = [
        {
            "room_id": "SAT-A1B2-C3D4-E5F6",
            "username": "QuantumLeap",
            "bio": "Physics PhD. Obsessed with topological insulators.",
            "wallet_sc": 450,
            "total_helped": 34,
            "avg_rating": 4.8,
            "followers": [],
            "following": [],
            "friends": [],
            "joined": "2025-01-15",
            "daily_helps_today": 12,
            "five_star_count": 28,
            "total_ratings": 32,
        },
        {
            "room_id": "SAT-7G8H-I9J0-K1L2",
            "username": "NeuralNomad",
            "bio": "ML researcher. Coffee-driven gradient descent.",
            "wallet_sc": 820,
            "total_helped": 67,
            "avg_rating": 4.9,
            "followers": [],
            "following": [],
            "friends": [],
            "joined": "2025-02-01",
            "daily_helps_today": 15,
            "five_star_count": 63,
            "total_ratings": 67,
        },
        {
            "room_id": "SAT-M3N4-O5P6-Q7R8",
            "username": "FractalMind",
            "bio": "Math teacher. Turning chaos into understanding.",
            "wallet_sc": 230,
            "total_helped": 18,
            "avg_rating": 4.5,
            "followers": [],
            "following": [],
            "friends": [],
            "joined": "2025-03-10",
            "daily_helps_today": 7,
            "five_star_count": 11,
            "total_ratings": 18,
        },
    ]
    
    for u in demo_users:
        db["users"][u["room_id"]] = u
    
    # Seed marketplace items
    demo_items = [
        {
            "id": "item_001",
            "title": "Advanced Quantum Mechanics Notes",
            "description": "Comprehensive handwritten notes on perturbation theory, variational methods, and path integrals. Covers Griffiths chapters 6-11.",
            "price_sc": 50,
            "creator_id": "SAT-A1B2-C3D4-E5F6",
            "creator_name": "QuantumLeap",
            "category": "Physics",
            "tags": ["quantum", "mechanics", "university"],
            "buyers": [],
            "flags": [],
            "status": "active",
            "created_at": "2025-03-01",
            "content_url": "https://example.com/notes/qm",
            "thumbnail": "🔬",
        },
        {
            "id": "item_002",
            "title": "Transformer Architecture Deep Dive",
            "description": "From self-attention to RLHF. Visual explanations with PyTorch code walkthroughs.",
            "price_sc": 80,
            "creator_id": "SAT-7G8H-I9J0-K1L2",
            "creator_name": "NeuralNomad",
            "category": "AI/ML",
            "tags": ["transformer", "attention", "NLP"],
            "buyers": [],
            "flags": [],
            "status": "active",
            "created_at": "2025-03-05",
            "content_url": "https://example.com/notes/transformer",
            "thumbnail": "🤖",
        },
        {
            "id": "item_003",
            "title": "Real Analysis — Epsilon-Delta Mastery",
            "description": "Every proof technique you need. Limits, continuity, compactness, and metric spaces.",
            "price_sc": 40,
            "creator_id": "SAT-M3N4-O5P6-Q7R8",
            "creator_name": "FractalMind",
            "category": "Mathematics",
            "tags": ["analysis", "proofs", "calculus"],
            "buyers": [],
            "flags": [],
            "status": "active",
            "created_at": "2025-03-12",
            "content_url": "https://example.com/notes/real-analysis",
            "thumbnail": "∞",
        },
    ]
    
    for item in demo_items:
        db["marketplace"][item["id"]] = item
    
    # Seed doubts
    demo_doubts = [
        {
            "id": "doubt_001",
            "asker_id": "SAT-M3N4-O5P6-Q7R8",
            "asker_name": "FractalMind",
            "question": "Why does the Fourier transform of a Gaussian remain a Gaussian? Is there a deep reason or just algebraic coincidence?",
            "subject": "Mathematics / Signal Processing",
            "answers": [
                {
                    "id": "ans_001a",
                    "solver_id": "SAT-A1B2-C3D4-E5F6",
                    "solver_name": "QuantumLeap",
                    "text": "It's deeply non-coincidental! The Gaussian is the eigenfunction of the Fourier transform operator. The transform operator F satisfies F⁴ = Identity. The Gaussian happens to be the eigenfunction with eigenvalue 1. This also connects to quantum mechanics — the coherent states of the harmonic oscillator are Gaussians precisely because uncertainty is minimized (ΔxΔp = ℏ/2).",
                    "stars": 5,
                    "tip_sc": 10,
                    "rated": True,
                    "timestamp": "2025-03-15 10:32",
                }
            ],
            "status": "answered",
            "created_at": "2025-03-15 09:00",
        },
        {
            "id": "doubt_002",
            "asker_id": "SAT-7G8H-I9J0-K1L2",
            "asker_name": "NeuralNomad",
            "question": "What's the mathematical intuition behind why dropout acts as a regularizer? I understand it prevents co-adaptation but why does that generalize?",
            "subject": "Machine Learning",
            "answers": [],
            "status": "open",
            "created_at": "2025-03-20 14:00",
        },
    ]
    
    for d in demo_doubts:
        db["doubts"][d["id"]] = d


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 4: DATA ACCESS LAYER (DAL)
#  Unified interface — works with Firebase OR demo state
# ═══════════════════════════════════════════════════════════════════════════════

class DAL:
    """
    Data Access Layer: like a compiler that translates high-level operations
    into the correct low-level instructions for either Firebase or demo state.
    """
    
    @staticmethod
    def _use_firebase() -> bool:
        db = FirestoreDB.get_db()
        return db is not None
    
    # ── USER OPERATIONS ────────────────────────────────────────────────────────
    
    @staticmethod
    def get_user(room_id: str) -> Optional[Dict]:
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            doc = db.collection("users").document(room_id).get()
            return doc.to_dict() if doc.exists else None
        else:
            return st.session_state.demo_db["users"].get(room_id)
    
    @staticmethod
    def create_user(room_id: str, username: str) -> Dict:
        """Mint a new user — like creating a new wallet address on the blockchain."""
        new_user = {
            "room_id": room_id,
            "username": username,
            "bio": "",
            "wallet_sc": 0,
            "total_helped": 0,
            "avg_rating": 0.0,
            "followers": [],
            "following": [],
            "friends": [],
            "joined": datetime.now(timezone.utc).isoformat(),
            "daily_helps_today": 0,
            "five_star_count": 0,
            "total_ratings": 0,
            "photo_url": "",
            "last_active": datetime.now(timezone.utc).isoformat(),
        }
        
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("users").document(room_id).set(new_user)
        else:
            st.session_state.demo_db["users"][room_id] = new_user
        
        # Dispense joining bonus from treasury (like block reward)
        DAL.treasury_dispense(room_id, JOINING_BONUS_SC, "joining_bonus")
        return new_user
    
    @staticmethod
    def update_user(room_id: str, fields: Dict):
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("users").document(room_id).update(fields)
        else:
            if room_id in st.session_state.demo_db["users"]:
                st.session_state.demo_db["users"][room_id].update(fields)
    
    @staticmethod
    def delete_user(room_id: str):
        """Account burn — irreversible annihilation of identity."""
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("users").document(room_id).delete()
        else:
            st.session_state.demo_db["users"].pop(room_id, None)
    
    @staticmethod
    def get_all_users() -> List[Dict]:
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            return [doc.to_dict() for doc in db.collection("users").stream()]
        else:
            return list(st.session_state.demo_db["users"].values())
    
    # ── TREASURY OPERATIONS ────────────────────────────────────────────────────
    
    @staticmethod
    def get_treasury() -> Dict:
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            doc = db.collection("system").document("treasury").get()
            return doc.to_dict() if doc.exists else {}
        else:
            return st.session_state.demo_db["treasury"]
    
    @staticmethod
    def treasury_dispense(recipient_id: str, amount: int, reason: str) -> bool:
        """
        Dispense SC from treasury → user wallet.
        Like proof-of-work reward: treasury shrinks, circulating supply grows.
        """
        treasury = DAL.get_treasury()
        if treasury.get("treasury_balance", 0) < amount:
            return False
        
        user = DAL.get_user(recipient_id)
        if not user:
            return False
        
        new_balance     = user.get("wallet_sc", 0) + amount
        new_treasury    = treasury["treasury_balance"] - amount
        new_circulating = treasury["circulating"] + amount
        
        DAL.update_user(recipient_id, {"wallet_sc": new_balance})
        
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("system").document("treasury").update({
                "treasury_balance": new_treasury,
                "circulating": new_circulating,
                "total_transactions": firestore.Increment(1),
            })
            # Log transaction
            db.collection("transactions").add({
                "type": "treasury_dispense",
                "recipient": recipient_id,
                "amount": amount,
                "reason": reason,
                "timestamp": firestore.SERVER_TIMESTAMP,
            })
        else:
            st.session_state.demo_db["treasury"]["treasury_balance"] = new_treasury
            st.session_state.demo_db["treasury"]["circulating"] = new_circulating
            st.session_state.demo_db["treasury"]["total_transactions"] += 1
        
        return True
    
    @staticmethod
    def peer_transfer(sender_id: str, recipient_id: str, amount: int, memo: str = "tip") -> bool:
        """
        P2P SC transfer — no intermediary, like a Bitcoin UTXO transfer.
        The sender's balance decreases, recipient's increases.
        """
        sender = DAL.get_user(sender_id)
        recipient = DAL.get_user(recipient_id)
        
        if not sender or not recipient:
            return False
        if sender.get("wallet_sc", 0) < amount:
            return False
        if amount <= 0:
            return False
        
        DAL.update_user(sender_id,    {"wallet_sc": sender["wallet_sc"] - amount})
        DAL.update_user(recipient_id, {"wallet_sc": recipient.get("wallet_sc", 0) + amount})
        
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("transactions").add({
                "type": "peer_transfer",
                "sender": sender_id,
                "recipient": recipient_id,
                "amount": amount,
                "memo": memo,
                "timestamp": firestore.SERVER_TIMESTAMP,
            })
        
        return True
    
    # ── MARKETPLACE OPERATIONS ─────────────────────────────────────────────────
    
    @staticmethod
    def get_all_items() -> List[Dict]:
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            return [doc.to_dict() for doc in db.collection("marketplace").where("status", "==", "active").stream()]
        else:
            return [i for i in st.session_state.demo_db["marketplace"].values() if i.get("status") == "active"]
    
    @staticmethod
    def get_item(item_id: str) -> Optional[Dict]:
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            doc = db.collection("marketplace").document(item_id).get()
            return doc.to_dict() if doc.exists else None
        else:
            return st.session_state.demo_db["marketplace"].get(item_id)
    
    @staticmethod
    def create_item(item_data: Dict) -> str:
        item_id = f"item_{uuid.uuid4().hex[:8]}"
        item_data["id"] = item_id
        item_data["buyers"] = []
        item_data["flags"] = []
        item_data["status"] = "active"
        item_data["created_at"] = datetime.now(timezone.utc).isoformat()
        
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("marketplace").document(item_id).set(item_data)
        else:
            st.session_state.demo_db["marketplace"][item_id] = item_data
        
        return item_id
    
    @staticmethod
    def purchase_item(buyer_id: str, item_id: str) -> tuple[bool, str]:
        """
        Execute purchase: split payment per tokenomics.
        30% → creator, 70% → treasury (deflationary pressure).
        """
        item   = DAL.get_item(item_id)
        buyer  = DAL.get_user(buyer_id)
        
        if not item or not buyer:
            return False, "Item or buyer not found"
        if item.get("status") != "active":
            return False, "Item is not available"
        if buyer_id in item.get("buyers", []):
            return False, "Already purchased"
        if buyer_id == item.get("creator_id"):
            return False, "Cannot buy your own content"
        
        price = item.get("price_sc", 0)
        if buyer.get("wallet_sc", 0) < price:
            return False, f"Insufficient SC. Need {price}, have {buyer.get('wallet_sc', 0)}"
        
        creator_cut  = int(price * CREATOR_SHARE_PCT)
        treasury_cut = price - creator_cut
        
        # Deduct from buyer
        DAL.update_user(buyer_id, {"wallet_sc": buyer["wallet_sc"] - price})
        
        # Pay creator
        creator = DAL.get_user(item["creator_id"])
        if creator:
            DAL.update_user(item["creator_id"], {
                "wallet_sc": creator.get("wallet_sc", 0) + creator_cut
            })
        
        # Treasury receives its 70%
        treasury = DAL.get_treasury()
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("system").document("treasury").update({
                "treasury_balance": firestore.Increment(treasury_cut),
                "total_transactions": firestore.Increment(1),
            })
            # Add buyer to item's buyer list
            db.collection("marketplace").document(item_id).update({
                "buyers": firestore.ArrayUnion([buyer_id])
            })
        else:
            st.session_state.demo_db["treasury"]["treasury_balance"] += treasury_cut
            st.session_state.demo_db["treasury"]["total_transactions"] += 1
            st.session_state.demo_db["marketplace"][item_id]["buyers"].append(buyer_id)
        
        return True, f"Purchase successful! Paid {price} SC"
    
    @staticmethod
    def flag_item(flagger_id: str, item_id: str) -> tuple[bool, str]:
        """
        Genuine User consensus moderation — like a blockchain fork vote.
        If 10 Genuine Users flag an item, auto-takedown triggers.
        """
        flagger = DAL.get_user(flagger_id)
        if not flagger:
            return False, "User not found"
        
        # Check Genuine User status
        daily_helps = flagger.get("daily_helps_today", 0)
        five_star   = flagger.get("five_star_count", 0)
        total_rat   = flagger.get("total_ratings", 1)
        star_ratio  = five_star / max(total_rat, 1)
        
        if daily_helps < GENUINE_DAILY_HELPS or star_ratio < GENUINE_STAR_RATIO:
            return False, "Only Genuine Users can flag content (need 10+ daily helps & 70%+ 5-star ratio)"
        
        item = DAL.get_item(item_id)
        if not item:
            return False, "Item not found"
        
        flags = item.get("flags", [])
        if flagger_id in flags:
            return False, "Already flagged by you"
        
        flags.append(flagger_id)
        
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("marketplace").document(item_id).update({
                "flags": firestore.ArrayUnion([flagger_id])
            })
        else:
            st.session_state.demo_db["marketplace"][item_id]["flags"] = flags
        
        # Consensus threshold reached → AUTO TAKEDOWN
        if len(flags) >= CONSENSUS_THRESHOLD:
            DAL._execute_takedown(item_id)
            return True, f"🚨 Consensus reached! Item auto-removed and buyers refunded."
        
        remaining = CONSENSUS_THRESHOLD - len(flags)
        return True, f"Flag recorded. {remaining} more Genuine User flags needed for takedown."
    
    @staticmethod
    def _execute_takedown(item_id: str):
        """
        Algorithmic takedown with smart refunds.
        Like a blockchain rollback — all SC transactions are reversed.
        """
        item = DAL.get_item(item_id)
        if not item:
            return
        
        price = item.get("price_sc", 0)
        
        # Refund all buyers (pull from creator wallet + treasury)
        for buyer_id in item.get("buyers", []):
            buyer = DAL.get_user(buyer_id)
            if buyer:
                DAL.update_user(buyer_id, {"wallet_sc": buyer.get("wallet_sc", 0) + price})
        
        # Mark item as taken down
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("marketplace").document(item_id).update({"status": "taken_down"})
        else:
            if item_id in st.session_state.demo_db["marketplace"]:
                st.session_state.demo_db["marketplace"][item_id]["status"] = "taken_down"
    
    # ── DOUBTS / Q&A ──────────────────────────────────────────────────────────
    
    @staticmethod
    def get_all_doubts() -> List[Dict]:
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            return [doc.to_dict() for doc in db.collection("doubts").order_by("created_at", direction=firestore.Query.DESCENDING).stream()]
        else:
            return sorted(
                st.session_state.demo_db["doubts"].values(),
                key=lambda x: x.get("created_at", ""), reverse=True
            )
    
    @staticmethod
    def post_doubt(asker_id: str, asker_name: str, question: str, subject: str) -> str:
        doubt_id = f"doubt_{uuid.uuid4().hex[:8]}"
        doubt = {
            "id": doubt_id,
            "asker_id": asker_id,
            "asker_name": asker_name,
            "question": question,
            "subject": subject,
            "answers": [],
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("doubts").document(doubt_id).set(doubt)
        else:
            st.session_state.demo_db["doubts"][doubt_id] = doubt
        
        return doubt_id
    
    @staticmethod
    def post_answer(doubt_id: str, solver_id: str, solver_name: str, answer_text: str) -> bool:
        answer = {
            "id": f"ans_{uuid.uuid4().hex[:6]}",
            "solver_id": solver_id,
            "solver_name": solver_name,
            "text": answer_text,
            "stars": 0,
            "tip_sc": 0,
            "rated": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("doubts").document(doubt_id).update({
                "answers": firestore.ArrayUnion([answer]),
                "status": "answered",
            })
        else:
            if doubt_id in st.session_state.demo_db["doubts"]:
                st.session_state.demo_db["doubts"][doubt_id]["answers"].append(answer)
                st.session_state.demo_db["doubts"][doubt_id]["status"] = "answered"
        
        # Update solver's helped count
        solver = DAL.get_user(solver_id)
        if solver:
            DAL.update_user(solver_id, {
                "total_helped": solver.get("total_helped", 0) + 1,
                "daily_helps_today": solver.get("daily_helps_today", 0) + 1,
            })
        
        return True
    
    @staticmethod
    def rate_answer(doubt_id: str, answer_id: str, stars: int, asker_id: str) -> bool:
        """Rate an answer — updates solver's reputation (their economic stake)."""
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            doubt_doc = db.collection("doubts").document(doubt_id).get()
            if not doubt_doc.exists:
                return False
            doubt = doubt_doc.to_dict()
            answers = doubt.get("answers", [])
            for ans in answers:
                if ans["id"] == answer_id and not ans.get("rated"):
                    ans["stars"] = stars
                    ans["rated"] = True
                    db.collection("doubts").document(doubt_id).update({"answers": answers})
                    # Update solver reputation
                    solver = DAL.get_user(ans["solver_id"])
                    if solver:
                        new_total = solver.get("total_ratings", 0) + 1
                        new_5star = solver.get("five_star_count", 0) + (1 if stars == 5 else 0)
                        new_avg   = ((solver.get("avg_rating", 0) * (new_total - 1)) + stars) / new_total
                        DAL.update_user(ans["solver_id"], {
                            "total_ratings": new_total,
                            "five_star_count": new_5star,
                            "avg_rating": round(new_avg, 2),
                        })
                    return True
        else:
            doubt = st.session_state.demo_db["doubts"].get(doubt_id)
            if not doubt:
                return False
            for ans in doubt.get("answers", []):
                if ans["id"] == answer_id and not ans.get("rated"):
                    ans["stars"] = stars
                    ans["rated"] = True
                    solver = DAL.get_user(ans["solver_id"])
                    if solver:
                        new_total = solver.get("total_ratings", 0) + 1
                        new_5star = solver.get("five_star_count", 0) + (1 if stars == 5 else 0)
                        new_avg   = ((solver.get("avg_rating", 0) * (new_total - 1)) + stars) / new_total
                        DAL.update_user(ans["solver_id"], {
                            "total_ratings": new_total,
                            "five_star_count": new_5star,
                            "avg_rating": round(new_avg, 2),
                        })
                    return True
        return False
    
    # ── MESSAGING / SOCIAL ─────────────────────────────────────────────────────
    
    @staticmethod
    def get_chat_id(user1: str, user2: str) -> str:
        """Deterministic chat ID from two room IDs (order-independent like XOR)."""
        return "chat_" + hashlib.md5((min(user1, user2) + max(user1, user2)).encode()).hexdigest()[:12]
    
    @staticmethod
    def send_message(sender_id: str, recipient_id: str, text: str) -> bool:
        chat_id = DAL.get_chat_id(sender_id, recipient_id)
        msg = {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "chat_id": chat_id,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False,
        }
        
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            db.collection("messages").add(msg)
        else:
            if "messages" not in st.session_state.demo_db:
                st.session_state.demo_db["messages"] = {}
            st.session_state.demo_db["messages"][msg["id"]] = msg
        
        return True
    
    @staticmethod
    def get_messages(user1: str, user2: str) -> List[Dict]:
        chat_id = DAL.get_chat_id(user1, user2)
        
        if DAL._use_firebase():
            db = FirestoreDB.get_db()
            msgs = db.collection("messages").where("chat_id", "==", chat_id).order_by("timestamp").stream()
            return [m.to_dict() for m in msgs]
        else:
            all_msgs = st.session_state.demo_db.get("messages", {}).values()
            return sorted(
                [m for m in all_msgs if m.get("chat_id") == chat_id],
                key=lambda x: x.get("timestamp", "")
            )
    
    @staticmethod
    def follow_user(follower_id: str, target_id: str) -> bool:
        follower = DAL.get_user(follower_id)
        target   = DAL.get_user(target_id)
        if not follower or not target:
            return False
        
        following = follower.get("following", [])
        followers = target.get("followers", [])
        
        if target_id not in following:
            following.append(target_id)
            followers.append(follower_id)
            DAL.update_user(follower_id, {"following": following})
            DAL.update_user(target_id, {"followers": followers})
        
        return True
    
    @staticmethod
    def add_friend(user1_id: str, user2_id: str) -> bool:
        """Bidirectional friend connection — like forming a covalent bond."""
        user1 = DAL.get_user(user1_id)
        user2 = DAL.get_user(user2_id)
        if not user1 or not user2:
            return False
        
        friends1 = user1.get("friends", [])
        friends2 = user2.get("friends", [])
        
        if user2_id not in friends1:
            friends1.append(user2_id)
            DAL.update_user(user1_id, {"friends": friends1})
        if user1_id not in friends2:
            friends2.append(user1_id)
            DAL.update_user(user2_id, {"friends": friends2})
        
        return True


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 5: FEYNMAN AI EVALUATION ENGINE
#  (Named after Richard Feynman's "if you can't explain it simply, you don't
#   understand it" — the best possible test of genuine comprehension)
# ═══════════════════════════════════════════════════════════════════════════════

class FeynmanAI:
    """
    Gold Logic Feynman AI Engine — powered by Groq's inference infrastructure.

    Pipeline (like signal transduction in a cell):
      Audio  → Whisper-large-v3-turbo (ASR) → transcript → LLaMA-3.3-70b
      Image  → base64 encode              → LLaMA-3.2-11b-vision-preview
      Text   → direct                     → LLaMA-3.3-70b-versatile

    The Persona system prompt acts as a transformer's attention mask —
    it gates which features of the explanation the model weighs most heavily.
    
    Score parsed from "Score: X/10" at end of LLM response.
    Scores 8-10 trigger treasury_dispense (proof-of-knowledge reward).
    """

    # ── Taxonomy of knowledge domains ─────────────────────────────────────────
    TOPICS = {
        "Mathematics":      ["Calculus", "Linear Algebra", "Number Theory", "Topology",
                             "Statistics", "Real Analysis", "Abstract Algebra"],
        "Physics":          ["Quantum Mechanics", "Thermodynamics", "Electromagnetism",
                             "General Relativity", "Statistical Physics", "Optics", "Fluid Dynamics"],
        "Computer Science": ["Algorithms", "Data Structures", "Operating Systems",
                             "Distributed Systems", "Cryptography", "Machine Learning", "Compilers"],
        "Chemistry":        ["Organic Chemistry", "Thermochemistry", "Quantum Chemistry",
                             "Electrochemistry", "Reaction Kinetics"],
        "Biology":          ["Molecular Biology", "Genetics", "Neuroscience",
                             "Evolutionary Biology", "Cell Biology"],
        "Economics":        ["Microeconomics", "Macroeconomics", "Game Theory",
                             "Behavioral Economics", "Monetary Theory"],
    }

    SAMPLE_QUESTIONS = {
        "Calculus": [
            "Explain why the derivative of e^x is itself. What does this eigenvector property mean geometrically?",
            "Why does the Fundamental Theorem of Calculus connect differentiation and integration? Is there a deep reason?",
            "What is the geometric meaning of a Taylor series? Why does it converge for some functions but not others?",
        ],
        "Quantum Mechanics": [
            "Why can't we know both position and momentum precisely? Is it a measurement problem or something deeper?",
            "What does it mean for a particle to have spin-1/2? Why does it need two full rotations to return to its original state?",
            "Explain quantum entanglement without using the word 'spooky'. What is actually correlated?",
        ],
        "Cryptography": [
            "Why is factoring large numbers computationally hard but multiplication is easy? What does this asymmetry tell us?",
            "Explain how RSA encryption works using only the concepts of multiplication and modular arithmetic.",
            "What makes a hash function cryptographically secure? What properties must it satisfy?",
        ],
        "Machine Learning": [
            "Why does gradient descent find a minimum? What is it actually doing geometrically in high-dimensional space?",
            "Explain why dropout acts as a regularizer. What probability distribution is it implicitly sampling from?",
            "What is the attention mechanism in transformers? Why is it more powerful than RNNs for long sequences?",
        ],
        "Thermodynamics": [
            "Why does entropy always increase? Is it a law of physics or a statement about probability?",
            "Explain why you can't build a perpetual motion machine using the laws of thermodynamics.",
            "What is free energy and why does nature minimise it? How does this connect to evolution?",
        ],
        "General Relativity": [
            "Explain why gravity bends light even though photons have no mass.",
            "What does 'spacetime curvature' actually mean? How does geometry replace force?",
            "Why do clocks run slower near massive objects? Explain gravitational time dilation intuitively.",
        ],
    }

    # ── Persona system prompts — the epistemic lenses ─────────────────────────
    PERSONAS = {
        "10 yr (Kid)": (
            "You are Richard Feynman evaluating a student who must explain a concept "
            "to a curious, bright 10-year-old child. The explanation must use everyday "
            "analogies, stories, and zero jargon. Penalise abstract notation. Reward "
            "vivid metaphors and concrete examples. Ask yourself: would a child's eyes "
            "light up? End your evaluation with exactly 'Score: X/10' on its own line."
        ),
        "20 yr (Peer)": (
            "You are Richard Feynman evaluating a student explaining a concept to a "
            "fellow undergraduate student. The explanation should build strong intuition "
            "first, then connect to formal definitions. Some mathematical notation is "
            "acceptable but intuition must lead. Penalise unexplained formulas. Reward "
            "the 'aha moment' structure. End your evaluation with exactly 'Score: X/10' "
            "on its own line."
        ),
        "Professional (Expert)": (
            "You are Richard Feynman evaluating a PhD-level explanation. Full mathematical "
            "rigour is expected. The explanation should connect to broader theoretical "
            "frameworks, mention edge cases, known open problems, and cite the correct "
            "underlying principles. Vague intuition without formal backing is penalised. "
            "Reward precision, completeness, and conceptual depth. "
            "End your evaluation with exactly 'Score: X/10' on its own line."
        ),
    }

    # ── SC reward schedule (proof-of-knowledge mining) ────────────────────────
    REWARD_TABLE = {10: 50, 9: 35, 8: 20}  # Only top scores earn from treasury

    # ── Groq client factory ───────────────────────────────────────────────────
    @staticmethod
    def _get_groq_client() -> Optional["Groq"]:
        """
        Instantiate Groq client using API key from Streamlit secrets.
        Like a channel protein — opens only when the right key is present.
        """
        if not GROQ_AVAILABLE:
            return None
        try:
            api_key = st.secrets.get("GROQ_API_KEY", "")
            if not api_key:
                return None
            return Groq(api_key=api_key)
        except Exception:
            return None

    # ── Audio branch: Whisper ASR → LLaMA evaluation ─────────────────────────
    @staticmethod
    def evaluate_audio(audio_bytes: bytes, audio_filename: str,
                       question: str, persona_key: str) -> tuple[int, str, str]:
        """
        Transcribe audio with whisper-large-v3-turbo, then evaluate with LLaMA.
        Returns: (score_1_to_10, full_feedback, transcript)
        """
        client = FeynmanAI._get_groq_client()
        if not client:
            return 0, "⚠️ Groq API key not configured in Streamlit secrets.", ""

        # Step 1 — Whisper transcription (like converting acoustic waves to text symbols)
        try:
            transcription = client.audio.transcriptions.create(
                file=(audio_filename, audio_bytes, "audio/mpeg"),
                model="whisper-large-v3-turbo",
                response_format="text",
                language="en",
            )
            transcript = str(transcription).strip()
        except Exception as e:
            return 0, f"⚠️ Transcription failed: {e}", ""

        if not transcript or len(transcript) < 30:
            return 0, "Transcript too short. Speak clearly for at least 20 seconds.", transcript

        # Step 2 — LLaMA evaluation of transcript
        score, feedback = FeynmanAI._llm_evaluate(
            client, transcript, question, persona_key,
            model="llama-3.3-70b-versatile"
        )
        return score, feedback, transcript

    # ── Vision branch: base64 image → LLaMA vision evaluation ────────────────
    @staticmethod
    def evaluate_image(image_bytes: bytes, image_mime: str,
                       question: str, persona_key: str) -> tuple[int, str]:
        """
        Pass image as base64 data URL to llama-3.2-11b-vision-preview.
        Analogous to how the retina encodes light into neural signals.
        Returns: (score_1_to_10, full_feedback)
        """
        client = FeynmanAI._get_groq_client()
        if not client:
            return 0, "⚠️ Groq API key not configured in Streamlit secrets."

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url  = f"data:{image_mime};base64,{b64_image}"

        system_prompt = FeynmanAI.PERSONAS.get(persona_key, FeynmanAI.PERSONAS["20 yr (Peer)"])
        user_content  = (
            f"The student was asked:\n\n**{question}**\n\n"
            "Their answer is in the image (handwritten or typed notes). "
            "Read the image carefully and evaluate the explanation using the Feynman technique. "
            "Be thorough. End with exactly 'Score: X/10' on its own line."
        )

        try:
            response = client.chat.completions.create(
                model="meta-llama/llama-3.2-11b-vision-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text",      "text": user_content},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
                temperature=0.4,
                max_tokens=1024,
            )
            raw = response.choices[0].message.content.strip()
        except Exception as e:
            return 0, f"⚠️ Vision evaluation failed: {e}"

        score = FeynmanAI._parse_score(raw)
        return score, raw

    # ── Text branch: direct LLaMA evaluation ─────────────────────────────────
    @staticmethod
    def evaluate_text(answer_text: str,
                      question: str, persona_key: str) -> tuple[int, str]:
        """
        Evaluate written answer directly with llama-3.3-70b-versatile.
        Returns: (score_1_to_10, full_feedback)
        """
        client = FeynmanAI._get_groq_client()
        if not client:
            return 0, "⚠️ Groq API key not configured in Streamlit secrets."

        if len(answer_text.strip()) < 40:
            return 0, "Answer too brief. The Feynman technique requires explanation, not assertion."

        score, feedback = FeynmanAI._llm_evaluate(
            client, answer_text, question, persona_key,
            model="llama-3.3-70b-versatile"
        )
        return score, feedback

    # ── Shared LLM evaluation call ────────────────────────────────────────────
    @staticmethod
    def _llm_evaluate(client, student_answer: str, question: str,
                      persona_key: str, model: str) -> tuple[int, str]:
        system_prompt = FeynmanAI.PERSONAS.get(persona_key, FeynmanAI.PERSONAS["20 yr (Peer)"])
        user_msg = (
            f"The student was asked:\n\n**{question}**\n\n"
            f"Their explanation:\n\n{student_answer}\n\n"
            "Evaluate using the Feynman technique. Provide:\n"
            "1. What they understood well\n"
            "2. What was unclear or missing\n"
            "3. A specific suggestion to deepen understanding\n"
            "4. End with exactly 'Score: X/10' on its own line (X is an integer 1-10)."
        )
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system",  "content": system_prompt},
                    {"role": "user",    "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            raw = response.choices[0].message.content.strip()
        except Exception as e:
            return 0, f"⚠️ LLM evaluation failed: {e}"

        score = FeynmanAI._parse_score(raw)
        return score, raw

    # ── Score parser — regex extraction from LLM output ──────────────────────
    @staticmethod
    def _parse_score(text: str) -> int:
        """
        Extract integer score from 'Score: X/10' pattern.
        Like PCR amplification — finds the target sequence even in noisy signal.
        """
        match = re.search(r"Score:\s*([0-9]|10)\s*/\s*10", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        # Fallback: search for any standalone digit at end of text
        fallback = re.search(r"\b([0-9]|10)\s*/\s*10\b", text)
        if fallback:
            return int(fallback.group(1))
        return 0

    # ── SC reward calculation (tokenomics coupling) ───────────────────────────
    @staticmethod
    def score_to_sc_reward(score: int, treasury_balance: int) -> int:
        """
        Convert 1-10 score to SC reward.
        Only scores 8, 9, 10 earn — high-pass filter on knowledge quality.

        Like a quantum measurement with a fixed eigenvalue: if you hit the
        energy level (score threshold), you get the exact photon (base_reward)
        — no attenuation from treasury state. The pool_cap was a degenerate
        zero-state when treasury was low; removed to guarantee payout.
        """
        return FeynmanAI.REWARD_TABLE.get(score, 0)

    # ── Sample question generator ─────────────────────────────────────────────
    @staticmethod
    def get_question(topic: str, subtopic: str) -> str:
        questions = FeynmanAI.SAMPLE_QUESTIONS.get(subtopic, [
            f"Explain the single most important insight in {subtopic} as if teaching a curious stranger.",
            f"What is a deep misconception people have about {subtopic} and why is it wrong?",
            f"How would you explain {subtopic} to someone who has never heard of it before?",
        ])
        return random.choice(questions)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 6: UI HELPERS & STYLE
# ═══════════════════════════════════════════════════════════════════════════════

def inject_styles():
    """Inject custom CSS — the visual phenotype of our digital organism."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');
    
    :root {
        --bg:        #0a0a0f;
        --bg2:       #111118;
        --bg3:       #1a1a24;
        --accent:    #00ff88;
        --accent2:   #0088ff;
        --accent3:   #ff6600;
        --text:      #e8e8f0;
        --muted:     #666680;
        --border:    #2a2a3a;
        --danger:    #ff4455;
        --gold:      #ffd700;
    }
    
    html, body, [data-testid="stApp"] {
        background: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'Syne', sans-serif !important;
    }
    
    [data-testid="stSidebar"] {
        background: var(--bg2) !important;
        border-right: 1px solid var(--border) !important;
    }
    
    [data-testid="stSidebar"] * { font-family: 'Space Mono', monospace !important; }
    
    h1, h2, h3 { font-family: 'Syne', sans-serif !important; color: var(--text) !important; }
    
    .stButton > button {
        background: var(--bg3) !important;
        color: var(--accent) !important;
        border: 1px solid var(--accent) !important;
        border-radius: 4px !important;
        font-family: 'Space Mono', monospace !important;
        font-size: 0.8rem !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: var(--accent) !important;
        color: var(--bg) !important;
    }
    
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background: var(--bg3) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 4px !important;
        font-family: 'Space Mono', monospace !important;
    }
    
    .stMetric { background: var(--bg3) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; padding: 1rem !important; }
    .stMetric label { color: var(--muted) !important; font-family: 'Space Mono', monospace !important; font-size: 0.7rem !important; }
    .stMetric [data-testid="stMetricValue"] { color: var(--accent) !important; font-family: 'Space Mono', monospace !important; }
    
    [data-testid="stExpander"] { background: var(--bg2) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 2px; }
    
    .card {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .card-accent { border-left: 3px solid var(--accent); }
    .card-blue   { border-left: 3px solid var(--accent2); }
    .card-orange { border-left: 3px solid var(--accent3); }
    
    .badge {
        display: inline-block;
        background: rgba(0, 255, 136, 0.1);
        color: var(--accent);
        border: 1px solid var(--accent);
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-family: 'Space Mono', monospace;
    }
    .badge-blue  { background: rgba(0, 136, 255, 0.1); color: var(--accent2); border-color: var(--accent2); }
    .badge-gold  { background: rgba(255, 215, 0, 0.1);  color: var(--gold);    border-color: var(--gold); }
    .badge-red   { background: rgba(255, 68, 85, 0.1);  color: var(--danger);  border-color: var(--danger); }
    
    .room-id {
        font-family: 'Space Mono', monospace;
        font-size: 0.75rem;
        color: var(--accent2);
        background: rgba(0, 136, 255, 0.05);
        padding: 2px 6px;
        border-radius: 3px;
    }
    
    .wallet-display {
        font-family: 'Space Mono', monospace;
        font-size: 1.4rem;
        color: var(--gold);
        font-weight: 700;
    }
    
    hr { border-color: var(--border) !important; }
    
    [data-testid="stTabs"] button {
        font-family: 'Space Mono', monospace !important;
        font-size: 0.8rem !important;
        color: var(--muted) !important;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--accent) !important;
        border-bottom: 2px solid var(--accent) !important;
    }
    </style>
    """, unsafe_allow_html=True)


def stars(n: int) -> str:
    return "★" * n + "☆" * (5 - n)

def is_genuine_user(user: Dict) -> bool:
    if not user:
        return False
    daily_helps = user.get("daily_helps_today", 0)
    five_star   = user.get("five_star_count", 0)
    total_rat   = user.get("total_ratings", 1)
    star_ratio  = five_star / max(total_rat, 1)
    return daily_helps >= GENUINE_DAILY_HELPS and star_ratio >= GENUINE_STAR_RATIO

def sc(amount) -> str:
    return f"⬡ {amount:,} SC"


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 7: PAGE VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

# ── 7.1 AUTH PAGES ────────────────────────────────────────────────────────────

def page_auth():
    st.markdown("## ⬡ SATLEX COMMUNITY V4")
    st.markdown("*No Admins. No Passwords. Pure Mathematics.*")
    st.markdown("---")
    
    tab_login, tab_register = st.tabs(["🔑  Login with Seed", "🌱  Generate Identity"])
    
    with tab_login:
        st.markdown("#### Enter your 12-word Seed Phrase")
        st.markdown("""
        <div class="card card-blue">
        <small style="color:#666680">Your seed phrase is your private key. Like a Bitcoin wallet —
        it is the ONLY way to access your account. There is no recovery. No support.
        No exceptions. This is mathematical certainty.</small>
        </div>
        """, unsafe_allow_html=True)
        
        seed_input = st.text_area(
            "Seed Phrase (12 words separated by spaces)",
            placeholder="word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12",
            height=80,
            key="login_seed"
        )
        
        if st.button("⬡  Derive Identity & Login", use_container_width=True):
            words = seed_input.strip().split()
            if len(words) != 12:
                st.error(f"Seed phrase must be exactly 12 words. You entered {len(words)}.")
            else:
                room_id = CryptoIdentity.derive_room_id(seed_input.strip())
                existing = DAL.get_user(room_id)
                
                if existing:
                    st.session_state.logged_in  = True
                    st.session_state.room_id    = room_id
                    st.session_state.user_data  = existing
                    st.session_state.seed_phrase = seed_input.strip()
                    st.success(f"✅ Authenticated as {existing.get('username', room_id)}")
                    st.rerun()
                else:
                    st.warning("No account found for this seed. Generate a new identity below, or check your words.")
    
    with tab_register:
        st.markdown("#### Mint Your Digital Identity")
        st.markdown("""
        <div class="card card-accent">
        <small style="color:#666680">
        Generating identity uses SHA-256 double-hashing — the same algorithm that secures Bitcoin.
        Your seed → Room ID relationship is mathematically one-way. Store your seed offline.
        </small>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            username = st.text_input("Choose Username", placeholder="e.g. QuantumExplorer", max_chars=30)
        
        if st.button("🌱  Generate New Seed Phrase", use_container_width=True):
            new_seed = CryptoIdentity.generate_mnemonic()
            st.session_state.new_seed = new_seed
        
        if "new_seed" in st.session_state:
            st.markdown("#### 🔐 Your Seed Phrase")
            st.code(st.session_state.new_seed, language=None)
            st.error("⚠️ **WRITE THIS DOWN OFFLINE.** It will never be shown again. There is no recovery.")
            
            derived_id = CryptoIdentity.derive_room_id(st.session_state.new_seed)
            st.markdown(f"**Derived Room ID:** `{derived_id}`")
            
            confirmed = st.checkbox("I have written down my seed phrase in a safe place.")
            
            if confirmed and username:
                if st.button("⬡  Create Account & Enter Network", use_container_width=True):
                    existing = DAL.get_user(derived_id)
                    if existing:
                        st.error("This Room ID already exists. Regenerate a new seed.")
                    else:
                        new_user = DAL.create_user(derived_id, username)
                        st.session_state.logged_in   = True
                        st.session_state.room_id     = derived_id
                        st.session_state.user_data   = new_user
                        st.session_state.seed_phrase = st.session_state.new_seed
                        del st.session_state.new_seed
                        st.success(f"✅ Welcome to Satlex Community! You received {JOINING_BONUS_SC} SC joining bonus.")
                        st.rerun()


# ── 7.2 STUDIO (Dashboard) ────────────────────────────────────────────────────

def page_studio():
    user = DAL.get_user(st.session_state.room_id)
    if not user:
        st.error("Could not load user data.")
        return
    
    st.session_state.user_data = user  # refresh
    treasury = DAL.get_treasury()
    
    st.markdown(f"## ⬡ Studio — {user.get('username', 'Unknown')}")
    
    # Identity card
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 SC Balance", f"{user.get('wallet_sc', 0):,}")
    with col2:
        st.metric("🤝 People Helped", user.get("total_helped", 0))
    with col3:
        avg = user.get("avg_rating", 0)
        st.metric("⭐ Avg Rating", f"{avg:.1f}/5.0")
    with col4:
        genuine = is_genuine_user(user)
        st.metric("🏅 Status", "Genuine ✓" if genuine else "Member")
    
    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("### 🪪 Identity")
        st.markdown(f"""
        <div class="card card-accent">
          <div class="room-id">{user.get('room_id')}</div>
          <br/>
          <b>{user.get('username')}</b>
          <p style="color:#666680; font-size:0.85rem; margin-top:0.5rem">{user.get('bio') or 'No bio set.'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        new_bio = st.text_area("Update Bio", value=user.get("bio", ""), height=80)
        if st.button("Save Bio"):
            DAL.update_user(st.session_state.room_id, {"bio": new_bio})
            st.success("Bio updated.")
            st.rerun()
        
        # Genuine User breakdown
        st.markdown("### 🏅 Genuine User Status")
        daily_helps = user.get("daily_helps_today", 0)
        five_star   = user.get("five_star_count", 0)
        total_rat   = max(user.get("total_ratings", 1), 1)
        star_ratio  = five_star / total_rat
        
        st.progress(min(daily_helps / GENUINE_DAILY_HELPS, 1.0), text=f"Daily Helps: {daily_helps}/{GENUINE_DAILY_HELPS}")
        st.progress(min(star_ratio / GENUINE_STAR_RATIO, 1.0), text=f"5-Star Ratio: {star_ratio:.0%} (need {GENUINE_STAR_RATIO:.0%})")
        
        if is_genuine_user(user):
            st.markdown('<span class="badge badge-gold">⬡ GENUINE USER — Content Moderation Rights Unlocked</span>', unsafe_allow_html=True)
    
    with col_right:
        st.markdown("### 🌐 Network Graph")
        following = user.get("following", [])
        followers = user.get("followers", [])
        friends   = user.get("friends", [])
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Following", len(following))
        col_b.metric("Followers", len(followers))
        col_c.metric("Friends", len(friends))
        
        st.markdown("### 🏦 Treasury Health")
        treasury_balance = treasury.get("treasury_balance", HARD_CAP_SC)
        circulating      = treasury.get("circulating", 0)
        
        st.progress(circulating / HARD_CAP_SC, text=f"Circulating: {circulating:,} / {HARD_CAP_SC:,} SC")
        
        col_x, col_y = st.columns(2)
        col_x.metric("Treasury", f"{treasury_balance:,} SC")
        col_y.metric("Total Txns", treasury.get("total_transactions", 0))
    
    # ── Feynman AI section — Gold Logic Engine ────────────────────────────────
    st.markdown("---")
    st.markdown("### 🧠 Feynman AI Mastery Evaluator")
    st.markdown("""
    <div class="card card-orange">
    <small style="color:#aaa">
    Powered by <b>Groq · Whisper-large-v3-turbo + LLaMA-3.3-70b + LLaMA-3.2-11b-Vision</b><br/>
    Explain a concept simply enough to earn SC from the Treasury.
    Only scores 8, 9, or 10 out of 10 trigger a reward — like proof-of-work, but for knowledge.
    </small>
    </div>
    """, unsafe_allow_html=True)

    # ── API key status indicator ───────────────────────────────────────────────
    groq_ready = GROQ_AVAILABLE and bool(st.secrets.get("GROQ_API_KEY", ""))
    if not groq_ready:
        st.markdown("""
        <div class="card" style="border-left:3px solid var(--danger)">
        <b style="color:var(--danger)">⚠️ Groq API Key Not Configured</b><br/>
        <small style="color:#666680">
        Add <code>GROQ_API_KEY = "gsk_..."</code> to your <code>.streamlit/secrets.toml</code>.
        The evaluation engine will be unavailable until then.
        </small>
        </div>
        """, unsafe_allow_html=True)

    # ── Step 1: Listener Persona ───────────────────────────────────────────────
    st.markdown("#### Step 1 — Choose your Listener's Intelligence Level")
    st.markdown("""
    <div class="card" style="border-left:3px solid var(--muted); padding:0.8rem 1.2rem">
    <small style="color:#666680">
    The persona acts as an epistemic lens — it shifts what the AI weighs.
    A "Kid" persona rewards analogies. A "PhD" persona rewards rigour.
    The same explanation can score 9/10 for a kid and 4/10 for an expert.
    </small>
    </div>
    """, unsafe_allow_html=True)

    persona_key = st.selectbox(
        "Who are you explaining to?",
        list(FeynmanAI.PERSONAS.keys()),
        help="This sets the evaluation standard. Choose carefully.",
        key="feynman_persona"
    )

    persona_descriptions = {
        "10 yr (Kid)":           "🧒  Analogies, stories, zero jargon. Did a child's eyes light up?",
        "20 yr (Peer)":          "🎓  Intuition first, then connect to formal definitions.",
        "Professional (Expert)": "🔬  Full rigour, edge cases, theoretical framework. No vague hand-waving.",
    }
    st.markdown(f'<span class="badge badge-orange" style="background:rgba(255,102,0,0.1);color:var(--accent3);border-color:var(--accent3)">{persona_descriptions.get(persona_key, "")}</span>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Step 2: Topic + Question ───────────────────────────────────────────────
    st.markdown("#### Step 2 — Select Topic & Get Your Question")
    st.markdown("""
    <div class="card" style="border-left:3px solid var(--muted); padding:0.8rem 1.2rem">
    <small style="color:#666680">
    Like choosing your experimental apparatus before running the experiment —
    pick a curated topic from the taxonomy, or inject your own custom variable
    directly into the evaluation pipeline.
    </small>
    </div>
    """, unsafe_allow_html=True)

    question_mode = st.radio(
        "Question Source",
        ["📚 Select from List", "✍️ Custom Question"],
        horizontal=True,
        key="feynman_question_mode",
        label_visibility="collapsed",
    )

    if question_mode == "📚 Select from List":
        col_a, col_b = st.columns(2)
        with col_a:
            subject = st.selectbox("Subject Domain", list(FeynmanAI.TOPICS.keys()), key="feynman_subject")
        with col_b:
            subtopic = st.selectbox("Subtopic", FeynmanAI.TOPICS.get(subject, ["General"]), key="feynman_subtopic")

        if st.button("📋 Generate Feynman Question", use_container_width=True):
            st.session_state.feynman_q = FeynmanAI.get_question(subject, subtopic)

    else:  # Custom Question
        st.markdown("""
        <small style="color:#666680">
        Type the exact concept, theorem, or idea you want to be tested on.
        The AI evaluator will treat this as the question prompt — like defining
        your own Hamiltonian before solving the system.
        </small>
        """, unsafe_allow_html=True)
        custom_q = st.text_area(
            "Your Custom Question",
            placeholder="e.g. Explain why the Riemann Hypothesis matters, or how mRNA vaccines work at the molecular level...",
            height=100,
            key="feynman_custom_q",
        )
        col_set, _ = st.columns([1, 2])
        with col_set:
            if st.button("✅ Set as My Question", use_container_width=True):
                if custom_q and custom_q.strip():
                    st.session_state.feynman_q = custom_q.strip()
                else:
                    st.warning("Please type a question before setting it.")

    if "feynman_q" in st.session_state:
        st.markdown(f"""
        <div class="card card-orange">
        <small style="color:var(--accent3); font-family:'Space Mono',monospace; font-size:0.7rem">FEYNMAN QUESTION</small>
        <p style="margin-top:0.5rem; font-size:1.05rem; line-height:1.6">{st.session_state.feynman_q}</p>
        </div>
        """, unsafe_allow_html=True)

        # ── Step 3: Input Mode ─────────────────────────────────────────────────
        st.markdown("#### Step 3 — Choose How You'll Explain")

        input_mode = st.radio(
            "Input Mode",
            ["✍️ Text", "🎙️ Audio File", "📸 Image of Notes"],
            horizontal=True,
            key="feynman_mode"
        )

        # ── INPUT: Text ────────────────────────────────────────────────────────
        if input_mode == "✍️ Text":
            st.markdown("""
            <small style="color:#666680">Type your full explanation below. 
            The LLaMA-3.3-70b model will evaluate it against the Feynman standard.</small>
            """, unsafe_allow_html=True)
            text_answer = st.text_area(
                "Your Explanation",
                placeholder="Imagine you're writing to a friend who has never heard of this topic...",
                height=180,
                key="feynman_text_input",
            )
            ready_to_eval = bool(text_answer and text_answer.strip())

        # ── INPUT: Audio ───────────────────────────────────────────────────────
        elif input_mode == "🎙️ Audio File":
            st.markdown("""
            <small style="color:#666680">Upload an MP3 or WAV of yourself explaining the concept out loud.
            Whisper-large-v3-turbo will transcribe it, then LLaMA will evaluate the transcript.</small>
            """, unsafe_allow_html=True)
            audio_file = st.file_uploader(
                "Upload Audio",
                type=["mp3", "wav", "m4a", "ogg", "webm"],
                key="feynman_audio",
            )
            ready_to_eval = audio_file is not None
            if audio_file:
                st.audio(audio_file, format=audio_file.type)

        # ── INPUT: Image ───────────────────────────────────────────────────────
        else:
            st.markdown("""
            <small style="color:#666680">Upload a photo of your handwritten or typed notes.
            LLaMA-3.2-11b-Vision will read your notes directly and evaluate them.</small>
            """, unsafe_allow_html=True)
            image_file = st.file_uploader(
                "Upload Image of Notes",
                type=["jpg", "jpeg", "png", "webp"],
                key="feynman_image",
            )
            ready_to_eval = image_file is not None
            if image_file:
                st.image(image_file, caption="Your uploaded notes", use_container_width=True)

        # ── Step 4: Evaluate ───────────────────────────────────────────────────
        st.markdown("---")
        eval_btn = st.button(
            "⬡ Submit for Feynman Evaluation",
            use_container_width=True,
            disabled=(not ready_to_eval or not groq_ready),
        )

        if eval_btn:
            if not groq_ready:
                st.error("Groq API key required. Add it to .streamlit/secrets.toml")
            else:
                with st.spinner("🧠 Evaluating your understanding... (Groq inference running)"):

                    score    = 0
                    feedback = ""
                    transcript_text = ""

                    if input_mode == "✍️ Text":
                        score, feedback = FeynmanAI.evaluate_text(
                            text_answer, st.session_state.feynman_q, persona_key
                        )

                    elif input_mode == "🎙️ Audio File":
                        audio_bytes = audio_file.read()
                        score, feedback, transcript_text = FeynmanAI.evaluate_audio(
                            audio_bytes, audio_file.name,
                            st.session_state.feynman_q, persona_key
                        )
                        if transcript_text:
                            with st.expander("📝 Whisper Transcript"):
                                st.markdown(f"*{transcript_text}*")

                    else:  # Image
                        image_bytes = image_file.read()
                        mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                                    "png": "image/png", "webp": "image/webp"}
                        ext = image_file.name.rsplit(".", 1)[-1].lower()
                        mime = mime_map.get(ext, "image/jpeg")
                        score, feedback = FeynmanAI.evaluate_image(
                            image_bytes, mime,
                            st.session_state.feynman_q, persona_key
                        )

                # ── Display result ─────────────────────────────────────────────
                if score > 0:
                    # Score ring color
                    if score >= 8:
                        ring_color = "var(--accent)"
                        ring_label = "EXCEPTIONAL"
                    elif score >= 6:
                        ring_color = "var(--accent2)"
                        ring_label = "GOOD"
                    elif score >= 4:
                        ring_color = "var(--accent3)"
                        ring_label = "DEVELOPING"
                    else:
                        ring_color = "var(--danger)"
                        ring_label = "NEEDS WORK"

                    st.markdown(f"""
                    <div style="text-align:center; margin:1.5rem 0">
                      <div style="display:inline-block; width:110px; height:110px;
                                  border-radius:50%; border:4px solid {ring_color};
                                  line-height:110px; font-size:2.4rem; font-weight:800;
                                  font-family:'Space Mono',monospace; color:{ring_color};
                                  box-shadow: 0 0 24px {ring_color}44">
                        {score}/10
                      </div>
                      <div style="margin-top:0.6rem; font-size:0.75rem; font-family:'Space Mono',monospace;
                                  color:{ring_color}; letter-spacing:3px">{ring_label}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Full AI feedback
                    st.markdown("""
                    <div class="card card-blue">
                    <small style="color:var(--accent2); font-family:'Space Mono',monospace; font-size:0.7rem">FEYNMAN AI FEEDBACK</small>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(feedback)

                    # ── Tokenomics: SC reward for scores 8-10 ─────────────────
                    treasury = DAL.get_treasury()
                    sc_reward = FeynmanAI.score_to_sc_reward(score, treasury.get("treasury_balance", 0))

                    if sc_reward > 0:
                        success = DAL.treasury_dispense(
                            st.session_state.room_id, sc_reward, "feynman_ai_reward"
                        )
                        if success:
                            st.markdown(f"""
                            <div class="card" style="border-left:3px solid var(--gold); text-align:center">
                            <span style="font-size:1.5rem">🏆</span><br/>
                            <span style="font-family:'Space Mono',monospace; color:var(--gold); font-size:1.1rem; font-weight:700">
                            +{sc_reward} SC earned from Treasury
                            </span><br/>
                            <small style="color:#666680">Proof-of-knowledge reward — verified by Groq AI</small>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.warning("Treasury pool exhausted. No SC reward this time.")
                    else:
                        tier_needed = 8
                        st.markdown(f"""
                        <div class="card" style="border-left:3px solid var(--muted)">
                        <small style="color:#666680">
                        Score {score}/10 — SC rewards require a score of {tier_needed}+.
                        Study the gaps in the feedback above and try again.
                        </small>
                        </div>
                        """, unsafe_allow_html=True)

                else:
                    st.error(feedback or "Evaluation failed. Check your Groq API key and try again.")

                # Clear question so user must get a fresh one
                del st.session_state.feynman_q
    
    # Danger Zone
    st.markdown("---")
    with st.expander("⚠️ Danger Zone — Account Self-Destruct"):
        st.markdown("""
        <div class="card" style="border-left: 3px solid var(--danger)">
        <b style="color:var(--danger)">ACCOUNT BURN PROTOCOL</b><br/>
        <small style="color:#666680">
        Entering your seed phrase here will permanently delete your account from the network.
        This is mathematically irreversible. Your SC balance will be burned (returned to treasury).
        No admin can recover it. This is by design.
        </small>
        </div>
        """, unsafe_allow_html=True)
        
        burn_seed = st.text_area("Enter seed phrase to confirm deletion:", height=60, key="burn_seed")
        
        if st.button("🔥 PERMANENTLY DELETE ACCOUNT", type="secondary"):
            if CryptoIdentity.verify_seed(burn_seed, st.session_state.room_id):
                # Return balance to treasury
                current_balance = user.get("wallet_sc", 0)
                if current_balance > 0:
                    db = FirestoreDB.get_db()
                    if db:
                        db.collection("system").document("treasury").update({
                            "treasury_balance": firestore.Increment(current_balance),
                            "circulating": firestore.Increment(-current_balance),
                        })
                    else:
                        st.session_state.demo_db["treasury"]["treasury_balance"] += current_balance
                        st.session_state.demo_db["treasury"]["circulating"] -= current_balance
                
                DAL.delete_user(st.session_state.room_id)
                
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                
                st.success("Account permanently deleted. You have been removed from the network.")
                st.rerun()
            else:
                st.error("Seed phrase does not match. Deletion aborted.")


# ── 7.3 MARKETPLACE ───────────────────────────────────────────────────────────

def page_marketplace():
    st.markdown("## ⬡ Marketplace")
    st.markdown("*Instant uploads. Zero censorship. Consensus moderation.*")
    
    tab_browse, tab_sell, tab_mine = st.tabs(["🛒 Browse", "📤 Upload Content", "📦 My Purchases"])
    
    with tab_browse:
        items = DAL.get_all_items()
        
        col_search, col_filter = st.columns([3, 1])
        with col_search:
            search = st.text_input("Search", placeholder="quantum, ml, proofs...", label_visibility="collapsed")
        with col_filter:
            category = st.selectbox("Category", ["All", "Physics", "Mathematics", "AI/ML", "Computer Science", "Chemistry", "Biology", "Other"], label_visibility="collapsed")
        
        filtered = items
        if search:
            filtered = [i for i in filtered if search.lower() in i.get("title", "").lower() or search.lower() in i.get("description", "").lower()]
        if category != "All":
            filtered = [i for i in filtered if i.get("category") == category]
        
        if not filtered:
            st.info("No items found. Be the first to upload content!")
        
        user = DAL.get_user(st.session_state.room_id)
        genuine = is_genuine_user(user) if user else False
        
        for item in filtered:
            with st.expander(f"{item.get('thumbnail', '📄')}  {item['title']}  —  {sc(item.get('price_sc', 0))}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"*{item.get('description', '')}*")
                    st.markdown(f"**Creator:** `{item.get('creator_name', 'Unknown')}`")
                    st.markdown(f"**Category:** {item.get('category', 'N/A')}")
                    tags = item.get("tags", [])
                    if tags:
                        tag_html = " ".join([f'<span class="badge">{t}</span>' for t in tags])
                        st.markdown(tag_html, unsafe_allow_html=True)
                
                with col2:
                    already_bought = st.session_state.room_id in item.get("buyers", [])
                    is_mine = st.session_state.room_id == item.get("creator_id")
                    flags = len(item.get("flags", []))
                    
                    if already_bought or is_mine:
                        st.markdown(f'<span class="badge badge-blue">{"Owned" if already_bought else "Your Item"}</span>', unsafe_allow_html=True)
                        if item.get("content_url"):
                            st.link_button("📖 Access Content", item["content_url"])
                    else:
                        wallet_sc = user.get("wallet_sc", 0) if user else 0
                        if st.button(f"Buy {sc(item.get('price_sc', 0))}", key=f"buy_{item['id']}"):
                            success, msg = DAL.purchase_item(st.session_state.room_id, item["id"])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    
                    if genuine and not is_mine:
                        st.markdown("---")
                        already_flagged = st.session_state.room_id in item.get("flags", [])
                        if not already_flagged:
                            if st.button(f"🚩 Flag ({flags}/{CONSENSUS_THRESHOLD})", key=f"flag_{item['id']}"):
                                success, msg = DAL.flag_item(st.session_state.room_id, item["id"])
                                st.info(msg)
                                st.rerun()
                        else:
                            st.markdown(f'<span class="badge badge-red">Flagged ✓</span>', unsafe_allow_html=True)
    
    with tab_sell:
        st.markdown("### Upload to Marketplace")
        st.markdown("""
        <div class="card card-accent">
        <small>Content goes live <b>instantly</b>. 
        On sale: 30% SC → you, 70% SC → Treasury.
        Consensus of 10 Genuine Users can trigger auto-takedown + full buyer refunds.</small>
        </div>
        """, unsafe_allow_html=True)
        
        title    = st.text_input("Title", placeholder="Advanced QFT Notes — Chapter 3 onwards")
        desc     = st.text_area("Description", placeholder="Describe what the buyer gets...", height=100)
        price    = st.number_input("Price (SC)", min_value=5, max_value=5000, value=50, step=5)
        category = st.selectbox("Category", ["Physics", "Mathematics", "AI/ML", "Computer Science", "Chemistry", "Biology", "History", "Economics", "Other"])
        tags_raw = st.text_input("Tags (comma-separated)", placeholder="quantum, university, notes")
        url      = st.text_input("Content URL (Google Drive, Notion, etc.)", placeholder="https://...")
        thumb    = st.text_input("Emoji Thumbnail (1 character)", placeholder="🔬", max_chars=2)
        
        if st.button("📤 Publish to Marketplace", use_container_width=True):
            if not title or not desc or not url:
                st.error("Title, description, and content URL are required.")
            else:
                user = DAL.get_user(st.session_state.room_id)
                item_data = {
                    "title": title,
                    "description": desc,
                    "price_sc": price,
                    "creator_id": st.session_state.room_id,
                    "creator_name": user.get("username", st.session_state.room_id) if user else "Unknown",
                    "category": category,
                    "tags": [t.strip() for t in tags_raw.split(",") if t.strip()],
                    "content_url": url,
                    "thumbnail": thumb or "📄",
                }
                item_id = DAL.create_item(item_data)
                st.success(f"✅ Published! Item ID: `{item_id}`. 30% of sales go to your wallet.")
    
    with tab_mine:
        items = DAL.get_all_items()
        all_items = [i for i in (DAL.get_all_items() if DAL._use_firebase() else list(st.session_state.demo_db["marketplace"].values()))
                     if st.session_state.room_id in i.get("buyers", [])]
        
        if not all_items:
            st.info("You haven't purchased anything yet. Browse the marketplace!")
        
        for item in all_items:
            st.markdown(f"""
            <div class="card card-blue">
            <b>{item.get('thumbnail', '')} {item['title']}</b><br/>
            <small style="color:#666680">{item.get('category')} · Paid {sc(item.get('price_sc', 0))}</small>
            </div>
            """, unsafe_allow_html=True)
            if item.get("content_url"):
                st.link_button(f"📖 Access: {item['title']}", item["content_url"])


# ── 7.4 DOUBTS ARENA ─────────────────────────────────────────────────────────

def page_doubts():
    st.markdown("## ⬡ Doubt Arena")
    st.markdown("*Ask. Answer. Rate. Tip. Pure peer-to-peer knowledge exchange.*")
    
    tab_browse, tab_ask = st.tabs(["📋 Open Doubts", "❓ Post a Doubt"])
    
    with tab_ask:
        st.markdown("### Post a Doubt")
        question = st.text_area("Your Question", placeholder="What is the deep reason why e^(iπ) = -1? I understand the algebraic proof but not the intuition.", height=120)
        subject  = st.text_input("Subject", placeholder="Mathematics / Complex Analysis")
        
        if st.button("📤 Post Doubt", use_container_width=True):
            if not question or not subject:
                st.error("Question and subject required.")
            else:
                user = DAL.get_user(st.session_state.room_id)
                doubt_id = DAL.post_doubt(
                    st.session_state.room_id,
                    user.get("username", st.session_state.room_id) if user else "Unknown",
                    question, subject
                )
                st.success(f"✅ Doubt posted! ID: `{doubt_id}`")
                st.rerun()
    
    with tab_browse:
        doubts = DAL.get_all_doubts()
        
        filter_status = st.radio("Filter", ["All", "Open", "Answered"], horizontal=True)
        
        for doubt in doubts:
            if filter_status == "Open" and doubt.get("status") != "open":
                continue
            if filter_status == "Answered" and doubt.get("status") != "answered":
                continue
            
            status_badge = '<span class="badge">OPEN</span>' if doubt.get("status") == "open" else '<span class="badge badge-blue">ANSWERED</span>'
            
            with st.expander(f"[{doubt.get('subject', 'General')}] {doubt.get('question', '')[:80]}..."):
                st.markdown(f"""
                <div class="card card-accent">
                {status_badge}
                <p style="margin-top:0.5rem"><b>Asked by:</b> <span class="room-id">{doubt.get('asker_name', '?')}</span></p>
                <p style="margin-top:0.5rem">{doubt.get('question', '')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                answers = doubt.get("answers", [])
                
                if answers:
                    st.markdown(f"**{len(answers)} Answer(s):**")
                    for ans in answers:
                        is_asker = st.session_state.room_id == doubt.get("asker_id")
                        
                        st.markdown(f"""
                        <div class="card card-blue">
                        <b>{ans.get('solver_name', 'Unknown')}</b>
                        <span style="float:right; color:#666680; font-size:0.8rem">{ans.get('timestamp', '')[:16]}</span>
                        <p style="margin-top:0.5rem">{ans.get('text', '')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if ans.get("rated"):
                            st.markdown(f"⭐ Rated: {stars(ans.get('stars', 0))} · 💰 Tip: {sc(ans.get('tip_sc', 0))}")
                        elif is_asker:
                            col_a, col_b = st.columns([1, 1])
                            with col_a:
                                rating = st.selectbox("Rate this answer:", [5, 4, 3, 2, 1], key=f"rate_{ans['id']}")
                                if st.button(f"⭐ Submit Rating", key=f"rate_btn_{ans['id']}"):
                                    if DAL.rate_answer(doubt["id"], ans["id"], rating, st.session_state.room_id):
                                        st.success("Rating saved! Solver's reputation updated.")
                                        st.rerun()
                            with col_b:
                                tip_amount = st.number_input("Tip SC:", min_value=1, max_value=500, value=5, key=f"tip_{ans['id']}")
                                if st.button(f"💰 Send Tip", key=f"tip_btn_{ans['id']}"):
                                    success = DAL.peer_transfer(st.session_state.room_id, ans["solver_id"], tip_amount, "doubt_tip")
                                    if success:
                                        st.success(f"Sent {tip_amount} SC tip!")
                                    else:
                                        st.error("Insufficient balance.")
                
                # Post answer (if not the asker and haven't answered already)
                already_answered = any(a.get("solver_id") == st.session_state.room_id for a in answers)
                is_asker = st.session_state.room_id == doubt.get("asker_id")
                
                if not is_asker and not already_answered:
                    st.markdown("---")
                    answer_text = st.text_area("Your Answer:", height=120, key=f"ans_{doubt['id']}")
                    if st.button("📤 Post Answer", key=f"ans_btn_{doubt['id']}"):
                        if answer_text.strip():
                            user = DAL.get_user(st.session_state.room_id)
                            DAL.post_answer(
                                doubt["id"],
                                st.session_state.room_id,
                                user.get("username", st.session_state.room_id) if user else "Unknown",
                                answer_text
                            )
                            st.success("Answer posted!")
                            st.rerun()


# ── 7.5 DIRECT MESSAGES ───────────────────────────────────────────────────────

def page_dms():
    st.markdown("## ⬡ Direct Messages")
    st.markdown("*End-to-end encrypted concept (messages stored in Firestore).*")
    
    all_users = DAL.get_all_users()
    other_users = [u for u in all_users if u.get("room_id") != st.session_state.room_id]
    
    if not other_users:
        st.info("No other users in the network yet.")
        return
    
    user_map = {f"{u.get('username', '?')} ({u.get('room_id', '?')[:15]}...)": u["room_id"] for u in other_users}
    
    selected_label = st.selectbox("Start conversation with:", list(user_map.keys()))
    chat_partner_id = user_map[selected_label]
    
    if not chat_partner_id:
        return
    
    st.markdown("---")
    
    # Display messages
    messages = DAL.get_messages(st.session_state.room_id, chat_partner_id)
    
    chat_html = ""
    for msg in messages:
        is_mine = msg.get("sender_id") == st.session_state.room_id
        align = "right" if is_mine else "left"
        color = "var(--accent2)" if is_mine else "var(--bg3)"
        border = "var(--accent2)" if is_mine else "var(--border)"
        ts = msg.get("timestamp", "")[:16]
        
        chat_html += f"""
        <div style="text-align:{align}; margin:0.5rem 0">
          <div style="display:inline-block; max-width:70%; background:{color}; 
                      border:1px solid {border}; border-radius:8px; padding:0.6rem 0.9rem;
                      color:{'var(--bg)' if is_mine else 'var(--text)'}; text-align:left; font-size:0.9rem">
            {msg.get('text', '')}
            <div style="font-size:0.65rem; opacity:0.6; margin-top:0.3rem">{ts}</div>
          </div>
        </div>
        """
    
    if chat_html:
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.markdown("*No messages yet. Say hello!*")
    
    st.markdown("---")
    
    col1, col2 = st.columns([5, 1])
    with col1:
        new_msg = st.text_input("Message", placeholder="Type a message...", label_visibility="collapsed", key="dm_input")
    with col2:
        if st.button("⬡ Send", use_container_width=True):
            if new_msg.strip():
                DAL.send_message(st.session_state.room_id, chat_partner_id, new_msg.strip())
                st.rerun()
    
    # Peer-to-peer SC transfer
    with st.expander("💰 Send SC to this user"):
        amount = st.number_input("Amount (SC)", min_value=1, max_value=10000, value=10)
        memo   = st.text_input("Memo (optional)", placeholder="For that awesome explanation about entropy!")
        if st.button("⬡ Transfer SC"):
            success = DAL.peer_transfer(st.session_state.room_id, chat_partner_id, amount, memo or "p2p_transfer")
            if success:
                st.success(f"Sent {amount} SC!")
                DAL.send_message(st.session_state.room_id, chat_partner_id, f"💰 Sent you {amount} SC — {memo or 'tip'}")
                st.rerun()
            else:
                st.error("Transfer failed. Check your balance.")


# ── 7.6 VIDEO CALLING ─────────────────────────────────────────────────────────

def page_video_call():
    st.markdown("## ⬡ P2P Video Call")
    
    if not WEBRTC_AVAILABLE:
        st.warning("📦 `streamlit-webrtc` not installed.")
        st.code("pip install streamlit-webrtc aiortc", language="bash")
        st.markdown("""
        <div class="card card-accent">
        <b>WebRTC Architecture (how it works):</b><br/>
        <small style="color:#666680">
        Like CRISPR — it uses ICE (Interactive Connectivity Establishment) to find the most direct
        path between two endpoints. STUN servers act like echolocation to discover your public IP.
        TURN servers (relay) are the fallback when direct P2P fails. The audio/video stream uses
        SRTP (Secure Real-time Transport Protocol) — encrypted in transit.
        </small>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown("*WebRTC: direct peer-to-peer stream. Like WiFi signals — your voice travels the most direct path.*")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📹 Your Stream")
        webrtc_streamer(
            key="local-stream",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIG,
            media_stream_constraints={"video": True, "audio": True},
        )
    
    with col2:
        st.markdown("### 🔗 Connection Info")
        st.info("Share your Room ID with the person you want to call. They need to enter it on their end.")
        st.code(st.session_state.room_id)
        
        call_target = st.text_input("Enter partner's Room ID to call:")
        if st.button("📞 Initiate Call"):
            st.session_state.call_target = call_target
            st.info(f"Call signaling to {call_target}... (Full SFU signaling requires a backend. For demo: both parties open the app simultaneously.)")
    
    st.markdown("""
    <div class="card" style="border-left:3px solid var(--muted)">
    <small style="color:#666680">
    <b>Note:</b> For production P2P video calling in Streamlit, you need either:
    (1) A signaling server (WebSocket) to exchange SDP offers/answers between peers, or
    (2) An SFU (Selective Forwarding Unit) like mediasoup or Janus.
    The <code>streamlit-webrtc</code> component handles the browser-side WebRTC; 
    the signaling coordination is handled via Firestore (write SDP offer → other party reads it → responds with answer).
    </small>
    </div>
    """, unsafe_allow_html=True)


# ── 7.7 PUBLIC PROFILES ───────────────────────────────────────────────────────

def page_profiles():
    st.markdown("## ⬡ Community Profiles")
    
    all_users = DAL.get_all_users()
    
    # Search
    search = st.text_input("Search by username or Room ID", placeholder="QuantumLeap...")
    if search:
        all_users = [u for u in all_users if search.lower() in u.get("username", "").lower()
                     or search.lower() in u.get("room_id", "").lower()]
    
    my_id = st.session_state.room_id
    
    for u in all_users:
        if u.get("room_id") == my_id:
            continue
        
        col1, col2, col3 = st.columns([3, 2, 2])
        
        genuine = is_genuine_user(u)
        
        with col1:
            st.markdown(f"""
            <div class="card card-blue">
              <b>{u.get('username', '?')}</b>
              {'<span class="badge badge-gold" style="margin-left:8px">Genuine ✓</span>' if genuine else ''}
              <br/><span class="room-id">{u.get('room_id', '')}</span>
              <p style="color:#666680; font-size:0.85rem; margin-top:0.5rem">{u.get('bio') or 'No bio.'}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.metric("Helped", u.get("total_helped", 0))
            st.metric("Avg Rating", f"{u.get('avg_rating', 0):.1f}⭐")
        
        with col3:
            user_data = DAL.get_user(my_id)
            friends   = user_data.get("friends", []) if user_data else []
            following  = user_data.get("following", []) if user_data else []
            target_id  = u.get("room_id")
            
            is_friend    = target_id in friends
            is_following = target_id in following
            
            if not is_friend:
                if st.button("🤝 Add Friend", key=f"friend_{target_id}"):
                    DAL.add_friend(my_id, target_id)
                    st.success(f"Added {u.get('username')} as friend!")
                    st.rerun()
            else:
                st.markdown('<span class="badge badge-gold">Friends ✓</span>', unsafe_allow_html=True)
            
            if not is_following:
                if st.button("➕ Follow", key=f"follow_{target_id}"):
                    DAL.follow_user(my_id, target_id)
                    st.success(f"Following {u.get('username')}!")
                    st.rerun()
            
            if st.button("💬 DM", key=f"dm_{target_id}"):
                st.session_state.dm_target = target_id
                st.session_state.nav = "💬  DMs"
                st.rerun()
        
        st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 8: MAIN APPLICATION ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    inject_styles()
    init_demo_state()
    
    # ── Auth gate ──────────────────────────────────────────────────────────────
    if not st.session_state.get("logged_in"):
        page_auth()
        return
    
    # ── Sidebar navigation ─────────────────────────────────────────────────────
    with st.sidebar:
        user = DAL.get_user(st.session_state.room_id)
        if user:
            genuine = is_genuine_user(user)
            badge = "🏅" if genuine else "⬡"
            st.markdown(f"### {badge} {user.get('username', '?')}")
            st.markdown(f'<span class="room-id">{st.session_state.room_id[:20]}...</span>', unsafe_allow_html=True)
            st.markdown(f'<span class="wallet-display">{sc(user.get("wallet_sc", 0))}</span>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        pages = [
            "🖥️  Studio",
            "🛒  Marketplace",
            "❓  Doubts Arena",
            "💬  DMs",
            "📹  Video Call",
            "👥  Profiles",
        ]
        
        nav = st.radio("Navigate", pages, key="nav", label_visibility="collapsed")
        
        st.markdown("---")
        
        # Network stats
        treasury = DAL.get_treasury()
        st.markdown("**⬡ Network Stats**")
        st.markdown(f"""
        <div style="font-family:'Space Mono',monospace; font-size:0.75rem; color:var(--muted)">
        Treasury: {treasury.get('treasury_balance', 0):,} SC<br/>
        Circulating: {treasury.get('circulating', 0):,} SC<br/>
        Transactions: {treasury.get('total_transactions', 0):,}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🚪 Logout"):
            for key in ["logged_in", "room_id", "user_data", "seed_phrase"]:
                st.session_state.pop(key, None)
            st.rerun()
    
    # ── Route to page ──────────────────────────────────────────────────────────
    if "Studio" in nav:
        page_studio()
    elif "Marketplace" in nav:
        page_marketplace()
    elif "Doubts" in nav:
        page_doubts()
    elif "DMs" in nav:
        page_dms()
    elif "Video" in nav:
        page_video_call()
    elif "Profiles" in nav:
        page_profiles()


if __name__ == "__main__":
    main()
