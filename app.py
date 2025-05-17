import streamlit as st
import openai
from io import BytesIO
import os
import base64
import time

openai.api_key = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

st.title("🎤 録音して文字起こし＆要約")

st.write("""
以下のボタンで録音を開始・停止してください。  
停止すると音声ファイルがアップロードされ、文字起こしと要約が行われます。
""")

recording_js = """
<script>
let mediaRecorder;
let audioChunks = [];
let timerInterval;

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();
        audioChunks = [];

        let startTime = Date.now();
        document.getElementById("timer").innerText = "⏱️ 録音中: 0 秒";

        timerInterval = setInterval(() => {
            let elapsed = Math.floor((Date.now() - startTime) / 1000);
            document.getElementById("timer").innerText = `⏱️ 録音中: ${elapsed} 秒`;
        }, 1000);

        mediaRecorder.addEventListener("dataavailable", event => {
            audioChunks.push(event.data);
        });

        mediaRecorder.addEventListener("stop", () => {
            clearInterval(timerInterval);
            document.getElementById("timer").innerText = "🛑 録音停止";

            const audioBlob = new Blob(audioChunks, {type: 'audio/wav'});
            const audioUrl = URL.createObjectURL(audioBlob);
            const audioElement = document.getElementById("audio_play");
            audioElement.src = audioUrl;
            audioElement.style.display = "block";

            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = () => {
                const base64data = reader.result;
                const el = window.parent.document.getElementById("audio_data_textarea");
                el.value = base64data;
                el.dispatchEvent(new Event('input'));
            };
        });
    });
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
    }
}
</script>

<div style="margin-top: 10px;">
    <button onclick="startRecording()">🎙️ 録音開始</button>
    <button onclick="stopRecording()" style="margin-left: 10px;">⏹️ 録音停止</button>
    <h4 id="timer">⏱️ 録音前</h4>
</div>
<audio id="audio_play" controls style="display:none; margin-top: 10px;"></audio>
"""

st.components.v1.html(recording_js, height=250)

# 非表示のtextareaでJavaScriptから音声データを受け取る
audio_base64 = st.text_area("audio_data_textarea", value="", height=100, key="audio_data_textarea")

if audio_base64:
    st.audio(audio_base64, format="audio/wav")
    st.write("🟢 音声データを受信しました。処理を開始します...")

    # 処理開始をユーザーに見せる
    with st.spinner("要約を生成中...お待ちください。"):
        try:
            header, encoded = audio_base64.split(",", 1)
            audio_bytes = base64.b64decode(encoded)

            with BytesIO(audio_bytes) as audio_file:
                transcript = openai.Audio.transcribe("whisper-1", audio_file)

            st.write("### 📝 文字起こし結果")
            st.write(transcript["text"])

            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "以下の文章を要約してください。"},
                    {"role": "user", "content": transcript["text"]},
                ],
                max_tokens=200,
                temperature=0.5,
            )
            summary = response["choices"][0]["message"]["content"]
            st.write("### ✨ 要約")
            st.write(summary)
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
