# -*- coding: utf-8 -*-
"""《未寄出的信》— write_audio_pro 旗舰示例。

A 小调 / 63 BPM 慢板 —— 一段悲伤的音乐。
用真实采样音源（真钢琴 + 弦乐 + 大提琴 + 合唱）发声。

编制：piano（主奏）/ strings（和声垫）/ cello（低音）/ choir（高潮叠色）
结构：独白 8 → 倾诉 12 → 翻涌 12 → 释放 8 → 归寂 8 = 48 小节 ≈ 3 分钟

运行：
    python make.py                                   # 渲染到 out/unsent-letter.mp3
    python -m write_audio_pro make.py --check             # 只看乐谱摘要
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "runtime"))

import write_audio_pro as wa

# ================================================================ 总设定
BPM = 63.0
BARS = 48

song = wa.Song(bpm=BPM, beats_per_bar=4, tail=2.5)

# 悲伤和声进行：Am - F - C - G - Am - F - Dm - E（末用 E 大调制造渴望感）
PROG = ["Am", "F", "C", "G", "Am", "F", "Dm", "E"]
ROOT_MIDI = {"Am": 45, "F": 41, "C": 48, "G": 43, "Dm": 38, "E": 40}


def chord_of(bar):
    return PROG[(bar - 1) % len(PROG)]


# ================================================================ 声部
piano = song.track("piano", gain_db=0)
strings = song.track("strings", gain_db=-6.5, pan=-0.15)
cello = song.track("cello", gain_db=-5.5)
choir = song.track("choir", gain_db=-11.0, pan=0.2)

B = song.bar_to_beat


def strings_pad(bar, octv=0, dur=4.0, vel=52):
    ch = wa.chord(chord_of(bar), 3)
    for p in ch:
        strings.note(B(bar, 0), p + 12 * octv, dur, vel)


def cello_note(bar, midi, dur=3.8, vel=58):
    cello.note(B(bar, 0), midi, dur, vel)


def play(bar0, mdict, vel=74):
    """把 {小节偏移: [(拍, 音名, 时值), ...]} 铺进钢琴声部。"""
    for k, notes in mdict.items():
        for (b, pitch, dur) in notes:
            piano.note(B(bar0 + k, b), pitch, dur, vel)


# ================================================================ 旋律素材
INTRO = {  # 独白
    0: [(0.0, "E4", 2.0), (2.5, "A4", 1.5)],
    1: [(0.0, "C5", 3.5)],
    2: [(1.0, "B4", 2.5)],
    3: [(2.0, "G4", 2.0)],
    4: [(0.0, "A4", 3.5)],
    5: [(1.5, "F4", 2.5)],
    6: [(0.0, "E4", 2.0), (2.5, "D4", 1.5)],
    7: [(0.0, "E4", 3.5)],
}

THEME = {  # 主歌主题：级进为主，长音落在和弦音
    0: [(0.0, "A4", 1.5), (1.5, "B4", 0.5), (2.0, "C5", 2.0)],
    1: [(0.0, "C5", 1.5), (1.5, "A4", 2.5)],
    2: [(0.0, "G4", 1.5), (1.5, "A4", 1.0), (2.5, "C5", 1.5)],
    3: [(0.0, "B4", 3.5)],
    4: [(0.0, "A4", 1.5), (1.5, "C5", 0.5), (2.0, "E5", 2.0)],
    5: [(0.0, "D5", 1.5), (1.5, "C5", 2.5)],
    6: [(0.0, "B4", 1.5), (1.5, "A4", 1.0), (2.5, "F4", 1.5)],
    7: [(0.0, "E4", 3.5)],
}

BTHEME = {  # 情绪上涌：移高八度、加流动
    0: [(0.0, "E5", 1.0), (1.0, "C5", 1.0), (2.0, "A4", 2.0)],
    1: [(0.0, "F5", 1.5), (1.5, "E5", 0.5), (2.0, "C5", 2.0)],
    2: [(0.0, "E5", 1.5), (1.5, "D5", 1.0), (2.5, "B4", 1.5)],
    3: [(0.0, "G4", 3.5)],
    4: [(0.0, "C5", 1.5), (1.5, "E5", 0.5), (2.0, "A5", 2.0)],
    5: [(0.0, "G5", 1.5), (1.5, "E5", 2.5)],
    6: [(0.0, "F5", 1.5), (1.5, "E5", 1.0), (2.5, "D5", 1.5)],
    7: [(0.0, "B4", 1.5), (1.5, "E5", 2.0)],
}

CLIMAX = {  # 全情释放
    0: [(0.0, "A5", 2.0), (2.0, "G5", 2.0)],
    1: [(0.0, "F5", 1.5), (1.5, "E5", 2.5)],
    2: [(0.0, "E5", 1.5), (1.5, "D5", 0.5), (2.0, "C5", 2.0)],
    3: [(0.0, "B4", 4.0)],
    4: [(0.0, "C6", 2.0), (2.0, "A5", 2.0)],
    5: [(0.0, "G5", 1.5), (1.5, "E5", 2.5)],
    6: [(0.0, "F5", 1.5), (1.5, "E5", 0.5), (2.0, "D5", 2.0)],
    7: [(0.0, "E5", 4.0)],
}

OUTRO = {  # 归寂
    0: [(0.0, "E5", 2.0), (2.0, "C5", 2.0)],
    1: [(0.0, "A4", 2.0), (2.0, "B4", 2.0)],
    2: [(0.0, "C5", 3.0), (3.0, "B4", 1.0)],
    3: [(0.0, "A4", 4.0)],
    4: [(0.0, "E4", 2.0), (2.0, "A4", 2.0)],
    5: [(0.0, "C5", 2.0), (2.0, "B4", 2.0)],
    6: [(0.0, "A4", 3.0), (3.0, "G4", 1.0)],
    7: [(0.0, "A4", 4.0)],
}

# ================================================================ 编配
# 独白 1-8：钢琴独白 + 极轻弦乐
for n in range(1, 9):
    strings_pad(n, octv=-1, vel=30)
play(1, INTRO, vel=66)

# 倾诉 9-20：主题浮出 + 大提琴 + 左手分解和弦
for n in range(9, 21):
    strings_pad(n, octv=0, vel=46)
    cello_note(n, ROOT_MIDI[chord_of(n)] - 12)
    root = ROOT_MIDI[chord_of(n)] - 12
    piano.note(B(n, 0.0), root, 2.0, 58)
    piano.note(B(n, 2.0), root + 7, 2.0, 52)
play(9, THEME, vel=76)

# 翻涌 21-32：情绪上涌，弦乐抬高，左手八分流动
for n in range(21, 33):
    strings_pad(n, octv=0, vel=58)
    cello_note(n, ROOT_MIDI[chord_of(n)] - 12, vel=60)
    root = ROOT_MIDI[chord_of(n)] - 12
    for i, p in enumerate([root, root + 12, root + 7, root + 12]):
        piano.note(B(n, i), p, 1.0, 56 + (4 if i % 2 else 0))
play(21, BTHEME, vel=84)

# 释放 33-40：全编制 + 合唱叠色 + 宽广琶音
for n in range(33, 41):
    strings_pad(n, octv=1, vel=74)
    cello_note(n, ROOT_MIDI[chord_of(n)] - 12, vel=68)
    if n >= 37:
        for p in wa.chord(chord_of(n), 3):
            choir.note(B(n, 0.0), p + 24, 4.0, 34)
    root = ROOT_MIDI[chord_of(n)] - 12
    ch = wa.chord(chord_of(n), 3)
    seq = [root, root + 7, root + 12, ch[2] + 12, root + 12, root + 7]
    for i, p in enumerate(seq):
        piano.note(B(n, i * (4.0 / len(seq))), p, 0.9, 60)
play(33, CLIMAX, vel=92)

# 归寂 41-48：层层退出 → 最后落定单音
for n in range(41, 45):
    strings_pad(n, octv=0, vel=44)
    cello_note(n, ROOT_MIDI[chord_of(n)] - 12, vel=50)
for n in range(45, 49):
    strings_pad(n, octv=-1, vel=28)
play(41, OUTRO, vel=70)
piano.note(B(48, 0.0), "A4", 4.0, 58)
piano.note(B(48, 0.0), "A2", 4.0, 48)

# ================================================================ 音量控制（AI 显式编配）
# 关键：抒情曲最怕"伴奏盖过人声/主奏"。这里用基准音量 + 段落音量包络，
# 让弦乐/大提琴在不同段落"让位"或"托起"，钢琴始终是主角。

# 1) 基准音量（整曲不动时的相对电平）—— 钢琴为主，其余压低给主奏留空间
song.mix(piano=0, strings=-7, cello=-5, choir=-11)

# 2) 段落音量包络（跟随情绪，把伴奏音量写成曲线）
#    独白 → 倾诉：弦乐从极轻缓缓浮出；到翻涌再抬；释放最大；归寂再退。
song.set_volume("strings", 1, -20)      # 独白起：弦乐几乎只是气声
song.set_volume("strings", 9, -13)      # 倾诉：浮出一点
song.set_volume("strings", 21, -8)      # 翻涌：抬起来托住情绪
song.set_volume("strings", 33, -5)      # 释放：最饱满
song.set_volume("strings", 41, -9)      # 归寂：退回去
song.set_volume("strings", 45, -16)     # 尾声：几乎消失

#    大提琴：主歌到高潮逐渐增强，高潮后先撤（避免和钢琴低音打架）
song.set_volume("cello", 9, -9)
song.set_volume("cello", 21, -6)
song.set_volume("cello", 33, -4)
song.set_volume("cello", 41, -8)
song.set_volume("cello", 45, -60)       # 尾声大提琴完全退场（"-60dB" 视作静音）

#    合唱：只在释放段出现，先淡入再收
choir.set_volume(B(37, 0.0), -30)
choir.set_volume(B(38, 0.0), -13)
choir.set_volume(B(40, 0.0), -60)

#    钢琴：独白最轻，逐段推到高潮，归寂回落（与力度配合做出整体表情）
song.set_volume("piano", 1, -6)
song.set_volume("piano", 9, -2)
song.set_volume("piano", 33, 0)
song.set_volume("piano", 45, -5)

# ================================================================ 渲染
song.length(bars=BARS)
song.fade(out_seconds=5.0, in_seconds=1.5)

if __name__ == "__main__":
    out_dir = os.path.join(HERE, "out")
    rep = song.render(out=os.path.join(out_dir, "unsent-letter.mp3"),
                      midi=os.path.join(out_dir, "unsent-letter.mid"),
                      reverb_mix=0.30, reverb_room=0.62,
                      title="未寄出的信 (Unsent Letter)")
    print("lufs=%s seconds=%s bars=%s sf=%s" %
          (rep["lufs"], rep["seconds"], rep["bars"], rep["soundfont"]))
    for t in rep["tracks"]:
        print("  %-10s GM%-3d %4d notes" % (t["name"], t["program"], t["notes"]))
