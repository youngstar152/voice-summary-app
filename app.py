# import streamlit as st
# import openai
# import base64
# from io import BytesIO
# import os

# openai.api_key = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

# st.title("🎤 録音して文字起こし＆要約（修正版）")

# st.write("録音開始・停止ボタンを押すと録音し、録音終了後に自動的に文字起こし＆要約します。")

# # JSコード（録音、base64変換、終了時にbase64文字列を返す）
# recording_js = """
# <script>
# let mediaRecorder;
# let audioChunks = [];
# let timerInterval;

# function startRecording() {
#     navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
#         mediaRecorder = new MediaRecorder(stream);
#         mediaRecorder.start();
#         audioChunks = [];
#         let startTime = Date.now();
#         document.getElementById("timer").innerText = "⏱️ 録音中: 0 秒";
#         timerInterval = setInterval(() => {
#             let elapsed = Math.floor((Date.now() - startTime) / 1000);
#             document.getElementById("timer").innerText = `⏱️ 録音中: ${elapsed} 秒`;
#         }, 1000);

#         mediaRecorder.ondataavailable = e => {
#             audioChunks.push(e.data);
#         };

#         mediaRecorder.onstop = () => {
#             clearInterval(timerInterval);
#             document.getElementById("timer").innerText = "🛑 録音停止";

#             const audioBlob = new Blob(audioChunks, {type: 'audio/wav'});
#             const reader = new FileReader();
#             reader.readAsDataURL(audioBlob);
#             reader.onloadend = () => {
#                 const base64data = reader.result;
#                 // base64文字列をStreamlit側に返す
#                 const streamlitAPI = window.parent.streamlitAPI || window.parent.parent.streamlitAPI;
#                 if(streamlitAPI && streamlitAPI.setComponentValue) {
#                     streamlitAPI.setComponentValue(base64data);
#                 }
#             };

#             const audioUrl = URL.createObjectURL(audioBlob);
#             const audioElement = document.getElementById("audio_play");
#             audioElement.src = audioUrl;
#             audioElement.style.display = "block";
#         };
#     });
# }

# function stopRecording() {
#     if (mediaRecorder && mediaRecorder.state === "recording") {
#         mediaRecorder.stop();
#     }
# }
# </script>

# <div style="margin-top: 10px;">
#     <button onclick="startRecording()">🎙️ 録音開始</button>
#     <button onclick="stopRecording()" style="margin-left: 10px;">⏹️ 録音停止</button>
#     <h4 id="timer">⏱️ 録音前</h4>
# </div>
# <audio id="audio_play" controls style="display:none; margin-top: 10px;"></audio>
# """

# # components.v1.html の戻り値でJSからbase64を受け取る
# audio_base64 = st.components.v1.html(recording_js, height=300, scrolling=False)

# if audio_base64:
#     st.audio(audio_base64, format="audio/wav")
#     st.write("🟢 音声データを受信しました。処理を開始します...")

#     with st.spinner("文字起こし＆要約中...お待ちください。"):
#         try:
#             header, encoded = audio_base64.split(",", 1)
#             audio_bytes = base64.b64decode(encoded)
#             audio_file = BytesIO(audio_bytes)

#             transcript = openai.Audio.transcribe("whisper-1", audio_file)
#             st.write("### 📝 文字起こし結果")
#             st.write(transcript["text"])

#             response = openai.ChatCompletion.create(
#                 model="gpt-4o-mini",
#                 messages=[
#                     {"role": "system", "content": "以下の文章を要約してください。"},
#                     {"role": "user", "content": transcript["text"]},
#                 ],
#                 max_tokens=200,
#                 temperature=0.5,
#             )
#             summary = response["choices"][0]["message"]["content"]
#             st.write("### ✨ 要約")
#             st.write(summary)

#         except Exception as e:
#             st.error(f"エラーが発生しました: {e}")

