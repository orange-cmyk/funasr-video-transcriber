# FunASR 视频转写工具

本项目基于 [FunASR](https://github.com/alibaba-damo-academy/FunASR)，提供简易的中文语音离线转写方案，可直接处理本地音频或视频并生成带标点的文本结果。仓库已预置 ModelScope 模型缓存，适合在无网络环境下使用。

## 功能亮点
- 支持 16 kHz 单声道 WAV 音频的离线识别。
- 内置 Flask Web 界面，可上传视频并自动抽取音频、切片、转写。
- 统一使用本地 `modelscope_cache/`，搬迁目录即可复用模型。
- 提供批量处理脚本，方便处理已有的音频切片。

## 环境准备
- Python 3.10+（建议使用虚拟环境）
- `ffmpeg`（用于抽取与切分音频）
- Python 依赖：`funasr`、`torch`、`torchaudio`、`flask`

创建虚拟环境并安装依赖示例：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install funasr torch torchaudio flask
```

第一次部署时需要下载 FunASR 模型，请在联网环境下执行 `FUNASR_OFFLINE_SETUP.md` 中的步骤，确保 `modelscope_cache/` 下包含 `asr`、`vad` 和 `punc` 三个模型目录。离线迁移时只需复制整个 `modelscope_cache/` 文件夹。

## 使用方式

### 1. 命令行离线识别

```bash
source .venv/bin/activate
python run_chinese_asr.py --audio path/to/audio.wav
```

参数说明：
- `--audio`：16 kHz 单声道 WAV 文件路径。
- `--cache-dir`（可选，默认 `modelscope_cache`）：指定 FunASR 模型缓存路径。

脚本会在终端输出识别结果。

### 2. Web 视频转写

```bash
source .venv/bin/activate
python app.py
```

随后访问 `http://localhost:5001/`：
1. 上传 MP4 等 `ffmpeg` 支持的视频格式；
2. 程序自动提取音频、按 15 秒切片并转写；
3. 页面显示识别文本，同时在 `transcripts/` 目录保存 `*_transcript.txt`。

注意事项：
- 处理视频需要较长时间，请耐心等待页面刷新。
- 如需修改上传体积限制或切片时长，可调整 `app.py` 中相关配置。

### 3. 批量转写已切片音频

若已使用 `ffmpeg` 将音频切分为多个 WAV 文件，可运行：

```bash
source .venv/bin/activate
python transcribe_segments.py \
    --segments-dir path/to/segments \
    --output output_transcript.txt
```

脚本会遍历目录内的 `*.wav`，逐个识别并写入同一个文本文件。

## 项目结构

```
.
├── app.py                     # Web 视频转写入口
├── run_chinese_asr.py         # 单文件离线识别脚本
├── transcribe_segments.py     # 批量处理音频切片脚本
├── FUNASR_OFFLINE_SETUP.md    # 模型与环境准备指南
├── modelscope_cache/          # 预下载的 FunASR 模型缓存
└── transcripts/               # 转写结果输出目录
```

## 常见问题
- **缺少模型或报错 `model not found`**：检查 `modelscope_cache/models/iic/` 是否包含三个模型目录，必要时重新执行下载步骤。
- **无法调用 `ffmpeg`**：确认系统已安装并能在终端直接运行 `ffmpeg`，macOS/Linux 可通过包管理器安装。
- **显存/内存占用较高**：大型模型转写较长音频时需要足够内存，建议分段处理或升级硬件。

## 许可证

本仓库随附的代码遵循 `LICENSE` 文件中的条款，FunASR 与 ModelScope 模型请遵循各自的开源协议与使用许可。
