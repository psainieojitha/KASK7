import streamlit as st
import time
import random
import requests
from datetime import datetime
import sqlite3
from fpdf import FPDF
import base64
import os

# --- Configuration ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:1b"
DB_PATH = "mindbridge_local.db"

# --- Page Configuration ---
st.set_page_config(
    page_title="MindBridge - Mental Health Support",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Advanced Styling ---
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    
    /* Main Background & Text */
    .stApp {
        background-color: #F8FAFC;
        color: #1E293B;
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3 {
        color: #0F172A;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        letter-spacing: -0.025em;
    }
    
    /* Supportive Cards */
    div.stCard {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 24px;
        border: 1px solid #F1F5F9;
        border-left: 6px solid #3B82F6;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div.stCard:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #3B82F6;
        color: white;
        border-radius: 9999px;
        padding: 10px 24px;
        font-weight: 500;
        border: none;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #2563EB;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    /* Chat messages */
    .user-msg {
        background-color: #EFF6FF;
        padding: 16px 20px;
        border-radius: 20px 20px 4px 20px;
        margin: 12px 0 12px auto;
        border: 1px solid #DBEAFE;
        max-width: 85%;
        color: #1E40AF;
        font-size: 1.05rem;
    }
    .ai-msg {
        background-color: #ffffff;
        padding: 16px 20px;
        border-radius: 20px 20px 20px 4px;
        margin: 12px auto 12px 0;
        border: 1px solid #F1F5F9;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        max-width: 85%;
        color: #334155;
        font-size: 1.05rem;
        line-height: 1.6;
    }
    
    /* PDF Badge Style */
    .verified-badge {
        display: inline-block;
        background-color: #D1FAE5;
        color: #065F46;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8em;
        margin-top: 10px;
        border: 1px solid #10B981;
    }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- Database Integration (Layer 1) ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_spaces
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, space_id INTEGER, role TEXT, content TEXT, timestamp TEXT,
                 FOREIGN KEY(space_id) REFERENCES chat_spaces(id))''')
    conn.commit()
    conn.close()

def get_chat_spaces():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name FROM chat_spaces ORDER BY id DESC")
    spaces = c.fetchall()
    conn.close()
    return spaces

def create_chat_space(name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO chat_spaces (name, created_at) VALUES (?, ?)", (name, timestamp))
    new_id = c.lastrowid
    
    # Insert initial AI greeting
    initial_msg = "Hi there. I'm MindBridge AI, running securely on your device. What would you like to talk about in this space?"
    c.execute("INSERT INTO messages (space_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
              (new_id, "assistant", initial_msg, timestamp))
              
    conn.commit()
    conn.close()
    return new_id

def rename_chat_space(space_id, new_name):
    if not space_id or not new_name.strip(): return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE chat_spaces SET name = ? WHERE id = ?", (new_name.strip(), space_id))
    conn.commit()
    conn.close()

def get_messages(space_id):
    if not space_id:
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE space_id=? ORDER BY id ASC", (space_id,))
    messages = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
    conn.close()
    return messages

def add_message(space_id, role, content):
    if not space_id: return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO messages (space_id, role, content, timestamp) VALUES (?, ?, ?, ?)", 
              (space_id, role, content, timestamp))
    conn.commit()
    conn.close()

# Ensure DB exists
init_db()

# --- Helper Functions ---
def generate_anonymous_name():
    adjectives = ["Calm", "Quiet", "Silver", "Gentle", "Brave", "Silent", "Peaceful"]
    nouns = ["River", "Sky", "Leaf", "Meadow", "Breeze", "Path", "Ocean"]
    num = random.randint(10, 99)
    return f"{random.choice(adjectives)}{random.choice(nouns)}{num}"

def query_ollama(prompt, system_prompt="You are a supportive mental health assistant."):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "I'm having trouble thinking right now. Could you tell me more?")
    except requests.exceptions.RequestException:
        return f"💡 **[Local AI Offline]** Please ensure Ollama is running locally with `{OLLAMA_MODEL}`. Local privacy cannot be guaranteed without it."

def get_ai_support_response(user_input, chat_history):
    context = ""
    for msg in chat_history[-6:]: 
        role = "User" if msg["role"] == "user" else "Assistant"
        context += f"{role}: {msg['content']}\n"
    
    system_prompt = (
        "You are MindBridge, an empathetic, private, and non-judgmental mental health AI "
        "designed to support students. Do not diagnose or offer professional medical advice. "
        "Provide comforting, concise responses. Encourage reflection, breathing exercises, and positive coping strategies. "
    )
    prompt = f"{context}\nUser: {user_input}\nAssistant:"
    return query_ollama(prompt, system_prompt)

def generate_therapist_summary(messages):
    history_text = "\n".join([f"{'User' if m['role']=='user' else 'AI'}: {m['content']}" for m in messages if m['content']])
    system_prompt = (
        "You are an assistant for a human therapist. Summarize the user's concerns based strictly on the chat history. "
        "Do not diagnose. Keep it brief. Use this format:\n\n"
        "Main Concern:\n[Brief paragraph]\n\n"
        "Symptoms Mentioned:\n- [Symptom 1]\n- [Symptom 2]\n\n"
        "AI Observations:\n[Brief, non-diagnostic observation]"
    )
    prompt = f"Summarize the following interaction securely and locally:\n\n{history_text}\n\nSummary:"
    return query_ollama(prompt, system_prompt)

# --- Layer 3: PDF Generation ---
def generate_pdf_report(summary_text, username):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Header
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, "MindBridge Professional Hand-off", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 5, f"Date Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.cell(0, 5, "Strictly Confidential | Locally Verified", ln=True, align="C")
    pdf.ln(10)
    
    # Body
    pdf.set_font("Arial", '', 12)
    # Strip smart quotes and other common unsupported unicode chars
    clean_summary = summary_text.replace("”", '"').replace("“", '"').replace("’", "'").replace("‘", "'")
    pdf.multi_cell(0, 8, txt=f"Anonymous ID: {username}\n\n{clean_summary}")
    
    # Badge equivalent text at the bottom
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(6, 95, 70) # Dark green
    pdf.cell(0, 10, "VALIDATED: STUDENT-VERIFIED (Stored On-Device)", border=1, ln=True, align="C", fill=False)
    
    # fpdf2 .output() returns a bytearray object, so we don't need .encode()
    return bytes(pdf.output())

# --- Initialize Session State ---
if 'mood' not in st.session_state:
    st.session_state.mood = None
if 'username' not in st.session_state:
    st.session_state.username = generate_anonymous_name()
if 'active_space_id' not in st.session_state:
    st.session_state.active_space_id = None
if 'show_summary_review' not in st.session_state:
    st.session_state.show_summary_review = False
if 'draft_summary' not in st.session_state:
    st.session_state.draft_summary = ""

# Auto-create first space if empty
if not get_chat_spaces():
    st.session_state.active_space_id = create_chat_space("Initial Conversation")

# Set active space if none is selected
if st.session_state.active_space_id is None:
    spaces = get_chat_spaces()
    if spaces:
        st.session_state.active_space_id = spaces[0][0]

# --- 0. Mood Check-In ---
if st.session_state.mood is None:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 3rem;'>MindBridge 🌱</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #64748B; font-weight: 400;'>On-Device Private Emotional Support</h3>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color: #E2E8F0; margin: 40px auto; max-width: 600px;'>", unsafe_allow_html=True)
    
    st.markdown("<h4 style='text-align: center; color: #334155; margin-bottom: 30px;'>Before we begin, how are you feeling right now?</h4>", unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 2])
    with col1: st.write("")
    with col2:
        if st.button("🙂 Calm", use_container_width=True):
            st.session_state.mood = "Calm"
            st.rerun()
    with col3:
        if st.button("😐 Okay", use_container_width=True):
            st.session_state.mood = "Okay"
            st.rerun()
    with col4:
        if st.button("😟 Stressed", use_container_width=True):
            st.session_state.mood = "Stressed"
            st.rerun()
    with col5:
        if st.button("😢 Overwhelmed", use_container_width=True):
            st.session_state.mood = "Overwhelmed"
            st.rerun()
    st.stop()


# --- Main Navigation Sidebar ---
st.sidebar.title("🌱 MindBridge")
st.sidebar.markdown(f"**Anonymous ID:** `{st.session_state.username}`")

if st.session_state.mood:
    st.sidebar.info(f"Initial Mood: **{st.session_state.mood}**")
    
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", ["1. Private AI Support", "2. Anonymous Community", "3. Therapist Directory"])

# Chat Spaces Sidebar UI (Layer 1)
if page == "1. Private AI Support":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 My Chat Spaces")
    st.sidebar.caption("Isolated, on-device conversations.")
    
    new_space_name = st.sidebar.text_input("New Space Name", placeholder="e.g. Exam Stress", key="new_space")
    if st.sidebar.button("➕ Create Space", use_container_width=True):
        if new_space_name.strip():
            new_id = create_chat_space(new_space_name.strip())
            st.session_state.active_space_id = new_id
            st.session_state.show_summary_review = False
            st.rerun()
            
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    
    spaces = get_chat_spaces()
    for space_id, space_name in spaces:
        # Highlight active space
        btn_type = "primary" if space_id == st.session_state.active_space_id else "secondary"
        if st.sidebar.button(f"🗯️ {space_name}", key=f"space_{space_id}", type=btn_type, use_container_width=True):
            st.session_state.active_space_id = space_id
            st.session_state.show_summary_review = False
            st.rerun()
            
        # If this is the active space, show a tiny rename field beneath it
        if space_id == st.session_state.active_space_id:
            rename_val = st.sidebar.text_input("Rename", value=space_name, key=f"rename_{space_id}", label_visibility="collapsed")
            if rename_val != space_name and rename_val.strip() != "":
                rename_chat_space(space_id, rename_val)
                st.rerun()



st.sidebar.markdown("---")
st.sidebar.caption("🔒 **Security Constraint:** Strictly NO auto-sync to cloud. Data is stored in local SQLite only.")


# --- 1. Private AI Support Mode (Layer 1 Base) ---
if page == "1. Private AI Support":
    
    # Layer 3 Handoff Trigger
    col_text, col_btn = st.columns([3, 2])
    with col_text:
        current_space_name = next((s[1] for s in get_chat_spaces() if s[0] == st.session_state.active_space_id), "Unknown")
        st.title(f"Private Base: {current_space_name} 🌿")
    with col_btn:
        st.write("")
        st.write("")
        if st.button("🗂️ Summarize for Professional", use_container_width=True):
            st.session_state.show_summary_review = True
            with st.spinner("Analyzing history locally..."):
                messages = get_messages(st.session_state.active_space_id)
                st.session_state.draft_summary = generate_therapist_summary(messages)
            st.rerun()
            
    # Professional Handoff Review Screen (Layer 3)
    if st.session_state.show_summary_review:
        st.markdown("---")
        st.markdown("### 📝 Professional Handoff Review")
        st.info("Please review and 'tweak' the AI-generated summary below. You have total control over this document.")
        
        edited_summary = st.text_area(
            "Review Screen (Editable text field)",
            value=st.session_state.draft_summary,
            height=250
        )
        
        pdf_bytes = generate_pdf_report(edited_summary, st.session_state.username)
        
        col_down, col_cancel = st.columns([1, 1])
        with col_down:
            st.download_button(
                label="📥 Download PDF Report (Local Export)", 
                data=pdf_bytes,
                file_name=f"mindbridge_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
            st.markdown("<div class='verified-badge'>✅ STUDENT-VERIFIED (On-Device)</div>", unsafe_allow_html=True)
            
        with col_cancel:
            if st.button("Cancel & Return to Chat", use_container_width=True):
                st.session_state.show_summary_review = False
                st.rerun()
        st.markdown("---")

    # Display Local Chat Interface
    if not st.session_state.show_summary_review:
        messages = get_messages(st.session_state.active_space_id)
        
        for msg in messages:
            if msg["role"] == "user":
                st.markdown(f'<div class="user-msg"><b>You</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="ai-msg"><b>MindBridge AI</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
                
        st.markdown("<br>", unsafe_allow_html=True)
        user_input = st.chat_input(f"Share what's on your mind securely...")
        
        if user_input:
            # Save user message to DB
            add_message(st.session_state.active_space_id, "user", user_input)
            st.markdown(f'<div class="user-msg"><b>You</b><br>{user_input}</div>', unsafe_allow_html=True)
            
            # Re-fetch messages for context
            updated_messages = get_messages(st.session_state.active_space_id)
            
            with st.spinner("MindBridge AI is reflecting (Local inference)..."):
                ai_reply = get_ai_support_response(user_input, updated_messages)
                
            # Save AI message to DB
            add_message(st.session_state.active_space_id, "assistant", ai_reply)
            st.rerun()

# --- 2. Anonymous Community Mode ---
elif page == "2. Anonymous Community":
    st.title("Anonymous Community 🤝")
    st.markdown(f"Welcome, **{st.session_state.username}**. Share your struggles and receive peer support without revealing your true identity.")
    
    # Initialize mock community posts if they don't exist yet
    if 'community_posts' not in st.session_state:
        st.session_state.community_posts = [
            {
                "id": 1, 
                "author": "QuietSky17", 
                "title": "Feeling stressed about exams", 
                "text": "I can't focus and deadlines are piling up. I don't know where to start.", 
                "time": "2 hours ago", 
                "replies": ["I feel you! Taking it one chapter at a time helps me.", "Hang in there, breaking it into smaller chunks really works."]
            },
            {
                "id": 2, 
                "author": "BraveOcean92", 
                "title": "Small wins today :)", 
                "text": "I finally managed to go for a 15-minute walk today after feeling down all week. Small victory!", 
                "time": "5 hours ago", 
                "replies": ["So proud of you! Small steps count.", "That's wonderful! 😊"]
            }
        ]

    with st.expander(f"📝 Write deeply. Post anonymously.", expanded=False):
        post_title = st.text_input("Title", placeholder="E.g., Feeling stressed about exams")
        new_post_text = st.text_area("Message", placeholder="I can't focus and deadlines are piling up...", height=150)
        if st.button("Post to Community"):
            if new_post_text.strip() and post_title.strip():
                new_post = {
                    "id": len(st.session_state.community_posts) + 1,
                    "author": st.session_state.username,
                    "title": post_title,
                    "text": new_post_text,
                    "time": "Just now",
                    "replies": []
                }
                st.session_state.community_posts.insert(0, new_post)
                st.success("Your post has been shared safely.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Please provide both a title and a message.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    for idx, post in enumerate(st.session_state.community_posts):
        st.markdown(f"""
        <div class='stCard'>
            <div style='display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #F1F5F9; padding-bottom: 10px; margin-bottom: 15px;'>
                <div>
                    <span style='font-size: 1.2rem;'>👤</span>
                    <strong style='color: #475569; margin-left: 5px;'>{post['author']}</strong>
                </div>
                <small style='color: #94A3B8;'>{post['time']}</small>
            </div>
            <h4 style='margin-top: 0; color: #0F172A; margin-bottom: 8px;'>{post['title']}</h4>
            <p style='color: #334155; line-height: 1.6; font-size: 1.05rem;'>{post['text']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if post["replies"]:
            for reply in post["replies"]:
                st.markdown(f"""
                <div style='margin-left: 32px; padding: 12px 16px; background-color: #F8FAFC; border-radius: 8px; border-left: 3px solid #CBD5E1; margin-bottom: 8px;'>
                    <span style='color: #1E293B;'>{reply}</span>
                </div>
                """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        reply_col1, reply_col2 = st.columns([5, 1])
        with reply_col1:
            reply_text = st.text_input("Reply", key=f"reply_input_{idx}", label_visibility="collapsed", placeholder="Offer an encouraging word...")
        with reply_col2:
            if st.button("Reply", key=f"btn_reply_{idx}", use_container_width=True):
                if reply_text.strip():
                    st.session_state.community_posts[idx]["replies"].append(reply_text)
                    st.rerun()
        st.markdown("<hr style='border-color: #F1F5F9; margin: 40px 0;'>", unsafe_allow_html=True)

# --- 3. Therapist Directory ---
elif page == "3. Therapist Directory":
    st.title("Therapist Directory 🩺")
    st.markdown("Find a verified professional to share your **Student-Verified PDF Report** with.")
    
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        st.markdown("""
        <div class='stCard' style='border-left-color: #10B981;'>
            <h4 style='margin-top:0;'>Dr. Sarah Jenkins</h4>
            <p style='color: #475569; font-size: 0.95em;'>Clinical Psychologist<br>Focus: Academic Pressure, Anxiety</p>
            <p style='color: #10B981; font-weight: 500; font-size: 0.9em;'>● Accepts University Insurance<br>● Next available: Today, 3:00 PM</p>
            <hr style='border-color: #F1F5F9; margin: 15px 0;'>
            <p style='color: #334155; font-size: 0.95em; margin-bottom: 5px;'><strong>📞 Phone:</strong> (555) 123-4567</p>
            <p style='color: #334155; font-size: 0.95em;'><strong>✉️ Email:</strong> intake@jenkinspsych.com</p>
        </div>
        """, unsafe_allow_html=True)
            
    with t_col2:
        st.markdown("""
        <div class='stCard' style='border-left-color: #10B981;'>
            <h4 style='margin-top:0;'>Mark Davis, LCSW</h4>
            <p style='color: #475569; font-size: 0.95em;'>Licensed Clinical Social Worker<br>Focus: Depression, Life Transitions</p>
            <p style='color: #10B981; font-weight: 500; font-size: 0.9em;'>● Out-of-network sliding scale<br>● Next available: Tomorrow, 10:00 AM</p>
            <hr style='border-color: #F1F5F9; margin: 15px 0;'>
            <p style='color: #334155; font-size: 0.95em; margin-bottom: 5px;'><strong>📞 Phone:</strong> (555) 987-6543</p>
            <p style='color: #334155; font-size: 0.95em;'><strong>✉️ Email:</strong> schedule@mdavislcsw.org</p>
        </div>
        """, unsafe_allow_html=True)
