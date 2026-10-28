"""earshot fit: translate a real recording into code (analysis by synthesis), then vary it.

    from earshot.forge import fit
    m = fit.fit('click.wav')                    # kind='auto' | 'modal' | 'spectral' | 'sines' | 'gesture' | 'hybrid'
    y = fit.render(m, seed=0)                   # the resynthesis (seeds change only noise / jitter); knobs vary it
    from earshot.forge.fit.quality import quality
    q = quality('click.wav', y)                 # mel dB, envelope r, tone dB, onset error, ... (clap=True: CLAP cos)
    src = fit.to_recipe(m, name='click_fit', source='click.wav')   # a forge recipe module (Python source)
    mm = fit.morph(m_a, m_b, 0.5)               # a new model between two fits of the same kind

    earshot fit click.wav -o made/click_fit.py --report       # recipe + resynthesis WAV + spectrogram PNG + metrics
    earshot fit --morph a.wav b.wav --amount 0.5 -o made/ab_morph.py
    earshot fit --forge made/click_fit.py --budget 96 --dir made/click_variations   # critic-searched variations

The fitters (one module each, plain-JSON models, deterministic per seed, pure numpy / scipy):
  modal.py     struck / ringing sounds -> strikes of damped sinusoids (ESPRIT + least squares) + band noise
  sines.py     tonal sounds -> tracked partials (McAulay-Quatieri / SMS) + strike atoms + 1/3-octave noise
  spectral.py  noisy sounds -> a time-varying 48-band noise gesture + stereo + texture + tonal ridges
  gesture.py   designed gestures (whooshes, swells, risers) -> tones (a sines / modal fit's partials) + air (noise)
  space.py     a stereo recording's decorrelated tail -> a seeded diffuse side layer (the chosen fit's post stage)
  auto.py      the engine: character -> candidates -> fit, render, score, keep the best; hybrids; morph
  quality.py   the metrics every fit is judged by (and the side-by-side spectrogram picture)
  codegen.py   model -> a forge recipe module (TARGET / SPACE / DEFAULTS / MODEL / render(p, r))
docs/FIT.md has how it works, the measured quality and the limits.
"""


def fit(x, kind='auto', **kw):
    from . import auto
    return auto.fit(x, kind=kind, **kw)


def render(model, seed=0, **knobs):
    from . import auto
    return auto.render(model, seed=seed, **knobs)


def morph(a, b, amount=0.5):
    from . import auto
    return auto.morph(a, b, amount)


def to_recipe(model, **kw):
    from . import codegen
    return codegen.to_recipe(model, **kw)
