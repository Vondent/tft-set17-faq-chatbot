import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import streamlit as st
from retrieval.retrieve import answer, get_collection, EMBED_MODEL, CHAT_MODEL

OLLAMA_URL = "http://localhost:11434"

def check_ollama():
    """Return (ok, error_message). Checks Ollama is up and required models are present."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        resp.raise_for_status()
    except Exception:
        return False, (
            "**Ollama is not running.**\n\n"
            "Start it with:\n```\nollama serve\n```"
        )

    installed = {m["name"].split(":")[0] for m in resp.json().get("models", [])}
    missing = [m for m in (EMBED_MODEL, CHAT_MODEL) if m.split(":")[0] not in installed]
    if missing:
        cmds = "\n".join(f"ollama pull {m}" for m in missing)
        return False, (
            f"**Missing Ollama models:** {', '.join(missing)}\n\n"
            f"Pull them with:\n```\n{cmds}\n```"
        )

    return True, None


st.set_page_config(page_title="TFT Set 17 FAQ", page_icon="🎮", layout="centered")
st.title("TFT Set 17 FAQ Bot")
st.caption("Powered by Qwen2.5 + nomic-embed-text · Local & free")

ok, err = check_ollama()
if not ok:
    st.error(err)
    st.stop()

@st.cache_resource
def load_collection():
    return get_collection()

collection = load_collection()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask anything about TFT Set 17..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = answer(prompt, collection)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
