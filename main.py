import os
import tempfile
import subprocess
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from pydub import AudioSegment
from io import BytesIO
from openai import OpenAI

app = FastAPI()

# CORS設定（本番運用時は制限を加える）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイル（index.htmlなど）を提供
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# OpenAIクライアント初期化
openai_api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# hh:mm:ss形式に変換
def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02}:{m:02}:{s:02}"

# ffmpegで音声分割（5分＋1分重複）
def split_audio(input_path, output_dir, duration_min=5, overlap_min=1):
    result = subprocess.run(
        ["ffprobe", "-i", input_path, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    total_duration = float(result.stdout.strip())
    segment_length = duration_min * 60
    overlap = overlap_min * 60
    total_length = segment_length + overlap

    start = 0
    index = 0
    output_files = []

    while start < total_duration:
        end = min(start + total_length, total_duration)
        output_file = os.path.join(output_dir, f"segment_{index}.wav")
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-ss", format_time(start), "-to", format_time(end),
            "-acodec", "pcm_s16le", "-ar", "16000", output_file
        ])
        output_files.append((output_file, start))
        start += segment_length
        index += 1

    return output_files

# Whisperでテキスト化
def transcribe_file(path):
    with open(path, "rb") as f:
        return client.audio.transcriptions.create(
            file=f,
            model="whisper-1",
            language="ja",
            response_format="verbose_json"
        )

# セグメントの時刻を統合
def merge_segments(transcripts_with_offset):
    merged = {
        "text": "",
        "segments": [],
        "duration": 0.0
    }

    for tdata, offset in transcripts_with_offset:
        for segment in tdata['segments']:
            segment['start'] += offset
            segment['end'] += offset
            merged["segments"].append(segment)
        merged["text"] += tdata['text'] + "\n"
        merged["duration"] += tdata['duration'] - 60  # 重複除去

    return merged

# ChatGPTで要約
def call_summary(text: str):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "次の文字起こし結果を議事録を制作するようにすべての発言をそれぞれ端的にまとめてください"},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    await file.seek(0)
    audio_bytes = await file.read()

    if not audio_bytes:
        return {"error": "ファイルが空です"}

    # アップロード拡張子確認
    filename = file.filename
    ext = filename.split('.')[-1].lower()

    # 一時フォルダ作成
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, f"input.{ext}")

        # 元音声保存
        with open(input_path, "wb") as f:
            f.write(audio_bytes)

        # 非WAV形式なら変換
        if ext != "wav":
            converted_path = os.path.join(tmpdir, "converted.wav")
            audio = AudioSegment.from_file(input_path)
            audio.export(converted_path, format="wav")
            input_path = converted_path

        # 分割実行
        segment_files = await run_in_threadpool(lambda: split_audio(input_path, tmpdir))

        # 分割ごとに文字起こし
        transcript_results = await run_in_threadpool(lambda: [
            (transcribe_file(path), offset) for path, offset in segment_files
        ])

        # 結合
        merged_result = await run_in_threadpool(lambda: merge_segments(transcript_results))

        # 要約
        summary = await run_in_threadpool(lambda: call_summary(merged_result["text"]))

        return {
            "transcription": merged_result["text"],
            "summary": summary
        }
