"""WAV in and out with the standard library and numpy (earshot decodes with ffmpeg; the bank only needs WAV).

    x = load('pop.wav')                  # (n, 2) float32 at 48 kHz (mono is duplicated at unity gain)
    write('pop.wav', y)                  # 24-bit PCM, the same bytes earshot writes through soundfile
"""
import os
import struct
import wave

import numpy as np

SR = 48000
AUDIO_EXTS = ('.wav',)


class AudioError(Exception):
    pass


def load(path, sr=SR, mono=False):
    try:
        with wave.open(str(path), 'rb') as w:
            ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(n)
    except (wave.Error, EOFError, OSError) as e:
        raise AudioError(f'cannot read {path}: {e} (sfxlite reads PCM WAV files only)') from e
    if width == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | b[:, 1] << 8 | b[:, 2] << 16
        x = np.where(v >= 1 << 23, v - (1 << 24), v) / 8388608.0
    elif width in (1, 2, 4):
        v = np.frombuffer(raw, {1: np.uint8, 2: '<i2', 4: '<i4'}[width]).astype(np.float64)
        x = (v - 128) / 128 if width == 1 else v / float(2 ** (8 * width - 1))
    else:
        raise AudioError(f'{path}: {8 * width}-bit samples are not supported')
    x = x.reshape(-1, ch)
    if rate != sr:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(rate, sr)
        x = resample_poly(x, sr // g, rate // g, axis=0)
    if mono:
        return x.mean(1).astype(np.float32)
    return (np.repeat(x, 2, 1) if ch == 1 else x[:, :2]).astype(np.float32)


def write(path, y, sr=SR):
    """24-bit PCM the way libsndfile writes float32 (soundfile.write(..., subtype='PCM_24')): lrintf(x * 2^31) as int32,
    then its top three bytes (an arithmetic shift by 8, so a floor, not a rounding, to 24 bits)"""
    y = np.asarray(y, np.float32)
    y = y[:, None] if y.ndim == 1 else y
    v = np.clip(np.rint(y * np.float32(2147483648.0)).astype(np.int64), -2 ** 31, 2 ** 31 - 1).astype('<i4') >> 8
    data = np.ascontiguousarray(v).view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    pad = b'\0' * (len(data) & 1)                     # RIFF chunks are word aligned (an odd mono take gets a pad byte)
    ch, sr = y.shape[1], int(sr)
    head = b'RIFF' + struct.pack('<I', 36 + len(data) + len(pad)) + b'WAVEfmt ' + struct.pack(
        '<IHHIIHH', 16, 1, ch, sr, sr * ch * 3, ch * 3, 24) + b'data' + struct.pack('<I', len(data))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(head + data + pad)
    return str(path).replace(chr(92), '/')
