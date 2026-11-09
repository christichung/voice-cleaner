"""Voice Cleaner web app. Run with:  uvicorn app:app --reload"""

from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from cleaner import STRENGTH, SUPPORTED_EXTS, DecodeError, clean_audio

MAX_BYTES = 500 * 1024 * 1024  # 500 MB (video files are large)
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Voice Cleaner")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/formats")
def formats():
    return sorted(SUPPORTED_EXTS)


@app.post("/api/clean")
async def clean(file: UploadFile = File(...), strength: str = Form("medium")):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(400, "Unsupported file type. Try MP3, WAV, M4A, MP4 or MOV.")
    if strength not in STRENGTH:
        raise HTTPException(400, "Unknown strength.")

    data = await file.read()
    if not data:
        raise HTTPException(400, "The file is empty.")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is too large (max 500 MB).")

    try:
        cleaned = await run_in_threadpool(clean_audio, data, strength, ext)
    except DecodeError:
        raise HTTPException(422, "Couldn't find any audio in that file.")
    except Exception:
        raise HTTPException(500, "Something went wrong while cleaning the audio.")

    name = f"{Path(file.filename).stem}-clean.mp3"
    ascii_name = name.encode("ascii", "ignore").decode() or "voice-clean.mp3"
    disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(name)}'
    return Response(
        content=cleaned,
        media_type="audio/mpeg",
        headers={"Content-Disposition": disposition},
    )


app.mount("/static", StaticFiles(directory=STATIC), name="static")
