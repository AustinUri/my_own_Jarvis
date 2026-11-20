import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_skill_inventory import inventory

class InventoryTest(unittest.TestCase):
    def test_present_missing_and_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packs = root / 'packs'
            packs.mkdir()
            (packs / 'SKILL.md').write_bytes(b'example')
            (root / 'SKILL.md').write_bytes(b'outside')
            (packs / '_skill-index.json').write_text(json.dumps([
                {'path':'SKILL.md','bytes':7},
                {'path':'missing/SKILL.md','bytes':7},
                {'path':'../SKILL.md','bytes':7},
                {'path':'SKILL.md','bytes':9},
            ]))
            rows = inventory(packs)
            self.assertEqual([r['integrity'] for r in rows], ['present','missing-or-invalid','missing-or-invalid','size-mismatch'])
            self.assertTrue(all(r['execution']=='not-tested' for r in rows))
