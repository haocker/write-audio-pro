# -*- coding: utf-8 -*-
"""write_audio_pro.song — 乐谱（显式音符）+ FluidSynth 真实采样音源渲染。

设计分工（核心）：
  - 曲式 / 和弦 / 旋律 / 织体 / 每个音符 → 由你在乐谱脚本里**显式写出**（本模块只存）
  - 音色合成 / 混响 / 母带 / 编码        → 由 FluidSynth + SoundFont + FFmpeg 完成

没有随机预设、没有自动作曲。同一乐谱 → 逐样本可复现。

快速上手：
    import write_audio_pro as wa

    s = wa.Song(bpm=66)                     # A 小调慢板
    piano = s.track("piano")
    strings = s.track("strings", gain_db=-6)
    piano.notes([(0, "A4", 2), (2, "C5", 2)])       # (拍, 音名/MIDI, 时值[拍]|力度)
    strings.chord_at(0, "Am", dur=4)                 # 和弦名直达
    s.length(bars=8)
    s.render("out.mp3", soundfont="auto")           # 真钢琴/弦乐发声
"""
import os
import shutil
import subprocess
import tempfile
import wave

import numpy as np

from . import instruments as inst_mod
from .theory import chord as _chord, parse_note


# ================================================================ SoundFont 发现
_SEARCH_PATHS = [
    # 环境变量优先
    os.environ.get("WRITE_AUDIO_PRO_SF2"),
    # Linux (Debian/Ubuntu 包)
    "/usr/share/sounds/sf3/MuseScore_General_Full.sf3",
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/sounds/sf3/default-GM.sf3",
    "/usr/share/sounds/sf2/default-GM.sf2",
    "/usr/share/sounds/sf2/TimGM6mb.sf2",
    # macOS
    "/opt/homebrew/share/soundfonts/FluidR3_GM.sf2",
    "/usr/local/share/soundfonts/FluidR3_GM.sf2",
    # Windows 常见位置
    r"C:\ProgramData\soundfonts\FluidR3_GM.sf2",
    r"C:\soundfonts\FluidR3_GM.sf2",
]


def find_soundfont():
    """找一个可用的 SoundFont（.sf2/.sf3）。找不到抛异常并给出安装提示。"""
    for p in _SEARCH_PATHS:
        if p and os.path.exists(p):
            return p
    # 兜底：pretty_midi 自带的极小音色库
    try:
        import pretty_midi
        p = os.path.join(os.path.dirname(pretty_midi.__file__), "TimGM6mb.sf2")
        if os.path.exists(p):
            return p
    except Exception:
        pass
    raise RuntimeError(
        "找不到 SoundFont 音色库。请任选其一：\n"
        "  Linux : sudo apt install fluid-soundfont-gm musescore-general-soundfont\n"
        "  macOS : brew install fluid-synth && 下载 FluidR3_GM.sf2\n"
        "  Win   : 下载 FluidR3_GM.sf2 / MuseScore_General.sf3\n"
        "  或用环境变量 WRITE_AUDIO_PRO_SF2=/path/to/xxx.sf2 指定。"
    )


def find_tool(name, env_var=None):
    """在 PATH / 环境变量 / 常见路径里找一个可执行文件。"""
    if env_var and os.environ.get(env_var):
        cand = os.environ[env_var]
        if os.path.exists(cand):
            return cand
    p = shutil.which(name)
    if p:
        return p
    for d in (r"C:\Program Files\fluidsynth\bin", r"C:\tools", "/usr/local/bin",
              "/opt/homebrew/bin", "/usr/bin"):
        cand = os.path.join(d, name + (".exe" if os.name == "nt" else ""))
        if os.path.exists(cand):
            return cand
    return None


# ================================================================ 乐谱对象
class Track:
    """一个声部（一件乐器）。音符按 (起始秒, 音高, 时值秒, 力度) 存储。"""

    def __init__(self, song, program, name, gain_db=0.0, pan=0.0, reverb=0.0):
        self.song = song
        self.program = int(program)
        self.name = name
        self.gain_db = float(gain_db)
        self.pan = float(pan)
        self.reverb = float(reverb)
        self.events = []         # [(start_beat, midi, dur_beat, vel)]
        # 音量包络：[(start_beat, gain_db)]，动画式音量变化（AI 在乐谱里显式写）
        # 缺省为空 → 整轨恒定 = gain_db。
        self._vol_points = None  # 惰性：None 表示未设置任何包络点

    # ---- 音量控制（写谱时由 AI 显式控制）----
    def set_volume(self, at, db):
        """在 at 拍处设定本轨音量（相对 dB，0=原声，负=更轻）。

        可多次调用形成**音量包络**——渲染时在相邻点之间线性（以 dB 计）过渡。
        第一个点之前的时值用第一个点的音量；最后一个点之后保持。

            cello.set_volume(0, -60)      # 从几乎无声开始
            cello.set_volume(8, -6)       # 第 8 拍渐入到 -6dB
            strings.set_volume(0, -14)    # 主歌：静音垫
            strings.set_volume(32, -6)    # 副歌：抬起来，但不抢钢琴
        """
        if self._vol_points is None:
            self._vol_points = []
        self._vol_points.append((float(at), float(db)))
        self._vol_points.sort(key=lambda p: p[0])
        return self

    def volume(self, at, db):
        """set_volume 的简写。"""
        return self.set_volume(at, db)

    def fade_volume(self, at0, db0, at1, db1):
        """便捷：一段音量过渡（两个包络点）。"""
        self.set_volume(at0, db0)
        self.set_volume(at1, db1)
        return self

    def has_volume_envelope(self):
        return bool(self._vol_points)

    def volume_db_at(self, beat):
        """查询某拍处的本轨音量（dB），含线性插值。供渲染与调试用。"""
        pts = self._vol_points
        if not pts:
            return self.gain_db
        if beat <= pts[0][0]:
            return pts[0][1]
        if beat >= pts[-1][0]:
            return pts[-1][1]
        for i in range(len(pts) - 1):
            b0, d0 = pts[i]
            b1, d1 = pts[i + 1]
            if b0 <= beat <= b1:
                if b1 == b0:
                    return d1
                t = (beat - b0) / (b1 - b0)
                return d0 + (d1 - d0) * t
        return pts[-1][1]

    def volume_curve(self, n_samples, sr, total_beats):
        """生成逐样本的线性增益曲线（float32, shape (n,1)）。

        把音量包络（拍→dB）转成每采样点的线性增益，供分轨渲染时乘上去。
        无包络时返回 None（调用方直接用恒定 gain_db）。
        """
        if not self._vol_points:
            return None
        n = int(n_samples)
        if n <= 0:
            return None
        spb = total_beats / n if total_beats > 0 else 0.0
        idx = np.arange(n, dtype=np.float64) * spb           # 每个采样点的拍位置
        # 用 zeros 初始化：未初始化的 empty 若某点未被任何区间覆盖，
        # 会保留内存垃圾值；若垃圾值为大正数，10^(db/20) 溢出为 inf，导致渲染 nan/损坏。
        # 用 0dB（即增益 1.0）兜底，安全且中性。
        db = np.zeros(n, dtype=np.float64)
        pts = self._vol_points
        # 逐段填充（点数通常很少，直接循环）
        first_b, first_d = pts[0]
        db[idx <= first_b] = first_d
        last_b, last_d = pts[-1]
        db[idx >= last_b] = last_d
        for i in range(len(pts) - 1):
            b0, d0 = pts[i]
            b1, d1 = pts[i + 1]
            # 半开区间 [b0, b1)：保证断点恰好落在采样点上时该点必被覆盖
            # （左闭右开即可覆盖所有边界；首/末点在上面已单独用 <= / >= 覆盖）
            m = (idx >= b0) & (idx < b1)
            if not np.any(m):
                continue
            t = (idx[m] - b0) / (b1 - b0) if b1 > b0 else np.ones(np.sum(m))
            db[m] = d0 + (d1 - d0) * t
        gain = np.power(10.0, db / 20.0).astype(np.float32)
        return gain.reshape(-1, 1)

    # ---- 写音符（时值单位一律 = 拍）----
    def note(self, at, pitch, dur=1.0, vel=72):
        """单音。at/dur 单位=拍；vel 0-127（也可 0.0-1.0 表示比例）。"""
        if pitch is None:
            raise ValueError("音高不能为空（写乐谱必须显式给音高，如 'A4' 或 57）")
        m = parse_note(pitch)
        v = self._vel(vel)
        self.events.append((float(at), m, float(dur), v))
        return self

    def notes(self, seq):
        """批量写。每项可为：
           数字             -> 无音高则不合法（write_audio_pro 无打击乐），必须给音高
           (at, pitch)                    dur=1, vel=默认
           (at, pitch, dur)
           (at, pitch, dur, vel)
           {"at":.., "pitch":.., "dur":.., "vel":..}
        """
        for item in seq:
            if isinstance(item, dict):
                self.note(item["at"], item["pitch"], item.get("dur", 1.0), item.get("vel", 72))
            elif isinstance(item, (tuple, list)):
                if len(item) < 2:
                    raise ValueError("音符元组至少 (at, pitch)：%r" % (item,))
                self.note(item[0], item[1],
                          item[2] if len(item) > 2 else 1.0,
                          item[3] if len(item) > 3 else 72)
            else:
                raise ValueError("无法解析的音符项 %r（需 (at,pitch[,dur[,vel]]) 或 dict）" % (item,))
        return self

    def chord_at(self, at, name, dur=4.0, octave=3, vel=64, voicing=None):
        """在小节内 at 拍处落一个和弦（可直接给和弦名 'Am' 'Cmaj7' 'C/E'）。

        voicing: 可选的 MIDI 列表，覆盖默认（用于自定义排列/加低音）。
        """
        pitches = voicing if voicing is not None else _chord(name, octave)
        for p in pitches:
            self.note(at, p, dur, vel)
        return self

    def pad_chord(self, bar, name, dur=4.0, octave=3, vel=52, add_root_octave=True):
        """按小节落一个和弦垫（第 bar 小节头，1 基）。可加低八度根音更饱满。"""
        at = self.song.bar_to_beat(bar, 0.0)
        pitches = _chord(name, octave)
        if add_root_octave:
            pitches = [pitches[0] - 12] + pitches
        for p in pitches:
            self.note(at, p, dur, vel)
        return self

    @staticmethod
    def _vel(v):
        if isinstance(v, float) and 0.0 <= v <= 1.0:
            v = round(v * 127)
        return int(max(1, min(127, v)))

    def sorted_notes(self):
        return sorted(self.events, key=lambda n: (n[0], n[1]))


class Song:
    """一首曲子：若干 Track + 全局速度/拍号/曲长/渐弱。"""

    def __init__(self, bpm=70.0, beats_per_bar=4, tail=2.0):
        self.bpm = float(bpm)
        self.beats_per_bar = int(beats_per_bar)
        self.tail = float(tail)
        self.tracks = []
        self._length_beats = None
        self._fade_in = None
        self._fade_out = None
        self._title = ""
        self._report = None
        self._rendered = False
        # 默认效果（可在 render 里覆盖）
        self.reverb_mix = 0.28        # 混响湿声比例 0..1
        self.tail_seconds = None

    # ---- 结构 ----
    def track(self, instrument, name=None, gain_db=0.0, pan=0.0, reverb=None):
        """加一个声部。instrument 可为乐器名（'piano'/'strings'/'cello'...）或 GM 号。"""
        program, canonical = inst_mod.resolve(instrument)
        if name is None:
            name = canonical
        # 重名自动加后缀
        existing = {t.name for t in self.tracks}
        base, i = name, 2
        while name in existing:
            name = "%s_%d" % (base, i)
            i += 1
        t = Track(self, program, name, gain_db=gain_db, pan=pan,
                  reverb=self.reverb_mix if reverb is None else reverb)
        self.tracks.append(t)
        return t

    def length(self, bars=None, beats=None, seconds=None):
        """显式曲长。渲染输出 = 曲长 + tail。"""
        if bars is not None:
            self._length_beats = float(bars) * self.beats_per_bar
        elif beats is not None:
            self._length_beats = float(beats)
        elif seconds is not None:
            self._length_beats = float(seconds) * self.bpm / 60.0
        else:
            raise ValueError("length 需要 bars= / beats= / seconds= 之一")
        return self

    def fade(self, in_seconds=None, out_seconds=None):
        self._fade_in = in_seconds
        self._fade_out = out_seconds
        return self

    # ---- 音量 / 平衡（写谱时由 AI 显式控制）----
    def set_volume(self, track, at_bar, db, at_beat=0.0):
        """按**小节**设定某轨音量（AI 最常用的写法）。

        track: 声部对象（Track）或声部名（str）。
        at_bar: 小节号（1 基）。db: 相对音量（0=原声，负=更轻）。

            song.set_volume("strings", 1, -14)   # 第 1 小节起：弦乐退到 -14dB
            song.set_volume("strings", 33, -6)   # 第 33 小节起：抬到 -6dB
        """
        t = self._track_ref(track)
        t.set_volume(self.bar_to_beat(at_bar, at_beat), db)
        return self

    def mix(self, **levels):
        """一次性设定多轨基准音量：song.mix(piano=0, strings=-8, cello=-5)。"""
        for name, db in levels.items():
            t = self._track_ref(name)
            t.gain_db = float(db)
        return self

    def balance(self, lead="piano", others_db=-9, lead_db=0):
        """便捷平衡：把 lead 设为主音量，其余声部统一压低到 others_db。"""
        for t in self.tracks:
            t.gain_db = float(lead_db) if t.name == lead else float(others_db)
        return self

    def _track_ref(self, ref):
        if isinstance(ref, Track):
            return ref
        for t in self.tracks:
            if t.name == ref:
                return t
        raise KeyError("没有名为 %r 的声部（现有：%s）"
                       % (ref, ", ".join(t.name for t in self.tracks)))

    # ---- 时间换算 ----
    def bar_to_beat(self, bar, b=0.0):
        """第 bar 小节（1 基）内第 b 拍 → 绝对拍位置。"""
        return (bar - 1) * self.beats_per_bar + b

    def beat_to_sec(self, beats):
        return beats * 60.0 / self.bpm

    @property
    def sec_per_bar(self):
        return self.beats_per_bar * 60.0 / self.bpm

    def total_beats(self):
        """实际内容长度（拍）：max(音符末, length)。"""
        end = 0.0
        for t in self.tracks:
            for (at, _, dur, _) in t.events:
                end = max(end, at + dur)
        if self._length_beats is not None:
            end = max(end, self._length_beats)
        return end

    def duration_sec(self):
        return self.beat_to_sec(self.total_beats())

    # ---- 摘要 ----
    def stats(self):
        st = {"bpm": self.bpm, "beats_per_bar": self.beats_per_bar,
              "beats": round(self.total_beats(), 3),
              "bars": round(self.total_beats() / self.beats_per_bar, 3),
              "seconds": round(self.duration_sec(), 1),
              "tail": self.tail, "tracks": []}
        for t in self.tracks:
            first = min((n[0] for n in t.events), default=None)
            last = max((n[0] + n[2] for n in t.events), default=None)
            st["tracks"].append({
                "name": t.name, "program": t.program, "notes": len(t.events),
                "gain_db": t.gain_db, "pan": t.pan,
                "vol_points": len(t._vol_points) if t._vol_points else 0,
                "first": round(first, 2) if first is not None else None,
                "last": round(last, 2) if last is not None else None,
            })
        return st

    # ============================================================ 导出 MIDI
    def export_midi(self, path):
        """把乐谱写成标准 MIDI 文件（可拖进 DAW / MuseScore 二次编曲）。"""
        import pretty_midi
        pm = pretty_midi.PrettyMIDI(initial_tempo=self.bpm)
        spb = 60.0 / self.bpm
        for t in self.tracks:
            inst = pretty_midi.Instrument(program=t.program, name=t.name)
            for (at, midi, dur, vel) in t.sorted_notes():
                inst.notes.append(pretty_midi.Note(
                    velocity=int(vel), pitch=int(midi),
                    start=self.beat_to_sec(at),
                    end=self.beat_to_sec(at + dur)))
            pm.instruments.append(inst)
        pm.write(path)
        return path

    # ============================================================ 渲染
    def render(self, out="track.mp3", wav=None, midi=None, soundfont="auto",
               lufs=-14.0, ceiling=0.94, bitrate=192, sr=44100,
               reverb_mix=None, reverb_room=0.6, keep_wav=False,
               fade_in=None, fade_out=None, title=None, gain_scale=1.0):
        """渲染成品音乐。

        管线：乐谱 → MIDI → FluidSynth(真实采样音源) → 声像/混响/渐变 →
              两遍法响度归一(-14 LUFS) → 限幅 → MP3/WAV。
        """
        import pretty_midi  # 校验依赖
        fs = find_tool("fluidsynth", "WRITE_AUDIO_PRO_FLUIDSYNTH")
        if fs is None:
            raise RuntimeError("找不到 fluidsynth。请安装：apt install fluidsynth / "
                               "brew install fluid-synth / 或用环境变量 WRITE_AUDIO_PRO_FLUIDSYNTH 指定。")
        ffmpeg = find_tool("ffmpeg", "WRITE_AUDIO_PRO_FFMPEG")

        sf = find_soundfont() if soundfont == "auto" else soundfont
        if not os.path.exists(sf):
            raise RuntimeError("SoundFont 不存在：%s" % sf)

        title = title or self._title or "untitled"
        tmpdir = tempfile.mkdtemp(prefix="write_audio_pro_")
        mid_path = os.path.join(tmpdir, "score.mid")

        # 1) 整曲 MIDI（供导出 / 作为兜底）
        self.export_midi(mid_path)
        if midi:
            os.makedirs(os.path.dirname(os.path.abspath(midi)) or ".", exist_ok=True)
            shutil.copy(mid_path, midi)

        render_tail = max(self.tail, 2.5)
        dur = self.duration_sec() + render_tail
        n_samples = int(dur * sr)
        total_beats = self.total_beats()

        # 2) **逐轨渲染 → 按 gain_db + 音量包络缩放 → 声像 → 累加混音**
        #    这样每件乐器的音量才真正可控（FluidSynth 整曲渲染不认分轨音量）。
        mixbuf = np.zeros((n_samples, 2), dtype=np.float32)
        track_stats = []
        gain = 1.0 * gain_scale

        for t in self.tracks:
            if not t.events:
                track_stats.append({"name": t.name, "program": t.program,
                                    "notes": 0, "peak_db": None, "rms_db": None})
                continue
            buf = self._render_one_track(t, fs, sf, sr, n_samples, tmpdir, gain)
            if buf is None:
                track_stats.append({"name": t.name, "program": t.program,
                                    "notes": len(t.events), "peak_db": None, "rms_db": None})
                continue
            # 2a) 音量：恒定 gain_db 或逐样本音量包络
            curve = t.volume_curve(n_samples, sr, total_beats) if t.has_volume_envelope() else None
            if curve is not None:
                buf *= curve
            else:
                buf *= (10.0 ** (t.gain_db / 20.0))
            # 2b) 每轨混响（按轨的 reverb 比例）
            if t.reverb and t.reverb > 0:
                buf = _apply_reverb(buf, sr, mix=t.reverb, room=reverb_room)
            # 2c) 声像（等功率）
            buf = _apply_pan(buf, t.pan)
            # 记录本轨（缩放后）响度，便于诊断"谁盖过谁"
            pk = float(np.max(np.abs(buf)) + 1e-9)
            rms = float(np.sqrt(np.mean(buf ** 2)) + 1e-9)
            track_stats.append({"name": t.name, "program": t.program,
                                "notes": len(t.events),
                                "peak_db": round(20 * np.log10(pk), 1),
                                "rms_db": round(20 * np.log10(rms), 1)})
            mixbuf += buf

        audio = mixbuf

        # 3) 整曲渐变 → 母带
        fi = self._fade_in if fade_in is None else fade_in
        fo = self._fade_out if fade_out is None else fade_out
        audio = _apply_fades(audio, sr, fi, fo)
        audio, loud = _master(audio, sr, lufs=lufs, ceiling=ceiling, ffmpeg=ffmpeg)

        # 4) 输出
        wav_out = wav
        if wav is None and keep_wav:
            wav_out = os.path.splitext(out)[0] + ".wav"
        if wav_out:
            os.makedirs(os.path.dirname(os.path.abspath(wav_out)) or ".", exist_ok=True)
            _write_wav(wav_out, audio, sr)

        out_path = out
        if out_path:
            os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
            if out_path.lower().endswith(".wav"):
                _write_wav(out_path, audio, sr)
            else:
                if ffmpeg is None:
                    raise RuntimeError("找不到 ffmpeg，无法编码 mp3。请安装或用 .wav 输出。")
                _encode_mp3(ffmpeg, audio, sr, out_path, bitrate)

        self._report = {
            "lufs": loud, "seconds": round(len(audio) / sr, 1),
            "bars": round(self.total_beats() / self.beats_per_bar, 2),
            "mp3": out_path, "wav": wav_out, "midi": midi,
            "soundfont": os.path.basename(sf),
            "tracks": track_stats,
            "warnings": _check_balance(track_stats),
        }
        self._rendered = True
        shutil.rmtree(tmpdir, ignore_errors=True)
        return self._report

    def _render_one_track(self, t, fs, sf, sr, n_samples, tmpdir, gain=1.0):
        """把单个声部渲染成 (n,2) stereo float 数组。"""
        import pretty_midi
        pm = pretty_midi.PrettyMIDI(initial_tempo=self.bpm)
        inst = pretty_midi.Instrument(program=t.program, name=t.name)
        for (at, midi, dur, vel) in t.sorted_notes():
            inst.notes.append(pretty_midi.Note(
                velocity=int(vel), pitch=int(midi),
                start=self.beat_to_sec(at), end=self.beat_to_sec(at + dur)))
        pm.instruments.append(inst)
        mid = os.path.join(tmpdir, "t_%s.mid" % _safe_name(t.name))
        wav = os.path.join(tmpdir, "t_%s.wav" % _safe_name(t.name))
        pm.write(mid)
        cmd = [fs, "-ni", "-g", "%.3f" % gain, "-r", str(sr), "-F", wav, sf, mid]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if not os.path.exists(wav):
            return None
        a = _read_wav(wav)
        if a.shape[0] < n_samples:
            pad = np.zeros((n_samples - a.shape[0], 2), dtype=np.float32)
            a = np.vstack([a, pad])
        return a[:n_samples].astype(np.float32)


# ================================================================ 音频处理
def _safe_name(name):
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(name))[:40] or "track"


def _apply_pan(audio, pan):
    """等功率声像：pan -1(左) .. 0(中) .. 1(右)。audio 形状 (n,2)。"""
    if pan == 0.0:
        return audio
    pan = max(-1.0, min(1.0, float(pan)))
    # 等功率：角度从 0(左) 到 pi/2(右)
    ang = (pan + 1.0) * 0.25 * np.pi
    gl = np.cos(ang)
    gr = np.sin(ang)
    out = audio.copy()
    out[:, 0] *= (gl * 1.4142)
    out[:, 1] *= (gr * 1.4142)
    return out


def _check_balance(track_stats):
    """诊断：若某轨 RMS 明显压过其它轨（差距 > 8dB），给出可能"盖过"的提示。"""
    rms = [(t["name"], t["rms_db"]) for t in track_stats
           if t.get("rms_db") is not None and t.get("notes")]
    if len(rms) < 2:
        return []
    vals = sorted(rms, key=lambda x: x[1], reverse=True)
    loudest_name, loudest = vals[0]
    second = vals[1][1]
    warn = []
    if loudest - second > 8.0:
        warn.append("%s 比次响的声部高 %.1fdB，可能盖过其他乐器；"
                    "建议调低它或调高伴奏（set_volume / mix）"
                    % (loudest_name, loudest - second))
    return warn


def _read_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(n)
    if sw != 2:
        raise RuntimeError("FluidSynth 输出位深异常：%d" % sw)
    a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch == 1:
        a = np.stack([a, a], axis=1)
    else:
        a = a.reshape(-1, ch)[:, :2]
    return a


def _write_wav(path, audio, sr):
    a = np.clip(audio, -1.0, 1.0)
    pcm = (a * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def _encode_mp3(ffmpeg, audio, sr, path, bitrate):
    a = np.clip(audio, -1.0, 1.0)
    pcm = (a * 32767.0).astype("<i2").tobytes()
    cmd = [ffmpeg, "-y", "-v", "error", "-f", "s16le", "-ar", str(sr),
           "-ac", "2", "-i", "-", "-b:a", str(bitrate), path]
    p = subprocess.run(cmd, input=pcm, capture_output=True)
    if p.returncode != 0 or not os.path.exists(path):
        raise RuntimeError("mp3 编码失败：%s" % p.stderr.decode("utf-8", "ignore"))


def _apply_reverb(audio, sr, mix=0.28, room=0.6):
    """用几个衰减的回声抽头模拟厅堂混响（确定性，无需外部 IR）。"""
    if mix <= 0:
        return audio
    taps = [(0.031, 0.55), (0.061, 0.40), (0.093, 0.30),
            (0.137, 0.22), (0.191, 0.15), (0.257, 0.10)]
    wet = np.zeros_like(audio)
    for delay, g in taps:
        d = int(delay * sr * (0.6 + room))
        g = g * room
        if d <= 0 or d >= len(audio):
            continue
        wet[d:] += audio[:-d] * g
    # 湿声再收敛一点，避免糊
    out = audio * (1.0 - mix) + wet * mix * 1.6
    return out


def _apply_fades(audio, sr, fade_in, fade_out):
    n = len(audio)
    out = audio.copy()
    if fade_in:
        k = min(int(fade_in * sr), n)
        env = np.linspace(0.0, 1.0, k, dtype=np.float32).reshape(-1, 1)
        out[:k] *= env
    if fade_out:
        k = min(int(fade_out * sr), n)
        env = np.linspace(1.0, 0.0, k, dtype=np.float32).reshape(-1, 1)
        out[n - k:] *= env
    return out


def _master(audio, sr, lufs=-14.0, ceiling=0.94, ffmpeg=None):
    """两遍法：测响度 → 增益 → 软限幅 → 复测。返回 (audio, 实测 lufs)。

    ceiling 同时约束"软限幅拐点"与"真峰值上限"，确保输出不削波。
    限幅会让响度回落，所以再做一轮"测量→补偿"，逼近目标。
    """
    audio = audio.astype(np.float32, copy=True)
    # 预归一：把峰值带到接近拐点，避免稀疏乐段需要极大增益（FluidSynth 输出常常很轻）
    peak0 = float(np.max(np.abs(audio)) + 1e-9)
    if peak0 > 0:
        audio = audio * min(ceiling / peak0, 64.0)
    # 朝目标增益，但**保护动态**：最多只把整体 RMS 抬到不再需要大动作；
    # 稀疏/长静音的抒情曲其自然 LUFS 本就低于密集混音，强行压到 -14 会毁掉情绪。
    for _ in range(3):
        measured = _measure_lufs(audio, sr, ffmpeg)
        if measured is None or measured <= -70:
            break
        gain = 10.0 ** ((lufs - measured) / 20.0)
        gain = max(0.5, min(6.0, gain))
        if abs(20.0 * np.log10(gain)) < 0.5:      # 已接近目标，停
            break
        audio = audio * gain
        # 线性压到限幅器拐点，再软限幅（tanh）
        peak_now = float(np.max(np.abs(audio)) + 1e-9)
        if peak_now > ceiling:
            audio = audio * (ceiling / peak_now)
        knee = ceiling * 0.98
        over = np.abs(audio) > knee
        if np.any(over):
            x = audio[over]
            audio[over] = np.sign(x) * (knee + (ceiling - knee) * np.tanh((np.abs(x) - knee)
                                                                         / (ceiling - knee)))
    # 硬保险（严格不超过 ceiling）
    peak2 = float(np.max(np.abs(audio)))
    if peak2 > ceiling:
        audio = audio * (ceiling / peak2)
    final = _measure_lufs(audio, sr, ffmpeg)
    return audio, (round(final, 1) if final is not None else None)


def _measure_lufs(audio, sr, ffmpeg):
    """用 ffmpeg loudnorm 测整体响度；失败则回退 RMS 近似。"""
    if ffmpeg:
        try:
            pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
            cmd = [ffmpeg, "-hide_banner", "-f", "s16le", "-ar", str(sr), "-ac", "2",
                   "-i", "-", "-af", "loudnorm=print_format=json", "-f", "null", "-"]
            p = subprocess.run(cmd, input=pcm, capture_output=True)
            txt = p.stderr.decode("utf-8", "ignore")
            i = txt.rfind('"input_i"')
            if i >= 0:
                seg = txt[i:i + 40]
                val = seg.split(":")[1].strip().strip(',"')
                return float(val)
        except Exception:
            pass
    rms = float(np.sqrt(np.mean(audio ** 2)) + 1e-9)
    return 20 * np.log10(rms) - 3.0   # 粗略近似
