#!/usr/bin/env python3
"""
Offline Chinese ASR entry point built on FunASR.

Usage:
    source .venv/bin/activate
    python run_chinese_asr.py --audio path/to/audio.wav
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from funasr import AutoModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run offline Chinese ASR with locally cached FunASR models."
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to a 16 kHz mono WAV file to transcribe.",
    )
    parser.add_argument(
        "--cache-dir",
        default="modelscope_cache",
        help="Directory that already contains the downloaded FunASR models.",
    )
    return parser.parse_args()


def ensure_audio(audio_path: Path) -> None:
    if not audio_path.exists():
        sys.exit(f"Audio file not found: {audio_path}")
    if audio_path.suffix.lower() != ".wav":
        sys.exit("Expected a WAV file recorded at 16 kHz mono for best results.")


def main() -> None:
    args = parse_args()
    audio_path = Path(args.audio).expanduser().resolve()
    ensure_audio(audio_path)

    cache_dir = Path(args.cache_dir).expanduser().resolve()
    if not cache_dir.exists():
        sys.exit(
            f"Cache directory {cache_dir} not found. "
            "Run the setup steps to download the models first."
        )

    os.environ.setdefault("MODELSCOPE_CACHE", str(cache_dir))

    model_root = cache_dir / "models" / "iic"
    asr_model = model_root / "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    vad_model = model_root / "speech_fsmn_vad_zh-cn-16k-common-pytorch"
    punc_model = model_root / "punc_ct-transformer_cn-en-common-vocab471067-large"

    for path in (asr_model, vad_model, punc_model):
        if not path.exists():
            sys.exit(f"Expected model directory missing: {path}")

    model = AutoModel(
        model=str(asr_model),
        vad_model=str(vad_model),
        punc_model=str(punc_model),
        disable_update=True,
    )

    result = model.generate(input=str(audio_path))
    # FunASR returns a list of dicts; the first item holds the ASR text.
    text = result[0]["text"]
    print(text)


if __name__ == "__main__":
    main()
