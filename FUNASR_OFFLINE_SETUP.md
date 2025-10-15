## FunASR 中文离线部署说明

本目录已经准备好 FunASR 运行环境与中文识别模型，可在完全离线的情况下做推理。下列步骤也可帮助你在其他机器复现。

### 1. 创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install funasr torch torchaudio
```

> 已在当前目录的 `.venv/` 中安装好依赖，如需重新安装可重复上述命令。

### 2. 下载所需中文模型

我们将 ModelScope 的缓存目录固定在 `./modelscope_cache`，方便离线搬迁：

```bash
source .venv/bin/activate
MODELSCOPE_CACHE=$(pwd)/modelscope_cache python - <<'PY'
from funasr import AutoModel

AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",
    punc_model="ct-punc",
    disable_update=True,
)
PY
```

首次运行会自动从 ModelScope 下载三个模型：

- `paraformer-zh`（约 944 MB）：中文语音识别主模型  
- `fsmn-vad`（约 1.6 MB）：语音活动检测  
- `ct-punc`（约 1.05 GB）：断句与标点

当前目录已经完成下载，可直接使用；如需迁移，只需携带 `modelscope_cache/`。

### 3. 离线推理

准备 16 kHz 单声道 WAV 音频后执行：

```bash
source .venv/bin/activate
python run_chinese_asr.py --audio path/to/audio.wav
```

脚本会自动读取 `modelscope_cache` 中的模型并输出带标点的中文文本。

### 4. 常见问题

- **磁盘占用**：当前中文模型缓存总计约 2.0 GB，可按需删除 `modelscope_cache/models/iic/` 中不需要的模型目录。  
- **断网环境**：确保在联网状态下完成第 2 步后再切换到离线环境，即可保持可用。  
- **音频格式**：输入需为 PCM 编码的 WAV，如是其它格式请先使用 `ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav` 转换。

### 5. Web 页面（可选）

项目中提供了 `app.py`，可启动一个简易网页把视频上传后自动转写：

```bash
source .venv/bin/activate
pip install flask  # 已安装可跳过
python app.py
```

浏览器访问 http://localhost:5000 ，上传 MP4 等视频，系统会：

1. 用 `ffmpeg` 抽取音频并切片  
2. 调用 FunASR 进行识别  
3. 在页面展示文本，同时将结果保存到 `transcripts/`，可下载 `.txt` 文件。
