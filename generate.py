#!/bin/python3
from pathlib import Path
import os

_pkgbase = "whisper.cpp-model"

models = {
    'tiny': 'bd577a113a864445d4c299885e0cb97d4ba92b5f',
    'tiny.en': 'c78c86eb1a8faa21b369bcd33207cc90d64ae9df',
    'base': '465707469ff3a37a2b9b8d8f89f2f99de7299dac',
    'base.en': '137c40403d78fd54d454da0f9bd998f78703390c',
    'small': '55356645c2b361a969dfd0ef2c5a50d530afd8d5',
    'small.en': 'db8a495a91d927739e50b3fc1cc4c6b8f6c2d022',
    'medium': 'fd9727b6e1217c2f614f9b698455c4ffd82463b4',
    'medium.en': '8c30f0e44ce9560643ebd10bbe50cd20eafd3723',
    'large-v1': 'b1caaf735c4cc1429223d5a74f0f4d0b9b59a299',
    'large-v2': '0f4c8e34f21cf1a914c59d8b3ce882345ad349d6',
    'large-v3': 'ad82bf6a9043ceed055076d0fd39f5f186ff8062',
}

extra_variables = {
    'large-v3': {
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
