import streamlit as st
import openai
from io import BytesIO
import os

openai.api_key = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

st.title("録音開始・停止で音声文字起こし＆要約")

st.write("""
以下のボタンで録音を開始・停止してください。  
停止すると音声ファイルがアップロードされ、文字起こしと要約が行われます。
""")

# HTML + JSで録音UIを作成
recording_js = """
<script>
let mediaRecorder;
let audioChunks = [];
let audioBlob;
let audioUrl;

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();
        audioChunks = [];
        mediaRecorder.addEventListener("dataavailable", event => {
            audioChunks.push(event.data);
        });
        mediaRecorder.addEventListener("stop", () => {
            audioBlob = new Blob(audioChunks, {type: 'audio/wav'});
            audioUrl = URL.createObjectURL(audioBlob);
            const audioElement = document.getElementById("audio_play");
            audioElement.src = audioUrl;
            audioElement.style.display = "block";

            // Streamlitへファイル送信
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = () => {
                const base64data = reader.result;
                // Streamlitのtextareaにセットして送信ボタン押しやすくする
                const el = window.parent.document.getElementById("audio_data_textarea");
                el.value = base64data;
                el.dispatchEvent(new Event('input'));
            };
        });
    });
}

function stopRecording() {
    mediaRecorder.stop();
}
</script>

<button onclick="startRecording()">録音開始</button>
<button onclick="stopRecording()">録音停止</button>
<br>
<audio id="audio_play" controls style="display:none"></audio>
"""

st.components.v1.html(recording_js, height=150)

# base64の音声データをhidden textareaで受け取る（Streamlit側）
audio_base64 = st.text_area("audio_data_textarea", value="", height=10, key="audio_data_textarea")

if audio_base64:
    st.audio(audio_base64, format="audio/wav")
    # base64からバイナリに変換
    import base64
    header, encoded = audio_base64.split(",", 1)
    audio_bytes = base64.b64decode(encoded)

    # Whisper APIに送信
    with BytesIO(audio_bytes) as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)

    st.write("=== 文字起こし結果 ===")
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
    st.write("=== 要約 ===")
    st.write(summary)
