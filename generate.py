#!/bin/python3
from pathlib import Path
import os
import json

_pkgbase = "whisper.cpp-model"

with open('models.json', 'r') as f:
    models = json.load(f)

extra_variables = {
    'large-v2': {
        'replaces': ['-'.join((_pkgbase, 'large'))]
    }
}

def parse_args():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--commit', action='store_true', help="Commit each model AUR repo.")
    p.add_argument('--push', action='store_true', help="Also push to each model AUR repo.")
    p.add_argument('--push-args', help="Extra arguments when pushing to each model AUR repo.", nargs='*')
    args = p.parse_args()
    return args


def system(cmd_str):
    print(cmd_str)
    return os.system(cmd_str)


def as_shell(x):
    if isinstance(x, list):
        x = ' '.join((as_shell(e) for e in x))
        return f'({x})'
    elif isinstance(x, (int, str)):
        return repr(x)
    raise NotImplementedError(f'unknown value: {repr(x)}')

if __name__ == '__main__':

    args = parse_args()

    src = Path('PKGBUILD.template').read_text()

    for model, checksum in models.items():
        dir = Path('models') / model
        print(f'### Model directory: {dir}')
        if not dir.exists():
            system(f'git clone ssh://aur@aur.archlinux.org/whisper.cpp-model-{model}.git {dir}')
            system(f'git -C {dir} switch -c master')
        system(f'git -C {dir} switch master')

        model_src = [
            f'_model="{model}"',
            f'_model_sha1sum="{checksum}"',
            f'_pkgbase="{_pkgbase}"',
            src,
        ]
        for k, v in extra_variables.get(model, {}).items():
            model_src.append(f'{k}={as_shell(v)}')
        model_src = os.linesep.join(model_src)

        pkgbuild = dir / 'PKGBUILD'
        pkgbuild.write_text(model_src)

        system(f'cd {dir} && makepkg --printsrcinfo > .SRCINFO')
        system(f'git -C {dir} add PKGBUILD .SRCINFO')
        if args.commit:
            system(f'git -C {dir} commit -m"chg"')
        if args.push:
            push_args = ' '.join(args.push_args) if args.push_args else ''
            system(f'git -C {dir} push {push_args}')
