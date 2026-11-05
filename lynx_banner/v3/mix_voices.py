import subprocess, wave, sys
import numpy as np
from pathlib import Path
from piper import PiperVoice

OUT = Path("/root/projects/ads/lynx_banner/out3")
VOICES = ["denis", "dmitri", "ruslan", "irina"]
SCRIPTS = {
    "s1": ("Всё тормозит? Включай рысь.", "Линкс, ВПН.", "Бот в профиле."),
    "s2": ("Быстрый интернет. Без лишних слов.", "Линкс, ВПН.", "Ищи бота в профиле."),
    "s3": ("Хватит терпеть тормоза и блоки.", "Линкс, ВПН.", "Бот в профиле, заходи."),
}
# (start, latest end) windows matching the animation
WIN = [(0.55, 2.85), (3.15, 4.6), (4.65, 6.1)]
SR = 44100


def read(p):
    with wave.open(str(p)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768


def synth(vname, text, tag):
    raw, fx = OUT / f"raw_{tag}.wav", OUT / f"fx_{tag}.wav"
    v = PiperVoice.load(f"/tmp/voices/ru_RU-{vname}-medium.onnx")
    with wave.open(str(raw), "wb") as w:
        v.synthesize_wav(text, w)
    return raw


sfx = read(OUT / "sfx.wav").reshape(-1, 2)
n = sfx.shape[0]
for vname in VOICES:
    voice = PiperVoice.load(f"/tmp/voices/ru_RU-{vname}-medium.onnx")
    for sk, lines in SCRIPTS.items():
        mix = sfx.copy()
        for li, (text, (t0, tmax)) in enumerate(zip(lines, WIN)):
            raw = OUT / "tmp_raw.wav"
            with wave.open(str(raw), "wb") as w:
                voice.synthesize_wav(text, w)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-ar", str(SR), "-ac", "1",
                            "-af", "highpass=f=70,silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                            str(OUT / "tmp_t.wav")], check=True)
            dur0 = len(read(OUT / "tmp_t.wav")) / SR
            tempo = min(1.3, max(1.0, (dur0 + 0.05) / (tmax - t0)))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / "tmp_t.wav"),
                            "-af", f"atempo={tempo:.3f}", str(OUT / "tmp_v.wav")], check=True)
            v = read(OUT / "tmp_v.wav"); v = v / np.abs(v).max() * 0.85
            i0 = int(t0 * SR); e = min(n, i0 + len(v))
            mix[i0:e, 0] += v[: e - i0]; mix[i0:e, 1] += v[: e - i0]
            print(vname, sk, li, f"{len(v)/SR:.2f}s tempo={tempo:.2f}", flush=True)
        mix = np.clip(mix, -0.98, 0.98)
        wav = OUT / f"mix_{sk}_{vname}.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((mix * 32767).astype("<i2").tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / f"{sk}_video.mp4"), "-i", str(wav),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                        str(OUT / f"{sk[1]}_{vname}.mp4")], check=True)
