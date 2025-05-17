import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from io import BytesIO
from openai import OpenAI
from fastapi.concurrency import run_in_threadpool
#ひとまず動く
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 運用時は限定してください
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

app.mount("/static", StaticFiles(directory="static", html=True), name="static")
# ルートでindex.htmlを返す（オプション）
from fastapi.responses import FileResponse
@app.get("/")
async def root():
    return FileResponse("static/index.html")

def call_chat(transcript_text: str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "次の文字起こし結果を短く要約してください。"},
            {"role": "user", "content": transcript_text}
        ]
    )
    return response.choices[0].message.content

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 念のためファイルポインタを先頭に戻す
    await file.seek(0)
    audio_bytes = await file.read()
    if not audio_bytes:
        return {"error": "アップロードされたファイルが空です"}
    print("Uploaded file type:", file.content_type)
    audio_file = BytesIO(audio_bytes)
    audio_file.name = file.filename  # Whisper APIには file.name が必要
    audio_file.seek(0)  # 念のため先頭に戻す
    # Whisperで文字起こし（非同期）
    def call_whisper():
        audio_file.seek(0)
        return client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            language="ja"
        )

    transcript_response = await run_in_threadpool(call_whisper)
    transcription_text = transcript_response.text

    # ChatGPTで要約（非同期）
    summary = await run_in_threadpool(lambda: call_chat(transcription_text))

    # 結果を返す
    return {
        "transcription": transcription_text,
        "summary": summary,
    }