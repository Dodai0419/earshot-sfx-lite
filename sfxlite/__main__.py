"""python -m sfxlite list | render | check | export: the `earshot sfx` commands, same arguments and output lines."""
import argparse
import json
import os
import sys

from .forge import bank, sfx


def main(argv=None):
    ap = argparse.ArgumentParser(prog='sfxlite', description="earshot's sound bank: 252 sound effects rendered from code")
    sub = ap.add_subparsers(dest='cmd', metavar='<list|render|check|export>')
    pl = sub.add_parser('list', help='the bank: ids, lengths, peak times, cue kinds, knobs')
    pl.add_argument('--category', help='one category (whoosh_fast, pro_impact, typing_key, pluck ...)')
    pl.add_argument('--kind', help='a cue kind or kit role (whoosh, whoosh.long, hit, key, bell ...)')
    pr = sub.add_parser('render', help='render one take to a WAV')
    pr.add_argument('sound', help='sound id, e.g. whoosh_fast/crisp (see: python -m sfxlite list)')
    pr.add_argument('-o', '--output', required=True, help='WAV to write (24-bit)')
    pr.add_argument('--seed', type=int, help="noise seed: a new take (default: the sound's own, the delivered final)")
    pr.add_argument('--dur', type=float, help='length in seconds (exact)')
    pr.add_argument('--apex', type=float, help='seconds from the start to the loudest moment (whoosh family)')
    pr.add_argument('--pitch', help="note name ('E5', 'Eb6') or Hz, through the recipe's own pitch parameter")
    pr.add_argument('--peak', type=float, default=-1.0, help='sample peak in dBFS, 0 or less (default -1)')
    pr.add_argument('--weight', type=float, help='level relative to --peak, 6 dB per doubling (0.5 = 6 dB down)')
    pr.add_argument('--sr', type=int, default=48000, choices=(44100, 48000, 88200, 96000),
                    help='sample rate of the WAV (default 48000; other rates need: pip install soxr)')
    pc = sub.add_parser('check', help='model-free audit: clicks, truncation, clipping, DC, ring, tail, rising pitch '
                                      'glide, stacked hits')
    pc.add_argument('files', nargs='+')
    pc.add_argument('--category', help='bank category, for context (a riser may stop on its peak)')
    pc.add_argument('--role', help='kit role, for context (hit / land: stacked layers and pre-swells are warnings)')
    pe = sub.add_parser('export', help='render every sound (or one --category / --kind) into a folder')
    pe.add_argument('dir')
    pe.add_argument('--category')
    pe.add_argument('--kind')
    for p in (pl, pr, pc, pe):
        p.add_argument('--json', action='store_true', help='print JSON instead of text')
    a = ap.parse_args(argv)
    out = lambda r, text: print(json.dumps(r, indent=1, default=str) if a.json else text)

    if a.cmd == 'list':
        r = sfx.sfx_list(a.category, a.kind)
        lines = [r['summary'], f"{'id':30s} {'dur s':>6s} {'peak s':>6s}  kinds / knobs"]
        for x in r['sounds']:
            kn = x['knobs']
            k = [f"dur {kn['dur']}"] + (['apex'] if kn['apex'] else []) + (
                [f"pitch {kn['pitch'].get('note')}"] if kn['pitch'] else [])
            lines.append(f"{x['id']:30s} {x['dur_s'] or 0:6.3f} {x['peak_s'] or 0:6.3f}  "
                         f"{','.join(x['kinds']) or '-'} | {', '.join(k)}")
        out(r, '\n'.join(lines))
        return 0
    if a.cmd == 'render':
        r = sfx.sfx_render(a.sound, a.output, seed=a.seed, dur=a.dur, apex=a.apex, pitch=a.pitch, peak_db=a.peak,
                           weight=a.weight, sr=a.sr)
        out(r, r['summary'])
        return 0
    if a.cmd == 'check':
        r = sfx.sfx_check(a.files if len(a.files) > 1 else a.files[0], a.category, a.role)
        rows = r.get('files') or [r]
        out(r, '\n'.join([r['summary']] * (len(rows) > 1) + [x['summary'] for x in rows]))
        return 0 if r['ok'] else 1
    if a.cmd == 'export':
        rows = bank.list_sounds(category=a.category, kind=a.kind)
        done = []
        for i, x in enumerate(rows, 1):
            f = os.path.join(a.dir, x['id'].replace('/', '__') + '.wav')
            r = sfx.sfx_render(x['id'], f)
            done.append(r['file'])
            if not a.json:
                print(f"[{i}/{len(rows)}] {r['summary']}", flush=True)
        if a.json:
            out({'files': done}, '')
        return 0
    ap.print_help()
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (bank.BankError, ValueError, OSError) as e:
        print(f'sfxlite: error: {e}', file=sys.stderr)
        sys.exit(1)
