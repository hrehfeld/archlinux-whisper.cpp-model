#!/bin/python3
from pathlib import Path
import os
import json
import re
import urllib.request
import hashlib
import dataclasses

_pkgbase = "whisper.cpp-model"

model_list_filepath = Path('models.json')
deprecated_model_list_filepath = Path('deprecated-models.txt')

repo_url = 'https://github.com/ggerganov/whisper.cpp'

download_script_url = "https://github.com/ggerganov/whisper.cpp/raw/master/models/download-ggml-model.sh"

def pkgname(model):
    return f'{_pkgbase}-{model}'


def var(name, value):
    value = as_shell(value)
    return f'{name}={value}'

extra_variables = {
    'large-v2': {
        'replaces': [pkgname('large')],
    },
}

def url_basename(url):
    return url.split('/')[-1]

def download_file(url):
    with urllib.request.urlopen(url) as response:
        res = response.read()
    return res

def sha256sum(data: bytes):
    return hashlib.sha256(data).hexdigest()


@dataclasses.dataclass
class Model:
    name: str
    version: str = '1'
    _checksum: str | None = None
    deprecated: bool = False

    @property
    def url(self):
        model_name = self.name
        # this should match the process in the original script: download_script_src
        src="https://huggingface.co/ggerganov/whisper.cpp"
        pfx = "resolve/main/ggml"
        if 'tdrz' in model_name:
            src = "https://huggingface.co/akashmjn/tinydiarize-whisper.cpp"
            # the original script sets this again
            pfx = "resolve/main/ggml"
        return src + '/' + pfx + f'-{model_name}.bin'

    def checksum(self, no_checksums):
        if not no_checksums and (not self._checksum or self._checksum == 'SKIP'):
            print(f'Downloading model {self.name} for checksum from {self.url}')
            self._checksum = sha256sum(download_file(self.url))
        return self._checksum


    @staticmethod
    def serialize_version():
        return 2

Models = dict[str, Model]

def make_Models(models):
    return {model.name: model for model in models}


def load_models() -> Models:
    with model_list_filepath.open('r') as f:
        models = json.load(f)

    version = 1
    if isinstance(models, list):
        assert len(models) == 2, models
        version, models = models
    if version >= 2:
        assert version == 2
        assert isinstance(models, dict), models
        models = {name: Model(name, **args) for name, args in models.items()}
    else:
        models = {name: Model(name=name, _checksum=checksum) for name, checksum in models.items()}
        save_models(models)
    return models


def save_models(models: Models):
    def asdict(model):
        ds = dataclasses.asdict(model)
        del ds['name']
        return ds

    _models = {model.name: asdict(model) for name, model in models.items()}

    data = [Model.serialize_version(), _models]

    with model_list_filepath.open('w') as f:
        json.dump(data, f, indent=2)


def update_models():
    import urllib.request

    response = urllib.request.urlopen(download_script_url)
    download_script_src = response.read().decode('utf-8')

    model_list_re = re.compile(r'''# Whisper models
models="(?P<models>[^"]+)''', re.MULTILINE)
    m = model_list_re.search(download_script_src)
    assert m, download_script_src
    updated_model_names = m.group('models').splitlines()

    models_org = load_models()

    for model_name, model in models_org.items():
        if model_name not in updated_model_names:
            print(f'Deprecating model {model_name}')
            model.deprecated = True

    for model_name in updated_model_names:
        if model_name not in models_org:
            print(f'Adding model {model_name}')
            models_org[model_name] = Model(name=model_name)


    save_models(models_org)


def parse_args():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--commit', action='store_true', help="Commit each model AUR repo.")
    p.add_argument('--push', action='store_true', help="Also push to each model AUR repo.")
    p.add_argument('--push-args', help="Extra arguments when pushing to each model AUR repo.", nargs='*')
    p.add_argument('--update-models', action='store_true', help="Update model list.")
    p.add_argument('--makepkg', action='store_true', help="Run `makepkg -f` on each model AUR repo.")
    p.add_argument('--dry-run', action='store_true', help="Do not run makepkg")
    p.add_argument('--no-checksums', action='store_true', help="Do not retrieve model files for checksums")
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
    elif isinstance(x, Path):
        return repr(str(x))
    raise NotImplementedError(f'unknown value: {repr(x)}')


if __name__ == '__main__':

    args = parse_args()

    if args.update_models:
        update_models()

    src = Path('PKGBUILD.template').read_text()

    models = load_models()

    # do_vcs = False

    for model_name, model in models.items():
        model_filepath = Path(f"ggml-{model_name}.bin")

        dir = Path('models') / model_name
        print(f'### Model directory: {dir}')
        if not dir.exists():
            system(f'git clone ssh://aur@aur.archlinux.org/whisper.cpp-model-{model_name}.git {dir}')
            system(f'git -C {dir} branch -c master')
        system(f'git -C {dir} switch master')

        checksum = model.checksum(args.no_checksums) or 'SKIP'
        if not args.no_checksums:
            # save the updated checksum
            save_models(models)

        model_src = [
            var('_baseurl', repo_url),
            var('_model', model_name),
            var('_model_url', (model.url)),
            var('_model_sha1sum', checksum),
            var('_pkgbase', _pkgbase),
            #var('_download_script_url', download_script_url),
            #var('_download_script_basename', download_script_basename),

        ]
        for k, v in extra_variables.get(model_name, {}).items():
            model_src.append(var(k, v))
#         if do_vcs:
#             model_src.append("""pkgver() {
#     # track whisper.cpp release tags
#     latest_release=$(git ls-remote -t "$_baseurl" | cut -f 2 | sed 's#^refs/tags/v\?##' | sort -r | head -n1 | cut -d '/' -f 3 )
#     latest_commit="$(git ls-remote "$_baseurl" master | head -n1 | cut -f 1 | cut -b -12)"
#     echo "$latest_release.r$latest_commit"
# }

# """)
        model_src.append(src)

        model_src = os.linesep.join(model_src)

        pkgbuild = dir / 'PKGBUILD'
        print(f'### writing {pkgbuild}')
        pkgbuild.write_text(model_src)

        if not args.dry_run:
            system(f'cd {dir} && makepkg --printsrcinfo > .SRCINFO')
            system(f'git -C {dir} add PKGBUILD .SRCINFO')
            if args.commit:
                system(f'git -C {dir} commit -m"chg"')
            if args.push:
                push_args = ' '.join(args.push_args) if args.push_args else ''
                system(f'git -C {dir} push --set-upstream origin master {push_args}')
            if args.makepkg:
                system(f'cd {dir} && makepkg -f')
