import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from io import BytesIO
from openai import OpenAI
from fastapi.concurrency import run_in_threadpool

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

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    audio_file = BytesIO(audio_bytes)
    audio_file.name = file.filename  # これが重要（Whisper APIがファイル名を使う）

    # Whisperの同期APIを非同期で呼び出す
    def call_whisper():
        audio_file.seek(0)
        return client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1"
        )

    transcript_response = await run_in_threadpool(call_whisper)
    text = transcript_response.text

    # GPTのChatCompletionも非同期で呼び出し
    def call_chat():
        return client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "以下の文章を要約してください。"},
                {"role": "user", "content": text},
            ],
            max_tokens=200,
            temperature=0.5,
        )

    response = await run_in_threadpool(call_chat)
    summary = response["choices"][0]["message"]["content"]

    return {"transcript": text, "summary": summary}
