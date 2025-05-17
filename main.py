import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from io import BytesIO
import openai
from fastapi.concurrency import run_in_threadpool

app = FastAPI()

# CORS設定（運用時は許可するオリジンを限定してください）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 環境変数からOpenAI APIキーを取得
openai.api_key = os.environ.get("OPENAI_API_KEY")
app.mount("/", StaticFiles(directory="static", html=True), name="static")
@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # 音声ファイルをバイト列で読み込み
    audio_bytes = await file.read()
    audio_file = BytesIO(audio_bytes)

    # Whisperで文字起こし
    # Whisperの同期APIを非同期で呼び出し
    def call_whisper():
        return openai.Audio.transcribe(
            "whisper-1", 
            audio_file, 
            file=file.filename,
            # content_type=file.content_type,  # もし必要なら
        )
    transcript = await run_in_threadpool(call_whisper)
    text = transcript["text"]

    # GPTで要約
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "以下の文章を要約してください。"},
            {"role": "user", "content": text},
        ],
        max_tokens=200,
        temperature=0.5,
    )
    summary = response["choices"][0]["message"]["content"]

    return {"transcript": text, "summary": summary}
