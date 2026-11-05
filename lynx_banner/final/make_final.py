import subprocess, sys
sys.path.insert(0, "/root/projects/ads/lynx_banner")
import make_banner_v3 as m   # needs T1 / P1 in the environment

mov = m.OUT / "lynxvpn_banner_final.mov"
p = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{m.W}x{m.H}",
     "-r", str(m.FPS), "-i", "-", "-i", str(m.OUT / "mix_s1_dmitri.wav"),
     "-c:v", "qtrle", "-pix_fmt", "argb", "-c:a", "pcm_s16le", "-ar", "44100", "-t", str(m.DUR), str(mov)],
    stdin=subprocess.PIPE)
for i in range(m.NF):
    p.stdin.write(m.frame(i).tobytes())
p.stdin.close(); p.wait()
print("done", mov)
