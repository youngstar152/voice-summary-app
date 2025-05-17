import streamlit as st
import openai
import tempfile

st.set_page_config(page_title="音声要約アプリ", layout="wide")  # ✅ モバイルでも画面を広く使う

st.title("🎤 音声を文字起こし & 要約（スマホ対応）")
st.markdown("スマホで録音し、ファイルをアップロードしてください。")

# ✅ 音声アップロード
uploaded_file = st.file_uploader("音声ファイルをアップロード（m4a / mp3 / webm など対応）", type=["mp3", "m4a", "webm", "wav"])

if uploaded_file is not None:
    st.audio(uploaded_file, format='audio/webm')  # ✅ 音声再生可能（スマホでも確認できる）

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name

    with st.spinner("⏳ Whisperで文字起こし中..."):
        openai.api_key = st.secrets["OPENAI_API_KEY"]
        transcript = openai.Audio.transcribe("whisper-1", open(tmp_path, "rb"))
        text = transcript["text"]
        st.subheader("📝 文字起こし結果")
        st.write(text)

    with st.spinner("💡 GPTで要約中..."):
        summary_prompt = f"以下の文章を簡潔に要約してください：\n\n{text}"
        summary_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.5,
        )
        summary = summary_response["choices"][0]["message"]["content"]
        st.subheader("🔍 要約")
        st.write(summary)
