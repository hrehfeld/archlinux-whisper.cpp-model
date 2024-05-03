#!/bin/python3
from pathlib import Path
import os
import json
import re

_pkgbase = "whisper.cpp-model"

model_list_filepath = 'models.json'


def var(name, value):
    value = as_shell(value)
    return f'{name}={value}'

extra_variables = {
    'large-v2': {
        'replaces': ['-'.join((_pkgbase, 'large'))]
    }
}


def load_models():
    with open(model_list_filepath, 'r') as f:
        models = json.load(f)
    return models


def save_models(models):
    with open(model_list_filepath, 'w') as f:
        json.dump(models, f, indent=2)

def update_models():
    model_list_url = 'https://github.com/ggerganov/whisper.cpp/raw/master/models/download-ggml-model.sh'
    import urllib.request

    response = urllib.request.urlopen(model_list_url)
    model_list = response.read().decode('utf-8')

    model_list_re = re.compile(r'''# Whisper models
models="(?P<models>[^"]+)''', re.MULTILINE)
    m = model_list_re.search(model_list)
    assert m, model_list
    models = m.group('models').splitlines()


    models_org = load_models()

    for model in models:
        if model not in models_org:
            print(f'Adding model {model}')
            models_org[model] = 'SKIP'


    save_models(models_org)


def parse_args():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--commit', action='store_true', help="Commit each model AUR repo.")
    p.add_argument('--push', action='store_true', help="Also push to each model AUR repo.")
    p.add_argument('--push-args', help="Extra arguments when pushing to each model AUR repo.", nargs='*')
    p.add_argument('--update-models', action='store_true', help="Update model list.")
    p.add_argument('--makepkg', action='store_true', help="Run `makepkg -f` on each model AUR repo.")
    args = p.parse_args()
    return args


def system(cmd_str):
    print('system:', cmd_str)
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

    if args.update_models:
        update_models()

    src = Path('PKGBUILD.template').read_text()

    models = load_models()

    for model, checksum in models.items():
        dir = Path('models') / model
        print(f'### Model directory: {dir}')
        if not dir.exists():
            system(f'git clone ssh://aur@aur.archlinux.org/whisper.cpp-model-{model}.git {dir}')
            system(f'git -C {dir} switch -c master')
        system(f'git -C {dir} switch master')

        model_src = [
            var('_model', model),
            var('_model_sha1sum', checksum),
            var('_pkgbase', _pkgbase),
        ]
        for k, v in extra_variables.get(model, {}).items():
            model_src.append(var(k, v))
        model_src.append(src)

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
        if args.makepkg:
            system(f'cd {dir} && makepkg -f')
