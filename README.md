> [🇨🇳 中文说明](README.zh.md)

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0-blue" alt="v2.0"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"/>
  <img src="https://img.shields.io/badge/python-3.8+-orange" alt="Python 3.8+"/>
  <img src="https://img.shields.io/github/stars/huajielong/video_splitter?style=social" alt="Stars"/>
  <img src="https://img.shields.io/badge/FFmpeg-✓-brightgreen" alt="FFmpeg"/>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Cross-platform"/>
</p>

<h1 align="center">✂️ Video Splitter</h1>
<p align="center"><b>Automatic Video Splicing and Moving Tool</b></p>
<p align="center">
  🧩 Smart Date Sorting · ⏱️ Customizable Target Duration · ⚡ Multi-threaded Parallel Preprocessing · 🖥️ Pure GUI Desktop App
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-orange" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/FFmpeg-✓-brightgreen" alt="FFmpeg"/>
  <img src="https://img.shields.io/badge/GUI-tkinter-blue" alt="tkinter"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"/>
</p>

---

## 🤔 Tired of Manually Concatenating Videos?

Have a massive collection of short videos that you want to merge into longer clips but don't know where to start? Manual operations are time-consuming and tedious:

| Problem You May Face | How This Tool Helps |
|:---------------------|:--------------------|
| Dozens of short videos to splice manually — too much time | ✅ **Auto-splicing** — Sort by date, intelligently concatenate to target duration |
| Concatenated video doesn't match the desired length | ✅ **Custom duration** — 60/120/180 seconds or any custom value |
| Too many files, sequential preprocessing takes forever | ✅ **Multi-threaded parallel** — Up to 6 threads concurrently |
| Complex CLI commands — team members struggle | ✅ **Pure GUI** — Pick a folder, click a button, that's it |
| Corrupted files crash the process | ✅ **Error handling** — Auto-detect and skip corrupted/empty files |

### 🔥 Use Cases

> **Surveillance Video Merging** → **Short Video Compilation** → **Educational Video Organization** → **Personal Video Archiving**

---

## 🚀 Quick Start

### Requirements

| Dependency | Version | Notes |
|:-----------|:-------:|:------|
| Python | 3.8+ | Runtime environment |
| FFmpeg | — | Video processing engine (must be in system PATH) |
| PyInstaller (for packaging) | — | Optional, for generating standalone exe |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/huajielong/video_splitter.git
cd video_splitter

# 2. Create a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Run

```bash
python video_splitter.py
```

Or directly run `dist\视频自动拼接与移动工具_修复版.exe` (Windows standalone executable).

---

## 🖥️ Interface Preview

![Video Splitter Interface](images/program_interface.svg)

| Area | Description |
|:-----|:------------|
| 📂 **Left main panel** | Folder selection, splicing parameters, progress display |
| 📊 **Right result dialog** | Detailed processing statistics (processed, success/fail counts, total duration) |
| ⏱️ **Duration settings** | Preset 60/120/180 seconds or custom input |
| 📈 **Real-time progress** | Preprocessing, optimization, splicing steps shown in real time |

---

## ⚡ Key Features

| Feature | Description |
|:--------|:------------|
| 🧩 **Smart Sorting** | Auto-sort by filename date, newest first |
| ⏱️ **Custom Duration** | Configurable target duration (60/120/180s or custom) |
| ⚡ **Multi-threaded Parallel** | Up to 6 threads for simultaneous video preprocessing |
| 🖥️ **Zero-Popup Experience** | Pure GUI operation, no terminal window interference |
| 🔒 **Safe Recovery** | Button state auto-recovers after abnormal interruption |
| 🧹 **Auto Cleanup** | Temporary files removed automatically after processing |
| 🔧 **Error Handling** | Auto-detect and remove corrupted/empty files |
| 📦 **Portable Packaging** | Supports PyInstaller single-file exe packaging |

---

## 📖 Usage Guide

1. **Select folders**: Click "Browse" to choose "Folder A" (video source) and "Folder B" (output target)
2. **Set duration**: Select target video duration (default 60 seconds)
3. **Optional config**: Check "Delete source files after successful splicing"
4. **Start processing**: Click the "Start" button

### Processing Logic

```
┌────────────────┐     ┌────────────────────┐     ┌────────────────┐
│  Read all MP4s  │────>│  Sort videos by    │────>│  Evaluate each │
│  from Folder A  │     │  date (newest first)│     │  video duration │
└────────────────┘     └────────────────────┘     └───────┬────────┘
                                                            │
                          ┌─────────────────────────────────┼─────────────────┐
                          ▼                                 ▼                 │
              ┌──────────────────────┐         ┌──────────────────────┐       │
              │  Single video >=     │         │  Single video <      │       │
              │  target duration     │         │  target duration     │       │
              │  → Move directly to B│         │  → Concatenate with  │       │
              └──────────────────────┘         │  subsequent videos   │       │
                                                │  until >= target    │       │
                                                └──────────────────────┘       │
                          └───────────────────────────────────────────────────┘
                                                            ▼
                                               ┌──────────────────────┐
                                               │  Show result summary │
                                               └──────────────────────┘
```
