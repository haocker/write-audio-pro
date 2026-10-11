# -*- coding: utf-8 -*-
"""write_audio_pro 命令行：运行乐谱脚本并用真实采样音源渲染。

    python -m write_audio_pro song.py                       # 按脚本内设定渲染
    python -m write_audio_pro song.py --out x.mp3            # 指定输出
    python -m write_audio_pro song.py --midi x.mid           # 同时导出 MIDI
    python -m write_audio_pro song.py --lufs -14 --bitrate 192
    python -m write_audio_pro song.py --soundfont /path.sf2  # 指定音色库
    python -m write_audio_pro song.py --check                # 只打印乐谱摘要，不渲染

约定：song.py 里定义名为 song 的对象（wa.Song 实例）。
"""
import argparse
import os
import runpy
import sys


def _fmt(v):
    return "-" if v is None else ("%g" % v if isinstance(v, float) else str(v))


def _print_stats(song):
    st = song.stats()
    print("%s bpm / %s 拍每小节 — %s 拍 / %s 小节 / %.1f 秒（+尾 %.1f s）"
          % (_fmt(st["bpm"]), st["beats_per_bar"], _fmt(st["beats"]), _fmt(st["bars"]),
             st["seconds"], st["tail"]))
    print("声部 %d 条：" % len(st["tracks"]))
    for t in st["tracks"]:
        vp = ("  音量包络 %d 点" % t["vol_points"]) if t.get("vol_points") else ""
        print("  %-12s GM%-3d %4d 音符  gain %+g dB  pan %+g%s  拍 [%s .. %s]"
              % (t["name"], t["program"], t["notes"], t["gain_db"], t["pan"], vp,
                 _fmt(t["first"]), _fmt(t["last"])))


def _print_report(rep):
    print("")
    print("lufs=%s  时长=%ss  音色库=%s" % (rep.get("lufs"), rep.get("seconds"),
                                            rep.get("soundfont")))
    # 分轨响度（帮助发现"谁盖过谁"）
    tracks = rep.get("tracks") or []
    leveled = [t for t in tracks if t.get("rms_db") is not None]
    if leveled:
        print("分轨响度（混音后，dB）：")
        for t in sorted(leveled, key=lambda x: x["rms_db"], reverse=True):
            print("  %-12s RMS %6.1f  peak %6.1f" % (t["name"], t["rms_db"], t["peak_db"]))
    for w in rep.get("warnings") or []:
        print("⚠  %s" % w)
    if rep.get("midi"):
        print("midi: %s" % rep["midi"])
    if rep.get("wav"):
        print("wav : %s" % rep["wav"])
    if rep.get("mp3"):
        print("mp3 : %s" % rep["mp3"])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="write_audio_pro",
                                 description="运行乐谱脚本并用真实采样音源渲染成品音乐。")
    ap.add_argument("script", help="乐谱脚本（*.py，里内定义 song = wa.Song(...)）")
    ap.add_argument("--out", default=None, help="输出 mp3/wav 路径")
    ap.add_argument("--wav", default=None, help="额外输出 wav 路径")
    ap.add_argument("--midi", default=None, help="导出 MIDI 路径（供 DAW 二次编曲）")
    ap.add_argument("--soundfont", default="auto", help="SoundFont 路径（默认自动查找）")
    ap.add_argument("--lufs", type=float, default=-14.0, help="响度目标（默认 -14）")
    ap.add_argument("--bitrate", type=int, default=192, help="mp3 码率 kbps")
    ap.add_argument("--reverb", type=float, default=None, help="混响湿声比例 0..1")
    ap.add_argument("--fade-in", type=float, default=None, help="整曲渐入（秒）")
    ap.add_argument("--fade-out", type=float, default=None, help="整曲渐出（秒）")
    ap.add_argument("--keep-wav", action="store_true", help="保留中间 wav")
    ap.add_argument("--check", action="store_true", help="只打印乐谱摘要，不渲染")
    args = ap.parse_args(argv)

    script = os.path.abspath(args.script)
    if not os.path.exists(script):
        print("找不到脚本：%s" % script)
        return 2
    d = os.path.dirname(script)
    if d and d not in sys.path:
        sys.path.insert(0, d)

    g = runpy.run_path(script)
    song = g.get("song")
    if song is None or not hasattr(song, "stats"):
        print("脚本里没有定义有效的 song 对象（应为 wa.Song 实例）")
        return 2

    _print_stats(song)
    if args.check:
        return 0
    if getattr(song, "_rendered", False) and getattr(song, "_report", None) is not None:
        _print_report(song._report)
        return 0
    rep = song.render(out=args.out, wav=args.wav, midi=args.midi,
                      soundfont=args.soundfont, lufs=args.lufs,
                      bitrate=args.bitrate, reverb_mix=args.reverb,
                      fade_in=args.fade_in, fade_out=args.fade_out,
                      keep_wav=args.keep_wav)
    _print_report(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
