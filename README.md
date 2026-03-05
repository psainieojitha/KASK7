# MindBridge 🧠
**A Privacy-First, Layered Mental Health Support Platform for Students**

## Overview
MindBridge is a hackathon prototype designed to bridge the gap between simple emotional distress and professional therapeutic help. Many students suffer in silence due to the stigma of seeking help, the cost of therapy, or the fear of their private data being tracked by big tech platforms.

MindBridge solves this by offering a **3-Layered Support System** where the student retains absolute control over their data at all times.

## The 3-Layered Architecture

### Layer 1: On-Device Private AI Support
- **The Problem:** Students need immediate, consequence-free emotional support without fear of surveillance.
- **The Solution:** A secure chat interface powered entirely by a local Large Language Model (e.g., `gemma3:1b` via Ollama). 
- **Privacy Guarantee:** Inference happens 100% on the student's hardware. Nothing is sent to OpenAI, Google, or any cloud API.
- **Data Isolation:** Conversations are stored locally in an on-device SQLite database (`mindbridge_local.db`). Students can create isolated "Chat Spaces" (e.g., "Exam Stress", "Roommate Issue") to compartmentalize their concerns.

### Layer 2: Anonymous Community
- **The Problem:** Sometimes students just need to know they aren't alone.
- **The Solution:** A peer-support bulletin board where users are automatically assigned whimsical, randomized IDs (e.g., `CalmRiver42`, `SilentPath33`). 
- **Safety:** Students can post their struggles and receive empathetic replies from peers without tying anything back to their real identity or university ID.

### Layer 3: The Professional Handoff (Private-to-Professional Bridge)
- **The Problem:** When a student finally decides to see a therapist, the intake process is exhausting. Summarizing weeks of complex emotions is difficult and often inaccurate.
- **The Solution:** The user can trigger the **"Summarize for Professional"** feature inside any Chat Space.
- **How it works:**
  1. The local AI reads the chat history and drafts a clinical, bulleted summary of their core concerns.
  2. The draft is presented on a **Review Screen** where the student can freely edit, redact, or expand on the text.
  3. Once approved, the app generates a clean PDF report stamped with a **"✅ STUDENT-VERIFIED (Stored On-Device)"** badge.
  4. The PDF is saved directly to the user's hard drive to be emailed or handed to a professional therapist on their own terms.

## Tech Stack
- **Frontend & Backend Logic:** Python + Streamlit 
- **Styling:** Custom injected CSS (`Inter` font, soft shadows, rounded dynamic components)
- **Local AI Inference:** Ollama API (`http://localhost:11434`)
- **Database:** Local SQLite (`sqlite3`)
- **Document Generation:** `fpdf2`

## Core Narrative for the Pitch
*“MindBridge isn’t just an AI chatbot. It’s an escalating ladder of care. It starts with a private, on-device AI space where you can safely vent. It moves to an anonymous community where you realize you aren’t alone. And when you are ready, it acts as a bridge, synthesizing your emotional journey into a student-verified document that helps a real therapist understand you immediately.”*
