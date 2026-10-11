"""Streamlit chatbot for tropical infectious disease education."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st
from google import genai
from google.genai import types

APP_TITLE = "TropiCare AI"
DEFAULT_MODEL = "gemini-2.5-flash"
KEMKES_PROFILE_URL = "https://www.kemkes.go.id/id/category/profil-kesehatan"

SYSTEM_INSTRUCTION = f"""
You are TropiCare AI, an Indonesian public-health education assistant focused on
 tropical infectious diseases such as malaria, dengue, chikungunya, tuberculosis,
 leptospirosis, and other diseases relevant to tropical regions.

Answer in the same language as the user's question. Use clear, non-alarmist language.
You provide general education only, never a diagnosis, prescription, or personalized
medicine dose. Do not infer that a user has a disease from symptoms. Encourage a
qualified health professional for personal advice.

When a user describes severe symptoms, recommend urgent medical evaluation. Mention
examples relevant to the question, such as difficulty breathing, confusion, seizure,
shock/fainting, severe dehydration, bleeding, persistent vomiting, or rapidly worsening
condition. Do not claim to contact emergency services.

For current case counts, outbreaks, or trends, do not invent numbers. Explain that the
Kementerian Kesehatan profile page is a publication index, not a live case dashboard.
Use the trusted context below only as a bibliographic reference, state its publication
date or year when known, and direct the user to the official page for verification.
If current data is unavailable, say so explicitly.

Reference source:
- Kementerian Kesehatan Republik Indonesia, Profil Kesehatan page:
  {KEMKES_PROFILE_URL}
- The page lists Profil Kesehatan Indonesia 2021, 2022, 2023, 2024, and 2025.
  The page shows the 2025 publication dated 1 September 2026 and the 2024 publication
  dated 12 September 2025. Treat these as publication metadata, not live surveillance.

Do not request or repeat unnecessary personal identifiers. Remind users not to share
sensitive health information in chat.
"""


def get_secret_api_key() -> str:
    """Read a deployed Streamlit secret without exposing it in the UI."""
    try:
        return str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except (FileNotFoundError, KeyError):
        return os.getenv("GEMINI_API_KEY", "").strip()


def create_client(api_key: str) -> genai.Client:
    """Create a Gemini client from a user-provided or configured key."""
    return genai.Client(api_key=api_key)


def generate_answer(client: genai.Client, history: list[dict[str, str]]) -> str:
    """Generate one answer while keeping the safety instruction server-side."""
    contents: list[types.Content] = []
    for message in history:
        role = "user" if message["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=message["content"])],
            )
        )

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
            max_output_tokens=900,
        ),
    )
    answer = (response.text or "").strip()
    if not answer:
        raise RuntimeError("Model tidak mengembalikan jawaban.")
    return answer


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []


def render_sidebar() -> str:
    with st.sidebar:
        st.header("Pengaturan")
        configured_key = get_secret_api_key()
        api_key = st.text_input(
            "Gemini API key",
            value=configured_key,
            type="password",
            help="Untuk deployment, simpan sebagai GEMINI_API_KEY di Streamlit Secrets.",
        ).strip()
        st.caption("API key hanya dipakai untuk sesi ini dan tidak ditampilkan kembali.")
        st.divider()
        st.markdown("**Rujukan kesehatan**")
        st.link_button("Buka Profil Kesehatan Kemenkes", KEMKES_PROFILE_URL)
        st.caption("Publikasi resmi, bukan dashboard kasus harian real-time.")
        if st.button("Hapus percakapan", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    return api_key


def render_chat() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="+", layout="centered")
    init_session_state()
    api_key = render_sidebar()

    st.title(APP_TITLE)
    st.write("Tanya jawab edukatif tentang penyakit infeksi tropis dengan rujukan kesehatan resmi.")
    st.info("Jawaban bersifat edukatif dan bukan pengganti pemeriksaan tenaga kesehatan.")
    render_chat()

    prompt = st.chat_input("Contoh: Apa tanda bahaya demam berdarah pada orang dewasa?")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not api_key:
            st.warning("Masukkan Gemini API key di sidebar terlebih dahulu.")
            return
        try:
            with st.spinner("Menyiapkan jawaban..."):
                answer = generate_answer(create_client(api_key), st.session_state.messages)
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as error:  # SDK errors vary across versions.
            st.error("Gagal menghubungi Gemini. Periksa API key, koneksi, dan kuota API.")


if __name__ == "__main__":
    main()
