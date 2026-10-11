# write-audio-pro

> 写乐谱，用**真实采样音源**发声 — Compose music in Python, render with real sampled instruments.

用代码写乐谱、用 **FluidSynth + SoundFont 真实采样** 渲染成品音乐（3 分钟级）。
乐谱即代码，全部显式，无随机预设——同一乐谱逐样本可复现。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![FluidSynth](https://img.shields.io/badge/engine-FluidSynth-green.svg)](https://www.fluidsynth.org/)

```python
import write_audio_pro as wa

s = wa.Song(bpm=66)
piano = s.track("piano")                      # 真·三角钢琴采样
strings = s.track("strings", gain_db=-6)      # 真·弦乐合奏
piano.notes([(0, "A4", 2), (2, "C5", 2), (4, "E5", 2)])
strings.pad_chord(1, "Am", dur=4)
s.length(bars=8)
s.render("out.mp3", midi="out.mid")           # 真音源 + 混响 + 母带
```

## 亮点

- **真实音色**：不是数学合成波形，而是 FluidSynth 加载 SoundFont 真实录音采样——真钢琴、真弦乐、真大提琴。
- **乐谱即代码**：曲式/和弦/旋律/织体/音量全部在 Python 脚本里显式写出，无自动作曲、无随机。
- **音量全可控**：分轨基准音量 + **段落级音量包络**，AI 自己编配，避免某件乐器盖过其他。
- **诊断友好**：渲染报告给出分轨响度，某轨盖过其他声部时自动警告。
- **可复现**：同乐谱两次渲染逐样本相等。
- **可导出**：同时输出 MIDI，拖进任何 DAW / MuseScore 二次编曲。

## 为什么音色好听

纯代码合成波形（正弦/锯齿叠加）只能得到"电子玩具"音色；**真实乐器的好听来自逐键/
逐音的录音采样**。write-audio-pro 用 FluidSynth 加载 SoundFont（如 MuseScore General、
FluidR3），你写的 MIDI 乐谱由这些真实采样发声——真钢琴、真弦乐、真大提琴。

## 安装

### 方式一：pip 安装（推荐）

```bash
pip install git+https://github.com/haocker/write-audio-pro.git
```

### 方式二：克隆仓库

```bash
git clone https://github.com/haocker/write-audio-pro.git
cd write-audio-pro
pip install -r requirements.txt
# 运行时把 runtime/ 加入 PYTHONPATH 即可 import write_audio_pro
```

### 系统依赖（发声引擎 + 音色库 + 编码器）

```bash
# Python 依赖
pip install numpy pretty_midi mido

# Linux（一键）
sudo apt install fluidsynth musescore-general-soundfont fluid-soundfont-gm ffmpeg

# macOS
brew install fluid-synth ffmpeg     # 再下载一个 .sf2 音色库
# Windows: 装 fluidsynth + ffmpeg，下载 FluidR3_GM.sf2 / MuseScore_General.sf3
```

音色库查找顺序：环境变量 `WRITE_AUDIO_PRO_SF2` → 系统标准位置 → pretty_midi 自带兜底。
可用 `wa.find_soundfont()` 查看当前会用什么。


## 30 秒上手

```bash
python examples/unsent-letter/make.py          # 渲染《未寄出的信》（3 分钟，≈40 秒）
python tests/smoke.py                          # 端到端自测
```

或在你自己的乐谱脚本目录：

```bash
python -m write_audio_pro song.py --out D:/music/track.mp3 --midi D:/music/track.mid
python -m write_audio_pro song.py --check           # 只打印乐谱摘要
```

## 库用法全表

```python
import write_audio_pro as wa

# ——— 乐谱 ———
s = wa.Song(bpm=66, beats_per_bar=4, tail=2.0)       # tail = 乐尾缓冲（秒）

t = s.track("cello", name="cello_line", gain_db=-5, pan=-0.2)
# instrument 可为乐器名（见 knowledge/gm-programs.md）或 GM 号 0-127
# name 可省（默认=乐器名，重名自动 _2）；pan -1..1 声像（默认 0 居中）
# gain_db 单轨音量调整（dB）

t.note(0, "A4", 2.0, 74)               # (拍, 音名/MIDI, 时值[拍], 力度 0-127 或 0.0-1.0)
t.notes([                               # 批量（三种写法混合均可）
    (0, "E5", 0.7),                     # 元组 (at, pitch[, dur[, vel]])
    {"at": 2, "pitch": "C5", "dur": 1},
    (4, 57, 2, 0.6),                    # vel 也可给 0.0-1.0 比例
])
t.chord_at(0, "Am7", dur=4, octave=3)           # 在 0 拍落一个 Am7
t.pad_chord(1, "Am", dur=4, add_root_octave=True)   # 按小节（1 基）落和弦垫

# ——— 音量 / 声部平衡（避免某件乐器盖过其他）———
song.mix(piano=0, strings=-7, cello=-5, choir=-11)   # 一次性设定各轨基准音量（dB）
song.balance(lead="piano", others_db=-9)             # 主奏 0dB，其余统一压低
t.set_volume(at_beat, db)                            # 逐拍设定本轨音量（形成包络）
song.set_volume("strings", bar, db)                  # 按小节设定某轨音量（AI 最常用）
t.fade_volume(at0, db0, at1, db1)                    # 一段音量过渡（渐入/渐出）
t.volume_db_at(beat)                                 # 查询某拍处的音量（调试用）

s.length(bars=48)                       # 曲长；渲染输出 = 曲长 + tail
s.fade(in_seconds=1.5, out_seconds=5.0) # 整曲渐入/渐出
print(s.duration_sec(), s.stats())

# ——— 渲染 ———
rep = s.render(
    out="track.mp3",        # 输出 mp3 或 wav
    wav=None,               # 额外输出 wav 路径
    midi="track.mid",       # 导出 MIDI（可拖进 DAW / MuseScore 二次编曲）
    soundfont="auto",       # 音色库；"auto" 自动查找
    lufs=-14.0,             # 响度目标（稀疏抒情曲会保护动态，不强压）
    reverb_mix=0.30,        # 混响湿声比例 0..1
    reverb_room=0.62,       # 空间大小 0..1
    bitrate=192,            # mp3 码率
    fade_in=None, fade_out=None,   # 覆盖 song.fade(...)
    keep_wav=False, title="标题",
)
print(rep["lufs"], rep["seconds"], rep["soundfont"])
# rep["tracks"]   每轨混音后的 rms_db / peak_db（发现"谁盖过谁"）
# rep["warnings"] 某轨明显压过其他声部时的提示

# ——— 乐理工具 ———
wa.midi("A3")            # -> 57（音名 → MIDI；也接受 MIDI 数值）
wa.freq("A3")            # -> 220.0
wa.note_name(57)         # -> "A3"
wa.chord("Am7", 3)       # -> [57, 60, 64, 67]；支持 C/E 斜杠低音、maj7、sus4、add9 …
wa.scale("A", "minor", 3)  # -> 音阶 8 个音（MIDI）
wa.resolve_scale("harmonic minor")
```

## 命令行

```
python -m write_audio_pro song.py                            # 渲染（脚本里定义 song = wa.Song(...)）
python -m write_audio_pro song.py --out x.mp3 --midi x.mid
python -m write_audio_pro song.py --lufs -14 --bitrate 192 --reverb 0.32
python -m write_audio_pro song.py --fade-out 5 --keep-wav
python -m write_audio_pro song.py --check                    # 只打印乐谱摘要，不渲染
```

## 输出说明

| 产物 | 说明 |
|---|---|
| `*.mp3` | 默认 192kbps；混响 → 母带（峰值 ≤0.94，报告整体响度） |
| `*.wav` | 44.1kHz 立体声 16-bit（指定或 `keep_wav` 时） |
| `*.mid` | 标准 MIDI，可拖进任何 DAW / MuseScore 再编曲 |

## 示例

`examples/unsent-letter/`：《未寄出的信》—— 48 小节 / A 小调 / 63 BPM ≈ 3 分钟，
钢琴 + 弦乐 + 大提琴 + 合唱四声部，全部音符与音量包络显式写出。
结构：独白 → 倾诉 → 翻涌 → 释放 → 归寂。

```bash
python examples/unsent-letter/make.py
```

- 成品：[`examples/unsent-letter/out/unsent-letter.mp3`](examples/unsent-letter/out/unsent-letter.mp3)
- 乐谱：[`examples/unsent-letter/make.py`](examples/unsent-letter/make.py)

## 自测

```bash
python tests/smoke.py     # 乐理/乐器/乐谱/音量/MIDI/渲染 端到端（≈10 秒）
```

## License

[MIT](LICENSE)。生成的 MIDI 无版权，可自由使用；所用 SoundFont 各有独立授权，请自行确认。

- **和"纯代码合成波形"的工具（如 codingaudio）有什么不同？**
  那个从零用 numpy 造波形，音色像电子玩具；write_audio_pro 是"写 MIDI → FluidSynth 加载
  真实采样发声"，真钢琴/真弦乐。同乐谱，两种引擎音色天差地别。
- **旋律怎么来？** 你（AI/作者）写：`piano.notes([(0, "E5", 0.7), ...])`，
  或用 Python 循环把 `wa.chord` / `wa.scale` 组织成乐句。
- **想换风格？** 没有"风格参数"——换乐器、换和声、换织体、换速度，就是你写的乐谱。
- **没有打击乐？** 本 skill 专注真实音色的抒情/管弦音乐。需要鼓组/电子乐，
  用合成引擎类工具；或用 GM 打击乐 program（通道 10）。
- **怎么做结尾？** 逐层退出 + 最后 1-2 小节只留钢琴/长音 + `s.fade(out_seconds=5)`。
- **能商用吗？** 生成的 MIDI 无版权；SoundFont 各自的授权请自行确认（MuseScore General
  为 CC0/MIT 系，FluidR3 为 MIT 系，一般可自由使用）。
