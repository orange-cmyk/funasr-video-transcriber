#!/usr/bin/env python3
"""
Simple web UI for uploading a video file, converting it with FunASR, and returning the transcript.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List

from flask import (
    Flask,
    render_template_string,
    request,
    send_from_directory,
)
from werkzeug.utils import secure_filename

from funasr import AutoModel


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "modelscope_cache"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
MODEL_ROOT = CACHE_DIR / "models" / "iic"


# Ensure transcript directory exists before serving requests.
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

# Cache the ASR model globally so we only load weights once.
ASR_MODEL: Optional[AutoModel] = None

HTML_TEMPLATE = """<!doctype html>
<html lang="zh">
  <head>
    <meta charset="utf-8">
    <title>FunASR 视频转写</title>
    <style>
      :root {
        color-scheme: light;
        --gradient-start: #536dfe;
        --gradient-end: #7c4dff;
        --card-bg: rgba(255, 255, 255, 0.86);
        --border-color: rgba(255, 255, 255, 0.35);
        --text-color: #1f1f2d;
        --muted-text: #5f6a7d;
        --button-bg: linear-gradient(135deg, #5c6bf7, #8f67ff);
        --button-bg-hover: linear-gradient(135deg, #4c5be4, #7a52f3);
        --error-bg: rgba(255, 82, 82, 0.12);
        --error-text: #d84343;
        --result-bg: rgba(82, 118, 255, 0.14);
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        font-family: "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
        background: linear-gradient(145deg, var(--gradient-start), var(--gradient-end));
        color: var(--text-color);
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
        padding: 2.5rem 1.5rem;
      }
      .page {
        width: min(960px, 100%);
      }
      header {
        text-align: center;
        color: white;
        margin-bottom: 2rem;
      }
      header h1 {
        margin: 0;
        font-size: clamp(2rem, 2.6vw, 2.8rem);
        font-weight: 700;
      }
      header p {
        margin: 0.75rem auto 0;
        max-width: 640px;
        line-height: 1.6;
        color: rgba(255, 255, 255, 0.8);
      }
      .card {
        background: var(--card-bg);
        backdrop-filter: blur(18px);
        border-radius: 18px;
        border: 1px solid var(--border-color);
        padding: 2rem 2.4rem;
        box-shadow:
          0 20px 60px rgba(30, 42, 92, 0.25),
          0 6px 20px rgba(30, 42, 92, 0.12);
      }
      form {
        display: flex;
        flex-direction: column;
        gap: 1.4rem;
      }
      .upload-box {
        border: 1.5px dashed rgba(82, 90, 110, 0.45);
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.75);
        padding: 1.8rem;
        text-align: center;
        transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
      }
      .upload-box:hover {
        transform: translateY(-2px);
        border-color: rgba(95, 119, 255, 0.75);
        box-shadow: 0 12px 30px rgba(90, 114, 255, 0.18);
      }
      .upload-box input[type="file"] {
        display: none;
      }
      .upload-label {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        padding: 0.85rem 1.6rem;
        border-radius: 40px;
        font-weight: 600;
        letter-spacing: 0.01em;
        color: white;
        background: var(--button-bg);
        cursor: pointer;
        transition: background 0.25s ease, transform 0.2s ease;
      }
      .upload-label:hover {
        background: var(--button-bg-hover);
        transform: translateY(-1px);
      }
      .filename {
        margin-top: 1rem;
        font-size: 0.95rem;
        color: var(--muted-text);
      }
      .hint {
        text-align: center;
        font-size: 0.95rem;
        color: var(--muted-text);
      }
      button[type="submit"] {
        border: none;
        border-radius: 46px;
        padding: 0.95rem 2.2rem;
        font-size: 1.02rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        background: var(--button-bg);
        color: white;
        cursor: pointer;
        box-shadow: 0 16px 30px rgba(94, 114, 255, 0.25);
        transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.25s ease;
        align-self: center;
      }
      button[type="submit"]:hover {
        background: var(--button-bg-hover);
        transform: translateY(-2px);
        box-shadow: 0 20px 34px rgba(90, 110, 255, 0.28);
      }
      .status {
        margin-top: 1.5rem;
        padding: 1rem 1.2rem;
        border-radius: 12px;
        line-height: 1.6;
      }
      .status.error {
        background: var(--error-bg);
        color: var(--error-text);
        border: 1px solid rgba(216, 67, 67, 0.28);
      }
      .links {
        margin-top: 1.4rem;
        text-align: center;
        font-size: 1rem;
      }
      .links a {
        color: #4c5be4;
        font-weight: 600;
        text-decoration: none;
        transition: color 0.2s ease;
      }
      .links a:hover {
        color: #3c4acc;
      }
      .result {
        margin-top: 1.8rem;
        background: var(--result-bg);
        border-radius: 16px;
        padding: 1.6rem;
        white-space: pre-wrap;
        line-height: 1.7;
        color: #1e2340;
        box-shadow: inset 0 0 0 1px rgba(94, 110, 255, 0.15);
      }
      .result strong {
        display: block;
        margin-bottom: 0.6rem;
        font-size: 1.05rem;
        font-weight: 600;
        color: #293268;
      }
      footer {
        margin-top: 2.4rem;
        text-align: center;
        color: rgba(255, 255, 255, 0.72);
        font-size: 0.92rem;
      }
      @media (max-width: 640px) {
        body {
          padding: 2rem 1.25rem;
        }
        .card {
          padding: 1.75rem 1.35rem;
        }
        .upload-label {
          width: 100%;
        }
      }
    </style>
  </head>
  <body>
    <div class="page">
      <header>
        <h1>FunASR 视频语音转写</h1>
        <p>上传 MP4 或其他 ffmpeg 支持的视频，系统会在本地完成音频提取、语音识别与标点恢复，转写过程不依赖外网。</p>
      </header>
      <div class="card">
        <form method="post" enctype="multipart/form-data">
          <div class="upload-box">
            <label class="upload-label" for="video">📁 选择或拖拽视频文件</label>
            <input type="file" id="video" name="video" accept="video/*" required>
            <div class="filename" id="filename">尚未选择文件</div>
          </div>
          <p class="hint">建议上传时长不超过 30 分钟的视频，文件仅在本地处理，不会上传至外部服务器。</p>
          <button type="submit">开始转换</button>
        </form>
        {% if error %}
          <div class="status error">{{ error }}</div>
        {% endif %}
        {% if transcript_path %}
          <div class="links">
            转写完成，文本已保存至
            <a href="{{ transcript_download }}">下载转写结果</a>
          </div>
        {% endif %}
        {% if transcript_text %}
          <div class="result">
            <strong>识别结果</strong>
            {{ transcript_text }}
          </div>
        {% endif %}
      </div>
      <footer>
        FunASR 本地部署 · ModelScope 中文模型 · Flask 前端
      </footer>
    </div>
    <script>
      const fileInput = document.getElementById("video");
      const fileName = document.getElementById("filename");
      fileInput.addEventListener("change", () => {
        if (!fileInput.files || fileInput.files.length === 0) {
          fileName.textContent = "尚未选择文件";
          return;
        }
        fileName.textContent = fileInput.files[0].name;
      });
      document.addEventListener("dragover", (event) => {
        event.preventDefault();
        if (event.target.closest(".upload-box")) {
          event.dataTransfer.dropEffect = "copy";
        }
      });
      document.addEventListener("drop", (event) => {
        const box = event.target.closest(".upload-box");
        if (!box) {
          return;
        }
        event.preventDefault();
        const files = event.dataTransfer.files;
        if (files && files.length > 0) {
          fileInput.files = files;
          fileInput.dispatchEvent(new Event("change"));
        }
      });
    </script>
  </body>
</html>
"""


class TranscriptionError(RuntimeError):
    """Raised when the transcription pipeline fails."""


def run_command(cmd: List[str]) -> None:
    """Run an external command and raise a helpful message on failure."""
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        raise TranscriptionError(exc.stderr.decode("utf-8", errors="ignore")) from exc


def load_asr_model() -> AutoModel:
    """Load or reuse the FunASR model from local cache."""
    global ASR_MODEL
    if ASR_MODEL is not None:
        return ASR_MODEL

    if not CACHE_DIR.exists():
        raise TranscriptionError("未找到 modelscope_cache，请先按说明下载模型。")

    asr_model_dir = MODEL_ROOT / "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    vad_model_dir = MODEL_ROOT / "speech_fsmn_vad_zh-cn-16k-common-pytorch"
    punc_model_dir = MODEL_ROOT / "punc_ct-transformer_cn-en-common-vocab471067-large"

    for path in (asr_model_dir, vad_model_dir, punc_model_dir):
        if not path.exists():
            raise TranscriptionError(f"缺少模型目录：{path}")

    os.environ.setdefault("MODELSCOPE_CACHE", str(CACHE_DIR))

    ASR_MODEL = AutoModel(
        model=str(asr_model_dir),
        vad_model=str(vad_model_dir),
        punc_model=str(punc_model_dir),
        disable_update=True,
    )
    return ASR_MODEL


def transcribe_video_file(video_path: Path, original_name: str) -> Tuple[str, Path]:
    """
    Convert a video file into text using FunASR.
    Returns the transcript text and the path to the saved transcript file.
    """
    model = load_asr_model()

    with tempfile.TemporaryDirectory(prefix="funasr_upload_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        audio_path = tmpdir_path / "audio.wav"
        segments_dir = tmpdir_path / "segments"
        segments_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: extract mono 16 kHz WAV audio.
        run_command(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(video_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-sample_fmt",
                "s16",
                str(audio_path),
            ]
        )

        # Step 2: segment audio into manageable chunks (15 seconds each).
        run_command(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(audio_path),
                "-f",
                "segment",
                "-segment_time",
                "15",
                "-c",
                "copy",
                str(segments_dir / "chunk_%03d.wav"),
            ]
        )

        segments = sorted(segments_dir.glob("chunk_*.wav"))
        if not segments:
            raise TranscriptionError("音频切分失败，未生成片段。")

        texts: List[str] = []
        for segment in segments:
            result = model.generate(input=str(segment))
            texts.append(result[0]["text"])

    transcript_text = "\n".join(texts).strip()
    if not transcript_text:
        raise TranscriptionError("模型未返回文本结果，请检查输入音频是否包含语音。")

    safe_name = Path(secure_filename(Path(original_name).stem))
    transcript_path = TRANSCRIPTS_DIR / f"{safe_name}_transcript.txt"
    transcript_path.write_text(transcript_text, encoding="utf-8")
    return transcript_text, transcript_path


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024  # 512 MB upload limit

    @app.route("/", methods=["GET", "POST"])
    def index():
        transcript_text = None
        transcript_path = None
        error = None

        if request.method == "POST":
            file = request.files.get("video")
            if not file or file.filename == "":
                error = "请先选择要上传的视频文件。"
            else:
                filename = secure_filename(file.filename)
                if filename == "":
                    error = "文件名无效。"
                else:
                    try:
                        with tempfile.NamedTemporaryFile(
                            suffix=Path(filename).suffix,
                            delete=False,
                        ) as tmpfile:
                            file.save(tmpfile.name)
                            tmp_path = Path(tmpfile.name)

                        transcript_text, transcript_path = transcribe_video_file(
                            tmp_path, filename
                        )
                    except TranscriptionError as exc:
                        error = f"转换失败：{exc}"
                    except Exception as exc:  # pragma: no cover - catch unexpected errors
                        error = f"发生未知错误：{exc}"
                    finally:
                        if "tmp_path" in locals() and tmp_path.exists():
                            tmp_path.unlink()

        transcript_download = None
        if transcript_path:
            transcript_download = f"/transcripts/{transcript_path.name}"

        return render_template_string(
            HTML_TEMPLATE,
            error=error,
            transcript_text=transcript_text,
            transcript_path=transcript_path,
            transcript_download=transcript_download,
        )

    @app.route("/transcripts/<path:filename>")
    def download_transcript(filename: str):
        return send_from_directory(TRANSCRIPTS_DIR, filename, as_attachment=True)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=False)
