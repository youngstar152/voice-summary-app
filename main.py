import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from io import BytesIO
from openai import OpenAI
from fastapi.concurrency import run_in_threadpool
from pydub import AudioSegment
import tempfile
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
    # ファイル拡張子を取得
    filename = file.filename
    ext = filename.split('.')[-1].lower()
    
     # 一時ファイルに書き出す
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_input:
        temp_input.write(audio_bytes)
        input_path = temp_input.name

    # mp4など非対応形式を wav に変換
    if ext in ["mp4", "m4a", "aac", "webm"]:
        # 出力ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
            output_path = temp_wav.name

        # pydub で変換
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="wav")

        # Whisper 用にバイナリ読み込み
        with open(output_path, "rb") as f:
            transcript_response = await run_in_threadpool(lambda: client.audio.transcriptions.create(
                file=f,
                model="whisper-1",
                language="ja"
            ))
            
    else:
        audio_file = BytesIO(audio_bytes)
        audio_file.name = file.filename  # Whisper APIには file.name が必要
        audio_file.seek(0)  # 念のため先頭に戻す
        # Whisperで文字起こし（非同期）
        transcript_response = await run_in_threadpool(lambda: client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                language="ja"
            ))
    transcription_text = transcript_response.text

    # ChatGPTで要約（非同期）
    summary = await run_in_threadpool(lambda: call_chat(transcription_text))

    # 結果を返す
    return {
        "transcription": transcription_text,
        "summary": summary,
    }