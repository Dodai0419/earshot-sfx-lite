"""Draw the README pictures from rendered WAVs: a labelled gallery and a sheet of every sound (needs Pillow).

    python -m sfxlite export out/all
    python tools/gallery.py out/all docs
"""
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from sfxlite.audio import load  # noqa: E402

PICKS = ['whoosh_fast/crisp', 'pro_impact/short', 'notify/mid_tine', 'ui_pop/soft', 'typing_key/crisp', 'riser/build',
         'shimmer/m0', 'glitch/stutter', 'mallet/glock', 'drip/drop', 'shutter/dslr', 'fit/key/thock']
BG, FG, DIM = (14, 15, 20), (236, 236, 240), (140, 142, 155)
STOPS = np.array([[14, 15, 20], [48, 18, 88], [150, 38, 110], [236, 92, 70], [252, 190, 90], [252, 252, 200]], float)


def font(size, mono=False):
    for name in (('consola.ttf', 'DejaVuSansMono.ttf') if mono else ('segoeui.ttf', 'DejaVuSans.ttf')):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def spectrogram(x, w, h):
    """log-frequency (60 Hz - 20 kHz) magnitude in dB, w frames x h rows, mapped to 0..1 over 70 dB"""
    m = x.mean(1)
    n = 1024
    hop = max(1, (len(m) - n) // w) if len(m) > n else 1
    m = np.pad(m, (0, max(0, n + hop * w - len(m))))
    frames = np.stack([m[i * hop:i * hop + n] for i in range(w)]) * np.hanning(n)
    mag = np.abs(np.fft.rfft(frames, axis=1))
    f = np.fft.rfftfreq(n, 1 / 48000)
    edges = np.geomspace(60, 20000, h + 1)
    rows = np.stack([mag[:, (f >= a) & (f < b)].max(1) if ((f >= a) & (f < b)).any() else
                     mag[:, np.argmin(np.abs(f - a))] for a, b in zip(edges[:-1], edges[1:])], 1)
    db = 20 * np.log10(rows + 1e-9)
    return np.clip((db - db.max() + 70) / 70, 0, 1)[:, ::-1].T


def colour(v):
    t = v * (len(STOPS) - 1)
    i = np.minimum(t.astype(int), len(STOPS) - 2)
    u = (t - i)[..., None]
    return (STOPS[i] * (1 - u) + STOPS[i + 1] * u).astype(np.uint8)


def tile(x, w, h):
    img = Image.fromarray(colour(spectrogram(x, w, h)))
    d = ImageDraw.Draw(img)
    env = np.abs(x).max(1)
    k = max(1, len(env) // w)
    env = np.array([env[i * k:(i + 1) * k].max() if i * k < len(env) else 0 for i in range(w)])
    pts = [(i, h - 2 - env[i] * (h * 0.35)) for i in range(w)]
    d.line(pts, fill=(255, 255, 255), width=1)
    return img


def main(src, out):
    os.makedirs(out, exist_ok=True)
    files = {os.path.basename(p)[:-4].replace('__', '/'): p for p in glob.glob(os.path.join(src, '*.wav'))}
    # gallery: 4 x 3 labelled tiles
    tw, th, pad, top = 300, 150, 18, 70
    g = Image.new('RGB', (4 * tw + 5 * pad, top + 3 * (th + 46) + pad), BG)
    d = ImageDraw.Draw(g)
    d.text((pad, 18), f'12 of the {len(files)} sounds, rendered from code (spectrogram + level)', font=font(26), fill=FG)
    for i, sid in enumerate(PICKS):
        x = load(files[sid])
        cx, cy = pad + (i % 4) * (tw + pad), top + (i // 4) * (th + 46)
        g.paste(tile(x, tw, th), (cx, cy))
        d.text((cx, cy + th + 6), sid, font=font(18, True), fill=FG)
        d.text((cx + tw, cy + th + 8), f'{len(x) / 48000:.2f} s', font=font(15), fill=DIM, anchor='ra')
    g.save(os.path.join(out, 'gallery.png'), optimize=True)
    # sheet: every sound as a small tile, in bank order
    ids = sorted(files)
    cols, sw, sh, gap = 18, 64, 40, 4
    rows = -(-len(ids) // cols)
    s = Image.new('RGB', (cols * (sw + gap) + gap, 54 + rows * (sh + gap) + gap), BG)
    ds = ImageDraw.Draw(s)
    ds.text((gap + 4, 14), f'All {len(ids)} sounds of the bank, one tile each', font=font(22), fill=FG)
    for i, sid in enumerate(ids):
        s.paste(tile(load(files[sid]), sw, sh), (gap + (i % cols) * (sw + gap), 54 + (i // cols) * (sh + gap)))
    s.save(os.path.join(out, 'all-sounds.png'), optimize=True)
    print(f"wrote {out}/gallery.png and {out}/all-sounds.png from {len(files)} WAVs")


if __name__ == '__main__':
    main(*sys.argv[1:3])
