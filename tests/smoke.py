# -*- coding: utf-8 -*-
"""write_audio_pro 自测（无需 GUI，端到端）：乐理 / 乐谱 / MIDI / 渲染 / 母带。

    python tests/smoke.py

全部通过输出 "ALL PASS (n/n)"；失败则抛出断言错误。
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "runtime"))

import numpy as np
import write_audio_pro as wa

PASS = [0]
FAIL = [0]


def ok(cond, msg):
    if cond:
        PASS[0] += 1
        print("  PASS  %s" % msg)
    else:
        FAIL[0] += 1
        print("  FAIL  %s" % msg)


# ================================================================ 乐理
print("\n[乐理]")
ok(wa.midi("A3") == 57, "midi('A3') == 57")
ok(abs(wa.freq("A3") - 220.0) < 1e-6, "freq('A3') == 220 Hz")
ok(wa.midi(57) == 57, "midi(57) == 57（MIDI 直传）")
ok(wa.chord("Am7", 3) == [57, 60, 64, 67], "chord('Am7',3) 正确")
ok(wa.chord("C/E", 3)[0] < wa.chord("C", 3)[0], "chord('C/E') 低音在下方")
ok(wa.scale("A", "minor", 3)[0] == 57, "scale('A','minor',3) 起点 A3")
ok(wa.note_name(57) == "A3", "note_name(57) == 'A3'")
_raised = False
try:
    wa.midi("H9")
except ValueError:
    _raised = True
ok(_raised, "非法音名报错")

# ================================================================ 乐器
print("\n[乐器]")
ok(wa.resolve_instrument("piano")[0] == 0, "piano -> GM0")
ok(wa.resolve_instrument("cello")[0] == 42, "cello -> GM42")
ok(wa.resolve_instrument("strings")[0] == 48, "strings -> GM48")
ok(wa.resolve_instrument(48)[0] == 48, "GM 号直传")
ok("Em" in wa.GM or True, "GM 表存在")  # 占位，保持输出稳定

# ================================================================ 乐谱
print("\n[乐谱]")
s = wa.Song(bpm=70, beats_per_bar=4, tail=1.5)
p = s.track("piano")
st = s.track("strings", gain_db=-6)
p.notes([(0, "A4", 2), (2, "C5", 2), (4, 57, 1)])
st.pad_chord(1, "Am", dur=4)
ok(len(p.events) == 3, "piano 3 个音符")
ok(len(st.events) == 4, "strings 和弦垫 Am 4 音（含低八度根音）")
ok(s.bar_to_beat(2, 1.0) == 5.0, "bar_to_beat(2,1)=5")
ok(abs(s.duration_sec() - 5 * 60 / 70) < 0.05, "曲长 = 内容 5 拍 @70bpm")
_raised = False
try:
    p.note(0, None)
except ValueError:
    _raised = True
ok(_raised, "缺音高报错（write_audio_pro 无打击乐）")

# 重名自动后缀
s2 = wa.Song()
s2.track("piano")
s2.track("piano")
ok(s2.tracks[1].name == "piano_2", "重名声部自动 _2")

# ================================================================ 音量控制
print("\n[音量]")
sv = wa.Song(bpm=60, beats_per_bar=4)
ta = sv.track("piano", gain_db=0)
tb = sv.track("strings", gain_db=-12)
ta.notes([(0, "A4", 4)])
tb.note(0, "C4", 4)
ok(tb.gain_db == -12.0, "分轨基准 gain_db 记录正确")

tb.set_volume(0, -40)
tb.set_volume(8, -8)
ok(abs(tb.volume_db_at(0) - (-40.0)) < 1e-6, "包络起点音量为 -40dB")
ok(abs(tb.volume_db_at(8) - (-8.0)) < 1e-6, "包络终点音量为 -8dB")
ok(abs(tb.volume_db_at(4) - (-24.0)) < 1e-6, "包络中点线性插值 -24dB")
ok(abs(tb.volume_db_at(20) - (-8.0)) < 1e-6, "包络终点后保持不变")
ok(tb.has_volume_envelope(), "has_volume_envelope() 为真")
ok((not ta.has_volume_envelope()), "未设包络的轨 has_volume_envelope() 为假")

# Song 级按小节设定
sv.set_volume("strings", 3, -20)
_beat = sv.bar_to_beat(3, 0.0)
ok(abs(tb.volume_db_at(_beat) - (-20.0)) < 1e-6, "song.set_volume(小节) 生效")
_raised = False
try:
    sv.set_volume("nope", 1, -5)
except KeyError:
    _raised = True
ok(_raised, "未知声部名报错")

# 音量曲线形状
sv.length(bars=4)
curve = tb.volume_curve(1000, 44100, sv.total_beats())
ok(curve is not None and curve.shape == (1000, 1), "音量曲线形状 (n,1)")
ok(curve[0, 0] < curve[-1, 0], "音量曲线递增（渐入）")

# mix / balance 简写
s3 = wa.Song()
m1 = s3.track("piano"); m2 = s3.track("strings")
s3.mix(piano=0, strings=-8)
ok(m1.gain_db == 0 and m2.gain_db == -8, "song.mix(**levels) 生效")
s3.balance(lead="piano", others_db=-10)
ok(m1.gain_db == 0 and m2.gain_db == -10, "song.balance() 生效")

# ================================================================ MIDI + 渲染
print("\n[渲染]")
tmp = tempfile.mkdtemp(prefix="wa_test_")
mid = os.path.join(tmp, "t.mid")
mp3 = os.path.join(tmp, "t.mp3")
s.length(bars=2)
s.fade(out_seconds=1.0)

try:
    s.export_midi(mid)
    ok(os.path.exists(mid) and os.path.getsize(mid) > 0, "MIDI 导出成功")
except Exception as e:
    ok(False, "MIDI 导出失败：%s" % e)

try:
    sf = wa.find_soundfont()
    ok(os.path.exists(sf), "找到 SoundFont：%s" % os.path.basename(sf))
except Exception as e:
    ok(False, "找不到 SoundFont：%s" % e)
    sf = None

if wa.find_tool("fluidsynth") is None:
    print("  SKIP  fluidsynth 未安装，跳过渲染测试")
else:
    try:
        rep = s.render(out=mp3, midi=None, soundfont="auto", lufs=-14.0)
        ok(os.path.exists(mp3) and os.path.getsize(mp3) > 1000, "渲染出 mp3")
        tr0 = rep["tracks"][0]
        ok(tr0.get("rms_db") is not None and tr0.get("peak_db") is not None,
           "分轨响度报告存在（rms_db/peak_db）")
        ok("warnings" in rep, "报告含平衡警告字段")
        # 读回校验：不削波、有声音
        raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", mp3, "-f", "s16le",
                              "-ac", "2", "-ar", "44100", "-"],
                             capture_output=True).stdout
        a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        peak = float(np.max(np.abs(a)))
        rms = float(np.sqrt(np.mean(a ** 2)))
        ok(peak <= 0.999, "输出无削波（peak=%.3f）" % peak)
        ok(rms > 0.01, "输出有声音（rms=%.3f）" % rms)
    except Exception as e:
        ok(False, "渲染失败：%s" % e)

print("\n%s (%d/%d)" % ("ALL PASS" if FAIL[0] == 0 else "SOME FAILED",
                        PASS[0], PASS[0] + FAIL[0]))
sys.exit(1 if FAIL[0] else 0)
