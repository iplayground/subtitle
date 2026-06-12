# translate scripts

這個專案主要提供一組 `.srt` 字幕處理腳本，以下為 `script/` 目錄中每一支 Python 檔案的用途與用法。

## 前置需求

- Python 3.9+
- 在專案根目錄執行指令（`/home/hokila/projects/translate`）
- `translate_srt.py` 需要可用的 `OPENAI_API_KEY`（可放在 `.env`）

## 腳本用法總表

| 檔案 | 功能 | 用法 | 範例 |
|---|---|---|---|
| `script/add_spaces_srt.py` | 在中文字幕與英數之間自動補空格（直接覆蓋原檔） | `python script/add_spaces_srt.py <字幕檔.srt>` | `python script/add_spaces_srt.py ./iosdc2025/demo.zh.srt` |
| `script/check_srt_format.py` | 檢查 SRT 格式（索引、時間軸、重疊、空內容）；失敗時寫出 `srt_report.txt` | `python script/check_srt_format.py` | `python script/check_srt_format.py` |
| `script/clean_subtitle_numbers.py` | 移除字幕文字行開頭的「數字.」與句尾 `，。`（直接覆蓋原檔） | `python script/clean_subtitle_numbers.py <檔案路徑>` | `python script/clean_subtitle_numbers.py ./iosdc2025/demo.zh.srt` |
| `script/fix_srt_overlap.py` | 修正相鄰字幕時間重疊（若重疊，後一條起始時間改成前一條結束 +1ms） | `python script/fix_srt_overlap.py <字幕檔.srt>` | `python script/fix_srt_overlap.py ./iosdc2025/demo.zh.srt` |
| `script/reindex_srt.py` | 重新編號 SRT 區塊索引（從 1 連號）；可處理單檔或資料夾遞迴 | `python script/reindex_srt.py [檔案或資料夾路徑]` | `python script/reindex_srt.py ./iosdc2025` |
| `script/shift_srt.py` | 從指定字幕編號開始，整體平移時間軸（可正可負秒） | `python script/shift_srt.py <檔名> <開始字幕編號> <調整秒數>` | `python script/shift_srt.py ./iosdc2025/demo.zh.srt 810 0.5` |
| `script/transcribe_media_to_zh_srt.py` | 使用 Breeze ASR 25 / faster-whisper 將音訊或影片轉錄為繁體中文 SRT；支援關鍵字提示與術語替換 | `python script/transcribe_media_to_zh_srt.py <影音檔> [--keywords ...]` | `python script/transcribe_media_to_zh_srt.py ./2025/talk.mp4 --keywords "COSCUP,Swift,iOS"` |
| `script/translate_srt.py` | 將輸入字幕翻譯成繁中，輸出同名 `.zh.srt` | `python script/translate_srt.py <input.srt>` | `python script/translate_srt.py ./iosdc2025/demo.jp.srt` |

## 補充

- 多數腳本會直接覆蓋原始檔案，建議先備份或先 commit 再執行。
- `check_srt_format.py` 在 CI 可透過 `CHANGED_FILES` 環境變數指定檢查檔案；本機未設定時會掃描目前目錄下所有 `.srt`。

## Breeze ASR 25 轉錄範例

第一次使用會自動安裝 Python 套件，並下載 `SoybeanMilk/faster-whisper-Breeze-ASR-25` 模型：

```bash
python3 script/transcribe_media_to_zh_srt.py \
  "2025/Day01-03-Let's Functional Programming in Your Swift.mp3" \
  --keywords "Garmin,鄭宇哲,iPlayground,COSCUP,try!Swift,Swift,iOS,Functional Programming,LeetCode"
```

預設會輸出同資料夾的 `_zh.srt` 檔。若要指定輸出檔：

```bash
python3 script/transcribe_media_to_zh_srt.py input.mp4 -o output.zh.srt
```

預設會依句子切字幕，每個 caption 最多 2 句，短句才會合併。若要調整每段最多句數：

```bash
python3 script/transcribe_media_to_zh_srt.py input.mp4 --max-sentences 1
```

短句合併門檻預設為 8 個字；例如「好」「謝謝」這種短句會比較容易跟前後句合併。若想降低合併機率：

```bash
python3 script/transcribe_media_to_zh_srt.py input.mp4 --merge-short-under 0
```

模型會放在 Hugging Face cache，例如 macOS 預設路徑：

```bash
~/.cache/huggingface/hub/models--SoybeanMilk--faster-whisper-Breeze-ASR-25
```

若要改用其他 faster-whisper 模型或本機模型資料夾，可以用 `--model` 指定：

```bash
python3 script/transcribe_media_to_zh_srt.py input.mp4 --model large-v3-turbo
```

轉錄後建議跑一次格式檢查：

```bash
python3 script/check_srt_format.py
```
