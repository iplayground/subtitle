#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


DEFAULT_KEYWORDS = [
    "Swift",
    "iOS",
    "Functional Programming",
    "Higher-order functions",
    "map",
    "flatMap",
    "compactMap",
    "filter",
    "reduce",
    "forEach",
    "sorted",
    "zip",
    "enumerated",
    "closure",
    "Optional",
    "Array",
    "Sequence",
    "Collection",
    "LeetCode",
    "Swift Algorithms",
]

DEFAULT_REPLACEMENTS = {
    "TrySwift": "try!Swift",
    "try Swift": "try!Swift",
    "Try Swift": "try!Swift",
    "I Playground": "iPlayground",
    "i playground": "iPlayground",
    "Coscop": "COSCUP",
    "Cos Cup": "COSCUP",
    "COS Cup": "COSCUP",
    "D code": "LeetCode",
    "D Code": "LeetCode",
    "Leetcode": "LeetCode",
    "Leet Code": "LeetCode",
    "WHDC": "WWDC",
    "Call along": "code-along",
    "code along": "code-along",
    "高階按數": "高階函數",
    "按數": "函數",
    "flamemap": "flatMap",
    "flatmap": "flatMap",
    "Flat Map": "flatMap",
    "companymap": "compactMap",
    "commentmap": "compactMap",
    "compactmap": "compactMap",
    "Compact Map": "compactMap",
    "4Loop": "for loop",
    "4 Loop": "for loop",
    "one and two": "one-liner",
    "civil aggregation": "Swift Algorithms",
    "import civil aggregation": "import Swift Algorithms",
}


def ensure_package(import_name: str, package_name: Optional[str] = None) -> None:
    try:
        __import__(import_name)
    except ImportError:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--user",
                package_name or import_name,
            ]
        )


def format_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def parse_replacements(values: list[str]) -> dict[str, str]:
    replacements = dict(DEFAULT_REPLACEMENTS)
    for value in values:
        if "=" not in value:
            raise ValueError(f"--replace must use OLD=NEW format: {value}")
        old, new = value.split("=", 1)
        replacements[old] = new
    return replacements


def normalize_text(text: str, converter, replacements: dict[str, str]) -> str:
    text = converter.convert(text.strip())
    text = re.sub(r"\s+", " ", text)
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"([\u4e00-\u9fff]),", r"\1，", text)
    text = re.sub(r",([\u4e00-\u9fff])", r"，\1", text)
    return text


def write_srt(segments, output_path: Path, converter, replacements: dict[str, str]) -> None:
    blocks = []
    last_end = 0.0
    index = 1

    for segment in segments:
        text = normalize_text(segment.text, converter, replacements)
        if not text:
            continue

        start = max(segment.start, last_end)
        end = max(segment.end, start + 0.001)
        last_end = end

        blocks.append(str(index))
        blocks.append(f"{format_timestamp(start)} --> {format_timestamp(end)}")
        blocks.append(text)
        blocks.append("")
        index += 1

    output_path.write_text("\n".join(blocks), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe audio/video to Traditional Chinese SRT with faster-whisper."
    )
    parser.add_argument("input", type=Path, help="Input audio or video file.")
    parser.add_argument("-o", "--output", type=Path, help="Output .srt path.")
    parser.add_argument(
        "--model",
        default="large-v3-turbo",
        help="Whisper model name. Use small/medium for faster CPU runs.",
    )
    parser.add_argument("--device", default="cpu", help="cpu, cuda, or auto.")
    parser.add_argument("--compute-type", default="int8", help="int8, float16, float32, etc.")
    parser.add_argument(
        "--keywords",
        default="",
        help="Comma-separated talk-specific keywords to bias recognition.",
    )
    parser.add_argument(
        "--replace",
        action="append",
        default=[],
        help="Post-processing replacement in OLD=NEW format. Can be repeated.",
    )
    parser.add_argument(
        "--language",
        default="zh",
        help="Spoken language code. Use zh for Mandarin, en for English, ja for Japanese.",
    )
    args = parser.parse_args()

    ensure_package("faster_whisper", "faster-whisper")
    ensure_package("opencc", "opencc-python-reimplemented")

    from faster_whisper import WhisperModel
    from opencc import OpenCC

    if not args.input.exists():
        raise FileNotFoundError(args.input)

    output = args.output or args.input.with_name(f"{args.input.stem}_zh.srt")
    extra_keywords = [item.strip() for item in args.keywords.split(",") if item.strip()]
    keywords = DEFAULT_KEYWORDS + extra_keywords
    prompt = (
        "這是一場台灣軟體研討會議程，請以繁體中文轉錄。"
        "專有名詞包含：" + "、".join(dict.fromkeys(keywords))
    )
    replacements = parse_replacements(args.replace)

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    segments, info = model.transcribe(
        str(args.input),
        language=args.language,
        task="transcribe",
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        initial_prompt=prompt,
        condition_on_previous_text=True,
    )

    print(
        f"Detected language={info.language}, probability={info.language_probability:.3f}, "
        f"duration={info.duration:.1f}s"
    )
    write_srt(segments, output, OpenCC("s2twp"), replacements)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
