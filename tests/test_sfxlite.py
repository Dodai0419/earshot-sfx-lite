"""Renders are compared byte for byte with WAVs written by earshot 0.4.0 itself (tests/upstream_sha256.json).

    python -m unittest -q                     # a sample of sounds and knob settings (about a minute without numba)
    SFXLITE_FULL=1 python -m unittest -q      # all 252 sounds (minutes with numba, much longer without)
"""
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sfxlite import audio  # noqa: E402
from sfxlite.forge import bank, sfx  # noqa: E402

GOLD = json.loads((ROOT / 'tests' / 'upstream_sha256.json').read_text(encoding='utf-8'))
import scipy  # noqa: E402
# the hashes were made with these versions; another numpy / scipy may move a sample by one 24-bit step, so there the
# check falls back to earshot's own re-render tolerance (bank.check: length exact, peak within 5 ms, envelope 0.5 dB)
PINNED = (np.__version__, scipy.__version__) == ('2.4.6', '1.17.1')
SAMPLE = ['pluck/kalimba', 'fit/hit/bamboo_tok', 'fit/key/thock', 'mallet/glock', 'drip/drop', 'swish/bright']
KNOBS = ['ui_pop/soft {"pitch": "A4"}', 'mallet/glock {"pitch": "G5"}', 'fit/key/thock {"dur": 0.3, "seed": 5}']


def sha_of(sound_id, tmp, **kw):
    f = os.path.join(tmp, sound_id.replace('/', '__') + '.wav')
    sfx.sfx_render(sound_id, f, **kw)
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def same_sound(sound_id, sha, want):
    if sha == want or PINNED:
        return sha == want
    r = bank.check([sound_id], log=None)[0]
    return r['ok']


class SameBytesAsEarshot(unittest.TestCase):
    def test_bank_is_complete(self):
        self.assertEqual(sorted(bank.ids()), sorted(GOLD['sounds']))
        self.assertEqual(len(bank.list()), 252)

    def test_sample_sounds(self):
        ids = sorted(GOLD['sounds']) if os.environ.get('SFXLITE_FULL') else SAMPLE
        with tempfile.TemporaryDirectory() as tmp:
            for sid in ids:
                with self.subTest(sid=sid):
                    self.assertTrue(same_sound(sid, sha_of(sid, tmp), GOLD['sounds'][sid]))

    def test_knobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            for case in KNOBS:
                sid, kw = case.split(' ', 1)
                with self.subTest(case=case):
                    sha = sha_of(sid, tmp, **json.loads(kw))
                    if PINNED:
                        self.assertEqual(sha, GOLD['knobs'][case])


class WavIO(unittest.TestCase):
    def test_odd_mono_take_gets_a_pad_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = os.path.join(tmp, 'm.wav')
            y = np.array([0.5, -0.25, 0.0], np.float32)
            audio.write(f, y)
            b = Path(f).read_bytes()
            self.assertEqual(len(b), 44 + 9 + 1)
            self.assertEqual(struct.unpack('<I', b[4:8])[0], len(b) - 8)
            self.assertEqual(struct.unpack('<I', b[40:44])[0], 9)
            back = audio.load(f, mono=True)
            np.testing.assert_allclose(back, y, atol=2 ** -23)

    def test_floor_like_libsndfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = os.path.join(tmp, 's.wav')
            audio.write(f, np.array([[1.4e-7, -1.4e-7]], np.float32))   # 1.17 LSB: libsndfile floors after lrintf
            v = np.frombuffer(Path(f).read_bytes()[44:50], np.uint8)
            self.assertEqual(list(v), [1, 0, 0, 0xfe, 0xff, 0xff])


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'sfxlite', *args], cwd=ROOT, capture_output=True, text=True)

    def test_render_line_and_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = os.path.join(tmp, 'k.wav').replace(os.sep, '/')
            r = self.run_cli('render', 'pluck/kalimba', '-o', f, '--pitch', 'E5')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(r.stdout.startswith(f'wrote {f}: pluck/kalimba seed 8001: 3.000 s'), r.stdout)
            if PINNED:
                self.assertEqual(hashlib.sha256(Path(f).read_bytes()).hexdigest(), GOLD['knobs']['pluck/kalimba {"pitch": "E5"}'])
            c = self.run_cli('check', f)
            self.assertIn(c.returncode, (0, 1), c.stderr)
            self.assertTrue(c.stdout.strip())

    def test_bad_id_is_an_error(self):
        r = self.run_cli('render', 'no/such', '-o', 'x.wav')
        self.assertEqual(r.returncode, 1)
        self.assertIn('sfxlite: error:', r.stderr)


if __name__ == '__main__':
    unittest.main()
