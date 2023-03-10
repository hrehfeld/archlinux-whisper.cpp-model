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
    'large': '0f4c8e34f21cf1a914c59d8b3ce882345ad349d6',
}

if __name__ == '__main__':

    src = Path('PKGBUILD.template').read_text()

    for model, checksum in models.items():
        dir = Path('models') / model
        if not dir.exists():
            os.system(f'git clone ssh://aur@aur.archlinux.org/whisper.cpp-model-{model}.git {dir}')
            os.system(f'git -C {dir} switch -c master')
        os.system(f'git -C {dir} switch master')

        model_src = f'_model="{model}"' + os.linesep + f'_model_sha1sum="{checksum}"' + os.linesep + f'_pkgbase="{_pkgbase}"' + os.linesep + src

        pkgbuild = dir / 'PKGBUILD'
        pkgbuild.write_text(model_src)

        os.system(f'cd {dir} && makepkg --printsrcinfo > .SRCINFO')
        os.system(f'git -C {dir} add PKGBUILD .SRCINFO')
        os.system(f'git -C {dir} commit -m"chg"')
