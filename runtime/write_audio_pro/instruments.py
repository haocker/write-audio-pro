# -*- coding: utf-8 -*-
"""write_audio_pro.instruments — 乐器名 → General MIDI program 映射。

write_audio_pro 用 FluidSynth + SoundFont 渲染，所以"乐器"就是 GM program 号（0-127）。
这里给出常用乐器的友好名 → program 映射，写乐谱时直接写名字即可：

    strings = song.track("strings")      # -> program 48 (String Ensemble 1)
    cello   = song.track("cello")        # -> program 42

完整 GM 表见 knowledge/gm-programs.md。也可以用 song.track(96) 直接给 program 号。
"""

# 名字 → GM program（0 基）。含常见别名。
GM = {
    # ---- 钢琴 / 键盘 ----
    "piano": 0, "grand": 0, "acoustic_grand": 0, "grand_piano": 0,
    "bright_piano": 1, "electric_piano": 4, "epiano": 4, "rhodes": 4,
    "honky_tonk": 3, "harpsichord": 6, "clavinet": 7,
    "celesta": 8, "music_box": 10, "vibraphone": 11, "marimba": 12,
    "xylophone": 13, "tubular_bells": 14, "glockenspiel": 9,
    "organ": 19, "church_organ": 19, "drawbar_organ": 16, "accordion": 21,
    "harmonica": 22,

    # ---- 吉他 / 贝斯 ----
    "nylon_guitar": 24, "classical_guitar": 24, "guitar": 25,
    "steel_guitar": 25, "acoustic_guitar": 24, "jazz_guitar": 26,
    "clean_guitar": 27, "muted_guitar": 28, "overdrive_guitar": 29,
    "distortion_guitar": 30, "guitar_harmonics": 31,
    "bass": 32, "acoustic_bass": 32, "finger_bass": 33, "bass_guitar": 32,
    "pick_bass": 34, "slap_bass": 36, "synth_bass": 38, "synth_bass_1": 38,

    # ---- 弦乐 ----
    "violin": 40, "viola": 41, "cello": 42, "contrabass": 43,
    "tremolo_strings": 44, "pizzicato_strings": 45, "harp": 46,
    "timpani": 47, "strings": 48, "string_ensemble": 48,
    "string_ensemble_1": 48, "strings_slow": 51, "string_ensemble_2": 49,
    "synth_strings": 50, "choir": 52, "choir_aahs": 52, "voice": 52,
    "voices": 52, "voice_oohs": 53,

    # ---- 铜管 ----
    "trumpet": 56, "trombone": 57, "tuba": 58, "muted_trumpet": 59,
    "french_horn": 60, "horn": 60, "brass": 61, "brass_section": 61,
    "synth_brass": 62, "synth_brass_1": 62,

    # ---- 管乐 ----
    "soprano_sax": 64, "alto_sax": 65, "tenor_sax": 66, "baritone_sax": 67,
    "sax": 65, "oboe": 68, "english_horn": 69, "bassoon": 70, "clarinet": 71,
    "piccolo": 72, "flute": 73, "recorder": 74, "pan_flute": 75,
    "blown_bottle": 76, "shakuhachi": 77, "whistle": 78, "ocarina": 79,

    # ---- 合成 / 铺垫 ----
    "lead": 80, "square_lead": 80, "saw_lead": 81, "sawtooth": 81,
    "calliope_lead": 82, "chiff_lead": 83, "charang_lead": 84,
    "voice_lead": 85, "fifths_lead": 86, "bass_lead": 87,
    "pad": 89, "new_age": 88, "warm_pad": 89, "pad_warm": 89,
    "polysynth_pad": 90, "choir_pad": 91, "bowed_pad": 92,
    "metallic_pad": 93, "halo_pad": 94, "sweep_pad": 95,
    "synth_pad": 89, "synth_choir": 91,

    # ---- 效果外 ----
    "glass_harmonica": 12, "bottle_blow": 76, "cello_pizz": 45,
}

# 推荐：不同音乐风格下的常用编制（写乐谱时可直接参考）
ENSEMBLES = {
    "sad_piano":   ["piano", "strings", "cello"],
    "cinematic":   ["piano", "strings", "cello", "choir"],
    "chamber":     ["piano", "violin", "cello", "viola"],
    "orchestral":  ["strings", "brass", "flute", "timpani"],
    "ambient":     ["pad", "piano", "bell", "synth_strings"],
    "lofi":        ["electric_piano", "bass", "vinyl", "vibraphone"],
}


def resolve(name):
    """乐器名或 GM program 号 → (program, canonical_name)。

    接受：'piano' / 'strings' / 0 / 48 / '  Cello  '（大小写与空格不敏感）。
    """
    if isinstance(name, (int, float)) and not isinstance(name, bool):
        p = int(name)
        if not (0 <= p <= 127):
            raise ValueError("GM program 号应在 0-127：%r" % (name,))
        return p, _canonical(p)
    key = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    if key not in GM:
        raise ValueError("未知乐器 %r。可用示例：piano/strings/cello/violin/"
                         "electric_piano/synth_bass/pad/choir/flute ...；"
                         "也可直接给 GM program 号 (0-127)。" % (name,))
    return GM[key], key


def _canonical(program):
    for k, v in GM.items():
        if v == program:
            return k
    return "program_%d" % program
