#!/usr/bin/env python3
"""
Batch transcribe segmented WAV files with FunASR and store the result in a text file.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from funasr import AutoModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe a directory of WAV segments and write the fused text to file."
    )
    parser.add_argument(
        "--segments-dir",
        required=True,
        help="Directory containing WAV segments (e.g. chunks created via ffmpeg).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path of the text file to write transcription into.",
    )
    parser.add_argument(
        "--cache-dir",
        default="modelscope_cache",
        help="Local ModelScope cache directory that already holds the FunASR models.",
    )
    return parser.parse_args()


def resolve_segments(path: Path) -> list[Path]:
    if not path.exists() or not path.is_dir():
        sys.exit(f"Segments directory not found: {path}")
    files = sorted(path.glob("*.wav"))
    if not files:
        sys.exit(f"No WAV segments found in {path}")
    return files


def main() -> None:
    args = parse_args()
    segments_dir = Path(args.segments_dir).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    segments = resolve_segments(segments_dir)
    if not cache_dir.exists():
        sys.exit(
            f"Cache directory {cache_dir} not found. Run setup to download FunASR models first."
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

    texts: list[str] = []
    for wav_path in segments:
        result = model.generate(input=str(wav_path))
        text = result[0]["text"]
        texts.append(text)

    output_path.write_text("\n".join(texts), encoding="utf-8")
    print(f"Wrote transcript with {len(texts)} segments to {output_path}")


if __name__ == "__main__":
    main()
