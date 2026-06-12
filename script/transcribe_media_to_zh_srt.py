#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


DEFAULT_MODEL = "SoybeanMilk/faster-whisper-Breeze-ASR-25"

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
    "course cup": "COSCUP",
    "Course Cup": "COSCUP",
    "D code": "LeetCode",
    "D Code": "LeetCode",
    "decode": "LeetCode",
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
    "swift algorithm": "Swift Algorithms",
    "Swift algorithm": "Swift Algorithms",
    "swift algorithms": "Swift Algorithms",
    "Swift algorithms": "Swift Algorithms",
    "severe algorithm": "Swift Algorithms",
    "smooth algorithm": "Swift Algorithms",
    "surface algorithm": "Swift Algorithms",
    "superalgorithm": "Swift Algorithms",
    "社群 media": "社群媒體",
    "社群媒體 上": "社群媒體上",
    "line 聊天機器人": "LINE 聊天機器人",
    "LeetCode 在使用 Swift 解題": "LeetCode，並使用 Swift 解題",
    "functional programming": "Functional Programming",
    "一程": "議程",
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


def split_sentences(text: str) -> list[str]:
    protected_tokens = {
        "try!Swift": "try<EXCLAMATION>Swift",
    }
    for token, placeholder in protected_tokens.items():
        text = text.replace(token, placeholder)

    sentences = []
    for part in re.split(r"(?<=[。！？!?])\s*", text):
        for token, placeholder in protected_tokens.items():
            part = part.replace(placeholder, token)
        part = part.strip()
        if part:
            sentences.append(part)
    return sentences or [text]


def group_sentences(
    sentences: list[str],
    max_sentences: int,
    merge_short_under: int,
) -> list[str]:
    groups = []
    current = []

    for sentence in sentences:
        if not current:
            current = [sentence]
            continue

        current_text = "".join(current)
        should_merge_short = (
            len(current_text) < merge_short_under or len(sentence) < merge_short_under
        )
        can_merge = len(current) < max_sentences and should_merge_short
        if can_merge:
            current.append(sentence)
        else:
            groups.append("".join(current))
            current = [sentence]

    if current:
        groups.append("".join(current))
    return groups


def allocate_timings(start: float, end: float, texts: list[str]) -> list[tuple[float, float]]:
    duration = max(end - start, 0.001)
    weights = [max(len(text), 1) for text in texts]
    total = sum(weights)
    timings = []
    cursor = start

    for index, weight in enumerate(weights):
        if index == len(weights) - 1:
            next_cursor = end
        else:
            next_cursor = cursor + duration * (weight / total)
        timings.append((cursor, max(next_cursor, cursor + 0.001)))
        cursor = next_cursor

    return timings


def write_srt(
    segments,
    output_path: Path,
    converter,
    replacements: dict[str, str],
    max_sentences: int,
    merge_short_under: int,
) -> None:
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
        captions = group_sentences(
            split_sentences(text),
            max_sentences=max_sentences,
            merge_short_under=merge_short_under,
        )

        for caption, (caption_start, caption_end) in zip(
            captions, allocate_timings(start, end, captions)
        ):
            blocks.append(str(index))
            blocks.append(
                f"{format_timestamp(caption_start)} --> {format_timestamp(caption_end)}"
            )
            blocks.append(caption)
            blocks.append("")
            index += 1

    output_path.write_text("\n".join(blocks), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Transcribe audio/video to Traditional Chinese SRT with "
            "Breeze ASR 25 through faster-whisper."
        )
    )
    parser.add_argument("input", type=Path, help="Input audio or video file.")
    parser.add_argument("-o", "--output", type=Path, help="Output .srt path.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=(
            "CTranslate2/faster-whisper model name or local model path. "
            f"Defaults to {DEFAULT_MODEL}."
        ),
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
    parser.add_argument(
        "--max-sentences",
        type=int,
        default=2,
        help="Maximum sentence count per caption.",
    )
    parser.add_argument(
        "--merge-short-under",
        type=int,
        default=8,
        help="Merge very short adjacent sentences under this character count.",
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
        "這是一場台灣軟體研討會議程，請以台灣繁體中文轉錄。"
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
    write_srt(
        segments,
        output,
        OpenCC("s2twp"),
        replacements,
        max_sentences=max(args.max_sentences, 1),
        merge_short_under=max(args.merge_short_under, 0),
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
