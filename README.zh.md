<p align="center">
  ⭐ If this tool helps you, please give it a Star!
</p>

---

# 中文版

---

<p align="center">
  <img src="https://img.shields.io/badge/version-2.0-blue" alt="v2.0"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"/>
  <img src="https://img.shields.io/badge/python-3.8+-orange" alt="Python 3.8+"/>
  <img src="https://img.shields.io/github/stars/huajielong/video_splitter?style=social" alt="Stars"/>
  <img src="https://img.shields.io/badge/FFmpeg-✓-brightgreen" alt="FFmpeg"/>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Cross-platform"/>
</p>

<h1 align="center">✂️ 视频自动拼接与移动工具</h1>
<p align="center"><b>Video Automatic Splicing and Moving Tool — 智能拼接，一键完成</b></p>
<p align="center">
  🎬 智能排序 · 🧩 自定义时长 · ⚡ 多线程并行 · 🖥️ 纯 GUI 体验
</p>

<p align="center">
  <a href="#-快速开始">🚀 快速开始</a> •
  <a href="#%EF%B8%8F-界面预览">🖥️ 界面预览</a> •
  <a href="#-核心特性">⚡ 核心特性</a> •
  <a href="#-使用说明">📖 使用说明</a> •
  <a href="#-常见问题">❓ 常见问题</a>
</p>

---

## 🤔 手动拼接视频又慢又烦？

整理了海量短视频，想合并成长视频却无从下手？手工操作费时费力：

| 你可能遇到的问题 | 这个工具帮你解决 |
|:-----------------|:---------------|
| ❓ 几十个短视频要手动拼接，太费时间 | ✅ **自动拼接** — 按日期排序，智能拼接至目标时长 |
| ❓ 拼接后时长不符合要求 | ✅ **自定义时长** — 60/120/180 秒或任意数值 |
| ❓ 文件太多，预处理单个等待太久 | ✅ **多线程并行** — 最多 6 线程同时预处理 |
| ❓ 命令行操作复杂，团队成员不会用 | ✅ **纯 GUI 设计** — 选择文件夹、点击按钮，就这么简单 |
| ❓ 碰见损坏文件就崩 | ✅ **异常处理** — 自动识别损坏/空文件并清理 |

### 🔥 适用场景

> **监控视频合并** → **短视频素材拼接** → **教学视频整理** → **个人视频归档**

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
|:-----|:----:|:-----|
| Python | 3.8+ | 运行环境 |
| FFmpeg | — | 视频处理引擎（需加入系统 PATH） |
| PyInstaller (打包用) | — | 可选，用于生成 exe |

### 一键安装

```bash
# 1. 克隆项目
git clone https://github.com/huajielong/video_splitter.git
cd video_splitter

# 2. 创建虚拟环境
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
python video_splitter.py
```

或者直接运行 `dist` 目录下的 `视频自动拼接与移动工具_修复版.exe`（Windows 免安装版）。

---

## 🖥️ 界面预览

![视频自动拼接与移动工具界面](images/program_interface.svg)

| 区域 | 说明 |
|:-----|:------|
| 📂 **左侧主界面** | 文件夹选择、拼接参数设置、处理进度显示 |
| 📊 **右侧结果弹窗** | 详细的处理统计信息（处理数、成功/失败数、总时长） |
| ⏱️ **时长设置** | 支持 60/120/180 秒预设或自定义输入 |
| 📈 **实时进度** | 预处理、优化、拼接步骤实时显示 |

---

## ⚡ 核心特性

| 特性 | 说明 |
|:-----|:------|
| 🧩 **智能排序** | 基于文件名日期自动排序，最新日期优先处理 |
| ⏱️ **自定义时长** | 目标拼接时长可配（60/120/180 秒或自定义） |
| ⚡ **多线程并行** | 最多 6 线程同时预处理视频，大幅提速 |
| 🖥️ **零弹窗体验** | 纯 GUI 操作，无终端窗口干扰 |
| 🔒 **安全恢复** | 异常中断后按钮状态自动恢复，不会卡死 |
| 🧹 **自动清理** | 处理完成后自动删除临时文件，不占磁盘 |
| 🔧 **异常处理** | 自动识别损坏文件、空文件并删除 |
| 📦 **便携打包** | 支持 PyInstaller 打包为单文件 exe |

---

## 📖 使用说明

1. **选择文件夹**：点击"浏览"选择「文件夹 A」（视频源）和「文件夹 B」（输出目标）
2. **设置时长**：选择目标视频时长（默认 60 秒）
3. **可选配置**：勾选「拼接成功后删除源文件」
4. **开始处理**：点击「开始处理」按钮

### 处理逻辑

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  读取文件夹 A  │────>│  按日期排序视频    │────>│  逐条判断时长  │
│  中的所有 MP4  │     │  (最新优先)       │     │              │
└──────────────┘     └──────────────────┘     └──────┬───────┘
                                                      │
                          ┌───────────────────────────┼───────────┐
                          ▼                           ▼           │
              ┌──────────────────┐         ┌──────────────────┐    │
              │  单视频 ≥ 设定时长 │         │  单视频 < 设定时长 │    │
              │  → 直接移至 B    │         │  → 拼接后续视频   │    │
              └──────────────────┘         │  直至 ≥ 设定时长  │    │
                                           └──────────────────┘    │
                          └───────────────────────────────────────┘
                                                      ▼
                                           ┌──────────────────┐
                                           │  显示结果汇总弹窗  │
                                           └──────────────────┘
```

---

## 📁 项目结构

```
video_splitter/
├── video_splitter.py        # 主程序（GUI 应用）
├── video_splitter.spec      # PyInstaller 打包配置
├── requirements.txt         # Python 依赖
├── images/                  # 界面截图
│   └── program_interface.svg
├── dist/                    # 打包好的可执行文件
├── Windows多版本兼容性说明.md # Windows 兼容性说明
└── README.md                # 💡 你在这里
```

---

## ❓ 常见问题

<details>
<summary><b>提示"缺少 FFmpeg"怎么办？</b></summary>
程序依赖 FFmpeg 进行视频处理。请从 <a href="https://ffmpeg.org/download.html">ffmpeg.org</a> 下载并添加到系统环境变量 PATH 中，或将 ffmpeg.exe 放在程序同目录下。
</details>

<details>
<summary><b>拼接后的视频没有声音？</b></summary>
请确保源视频包含音频轨道。程序会自动处理音频流，如果源视频没有音频，拼接后自然也是无声的。
</details>

<details>
<summary><b>处理超大视频（>1GB）时卡顿？</b></summary>
超大文件的拼接处理需要更多时间，请耐心等待。建议在性能较好的电脑上处理大文件。
</details>

<details>
<summary><b>可以打包成 exe 给其他人用吗？</b></summary>
可以。安装 PyInstaller 后运行：<code>pyinstaller video_splitter.spec</code>，或使用 <code>pyinstaller --onefile --windowed video_splitter.py</code> 生成单文件 exe。
</details>

<details>
<summary><b>文件名日期格式有要求吗？</b></summary>
程序识别 "年-月-日"（2024-05-20）和 "年月日"（20240520）两种格式。如果文件名中没有可识别的日期，文件将按默认顺序处理。
</details>

---

## 🤝 贡献

欢迎任何形式的贡献——提交 Issue、Pull Request 或改进文档。

<a href="https://github.com/huajielong/video_splitter/graphs/contributors">
  <img src="https://img.shields.io/badge/contributions-welcome-brightgreen" alt="Contributions Welcome"/>
</a>

## 📄 License

MIT © [huajielong](https://github.com/huajielong)

---

<p align="center">
  ⭐ 如果这个工具对你有帮助，请点个 Star 支持一下！
</p>
