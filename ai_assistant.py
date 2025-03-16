import streamlit as st
import os
import json
from openai import OpenAI
import re

# Fetch the API key from environment variables
api_key = os.getenv("NVIDIA_API_KEY")

# Simulated database for user authentication
USER_DB = "users.json"
CHAT_DB = "chats.json"

def load_users():
    if os.path.exists(USER_DB):
        with open(USER_DB, "r") as file:
            return json.load(file)
    return {}

def save_users(users):
    with open(USER_DB, "w") as file:
        json.dump(users, file)

def load_chats():
    if os.path.exists(CHAT_DB):
        with open(CHAT_DB, "r") as file:
            return json.load(file)
    return {}

def save_chats(chats):
    with open(CHAT_DB, "w") as file:
        json.dump(chats, file)

def get_ai_response(messages):
    if not api_key:
        return "API key not found. Please set NVIDIA_API_KEY in your environment."
    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        completion = client.chat.completions.create(
            model="meta/llama-3.1-405b-instruct",
            messages=messages,
            temperature=0.2,
            top_p=0.7,
            max_tokens=1024,
            stream=True
        )
        response_text = ""
        for chunk in completion:
            if chunk.choices[0].delta.content is not None:
                response_text += chunk.choices[0].delta.content
        return response_text
    except Exception as e:
        return f"Error: {e}"

users = load_users()
chats = load_chats()

# Streamlit UI Setup
st.set_page_config(layout="wide")
st.title("TalentScout Hiring Assistant - NVIDIA AI")

# User Authentication
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.subheader("Login / Signup")
    option = st.radio("Select an option", ["Login", "Signup"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if option == "Signup":
        if st.button("Sign Up"):
            if username in users:
                st.error("Username already exists!")
            else:
                users[username] = password
                save_users(users)
                st.success("Signup successful! Please log in.")
    elif st.button("Login"):
        if username in users and users[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.selected_chat_index = None
            st.session_state.generated_questions = []
            st.session_state.candidate_info = {}
            st.rerun()
        else:
            st.error("Invalid credentials!, SIGNUP TO USE")
    st.stop()

# User logged in
st.sidebar.write(f"Logged in as: {st.session_state.username}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.selected_chat_index = None
    st.session_state.generated_questions = []
    st.session_state.candidate_info = {}
    st.rerun()

# Ensure user has chat sessions
if st.session_state.username not in chats:
    chats[st.session_state.username] = []

# Create New Chat
chat_name = st.sidebar.text_input("Enter Chat Name")
if st.sidebar.button("Create Chat"):
    if chat_name:
        chats[st.session_state.username].append({"name": chat_name, "questions": []})
        save_chats(chats)
        st.session_state.selected_chat_index = len(chats[st.session_state.username]) - 1
        st.session_state.generated_questions = []
        st.session_state.candidate_info = {}
        st.rerun()
    else:
        st.sidebar.warning("Please enter a name for the chat.")

st.sidebar.subheader("Chat Sessions")
for i, chat in enumerate(chats[st.session_state.username]):
    if "name" in chat:
        if st.sidebar.button(chat["name"], key=f"chat_{i}"):
            st.session_state.selected_chat_index = i
            st.session_state.generated_questions = chat.get("questions", [])
            st.rerun()

# Handle Chat Deletion
if st.sidebar.button("Delete Chat"):
    if "selected_chat_index" in st.session_state and st.session_state.selected_chat_index is not None:
        del chats[st.session_state.username][st.session_state.selected_chat_index]
        save_chats(chats)
        st.session_state.selected_chat_index = None
        st.session_state.generated_questions = []
        st.session_state.candidate_info = {}
        st.rerun()
    else:
        st.sidebar.warning("No chat selected.")

selected_chat_index = st.session_state.get("selected_chat_index", None)

st.subheader("Candidate Information")
if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = {}

for key in ["name", "email", "phone", "experience", "position", "location", "tech_stack"]:
    st.session_state.candidate_info[key] = st.text_input(key.replace("_", " ").title(), value=st.session_state.candidate_info.get(key, ""))

# Generate technical interview questions
if st.button("Generate Technical Questions"):
    tech_stack = st.session_state.candidate_info.get("tech_stack", "").strip()
    role = st.session_state.candidate_info.get("position", "").strip()
    
    if not tech_stack and not role:
        st.warning("Both tech stack and role are missing or incorrect. Please enter valid details.")
    elif not tech_stack:
        st.warning("Tech stack is missing or incorrect. Please enter valid details.")
    elif not role:
        st.warning("Role is missing or incorrect. Please enter valid details.")
    else:
        prompt = f"Generate 3-5 technical interview questions for a candidate skilled in {tech_stack} applying for {role}."
        messages = [{"role": "user", "content": prompt}]
        questions = get_ai_response(messages).split('\n')
        if selected_chat_index is not None:
            chats[st.session_state.username][selected_chat_index]["questions"] = questions
            save_chats(chats)
        st.session_state.generated_questions = questions

st.write("### Technical Questions")
for q in st.session_state.generated_questions:
    st.write(q)

# Chatbot for doubts
st.subheader("Doubts Clarification")
doubt_query = st.text_area("Ask your doubts")
if st.button("Submit Doubt"):
    if doubt_query:
        messages = [{"role": "user", "content": doubt_query}]
        doubt_response = get_ai_response(messages)
        st.write("### Chatbot Response")
        st.write(doubt_response)
