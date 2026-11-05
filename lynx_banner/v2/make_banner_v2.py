"""LynxVPN banner: 1080x540, 25 fps, 6.5 s, RGBA (qtrle) + stereo 44.1k audio."""
import math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

LOGO_SRC = "/root/.claude/uploads/0e539152-892d-51c9-b030-355c97adf9f1/8f3a999a-image.jpg"
OUT = Path("/root/projects/ads/lynx_banner/out2")
OUT.mkdir(parents=True, exist_ok=True)
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

W, H, FPS, DUR = 1032, 312, 25, 6.5
NF = 163
CW, CH, CR = 960, 240, 46          # card size, radius
CX0, CY0 = (W - CW) // 2, (H - CH) // 2
BG = (11, 8, 18)
PURPLE = (155, 77, 255)
LILAC = (196, 160, 255)


def ease_out_back(x):
    x = min(max(x, 0), 1); c1, c3 = 1.4, 2.4
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    x = min(max(x, 0), 1); return 1 - (1 - x) ** 3


def seg(t, a, b):
    return min(max((t - a) / (b - a), 0), 1)


def rr_mask(w, h, r, ss=4):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


# ---------- static layers ----------
card_mask = rr_mask(CW, CH, CR)
card = Image.new("RGBA", (CW, CH), BG + (255,))
# soft purple gradient inside the card (left glow behind the logo)
grad = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
gd = ImageDraw.Draw(grad)
gd.ellipse((-120, -60, 420, CH + 60), fill=PURPLE + (70,))
grad = grad.filter(ImageFilter.GaussianBlur(60))
card = Image.alpha_composite(card, grad)
# border
inner = Image.new("L", (CW, CH), 0)
inner.paste(rr_mask(CW - 6, CH - 6, CR - 3), (3, 3))
border = ImageChops.subtract(card_mask, inner)
border_img = Image.new("RGBA", (CW, CH), PURPLE + (255,))
border_img.putalpha(border)
card = Image.alpha_composite(card, border_img)
card.putalpha(card_mask)

# glow behind card
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gl = Image.new("L", (W, H), 0)
gl.paste(card_mask, (CX0, CY0))
gl = gl.filter(ImageFilter.GaussianBlur(16))
glow = Image.new("RGBA", (W, H), PURPLE + (0,))
glow.putalpha(gl.point(lambda v: int(v * 0.55)))

# logo (crop head, drop the baked-in "LYNXVPN" caption), black -> transparent
logo = Image.open(LOGO_SRC).convert("RGB").crop((60, 40, 600, 540))
lum = logo.convert("L").point(lambda v: 0 if v < 14 else min(255, (v - 14) * 4))
logo = logo.convert("RGBA"); logo.putalpha(lum)
LH = 200
logo = logo.resize((int(logo.width * LH / logo.height), LH), Image.LANCZOS)
LX, LY = CX0 + 52, CY0 + (CH - LH) // 2

f_title = ImageFont.truetype(BOLD, 84)
f_handle = ImageFont.truetype(BOLD, 38)
f_small = ImageFont.truetype(REG, 30)
TX = CX0 + 52 + logo.width + 36
MAXW = CX0 + CW - 40 - TX


def fit_font(txt, size):
    while True:
        f = ImageFont.truetype(BOLD, size)
        if ImageDraw.Draw(Image.new("L", (1, 1))).textlength(txt, font=f) <= MAXW or size < 40:
            return f
        size -= 2


def title_layer(txt):
    t = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(t).text((TX, CY0 + 22), txt, font=fit_font(txt, 84), fill=(255, 255, 255, 255))
    return t


def pill_layer(txt, small=None):
    p = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(p)
    tw = d.textlength(txt, font=f_handle)
    px, py, ph = TX, CY0 + 140, 62
    pw = int(tw + 48)
    fill = Image.new("RGBA", (pw, ph), PURPLE + (255,))
    fill.putalpha(rr_mask(pw, ph, ph // 2))
    p.alpha_composite(fill, (px, py))
    d.text((px + 24, py + ph // 2), txt, font=f_handle, fill=(255, 255, 255, 255), anchor="lm")
    sm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if small:
        ImageDraw.Draw(sm).text((px + pw + 22, py + ph // 2), small, font=f_small, fill=LILAC + (255,), anchor="lm")
    return p, sm


title1 = title_layer("Блокировки")
pill1, _ = pill_layer("идут лесом")
title2 = title_layer("LynxVPN")
pill2, small2 = pill_layer("@LynxVPSbot", "бот в профиле")
logo_glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
lg = Image.new("RGBA", (W, H), (0, 0, 0, 0)); lg.alpha_composite(logo, (LX, LY))
lg_a = lg.split()[3].filter(ImageFilter.GaussianBlur(14))
logo_glow = Image.new("RGBA", (W, H), PURPLE + (0,)); logo_glow.putalpha(lg_a.point(lambda v: int(v * 0.8)))


def shift(img, dx, dy, alpha):
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (int(round(dx)), int(round(dy))))
    if alpha < 1:
        out.putalpha(out.split()[3].point(lambda v: int(v * alpha)))
    return out


def shine(t):
    """diagonal light band sweeping across the card at ~1.3 s and ~4.2 s"""
    best = 0
    for t0 in (3.35,):
        best = max(best, seg(t, t0, t0 + 0.9) if t0 <= t <= t0 + 0.9 else 0)
    if best <= 0:
        return None
    x = -200 + best * (CW + 400)
    band = Image.new("L", (CW, CH), 0)
    d = ImageDraw.Draw(band)
    d.polygon([(x, 0), (x + 90, 0), (x + 40, CH), (x - 50, CH)], fill=70)
    band = band.filter(ImageFilter.GaussianBlur(14))
    band = ImageChops.multiply(band, card_mask)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    b = Image.new("RGBA", (CW, CH), (255, 255, 255, 0)); b.putalpha(band)
    lay.alpha_composite(b, (CX0, CY0))
    return lay


def frame(i):
    t = i / FPS
    pop = ease_out_back(seg(t, 0.0, 0.5))
    a_in = seg(t, 0.0, 0.3)
    out_p = seg(t, DUR - 0.45, DUR)
    a_global = a_in * (1 - out_p)
    scale = (0.82 + 0.18 * pop) * (1 - 0.04 * ease_out(out_p))
    pulse = 0.75 + 0.25 * math.sin(t * 2 * math.pi / 1.6)

    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c.alpha_composite(shift(glow, 0, 0, pulse))
    c.alpha_composite(card, (CX0, CY0))
    la = ease_out(seg(t, 0.35, 0.85))
    c.alpha_composite(shift(logo_glow, 0, 0, la * pulse))
    c.alpha_composite(shift(Image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)),
                            lg), 0, (1 - la) * 14, la))
    # phase 1: "Блокировки / идут лесом"; phase 2: "LynxVPN / @LynxVPSbot"
    out1 = ease_out(seg(t, 2.85, 3.2))
    ta = ease_out(seg(t, 0.45, 0.95)) * (1 - out1)
    c.alpha_composite(shift(title1, (1 - ease_out(seg(t, 0.45, 0.95))) * 40 - out1 * 30, 0, ta))
    pa = ease_out(seg(t, 1.2, 1.6)) * (1 - out1)
    c.alpha_composite(shift(pill1, (1 - ease_out(seg(t, 1.2, 1.6))) * 40 - out1 * 30, 0, pa))
    t2 = ease_out(seg(t, 3.1, 3.6))
    c.alpha_composite(shift(title2, (1 - t2) * 40, 0, t2))
    p2 = ease_out(seg(t, 3.55, 4.0))
    c.alpha_composite(shift(pill2, (1 - p2) * 40, 0, p2))
    s2 = ease_out(seg(t, 4.6, 5.0))
    c.alpha_composite(shift(small2, (1 - s2) * 20, 0, s2))
    s = shine(t)
    if s:
        c.alpha_composite(s)

    if abs(scale - 1) > 1e-3:
        nw, nh = int(W * scale), int(H * scale)
        r = c.resize((nw, nh), Image.LANCZOS)
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        c.paste(r, ((W - nw) // 2, (H - nh) // 2))
    if a_global < 1:
        c.putalpha(c.split()[3].point(lambda v: int(v * a_global)))
    return c


# ---------- audio ----------
def make_audio(path):
    sr = 44100; n = int(sr * DUR)
    rng = np.random.default_rng(7)
    L = np.zeros(n); t = np.arange(n) / sr

    def add(sig, t0, gain=1.0):
        i0 = int(t0 * sr); e = min(n, i0 + len(sig))
        L[i0:e] += sig[: e - i0] * gain

    def swoosh(dur, up=True):
        m = int(sr * dur); tt = np.arange(m) / sr
        noise = rng.standard_normal(m)
        f = (400 + 5000 * (tt / dur) ** 2) if up else (5400 - 5000 * (tt / dur) ** 2)
        # time-varying one-pole lowpass
        out = np.zeros(m); y = 0.0
        for k in range(m):
            a = 1 - math.exp(-2 * math.pi * f[k] / sr)
            y += a * (noise[k] - y); out[k] = y
        env = np.sin(np.pi * tt / dur) ** 2
        return out * env * 3.0

    def ding(freq, dur, gain):
        tt = np.arange(int(sr * dur)) / sr
        return gain * np.sin(2 * np.pi * freq * tt) * np.exp(-tt * 6.5) * np.minimum(tt / 0.005, 1)

    add(swoosh(0.45, True), 0.0, 0.5)
    add(swoosh(0.35, True), 2.85, 0.4)
    add(ding(988, 0.9, 0.35) + ding(1480, 0.9, 0.18), 3.1, 0.8)
    add(swoosh(0.4, False), DUR - 0.5, 0.35)
    L = L / max(1e-9, np.abs(L).max()) * 0.45          # sfx bed, quieter than voice
    for f, t0 in (("A", 0.55), ("B", 3.15), ("C", 4.65)):
        with wave.open(f"/tmp/voices/v_{f}.wav") as w:
            v = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
        v = v / np.abs(v).max() * 0.85
        i0 = int(t0 * sr); e = min(n, i0 + len(v))
        L[i0:e] += v[: e - i0]
    L = np.clip(L, -0.98, 0.98)
    pcm = (np.stack([L, L], 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    wav = OUT / "lynx_sfx.wav"
    make_audio(wav)
    mov = OUT / "lynxvpn_banner65_v2.mov"
    p = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(wav),
         "-c:v", "qtrle", "-pix_fmt", "argb", "-c:a", "pcm_s16le", "-ar", "44100",
         "-t", str(DUR), str(mov)], stdin=subprocess.PIPE)
    for i in range(NF):
        fr = frame(i)
        if i in (6, 20, 40, 80, 100, 130, 156):
            bg = Image.new("RGBA", (W, H), (27, 27, 34, 255)); bg.alpha_composite(fr)
            bg.convert("RGB").save(OUT / f"still_{i:03d}.png")
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    print("done", mov)
