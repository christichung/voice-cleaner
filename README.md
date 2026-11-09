# Voice Cleaner

Voice cleaner and noise remover. Upload a voiceover as audio or video, remove background noise with AI, and download a clean MP3.

Everything runs locally on your computer. No audio is sent to any outside service.

## Features

- **AI noise removal** with [DeepFilterNet3](https://github.com/Rikorose/DeepFilterNet), a pretrained speech-enhancement model. It handles steady noise (hiss, hum, fans, room tone) and changing noise (clicks, bumps, background chatter).
- **Voice polish** after denoising: EQ, compression and peak normalization for an even, clear voice.
- **Many input formats**, audio or video. Output is always a 192 kbps mono MP3.
- **Three strength levels** to balance cleanliness against a natural sound.
- **Before/after players** in the browser to compare results before downloading.
- **Minimal web interface** with drag and drop, automatic light and dark mode, and support for phone-sized screens.

### Supported formats

| Type | Extensions |
|---|---|
| Audio | `.mp3` `.wav` `.m4a` `.aac` `.flac` `.ogg` `.oga` `.opus` `.wma` `.aif` `.aiff` `.caf` `.amr` |
| Video | `.mp4` `.m4v` `.mov` `.webm` `.mkv` `.avi` `.3gp` (only the audio track is used) |

Maximum upload size: 100 MB by default. Change it with the `MAX_UPLOAD_MB` environment variable, for example `MAX_UPLOAD_MB=500 uvicorn app:app`.

## Requirements

- macOS on Apple Silicon (tested). Other platforms should work with the same steps, but haven't been tested.
- **Python 3.11.** DeepFilterNet doesn't publish ready-made packages for newer Python versions on Apple Silicon.
- [uv](https://docs.astral.sh/uv/), the easiest way to get Python 3.11 alongside a newer system Python.

You don't need to install FFmpeg separately: the `imageio-ffmpeg` package includes its own copy.

## Setup

From the `voice-cleaner` folder:

```bash
brew install uv
```

```bash
uv venv --python 3.11 .venv
```

```bash
uv pip install --python .venv/bin/python -r requirements.txt
```

The model files are already in `models/DeepFilterNet3` (about 8 MB), so nothing else needs to be downloaded.

## Usage

Start the server:

```bash
source .venv/bin/activate
```

```bash
uvicorn app:app --reload
```

Open http://localhost:8000, then:

1. Choose a file or drag it onto the upload area.
2. Pick a strength.
3. Click **Clean audio**.
4. Compare the **Original** and **Cleaned** players, then click **Download MP3**.

The downloaded file is named after the original, for example `interview.mp4` becomes `interview-clean.mp3`.

### Strength levels

| Setting | Max noise reduction | When to use |
|---|---|---|
| Light | 12 dB | Already-decent recordings. Keeps the most natural room sound. |
| Medium | 24 dB | Most voiceovers. This is the default. |
| Strong | No limit | Very noisy recordings, where silence between words should be truly silent. |

## API

The web page uses a single endpoint, which you can also call directly.

### `POST /api/clean`

Multipart form fields:

| Field | Required | Value |
|---|---|---|
| `file` | yes | The audio or video file |
| `strength` | no | `light`, `medium` (default) or `strong` |

On success, the response is the cleaned MP3 (`audio/mpeg`) with a download filename.

```bash
curl -F file=@interview.mp4 -F strength=medium http://localhost:8000/api/clean -o interview-clean.mp3
```

Errors return JSON like `{"detail": "..."}`:

| Status | Meaning |
|---|---|
| 400 | Unsupported file type, unknown strength, or empty file |
| 413 | File is over the upload limit |
| 422 | The file has no audio track |
| 500 | Processing failed unexpectedly |

### `GET /api/formats`

Returns the list of accepted file extensions.

### `GET /api/config`

Returns the upload limit and accepted extensions, for example `{"max_upload_mb": 100, "formats": [...]}`.

## Deployment

The app needs about 1–2 GB of memory for PyTorch and the model, so it needs a host that runs containers. Static hosts like Vercel, Netlify and GitHub Pages won't work.

### Hugging Face Spaces (free)

The `deploy/huggingface` folder holds the two files a Space needs:

- `README.md`: Space settings (Docker, port 7860, title and emoji).
- `Dockerfile`: clones this GitHub repo and builds it. Hugging Face rejects the model's binary file unless it's stored with Git LFS, so the Space pulls the code from GitHub instead of storing a copy.

To set it up:

1. Create a Space at https://huggingface.co/new-space with **Docker** as the SDK and the **Blank** template.
2. Upload both files from `deploy/huggingface` to the Space, replacing its default `README.md`.
3. The Space builds automatically, which takes about 5–10 minutes the first time.

To update the Space after pushing new code to GitHub, open the Space's **Settings** and click **Factory rebuild**.

### Any other container host

The root `Dockerfile` works on Render, Railway, Fly.io, Google Cloud Run and similar hosts. Give it at least 2 GB of memory. It listens on port 7860, or on `$PORT` if the host sets it.

```bash
docker build -t voice-cleaner .
```

```bash
docker run -p 7860:7860 voice-cleaner
```

## How it works

The pipeline is in `cleaner.py`:

1. **Decode.** FFmpeg converts any input to mono, 48 kHz audio and drops any video. 48 kHz is the rate DeepFilterNet expects.
2. **High-pass filter.** Removes rumble below 80 Hz.
3. **AI noise removal.** DeepFilterNet3 separates speech from everything else. The strength setting caps how much it removes.
4. **Voice polish.** A slight cut around 200 Hz reduces muddiness, a small boost around 3.5 kHz adds clarity, and a compressor and limiter even out the volume.
5. **Normalize.** Sets the loudest point to about −1 dB.
6. **Encode.** Writes a 192 kbps MP3 with `pedalboard`.

The model is loaded once when the server starts and runs on the CPU. An 8-second clip takes about 0.3 seconds to process.

## Project structure

```
voice-cleaner/
├── app.py               FastAPI server: routes, upload checks, error handling
├── cleaner.py           Audio pipeline: decode, denoise, polish, encode
├── requirements.txt     Pinned Python dependencies
├── Dockerfile           Container build for any host
├── deploy/
│   └── huggingface/     Space settings and Dockerfile for Hugging Face Spaces
├── models/
│   └── DeepFilterNet3/  Pretrained model weights and config
└── static/
    ├── index.html       Web page
    ├── style.css        Styles (light and dark mode)
    └── app.js           Upload, strength picker, players, download
```

## Troubleshooting

**`ModuleNotFoundError: No module named 'torchaudio.backend'`**
A newer torchaudio was installed. DeepFilterNet needs the pinned versions, so reinstall from `requirements.txt`:

```bash
uv pip install --python .venv/bin/python -r requirements.txt
```

**`maturin failed` or `Do you have cargo in your PATH?` during install**
The environment is using Python 3.12 or newer. Recreate it with Python 3.11 as shown in [Setup](#setup).

**The model fails to load or tries to download from GitHub**
Check that `models/DeepFilterNet3/config.ini` and `models/DeepFilterNet3/checkpoints/` exist. To download the model again:

```bash
curl -L -o models/DeepFilterNet3.zip https://raw.githubusercontent.com/Rikorose/DeepFilterNet/main/models/DeepFilterNet3.zip
```

```bash
unzip -o models/DeepFilterNet3.zip -d models && rm models/DeepFilterNet3.zip
```

**The "Original" player is missing after cleaning**
Some formats (MKV, AVI, WMA and others) can't play in a web browser. Cleaning and downloading still work.

**`python: command not found`**
On macOS, use `python3`, or activate the virtual environment first with `source .venv/bin/activate`.

## Limitations

- Output is always mono. Stereo input is mixed down, which is normal for voiceovers.
- Very long files are processed in one go and held in memory. Hour-long recordings may be slow or use a lot of RAM.
- One file is processed at a time. Simultaneous uploads wait their turn.
- DeepFilterNet is built for speech. Music or singing in the background may be partly removed or distorted.

## Credits

- [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) by Hendrik Schröter et al., for noise removal. The model files in `models/DeepFilterNet3` are from that project, dual-licensed under MIT and Apache-2.0.
- [pedalboard](https://github.com/spotify/pedalboard) by Spotify, for audio effects and MP3 encoding
- [FFmpeg](https://ffmpeg.org/) via [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg), for decoding
- [FastAPI](https://fastapi.tiangolo.com/), for the web server
