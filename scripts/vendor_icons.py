"""Vendor a small, pinned subset of official Tabler SVGs for offline rendering."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.etree import ElementTree as ET
import json
import urllib.request

NAMES = [
    'layout-dashboard', 'books', 'clipboard-list', 'arrows-exchange',
    'file-description', 'settings', 'building-community', 'logout', 'menu-2',
    'x', 'arrow-right', 'arrow-up-right', 'arrow-down', 'arrow-left', 'plus',
    'filter', 'search', 'check', 'circle-check', 'inbox', 'book-2',
    'truck-delivery', 'sun', 'moon', 'device-floppy', 'shield-check',
    'eye', 'eye-off', 'help-circle', 'refresh',
]


def main():
    assets = Path(__file__).resolve().parent.parent / 'static/vendor/tabler'
    manifest = assets / 'SOURCE.json'
    if manifest.exists():
        sha = json.loads(manifest.read_text(encoding='utf-8'))['commit']
    else:
        request = urllib.request.Request(
            'https://api.github.com/repos/tabler/tabler-icons/commits/main',
            headers={'User-Agent': 'BookBridge-local-assets'},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            sha = json.load(response)['sha']
    base = f'https://raw.githubusercontent.com/tabler/tabler-icons/{sha}/'
    ET.register_namespace('', 'http://www.w3.org/2000/svg')

    def fetch(name):
        with urllib.request.urlopen(base + f'icons/outline/{name}.svg', timeout=30) as response:
            root = ET.fromstring(response.read())
        symbol = ET.Element('{http://www.w3.org/2000/svg}symbol', id=name, viewBox='0 0 24 24')
        symbol.extend(root)
        return symbol

    sprite = ET.Element('{http://www.w3.org/2000/svg}svg')
    with ThreadPoolExecutor(max_workers=6) as pool:
        sprite.extend(pool.map(fetch, NAMES))
    with urllib.request.urlopen(base + 'LICENSE', timeout=30) as response:
        license_text = response.read().decode()
    assets.mkdir(parents=True, exist_ok=True)
    (assets / 'LICENSE').write_text(license_text, encoding='utf-8')
    (assets / 'icons.svg').write_text(ET.tostring(sprite, encoding='unicode'), encoding='utf-8')
    manifest.write_text(json.dumps({
        'repository': 'https://github.com/tabler/tabler-icons', 'commit': sha,
        'icons': NAMES,
    }, indent=2), encoding='utf-8')
    print(f'Vendored {len(NAMES)} official Tabler icons at {sha}')


if __name__ == '__main__':
    main()
