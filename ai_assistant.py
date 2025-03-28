import streamlit as st
import os
import json
from openai import OpenAI
from email_validator import validate_email, EmailNotValidError

# Load API Key
api_key = os.getenv("NVIDIA_API_KEY")

USER_DB = "users.json"
CHAT_DB = "chats.json"

def load_json(file):
    return json.load(open(file)) if os.path.exists(file) else {}

def save_json(data, file):
    json.dump(data, open(file, "w"))

def get_ai_response(messages):
    if not api_key:
        return "API key not found. Please set NVIDIA_API_KEY."
    try:
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
        completion = client.chat.completions.create(
            model="meta/llama-3.1-405b-instruct",
            messages=messages,
            temperature=0.2,
            top_p=0.7,
            max_tokens=1024
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# Initialize Session State
if "logged_in" not in st.session_state:
    st.session_state.update({
        "logged_in": False,
        "username": "",
        "selected_chat_index": None,
        "generated_questions": [],
        "candidate_info": {},
        "submitted": False
    })

users = load_json(USER_DB)
chats = load_json(CHAT_DB)

st.set_page_config(layout="wide")
st.title("AI-Powered Interview Chatbot")

# Authentication
if not st.session_state.logged_in:
    st.subheader("Login / Signup")
    option = st.radio("Select an option", ["Login", "Signup"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if option == "Signup" and st.button("Sign Up"):
        if username in users:
            st.error("Username already exists!")
        else:
            users[username] = password
            save_json(users, USER_DB)
            st.success("Signup successful! Please log in.")
    elif st.button("Login"):
        if username in users and users[username] == password:
            st.session_state.update({"logged_in": True, "username": username})
            st.experimental_rerun()
        else:
            st.error("Invalid credentials! Please Sign Up.")
    st.stop()

# Logout
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.experimental_rerun()

# Chat Handling
if st.session_state.username not in chats:
    chats[st.session_state.username] = []

chat_name = st.sidebar.text_input("Enter Chat Name")
if st.sidebar.button("Create Chat"):
    if chat_name and not any(chat['name'] == chat_name for chat in chats[st.session_state.username]):
        chats[st.session_state.username].append({"name": chat_name, "questions": []})
        save_json(chats, CHAT_DB)
        
        # Reset session state to show form again
        st.session_state.selected_chat_index = len(chats[st.session_state.username]) - 1
        st.session_state.candidate_info = {}  
        st.session_state.submitted = False  
        st.session_state.generated_questions = []  

        st.experimental_rerun()
    else:
        st.sidebar.warning("Chat name already exists or is empty.")


# Display Chats
st.sidebar.subheader("Chat Sessions")
for i, chat in enumerate(chats[st.session_state.username]):
    if st.sidebar.button(chat["name"], key=f"chat_{i}"):
        st.session_state.selected_chat_index = i
        st.session_state.generated_questions = chat.get("questions", [])
        st.experimental_rerun()

# Delete Chat
if st.sidebar.button("Delete Chat") and st.session_state.selected_chat_index is not None:
    del chats[st.session_state.username][st.session_state.selected_chat_index]
    save_json(chats, CHAT_DB)
    st.session_state.selected_chat_index = None
    st.experimental_rerun()

# Candidate Info Form & Generate Questions
st.subheader(f"Hello, {st.session_state.username}")
if not st.session_state.submitted:
    st.write("### Enter Candidate Details")
    for key in ["name", "email", "phone", "experience", "position", "tech_stack"]:
        value = st.text_input(key.replace("_", " ").title(), value=st.session_state.candidate_info.get(key, ""))
        st.session_state.candidate_info[key] = value
        
        
        if key == "email" and value:
            try:
                validate_email(value)
            except EmailNotValidError:
                st.error("Invalid Email ID!")
        if key == "phone" and value and (len(value) != 10 or not value.isdigit()):
            st.error("Invalid Phone Number!")

    if st.button("Generate Questions"):
        tech_stack = st.session_state.candidate_info.get("tech_stack", "").strip()
        role = st.session_state.candidate_info.get("position", "").strip()

        if not tech_stack or not role:
            st.warning("Tech stack and role are required.")
        else:
            prompt = f"Generate 3-5 technical interview questions for a {role} skilled in {tech_stack}."
            messages = [{"role": "user", "content": prompt}]
            questions = get_ai_response(messages).split("\n")

            if st.session_state.selected_chat_index is not None:
                chats[st.session_state.username][st.session_state.selected_chat_index]["questions"] = questions
                save_json(chats, CHAT_DB)

            st.session_state.generated_questions = questions
            st.session_state.submitted = True  
            st.experimental_rerun()

questions = []
current_question = None

for line in st.session_state.generated_questions:
    if line.startswith("**Question"): 
        if current_question:  
            questions.append(current_question)
        current_question = line + "\n\n" 
    elif current_question is not None:  
        current_question += line + "\n"

if current_question:  
    questions.append(current_question)


for i, q in enumerate(questions, start=1):
    with st.expander(f"Question {i}"):
        st.write(q)

st.subheader("Doubts Clarification")
doubt_query = st.text_area("Ask your doubts")
if st.button("Submit Doubt") and doubt_query:
    messages = [{"role": "user", "content": doubt_query}]
    doubt_response = get_ai_response(messages)
    st.write("### Chatbot Response")
    st.write(doubt_response)
