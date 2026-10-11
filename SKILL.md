---
name: write-audio-pro
description: 用代码写乐谱、用真实采样音源渲染成品音乐（钢琴/弦乐/管弦/抒情，3 分钟级 MP3/WAV）。乐谱即代码——曲式/和弦/旋律/织体/音量全部由你在 Python 脚本里显式写出（无自动作曲、无随机预设）；发声由 FluidSynth + SoundFont 真实采样完成，支持分轨音量与段落级音量包络（AI 自己编配，避免某件乐器盖过其他），自带混响/母带与 MIDI 导出。适合写悲伤/治愈/电影感等抒情音乐。
---

# write-audio-pro — 写乐谱，用真实采样音源发声

**一句话**：乐谱（显式音符）进 → **真钢琴/真弦乐**成品出。
没有随机预设、没有自动作曲；曲式/和弦/旋律/织体全部由你在 Python 乐谱里显式写出。
音色由 FluidSynth 加载真实录制的 SoundFont 采样完成——这是它比"纯代码造波形"好听的关键。

```python
import write_audio_pro as wa

s = wa.Song(bpm=66)                          # A 小调慢板
piano   = s.track("piano")                    # 真·三角钢琴采样
strings = s.track("strings", gain_db=-6)      # 真·弦乐合奏
cello   = s.track("cello", gain_db=-5)

piano.notes([(0, "A4", 2), (2, "C5", 2), (4, "E5", 2)])   # (拍, 音名/MIDI, 时值[拍])
strings.pad_chord(1, "Am", dur=4)                          # 和弦名直达
for bar in range(1, 9):
    cello.note(s.bar_to_beat(bar, 0), "A2", 3.8, 58)

s.length(bars=8)
rep = s.render("out.mp3", midi="out.mid")      # 渲染：真实音源 + 混响 + 母带
print(rep["lufs"], rep["seconds"], rep["soundfont"])
```

命令行：

```bash
python -m write_audio_pro song.py --out track.mp3 --midi track.mid   # 渲染
python -m write_audio_pro song.py --check                            # 只看乐谱摘要
```

## 分工（核心理念）

| 层 | 是谁的事 | 说明 |
|---|---|---|
| 曲式、和弦、旋律、织体、**每个音符、每处音量变化** | **你（AI）** | 在乐谱脚本里显式写出；用 Python 循环/函数组织重复与变奏 |
| 音色合成、混响、母带、编码 | **引擎** | FluidSynth + SoundFont + FFmpeg：忠实渲染，不做创作决策 |

- **真实采样音源**：乐器 = General MIDI program，由 SoundFont（真实录制采样）发声。真钢琴、真弦乐、真大提琴。
- **音量由你控制**：分轨基准音量 + 段落级音量包络，全部在乐谱里写死。引擎不做"自动平衡"——
  该让谁让位、该让谁托起，都是你编配的一部分（见下节）。
- **无随机预设**：没有"自动选音型/自动旋律/自动曲式"；同乐谱两次渲染逐样本相等。
- **可验收**：输出 MP3/WAV，峰值受限幅保护（≤ 0.94），渲染报告给出**分轨响度**与**盖过警告**。

## 音量控制（重点：避免乐器互相盖过）

抒情曲最常翻车的地方是"伴奏盖过主奏"。引擎提供三层音量手段，**全部由 AI 在乐谱里显式控制**：

```python
# ① 分轨基准音量——整曲电平，写谱时先定大局
song.mix(piano=0, strings=-7, cello=-5, choir=-11)   # 或 s.track("strings", gain_db=-7)
song.balance(lead="piano", others_db=-9)             # 主奏 0dB，其余统一压低

# ② 段落级音量包络——跟随情绪，把伴奏写成曲线（最常用）
song.set_volume("strings", 1, -20)    # 第 1 小节起：弦乐几乎只是气声
song.set_volume("strings", 9, -13)    # 第 9 小节起：浮出
song.set_volume("strings", 33, -5)    # 第 33 小节起：高潮最饱满
song.set_volume("strings", 41, -9)    # 归寂：退回去
# 也可用逐拍 t.set_volume(at_beat, db) 或 t.fade_volume(at0, db0, at1, db1)

# ③ 同轨内的力度（velocity）——表情起伏
piano.notes([(0, "A4", 2, 74), (2, "C5", 2, 82)])    # 后一个音更响
```

- 相邻音量点之间按 **dB 线性过渡**，首点之前/末点之后保持——所以 `set_volume(0, -60)` 可实现"从静音渐入"。
- 渲染报告里 `rep["tracks"]` 给出每轨混音后的 `rms_db` / `peak_db`，`rep["warnings"]` 会在某轨
  明显压过其他声部（RMS 差 > 8dB）时提示你调整。
- **-60dB 视作静音**：用来让某轨"退场"（如 `song.set_volume("cello", 45, -60)`）。

## 环境

- Python 3.8+；依赖 `numpy`、`pretty_midi`、`mido`
- **FluidSynth**（发声引擎）：`apt install fluidsynth` / `brew install fluid-synth` / [官网](https://www.fluidsynth.org/)
- **SoundFont 音色库**（真实采样）：`apt install musescore-general-soundfont` 或 `fluid-soundfont-gm`；
  或用环境变量 `WRITE_AUDIO_PRO_SF2=/path/to/xxx.sf2` 指定
- **FFmpeg**（响度测量 + mp3 编码）：`apt install ffmpeg` / `brew install ffmpeg`

```bash
pip install numpy pretty_midi mido
# Linux 一键：
sudo apt install fluidsynth musescore-general-soundfont fluid-soundfont-gm ffmpeg
```

## API 速览

```python
# — 乐谱 —
s = wa.Song(bpm=66, beats_per_bar=4, tail=2.0)
t = s.track(instrument, name=None, gain_db=0.0, pan=0.0)   # instrument=乐器名或 GM 号
t.note(at, pitch, dur=1.0, vel=72)          # at/dur 单位=拍；vel 0-127 或 0.0-1.0
t.notes([(0,"A4",2), (2,"C5",2), {"at":4,"pitch":57,"dur":1}])
t.chord_at(at, "Am", dur=4, octave=3)        # 和弦名直达（支持 'Cmaj7' 'C/E'）
t.pad_chord(bar, "Am", dur=4)                # 按小节落和弦垫（自动加低八度根音）

# — 音量 / 声部平衡（怕某件乐器盖过其他？用这套）—
song.mix(piano=0, strings=-7, cello=-5)      # 一次性设定各轨基准音量（dB）
song.balance(lead="piano", others_db=-9)     # 主奏 0dB、其余统一压低
t.set_volume(at_beat, db)                    # 逐拍设定本轨音量（形成包络）
song.set_volume("strings", bar, db)          # 按小节设定某轨音量（AI 常用）
t.fade_volume(at0, db0, at1, db1)            # 一段音量过渡（渐入/渐出）

s.length(bars=48)                            # 显式曲长（输出 = 曲长 + tail）
s.fade(in_seconds=1.5, out_seconds=5.0)      # 整曲渐变
s.bar_to_beat(bar, b=0.0)                    # 小节内第 b 拍 → 绝对拍位置
s.duration_sec() / s.stats()                 # 时长 / 摘要（不渲染）

rep = s.render(out="x.mp3", midi="x.mid", soundfont="auto",
               lufs=-14.0, reverb_mix=0.30, reverb_room=0.62,
               fade_in=None, fade_out=None, bitrate=192, keep_wav=False)
# rep["tracks"] 每条含 rms_db / peak_db（分轨响度，用于发现"谁盖过谁"）
# rep["warnings"] 自动提示某轨是否明显压过其他声部

# — 乐理工具 —
wa.midi("A3") -> 57     wa.freq("A3") -> 220.0     wa.note_name(57) -> "A3"
wa.chord("Am7", 3) -> [57,60,64,67]     wa.chord("C/E", 3)   # 斜杠低音
wa.scale("A", "minor", 3) -> 8 个音的 MIDI 列表
```

**乐器名**（`s.track(name)` 或 GM 号）：`piano` `electric_piano` `rhodes` `organ`
`guitar` `bass` `violin` `viola` `cello` `contrabass` `strings` `pizzicato_strings`
`choir` `trumpet` `brass` `flute` `clarinet` `sax` `pad` `synth_strings` `bell`
`marimba` `vibraphone` `harp` `timpani` … 完整表见 `knowledge/gm-programs.md`；
成分编制建议见 `wa.ENSEMBLES`。

## 示例曲

- `examples/unsent-letter/make.py`：《未寄出的信》48 小节 / A 小调 / 63 BPM ≈ 3 分钟，
  钢琴 + 弦乐 + 大提琴 + 合唱，全部音符显式；结构 独白→倾诉→翻涌→释放→归寂。
  含成品 mp3 与 MIDI。

```bash
python examples/unsent-letter/make.py
```

## 验证

```bash
python tests/smoke.py      # 乐理/乐器/乐谱/MIDI/渲染 端到端自测（≈10 秒）
```

## 目录

- `runtime/write_audio_pro/` — 运行时（`song.py` 乐谱+渲染、`theory.py` 乐理、`instruments.py` 音色表）
- `knowledge/writing-guide.md` — 写乐谱指南（音符写法/编曲/配器/母带/避坑）
- `knowledge/gm-programs.md` — General MIDI 音色全表 + 常用编制
- `examples/unsent-letter/` — 旗舰示例（含成曲、MIDI）
- `tests/smoke.py` — 自测
- `SKILL.md` / `README.md` — 技能说明 / 安装
