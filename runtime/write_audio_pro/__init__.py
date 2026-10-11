# -*- coding: utf-8 -*-
"""write_audio_pro — 用代码写乐谱，用真实采样音源渲染成品音乐。

分工：
  曲式 / 和弦 / 旋律 / 织体 / 每个音符 → 你在乐谱脚本里显式写出（本库只存）
  音色合成 / 混响 / 母带 / 编码        → FluidSynth + SoundFont + FFmpeg

没有随机预设、没有自动作曲；同一乐谱 → 逐样本可复现。

快速上手：
    import write_audio_pro as wa

    s = wa.Song(bpm=66)
    piano = s.track("piano")
    strings = s.track("strings", gain_db=-6)
    piano.notes([(0, "A4", 2), (2, "C5", 2)])
    strings.pad_chord(1, "Am", dur=4)
    s.length(bars=8)
    s.render("out.mp3")

乐理工具：
    wa.midi("A3") -> 57      wa.freq("A3") -> 220.0
    wa.chord("Am7", 3)       wa.scale("A", "minor", 3)

命令行：
    python -m write_audio_pro <song.py> [--out x.mp3] [--midi x.mid] [--check]
"""
from . import instruments, theory
from .instruments import GM, ENSEMBLES, resolve as resolve_instrument
from .song import Song, Track, find_soundfont, find_tool
from .theory import (SCALES, chord, chord_freqs, freq, midi_to_freq, note_name,
                     parse_note, resolve_scale, scale)

midi = parse_note

__version__ = "1.0.0"
__all__ = ["Song", "Track", "midi", "freq", "midi_to_freq", "parse_note",
           "note_name", "chord", "chord_freqs", "scale", "resolve_scale", "SCALES",
           "GM", "ENSEMBLES", "resolve_instrument",
           "find_soundfont", "find_tool",
           "instruments", "theory"]
