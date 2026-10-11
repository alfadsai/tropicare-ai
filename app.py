"""Streamlit chatbot for tropical infectious disease education."""

from __future__ import annotations

import os

import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI

APP_TITLE = "🦟 TropiCare AI"
DEFAULT_MODEL = "gemini-3.8-flash"
MAX_OUTPUT_TOKENS = 2048
KEMKES_PROFILE_URL = "https://www.kemkes.go.id/id/category/profil-kesehatan"
PROVIDERS = {
    "Gemini": {
        "secret_name": "GEMINI_API_KEY",
        "model": DEFAULT_MODEL,
        "models": [
            DEFAULT_MODEL,
            "gemini-3.6-flash",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
        ],
        "help": "Buat API key melalui Google AI Studio.",
    },
    "Groq (Free Tier)": {
        "secret_name": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3-32b",
        ],
        "help": "Gunakan API key dari Groq Console. Free tier memiliki batas penggunaan.",
    },
}

SYSTEM_INSTRUCTION = f"""
You are TropiCare AI, an Indonesian public-health education assistant focused on
 tropical infectious diseases such as malaria, dengue, chikungunya, tuberculosis,
 leptospirosis, and other diseases relevant to tropical regions.

Answer in the same language as the user's question. Use clear, non-alarmist language.
You provide general education only, never a diagnosis, prescription, or personalized
medicine dose. Do not infer that a user has a disease from symptoms. Encourage a
qualified health professional for personal advice.
Complete every sentence and do not stop mid-word. Prefer a concise answer with
headings or bullet points when that makes the explanation clearer.

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


def get_secret_api_key(secret_name: str) -> str:
    """Read a deployed Streamlit secret without exposing it in the UI."""
    try:
        return str(st.secrets.get(secret_name, "")).strip()
    except (FileNotFoundError, KeyError):
        return os.getenv(secret_name, "").strip()


def create_gemini_client(api_key: str) -> genai.Client:
    """Create a Gemini client from a user-provided or configured key."""
    return genai.Client(api_key=api_key)


def generate_groq_client(api_key: str) -> OpenAI:
    """Create an OpenAI-compatible client configured for Groq."""
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def get_finish_reason(response: object) -> str:
    """Extract a Gemini finish reason without depending on one SDK enum type."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return ""
    return str(getattr(candidates[0], "finish_reason", "")).upper()


def stream_gemini_answer(
    client: genai.Client,
    history: list[dict[str, str]],
    model: str,
) -> object:
    """Yield Gemini text chunks as they arrive from the streaming endpoint."""
    contents: list[types.Content] = []
    for message in history:
        role = "user" if message["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=message["content"])],
            )
        )

    response_stream = client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ),
    )
    yielded_text = False
    partial_answer: list[str] = []
    finish_reason = ""
    for response in response_stream:
        text = response.text or ""
        if text:
            yielded_text = True
            partial_answer.append(text)
            yield text
        response_finish_reason = get_finish_reason(response)
        if response_finish_reason:
            finish_reason = response_finish_reason

    if "MAX_TOKENS" in finish_reason:
        continuation_contents = [
            *contents,
            types.Content(
                role="model",
                parts=[types.Part(text="".join(partial_answer))],
            ),
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=(
                            "Lanjutkan jawaban tepat dari bagian terakhir. "
                            "Jangan mengulang teks sebelumnya dan jangan mengawali "
                            "dengan pengantar baru."
                        )
                    )
                ],
            ),
        ]
        continuation_stream = client.models.generate_content_stream(
            model=model,
            contents=continuation_contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )
        for response in continuation_stream:
            text = response.text or ""
            if text:
                yielded_text = True
                yield text
    if not yielded_text:
        raise RuntimeError("Model tidak mengembalikan jawaban.")


def stream_groq_answer(
    client: OpenAI,
    history: list[dict[str, str]],
    model: str,
) -> object:
    """Yield Groq text chunks as they arrive from the streaming endpoint."""
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}, *history]
    response_stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=MAX_OUTPUT_TOKENS,
        stream=True,
    )
    yielded_text = False
    for chunk in response_stream:
        if not chunk.choices:
            continue
        text = chunk.choices[0].delta.content or ""
        if text:
            yielded_text = True
            yield text
    if not yielded_text:
        raise RuntimeError("Model tidak mengembalikan jawaban.")


def stream_answer(
    provider: str,
    api_key: str,
    history: list[dict[str, str]],
    model: str,
) -> object:
    """Route streaming to the SDK and payload format for the selected provider."""
    if provider == "Gemini":
        return stream_gemini_answer(create_gemini_client(api_key), history, model)
    if provider == "Groq (Free Tier)":
        return stream_groq_answer(generate_groq_client(api_key), history, model)
    raise ValueError(f"Provider tidak didukung: {provider}")


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []


def render_sidebar() -> tuple[str, str, str]:
    with st.sidebar:
        st.header("⚙️ Pengaturan")
        provider = st.selectbox("🤖 Pilih provider AI", list(PROVIDERS))
        provider_config = PROVIDERS[provider]
        model = st.selectbox("🧠 Model", provider_config["models"])
        configured_key = get_secret_api_key(provider_config["secret_name"])
        api_key = st.text_input(
            f"🔑 {provider} API key",
            value=configured_key,
            type="password",
            help=provider_config["help"],
        ).strip()
        st.caption("🔒 Gunakan API key milik Anda sendiri. Jangan gunakan atau membagikan key publik.")
        st.caption("⏱️ Free tier tetap memiliki rate limit dan kebijakan penggunaan provider.")
        st.divider()
        st.markdown("**📚 Rujukan kesehatan**")
        st.link_button("🔗 Buka Profil Kesehatan Kemenkes", KEMKES_PROFILE_URL)
        st.caption("📄 Publikasi resmi, bukan dashboard kasus harian real-time.")
        if st.button("🧹 Hapus percakapan", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    return provider, model, api_key


def render_chat() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="+", layout="centered")
    init_session_state()
    provider, model, api_key = render_sidebar()

    st.title(APP_TITLE)
    st.write("💬 Tanya jawab edukatif tentang penyakit infeksi tropis dengan rujukan kesehatan resmi.")
    st.info("⚕️ Jawaban bersifat edukatif dan bukan pengganti pemeriksaan tenaga kesehatan.")
    render_chat()

    prompt = st.chat_input("💬 Contoh: Apa tanda bahaya demam berdarah pada orang dewasa?")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not api_key:
            st.warning(f"Masukkan {provider} API key di sidebar terlebih dahulu.")
            return
        try:
            answer = st.write_stream(
                stream_answer(provider, api_key, st.session_state.messages, model)
            )
            answer = str(answer).strip()
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception:  # SDK errors vary across versions.
            st.error(
                f"Gagal menghubungi {provider} dengan model {model}. "
                "Periksa API key, ketersediaan model, koneksi, dan kuota API."
            )


if __name__ == "__main__":
    main()
