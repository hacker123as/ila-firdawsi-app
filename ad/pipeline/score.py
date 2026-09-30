"""Original score for the Ila Firdawsi commercial: felt piano, warm pad, quiet low pulse. 72 BPM, F major.
Arc: city pulse -> room for the alert -> warmth -> stillness at home -> gentle lift -> resolve. Writes score.wav."""
import sys, wave
import numpy as np
SR = 48000; T = 57.0; N = int(SR * T)
OUT = sys.argv[1] if len(sys.argv) > 1 else 'score.wav'
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(7)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, d, s, r, sus_len):
    e = np.zeros(n); A = int(a * SR); D = int(d * SR); S = int(sus_len * SR)
    e[:A] = np.linspace(0, 1, A, endpoint=False)
    k = max(0, min(D, n - A)); e[A:A + k] = np.linspace(1, s, D)[:k]
    e[A + D:A + D + S] = s
    rel = n - (A + D + S)
    if rel > 0: e[A + D + S:] = s * np.exp(-np.arange(rel) / SR / r * 5)
    return e


def add(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR); j = min(N, i + len(sig)); s = sig[:j - i] * gain
    L[i:j] += s * np.sqrt(0.5 * (1 - pan)); R[i:j] += s * np.sqrt(0.5 * (1 + pan))


def piano(m, dur=4.0, vel=0.5):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m); s = np.zeros(n); B = 0.0002
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + B * k * k)
        if fk > 16000: break
        amp = vel * (0.9 ** (k - 1)) / (k ** 0.9) * (1.2 if k == 1 else 1.0)
        s += amp * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28)) * np.exp(-t * (0.6 + 0.35 * k) * (f / 260) ** 0.35)
    s *= np.minimum(1, t / 0.012)
    hn = rng.normal(0, 1, int(0.03 * SR)); hn = np.convolve(hn, np.ones(40) / 40, 'same') * np.exp(-np.arange(len(hn)) / SR * 120)
    s[:len(hn)] += hn * vel * 0.05
    return s * 0.35


def pad(ms, dur, vol=0.08, att=2.5, rel=3.0):
    n = int((dur + rel) * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for m in ms:
        for det in (-0.07, 0.0, 0.07):
            ph = 2 * np.pi * hz(m) * 2 ** (det / 12) * t + rng.uniform(0, 6.28)
            s += np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    return s * env_adsr(n, att, 0.5, 0.85, rel, max(0, dur - att - 0.5)) * (1 + 0.15 * np.sin(2 * np.pi * 0.12 * t)) * vol / len(ms)


def pulse(t0, t1, bpm=72, vol=0.25, m=29):
    t = t0
    while t < t1:
        n = int(0.5 * SR); tt = np.arange(n) / SR
        f = hz(m) * (1 + 0.6 * np.exp(-tt * 40))
        add(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9), t, vol)
        t += 60 / bpm


F9 = [53, 57, 60, 64, 67]; Am7 = [57, 60, 64, 67]; Dm9 = [50, 53, 57, 60, 64]; Bb9 = [46, 53, 57, 60, 62]; Csus = [48, 53, 55, 60]; Fadd9 = [41, 53, 57, 60, 67]
bar = 60 / 72 * 4
prog = [F9, Am7, Dm9, Bb9, Csus, Bb9, F9, Dm9, Bb9, F9, Am7, Dm9, Bb9, Csus, Bb9, Fadd9, Fadd9]
for b, ch in enumerate(prog):
    t0 = b * bar
    vol = 0.05 if t0 < 11 else (0.06 if 19 < t0 < 36 else 0.075)
    add(pad([c + 12 if c < 50 else c for c in ch], bar, vol=vol, att=1.8, rel=2.5), t0)
    add(pad([ch[0] - 12], bar, vol=0.05, att=1.0, rel=2.0), t0)
motif = {0: [(0, 72), (1.25, 69), (2.5, 67)], 1: [(0, 72), (1.9, 76)], 2: [(0.4, 74), (2.5, 72)], 3: [(0, 69), (1.6, 72), (2.5, 74)],
         4: [(0.2, 72)], 5: [(0, 74), (1.8, 72)], 6: [(0.3, 77), (1.9, 76), (2.6, 72)], 7: [(0.5, 74)], 8: [(0, 72), (2.0, 69)], 9: [(0.8, 72)],
         10: [(0, 76), (1.3, 74), (2.4, 72)], 11: [(0, 77), (1.5, 76), (2.6, 74)], 12: [(0, 74), (1.2, 72), (2.4, 69)], 13: [(0, 72), (1.7, 74)],
         14: [(0, 77), (2, 76)], 15: [(0, 72), (0.02, 65), (0.04, 60)], 16: []}
for b, notes in motif.items():
    for off, m in notes:
        t0 = b * bar + off * bar / 4
        v = 0.45 if 15 < t0 < 36 else 0.38
        add(piano(m, 5.0, v), t0, 1.0, rng.uniform(-0.3, 0.3))
        if b in (6, 15): add(piano(m - 12, 5.0, v * 0.6), t0, 1.0, -0.2)
pulse(0.0, 10.8, vol=0.22)     # the city
pulse(36.0, 46.3, vol=0.14)    # the product montage


def verb(x, dec=0.5):
    y = x.copy()
    for d, g in [(0.029, 0.5), (0.037, 0.45), (0.041, 0.42), (0.053, 0.4), (0.067, 0.35), (0.083, 0.3), (0.11, 0.26), (0.15, 0.2), (0.21, 0.15), (0.3, 0.1)]:
        k = int(d * SR); y[k:] += x[:-k] * g * dec
    return y


L2 = L + 0.6 * verb(R, 0.7); R2 = R + 0.6 * verb(L, 0.7)
fi = int(0.4 * SR); L2[:fi] *= np.linspace(0, 1, fi); R2[:fi] *= np.linspace(0, 1, fi)
fo = int(3.0 * SR); L2[-fo:] *= np.linspace(1, 0, fo) ** 2; R2[-fo:] *= np.linspace(1, 0, fo) ** 2
st = np.stack([L2, R2], 1); st /= np.max(np.abs(st)) * 1.12
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
print('score ok')
