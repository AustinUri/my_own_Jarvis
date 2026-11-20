"""Read-only inventory of harvested skills. No skill execution or trust assignment."""
import argparse
import hashlib
import json
from pathlib import Path


def inventory(packs):
    packs = Path(packs).resolve()
    index = json.loads((packs / '_skill-index.json').read_text(encoding='utf-8'))
    if not isinstance(index, list):
        raise ValueError('Expected a list of indexed skills')
    rows = []
    for item in index:
        relative = Path(item['path'])
        path = (packs / relative).resolve()
        result = {'name': item.get('name'), 'source': item.get('source'), 'path': str(relative), 'review': 'pending', 'execution': 'not-tested'}
        if not path.is_relative_to(packs) or path.name != 'SKILL.md' or not path.is_file():
            result['integrity'] = 'missing-or-invalid'
        else:
            data = path.read_bytes()
            result['sha256'] = hashlib.sha256(data).hexdigest()
            result['integrity'] = 'present' if len(data) == item.get('bytes') else 'size-mismatch'
        rows.append(result)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packs', type=Path, default=Path('.jarvis/skill-fabric/packs'))
    parser.add_argument('--output', type=Path, default=Path('.jarvis/skill-fabric/audit-inventory.json'))
    args = parser.parse_args()
    rows = inventory(args.packs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    present = sum(row['integrity'] == 'present' for row in rows)
    print(f'{present}/{len(rows)} indexed skill files present; security review and execution tests pending. {args.output}')
    return int(present != len(rows))


if __name__ == '__main__':
    raise SystemExit(main())
