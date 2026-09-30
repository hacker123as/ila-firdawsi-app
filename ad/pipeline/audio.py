"""Ila Firdawsi commercial: sound design + mix (runs in the Higgsfield sandbox).
Usage: python3 audio.py <workdir>. Needs <workdir>/score.wav, city.wav, vo_*.wav; writes mix.wav."""
import json, os, subprocess, sys, wave
import numpy as np
SR = 48000
WORK = sys.argv[1]
CFG = json.load(open(os.path.join(os.path.dirname(__file__), 'shots.json')))['audio']
T = CFG['length']
N = int(T * SR)
rng = np.random.default_rng(11)


def load(path):
    raw = subprocess.run(f'ffmpeg -v error -i "{path}" -f f32le -ac 2 -ar {SR} -', shell=True, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def place(bus, sig, t, gain=1.0):
    i = int(t * SR); j = min(len(bus), i + len(sig))
    if j > i:
        bus[i:j] += sig[:j - i] * gain


def db(x):
    return 10 ** (x / 20)


def lowpass(x, fc):
    """one-pole, per-sample cutoff array allowed"""
    y = np.zeros_like(x); a = np.exp(-2 * np.pi * np.asarray(fc) / SR)
    a = np.broadcast_to(a, (len(x),))
    acc = np.zeros(2)
    for n in range(len(x)):
        acc = (1 - a[n]) * x[n] + a[n] * acc
        y[n] = acc
    return y


def lowpass_fast(x, fc):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(2, fc / (SR / 2), output='sos'), x, axis=0)


# ---- city bed: loop the plate's native city audio with long crossfades, then close it down
city = load(os.path.join(WORK, 'city.wav'))
bed = np.zeros((N, 2), np.float32)
seg = len(city); xf = int(0.8 * SR); pos = 0; k = 0
while pos < int(CFG['city_end'] * SR) + SR:
    s = city.copy()
    if k % 2:
        s = s[::-1] if False else np.roll(s, seg // 3, axis=0)
    ramp = np.ones(seg); ramp[:xf] = np.linspace(0, 1, xf); ramp[-xf:] = np.linspace(1, 0, xf)
    place(bed, s * ramp[:, None], pos / SR)
    pos += seg - xf; k += 1
bed = bed[:N]
# the moment she reads the screen: the city stays, but recedes (low-pass + -7 dB), then cuts home
t = np.arange(N) / SR
q0, q1, ce = CFG['city_quiet'], CFG['city_quiet'] + 2.5, CFG['city_end']
try:
    from scipy.signal import butter, sosfilt
    dull = sosfilt(butter(2, 1400 / (SR / 2), output='sos'), bed, axis=0)
except Exception:
    dull = bed
mixk = np.clip((t - q0) / (q1 - q0), 0, 1)[:, None]
bed = bed * (1 - mixk) + dull * mixk * db(-5)
bed *= np.clip((ce - t) / 0.12, 0, 1)[:, None]  # hard-ish cut on the match cut
bed *= np.clip(t / 0.3, 0, 1)[:, None]

# ---- home room tone: very low brown noise with a hint of air; J-cut in just before the picture
rt = np.cumsum(rng.normal(0, 1, (N, 2)), 0); rt -= np.convolve(rt[:, 0], np.ones(4800) / 4800, 'same')[:, None]
rt /= np.abs(rt).max() + 1e-9
room = rt * db(-44) * (np.clip((t - (ce - 0.25)) / 0.25, 0, 1) * np.clip((CFG['room_end'] - t) / 0.8, 0, 1))[:, None]


# ---- designed sounds
def chime():
    """Soft two-note notification: warm bell partials, no sacred audio."""
    out = np.zeros((int(1.8 * SR), 2))
    for t0, f0, g in ((0.0, 1318.5, 0.5), (0.16, 987.8, 0.6)):
        n = len(out) - int(t0 * SR); tt = np.arange(n) / SR
        s = sum(a * np.sin(2 * np.pi * f0 * r * tt) * np.exp(-tt * d) for r, a, d in ((1, 1, 3.2), (2.01, .35, 6), (2.76, .18, 9), (4.1, .07, 14)))
        s *= np.minimum(1, tt / 0.004) * g
        out[int(t0 * SR):, 0] += s * 0.95; out[int(t0 * SR):, 1] += s
    return out * 0.35


def tick():
    n = int(0.35 * SR); tt = np.arange(n) / SR
    s = np.sin(2 * np.pi * 740 * tt) * np.exp(-tt * 28) + 0.4 * np.sin(2 * np.pi * 1110 * tt) * np.exp(-tt * 40)
    return np.stack([s, s], 1) * 0.16


def placement():
    n = int(0.4 * SR); tt = np.arange(n) / SR
    thud = np.sin(2 * np.pi * 95 * tt) * np.exp(-tt * 38)
    click = rng.normal(0, 1, n) * np.exp(-tt * 180)
    try:
        from scipy.signal import butter, sosfilt
        click = sosfilt(butter(2, [1800 / (SR / 2), 6000 / (SR / 2)], btype='band', output='sos'), click)
    except Exception:
        pass
    s = thud * 0.5 + click * 0.25
    return np.stack([s, s], 1) * 0.5


def fabric(dur=0.9):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = rng.normal(0, 1, n)
    try:
        from scipy.signal import butter, sosfilt
        s = sosfilt(butter(2, [300 / (SR / 2), 3000 / (SR / 2)], btype='band', output='sos'), s)
    except Exception:
        pass
    e = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 2
    return np.stack([s * e, s * e * 0.9], 1) * 0.05


sfx = np.zeros((N, 2), np.float32)
for ev in CFG['sfx']:
    fn = {'chime': chime, 'tick': tick, 'placement': placement, 'fabric': fabric}[ev['type']]
    place(sfx, fn(), ev['t'], db(ev.get('db', 0)))

# ---- voice
vo = np.zeros((N, 2), np.float32)
for line in CFG['vo']:
    s = load(os.path.join(WORK, line['file']))
    # trim leading/trailing silence
    a = np.abs(s).max(1); nz = np.where(a > 0.01)[0]
    if len(nz):
        s = s[max(0, nz[0] - 480): nz[-1] + 4800]
    s = s / (np.abs(s).max() + 1e-9) * db(-4)
    place(vo, s, line['t'], db(line.get('db', 0)))

# ---- music, ducked under the voice
music = load(os.path.join(WORK, 'score.wav'))[:N]
if len(music) < N:
    music = np.pad(music, ((0, N - len(music)), (0, 0)))
env = np.abs(vo).max(1)
env = np.convolve(env, np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
duck = 1 - 0.45 * np.clip(env / 0.05, 0, 1)
music = music * duck[:, None] * db(CFG.get('music_db', -3))

mix = bed * db(CFG.get('city_db', -2)) + room + sfx + vo * db(CFG.get('vo_db', 0)) + music
mix = np.tanh(mix * 0.95) / 0.95
st = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
with wave.open(os.path.join(WORK, 'mix_raw.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
subprocess.run(f'ffmpeg -v error -y -i {WORK}/mix_raw.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar {SR} {WORK}/mix.wav', shell=True, check=True)
print('mix ok', N / SR)
