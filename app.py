# app.py
import streamlit as st
from openai import OpenAI
from fpdf import FPDF
import json
import os
from datetime import datetime
import traceback
import sqlite3
from passlib.hash import pbkdf2_sha256
import re


def get_db_path():
    if 'streamlit' in os.getcwd():  # Detect if running in Streamlit Cloud
        return '/tmp/prepclass.db'  # Use /tmp which has write permissions
    return 'prepclass.db'  # Local development path


# Database setup
def init_db():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, 
                  password_hash TEXT)''')
    
    # History table
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  topic TEXT,
                  difficulty TEXT,
                  timestamp TEXT,
                  pre_class TEXT,
                  in_class TEXT,
                  post_class TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# Password hashing
def hash_password(password):
    return pbkdf2_sha256.hash(password)

def verify_password(password, hashed):
    return pbkdf2_sha256.verify(password, hashed)

# Authentication functions
def create_user(username, password):
    conn = sqlite3.connect('prepclass.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?)", 
                 (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Username exists
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = sqlite3.connect('prepclass.db')
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result and verify_password(password, result[0]):
        return True
    return False

# History database functions
def save_history_to_db(username, topic, difficulty, content):
    conn = sqlite3.connect('prepclass.db')
    c = conn.cursor()
    
    # Check if topic exists for this user
    c.execute('''SELECT id FROM history 
                 WHERE username=? AND topic=?''', (username, topic))
    exists = c.fetchone()
    
    if exists:
        # Update existing entry
        c.execute('''UPDATE history SET 
                    difficulty=?, timestamp=?, 
                    pre_class=?, in_class=?, post_class=?
                    WHERE id=?''',
                 (difficulty, datetime.now().strftime("%Y-%m-%d %H:%M"),
                  content["pre_class"], content["in_class"], content["post_class"],
                  exists[0]))
    else:
        # Insert new entry
        c.execute('''INSERT INTO history 
                    (username, topic, difficulty, timestamp, pre_class, in_class, post_class)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (username, topic, difficulty, 
                  datetime.now().strftime("%Y-%m-%d %H:%M"),
                  content["pre_class"], content["in_class"], content["post_class"]))
    
    conn.commit()
    conn.close()

def load_history_from_db(username):
    conn = sqlite3.connect('prepclass.db')
    c = conn.cursor()
    c.execute('''SELECT topic, difficulty, timestamp, 
                pre_class, in_class, post_class 
                FROM history WHERE username=? 
                ORDER BY timestamp DESC''', (username,))
    history = {}
    for row in c.fetchall():
        topic, difficulty, timestamp, pre_class, in_class, post_class = row
        history[topic] = {
            "difficulty": difficulty,
            "timestamp": timestamp,
            "pre_class": pre_class,
            "in_class": in_class,
            "post_class": post_class
        }
    conn.close()
    return history

# Authentication UI
def auth_ui():
    st.title("PrepClass Mentor Login")
    with st.container():
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login"):
                if authenticate_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        with tab2:
            new_user = st.text_input("New Username", key="new_user")
            new_pass = st.text_input("New Password", type="password", key="new_pass")
            confirm_pass = st.text_input("Confirm Password", type="password", key="confirm_pass")
            
            if st.button("Create Account"):
                if not new_user or not new_pass:
                    st.error("Username and password required")
                elif new_pass != confirm_pass:
                    st.error("Passwords don't match")
                elif not re.match("^[a-zA-Z0-9_]{3,20}$", new_user):
                    st.error("Username must be 3-20 chars (letters, numbers, _)")
                elif len(new_pass) < 8:
                    st.error("Password must be at least 8 characters")
                else:
                    if create_user(new_user, new_pass):
                        st.success("Account created! Please login")
                    else:
                        st.error("Username already exists")

# Main App
def main_app():
    # Initialize session state for history
    if 'history' not in st.session_state:
        st.session_state.history = load_history_from_db(st.session_state.username)
    
    if 'current_topic' not in st.session_state:
        st.session_state.current_topic = None
        
    if 'displayed_content' not in st.session_state:
        st.session_state.displayed_content = {
            "pre_class": None,
            "in_class": None,
            "post_class": None
        }

    if 'selected_difficulty' not in st.session_state:
        st.session_state.selected_difficulty = "Beginner"

    # Configure the app
    st.set_page_config(page_title="Placement Mentor", page_icon="🎓", layout="wide")
    st.title("🎓 Placement Mentor Dashboard")
    st.subheader(f"Welcome, {st.session_state.username}!")
    st.subheader("AI-powered Placement Preparation Toolkit for IIT Bombay Mentors")

    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Enter OpenAI API Key:", type="password", 
                               help="Get your API key from https://platform.openai.com/account/api-keys",
                               key="api_key_input")
        
        # Topic input
        topic = st.text_input("Enter Topic (e.g., Dynamic Programming, SQL Joins):", 
                             placeholder="Enter your topic here...",
                             key="topic_input")
        
        # Difficulty select
        difficulty = st.selectbox("Select Difficulty Level:", 
                                 ["Beginner", "Intermediate", "Advanced"],
                                 key="difficulty_display",
                                 index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.selected_difficulty))
        
        generate_btn = st.button("Generate Learning Materials", type="primary", key="generate_btn")
        
        st.divider()
        st.header("History")
        
        # Display history with selection
        if st.session_state.history:
            history_topics = list(st.session_state.history.keys())
            selected_topic = st.selectbox("Previously Generated Topics:", history_topics, key="history_select")
            
            if st.button("Load Selected Topic", key="load_topic_btn"):
                # Load content from history without modifying widget states
                st.session_state.current_topic = selected_topic
                history = st.session_state.history[selected_topic]
                st.session_state.displayed_content = {
                    "pre_class": history["pre_class"],
                    "in_class": history["in_class"],
                    "post_class": history["post_class"]
                }
                # Update the selected difficulty in our safe session state variable
                st.session_state.selected_difficulty = history["difficulty"]
                st.rerun()
        else:
            st.info("No generation history yet")
        
        # Clear history button
        if st.button("Clear History", key="clear_history_btn"):
            st.session_state.history = {}
            st.session_state.current_topic = None
            st.session_state.displayed_content = {
                "pre_class": None,
                "in_class": None,
                "post_class": None
            }
            st.session_state.selected_difficulty = "Beginner"
            st.rerun()
        
        # Logout button
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.rerun()

    # Document generation functions using GPT-4o
    def generate_document(prompt, api_key):
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert computer science mentor preparing IIT Bombay students for placements."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    def generate_pre_class(topic, difficulty, api_key):
        prompt = f"""
        Create a comprehensive pre-class document for {difficulty.lower()} level undergraduate students preparing for placement interviews. 
        Topic: {topic}
        
        Document should include:
        1. Brief overview (1 paragraph)
        2. 5 key concepts with concise explanations
        3. Prerequisite knowledge required
        4. Real-world applications (2-3 examples)
        5. Recommended pre-reading (3-5 bullet points)
        6. Common interview questions related to the topic
        
        Format as a structured document with clear headings. Use academic but accessible language.
        """
        return generate_document(prompt, api_key)

    def generate_in_class(topic, difficulty, api_key):
        prompt = f"""
        Create a detailed 1-hour lesson plan for teaching {topic} to {difficulty.lower()} level students at IIT Bombay.
        
        Structure:
        1. Learning objectives (3-5 bullet points)
        2. Time-allocated session breakdown:
           - Introduction (5 minutes)
           - Core concept explanation (15 minutes)
           - Practical example walkthrough (20 minutes)
           - Student practice activity (15 minutes)
           - Q&A and summary (5 minutes)
        3. Teaching tips and common pitfalls
        4. Required materials/resources
        5. Engagement strategies for each section
        6. Whiteboard diagrams/examples to use
        
        Include specific IIT Bombay context where relevant.
        """
        return generate_document(prompt, api_key)

    def generate_post_class(topic, difficulty, api_key):
        prompt = f"""
        Create a post-class document for {topic} at {difficulty.lower()} level including:
        
        1. Key takeaways summary (1 paragraph)
        2. 8-question quiz (4 MCQ, 2 true/false, 2 short answer) with solutions
        3. Additional practice problems (3-5) with difficulty ratings
        4. Recommended next steps/resources for further learning
        5. Common mistakes to avoid in interviews
        
        Format with clear section headings. Include IIT-specific examples where appropriate.
        """
        return generate_document(prompt, api_key)

    # PDF generation with built-in font to avoid external dependencies
    def create_pdf(content, filename):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Function to clean text for PDF
        def clean_text(text):
            return text.encode('latin-1', 'replace').decode('latin-1')
        
        # Split content into lines
        lines = content.split('\n')
        for line in lines:
            # Handle section headings
            if line.strip().endswith(':') or (line.strip() and line.strip()[0] == '#'):
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(200, 10, txt=clean_text(line), ln=True)
                pdf.set_font("Arial", size=12)
            else:
                pdf.multi_cell(0, 8, txt=clean_text(line))
        
        return pdf.output(dest='S').encode('latin1')

    def create_markdown(content, filename):
        return content.encode('utf-8')

    # Display function for content
    def display_content():
        if not st.session_state.displayed_content["pre_class"]:
            return
        
        topic = st.session_state.current_topic or "current_topic"
        
        col1, col2, col3 = st.tabs(["Pre-Class", "In-Class", "Post-Class"])
        
        with col1:
            st.subheader("Pre-Class Document")
            st.write(st.session_state.displayed_content["pre_class"])
            
            # Download buttons
            pdf_btn = st.download_button(
                label="Download PDF",
                data=create_pdf(st.session_state.displayed_content["pre_class"], f"pre_class_{topic}"),
                file_name=f"pre_class_{topic}.pdf",
                mime="application/pdf",
                key="pre_class_pdf"
            )
            md_btn = st.download_button(
                label="Download Markdown",
                data=create_markdown(st.session_state.displayed_content["pre_class"], f"pre_class_{topic}"),
                file_name=f"pre_class_{topic}.md",
                mime="text/markdown",
                key="pre_class_md"
            )
        
        with col2:
            st.subheader("In-Class Lesson Plan")
            st.write(st.session_state.displayed_content["in_class"])
            
            pdf_btn = st.download_button(
                label="Download PDF",
                data=create_pdf(st.session_state.displayed_content["in_class"], f"in_class_{topic}"),
                file_name=f"in_class_{topic}.pdf",
                mime="application/pdf",
                key="in_class_pdf"
            )
            md_btn = st.download_button(
                label="Download Markdown",
                data=create_markdown(st.session_state.displayed_content["in_class"], f"in_class_{topic}"),
                file_name=f"in_class_{topic}.md",
                mime="text/markdown",
                key="in_class_md"
            )
        
        with col3:
            st.subheader("Post-Class Materials")
            st.write(st.session_state.displayed_content["post_class"])
            
            pdf_btn = st.download_button(
                label="Download PDF",
                data=create_pdf(st.session_state.displayed_content["post_class"], f"post_class_{topic}"),
                file_name=f"post_class_{topic}.pdf",
                mime="application/pdf",
                key="post_class_pdf"
            )
            md_btn = st.download_button(
                label="Download Markdown",
                data=create_markdown(st.session_state.displayed_content["post_class"], f"post_class_{topic}"),
                file_name=f"post_class_{topic}.md",
                mime="text/markdown",
                key="post_class_md"
            )

    # Main content generation
    if generate_btn:
        current_topic = st.session_state.topic_input if 'topic_input' in st.session_state else None
        if not current_topic:
            st.warning("Please enter a topic first")
            st.stop()
        
        if not api_key:
            st.warning("Please enter your OpenAI API key")
            st.stop()
            
        try:
            with st.spinner(f"Generating {st.session_state.selected_difficulty} level materials for '{current_topic}' using GPT-4o..."):
                # Generate documents using the current topic from session state
                pre_class_content = generate_pre_class(current_topic, st.session_state.selected_difficulty, api_key)
                in_class_content = generate_in_class(current_topic, st.session_state.selected_difficulty, api_key)
                post_class_content = generate_post_class(current_topic, st.session_state.selected_difficulty, api_key)
                
                # Store in session state
                st.session_state.displayed_content = {
                    "pre_class": pre_class_content,
                    "in_class": in_class_content,
                    "post_class": post_class_content
                }
                st.session_state.current_topic = current_topic
                
                # Save to history in database
                save_history_to_db(
                    st.session_state.username,
                    current_topic,
                    st.session_state.selected_difficulty,
                    {
                        "pre_class": pre_class_content,
                        "in_class": in_class_content,
                        "post_class": post_class_content
                    }
                )
                
                # Reload history from DB to update session state
                st.session_state.history = load_history_from_db(st.session_state.username)
                
                st.success("Materials generated successfully!")
                st.rerun()
        
        except Exception as e:
            st.error(f"Error generating materials: {str(e)}")
            st.info("Please check your API key and try again")

    # Display content if available
    if (st.session_state.displayed_content["pre_class"] and 
        st.session_state.displayed_content["in_class"] and 
        st.session_state.displayed_content["post_class"]):
        display_content()
    else:
        # Display instructions if no content
        st.info("""
        **Welcome to PrepClass Mentor!**
        
        To get started:
        1. Enter your OpenAI API key in the sidebar
        2. Enter a technical topic
        3. Select difficulty level
        4. Click 'Generate Learning Materials'
        
        This tool will create:
        - **Pre-Class Document**: Student preparation material
        - **In-Class Lesson Plan**: Teaching guide for 1-hour session
        - **Post-Class Materials**: Quiz and summary for reinforcement
        """)
        
        # Sample output display
        with st.expander("Sample Output Preview"):
            st.subheader("Pre-Class Document Sample")
            st.code("""
            # Dynamic Programming (Intermediate Level)
            
            ## Overview
            Dynamic Programming (DP) is an algorithmic technique for solving complex problems by breaking them down into simpler subproblems...
            
            ## Key Concepts
            1. Overlapping Subproblems: Problems that can be broken down into subproblems which are reused multiple times...
            2. Optimal Substructure: An optimal solution to the problem contains optimal solutions to subproblems...
            """)
            
            st.subheader("In-Class Lesson Plan Sample")
            st.code("""
            ## Dynamic Programming Workshop (60 mins)
            
            ### Introduction (5 mins)
            - Define DP and its importance in coding interviews
            - Show real-world applications: Fibonacci sequence, shortest path problems
            
            ### Core Concepts (15 mins)
            - Explain memoization vs. tabulation
            - Walk through Fibonacci sequence implementation
            """)

    # Export history feature
    if st.session_state.history:
        st.sidebar.divider()
        st.sidebar.header("Export History")
        history_json = json.dumps(st.session_state.history, indent=2)
        st.sidebar.download_button(
            label="Download History as JSON",
            data=history_json,
            file_name="prepclass_history.json",
            mime="application/json",
            key="history_download"
        )

    # Add footer
    st.divider()
    st.caption("Cantilever Mentor v1.0 | Developed for IIT Bombay Placement Preparation | Using GPT-4o model")

# App flow control
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if st.session_state.authenticated:
    main_app()
else:
    auth_ui()