# General MIDI 音色表 + 常用编制（write_audio_pro）

write_audio_pro 的"乐器"就是 General MIDI program 号（0-127）。
`song.track("cello")` 或 `song.track(42)` 都行；名字见 `runtime/write_audio_pro/instruments.py` 的 `GM` 字典。

> 中文名仅为参考；程序化写乐谱时用英文 key 或 GM 号。

## 钢琴 / 键盘
| GM | key | 音色 |
|---|---|---|
| 0 | `piano` / `grand` / `acoustic_grand` | 三角钢琴（**最常用**） |
| 1 | `bright_piano` | 明亮钢琴 |
| 3 | `honky_tonk` | 酒吧钢琴 |
| 4 | `electric_piano` / `rhodes` / `epiano` | 电钢琴 |
| 6 | `harpsichord` | 拨弦古钢琴 |
| 7 | `clavinet` | 击弦古钢琴 |
| 8 | `celesta` | 钢片琴 |
| 9 | `glockenspiel` | 钟琴 |
| 10 | `music_box` | 八音盒 |
| 11 | `vibraphone` | 颤音琴 |
| 12 | `marimba` | 马林巴 |
| 13 | `xylophone` | 木琴 |
| 14 | `tubular_bells` | 管钟 |
| 16 | `drawbar_organ` | 拉杆风琴 |
| 19 | `organ` / `church_organ` | 教堂管风琴 |
| 21 | `accordion` | 手风琴 |
| 22 | `harmonica` | 口琴 |

## 吉他 / 贝斯
| GM | key | 音色 |
|---|---|---|
| 24 | `classical_guitar` / `nylon_guitar` | 尼龙弦吉他 |
| 25 | `guitar` / `steel_guitar` | 钢弦吉他 |
| 26 | `jazz_guitar` | 爵士吉他 |
| 27 | `clean_guitar` | 清音电吉他 |
| 30 | `distortion_guitar` | 失真吉他 |
| 32 | `bass` / `acoustic_bass` | 原声贝斯 |
| 33 | `finger_bass` | 指弹贝斯 |
| 36 | `slap_bass` | 击弦贝斯 |
| 38 | `synth_bass` | 合成贝斯 |

## 弦乐（抒情曲主力）
| GM | key | 音色 |
|---|---|---|
| 40 | `violin` | 小提琴 |
| 41 | `viola` | 中提琴 |
| 42 | `cello` | 大提琴（**低音线条**） |
| 43 | `contrabass` | 低音提琴 |
| 44 | `tremolo_strings` | 颤弓弦乐 |
| 45 | `pizzicato_strings` | 拨奏弦乐 |
| 46 | `harp` | 竖琴 |
| 47 | `timpani` | 定音鼓 |
| 48 | `strings` / `string_ensemble` | 弦乐合奏 1（**和声垫**） |
| 49 | `string_ensemble_2` | 弦乐合奏 2 |
| 50 | `synth_strings` | 合成弦乐 |
| 51 | `strings_slow` | 慢弦乐 |
| 52 | `choir` / `choir_aahs` / `voice` | 人声合唱（**高潮叠色**） |
| 53 | `voice_oohs` | 人声 Ooh |

## 铜管 / 管乐
| GM | key | 音色 |
|---|---|---|
| 56 | `trumpet` | 小号 |
| 57 | `trombone` | 长号 |
| 58 | `tuba` | 大号 |
| 60 | `french_horn` / `horn` | 圆号 |
| 61 | `brass` / `brass_section` | 铜管组 |
| 64-67 | `soprano_sax` `alto_sax` `tenor_sax` `baritone_sax` | 萨克斯 |
| 68 | `oboe` | 双簧管 |
| 70 | `bassoon` | 大管 |
| 71 | `clarinet` | 单簧管 |
| 73 | `flute` | 长笛 |
| 74 | `recorder` | 竖笛 |
| 75 | `pan_flute` | 排箫 |
| 77 | `shakuhachi` | 尺八 |
| 78 | `whistle` | 口哨 |
| 79 | `ocarina` | 陶笛 |

## 合成 / 铺垫
| GM | key | 音色 |
|---|---|---|
| 80 | `lead` / `square_lead` | 方波主音 |
| 81 | `saw_lead` | 锯齿主音 |
| 88 | `new_age` | 新世纪 |
| 89 | `pad` / `warm_pad` | 温暖垫（**氛围**） |
| 90 | `polysynth_pad` | 合成垫 |
| 91 | `choir_pad` / `synth_choir` | 人声垫 |
| 92 | `bowed_pad` | 弓弦垫 |
| 94 | `halo_pad` | 光环垫 |

## 常用编制（写在代码里用 `wa.ENSEMBLES`）

```python
wa.ENSEMBLES
# {
#   "sad_piano":  ["piano", "strings", "cello"],
#   "cinematic":  ["piano", "strings", "cello", "choir"],
#   "chamber":    ["piano", "violin", "cello", "viola"],
#   "orchestral": ["strings", "brass", "flute", "timpani"],
#   "ambient":    ["pad", "piano", "bell", "synth_strings"],
#   "lofi":       ["electric_piano", "bass", "vinyl", "vibraphone"],
# }
```

## 音域参考（写旋律时避免超出）

| 乐器 | 常用音域 | 舒适区 |
|---|---|---|
| 钢琴（右手） | A0-C8 | C4-C6 |
| 钢琴（左手） | A0-C8 | A1-C3 |
| 小提琴 | G3-E7 | G4-E6 |
| 大提琴 | C2-A5 | C3-C5 |
| 弦乐合奏 | C2-C7 | C3-C6 |
| 长笛 | C4-C7 | C5-G6 |
| 合唱（混声） | E2-C6 | C3-C5 |

> 写悲伤曲时，主旋律常落在 **C4-C6** 之间的中高音区——既明亮又脆弱；
> 低音交给大提琴 C2-C3，和声垫交给弦乐 C3-C5。
