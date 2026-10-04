#!/usr/bin/env python3
"""Checks that the Google Sheet and Google Doc imports follow the Pokemon, not the dex number.

    .venv/bin/python tests/test_import_identity.py

Everything happens in a temporary folder; the real species files and snapshots are not touched.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dexlib          # noqa: E402
import import_doc      # noqa: E402
import import_sheet    # noqa: E402

# Dex numbers before and after a reorder on the website (Gamma moved to the front; slot 4 is open).
BEFORE = {"Alpha": 1, "Beta": 2, "Gamma": 3}
AFTER = {"Gamma": 1, "Alpha": 2, "Beta": 3}
OLD_SHEET = "Dex #,Name,Type 1,HP\n1,Alpha,Grass,40\n2,Beta,Fire,50\n3,Gamma,Water,60\n"
OLD_DOC = "#1 Alpha (Grass)\n#2 Beta (Fire)\n#3 Gamma (Water)\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "species").mkdir()
        self.root = root
        self.saved = (dexlib.SPECIES_DIR, import_sheet.SNAPSHOT, import_sheet.REPORT, import_doc.SNAPSHOT, import_doc.REPORT)
        dexlib.SPECIES_DIR = root / "species"
        import_sheet.SNAPSHOT, import_sheet.REPORT = root / "sheet_snapshot.json", root / "sheet_problems.json"
        import_doc.SNAPSHOT, import_doc.REPORT = root / "doc_snapshot.json", root / "doc_problems.json"
        self.numbers(BEFORE)

    def tearDown(self):
        dexlib.SPECIES_DIR, import_sheet.SNAPSHOT, import_sheet.REPORT, import_doc.SNAPSHOT, import_doc.REPORT = self.saved
        self.tmp.cleanup()

    def numbers(self, layout):
        """Write the species files with these dex numbers (what the website's Change numbers does)."""
        existing = {sid: data for sid, _, data in dexlib.load_species()[0]}
        for name, dex in layout.items():
            data = existing.get(name.lower()) or {"name": name, "types": ["Grass"]}
            dexlib.write_species(dexlib.SPECIES_DIR / (name.lower() + ".yaml"), dict(data, dex=dex))

    def species(self, sid):
        return {s: d for s, _, d in dexlib.load_species()[0]}[sid]

    def run_import(self, module, text):
        path = self.root / "input.txt"
        path.write_text(text, encoding="utf-8")
        argv, sys.argv = sys.argv, ["import", str(path)]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                module.main()
        finally:
            sys.argv = argv
        report = module.REPORT
        return json.loads(report.read_text(encoding="utf-8"))

    def files_text(self):
        return {p.name: p.read_text(encoding="utf-8") for p in dexlib.SPECIES_DIR.glob("*.yaml")}


class SheetTests(Base):
    def setUp(self):
        super().setUp()
        self.run_import(import_sheet, OLD_SHEET)          # the first import creates the snapshot
        self.numbers(AFTER)                                # then the dex is reordered; the sheet is stale

    def test_snapshot_is_keyed_by_id(self):
        snapshot = json.loads(import_sheet.SNAPSHOT.read_text(encoding="utf-8"))
        self.assertEqual(set(snapshot), {"alpha", "beta", "gamma"})

    def test_edit_in_stale_row_lands_on_the_right_pokemon(self):
        before = self.files_text()
        problems = self.run_import(import_sheet, OLD_SHEET.replace("2,Beta,Fire,50", "2,Beta,Fire,99"))
        self.assertEqual(problems, [])
        self.assertEqual(self.species("beta")["base_stats"]["hp"], 99)
        self.assertEqual(self.species("beta")["dex"], 3)                 # not moved
        after = self.files_text()
        self.assertEqual({k for k in after if after[k] != before[k]}, {"beta.yaml"})

    def test_unchanged_stale_sheet_changes_nothing(self):
        before = self.files_text()
        self.assertEqual(self.run_import(import_sheet, OLD_SHEET), [])
        self.assertEqual(self.files_text(), before)

    def test_repasted_sheet_with_new_numbers_changes_nothing(self):
        before = self.files_text()
        new = "Dex #,Name,Type 1,HP\n1,Gamma,Water,60\n2,Alpha,Grass,40\n3,Beta,Fire,50\n"
        self.assertEqual(self.run_import(import_sheet, new), [])
        self.assertEqual(self.files_text(), before)

    def test_changed_number_cell_does_not_move_anything(self):
        before = self.files_text()
        self.run_import(import_sheet, OLD_SHEET.replace("1,Alpha,Grass,40", "9,Alpha,Grass,40"))
        self.assertEqual(self.files_text(), before)

    def test_new_pokemon_in_open_slot(self):
        problems = self.run_import(import_sheet, OLD_SHEET + "4,Delta,Water,70\n")
        self.assertEqual(problems, [])
        self.assertEqual(self.species("delta")["dex"], 4)
        self.assertEqual(self.species("delta")["base_stats"]["hp"], 70)

    def test_new_pokemon_on_a_taken_number_is_reported(self):
        before = self.files_text()
        problems = self.run_import(import_sheet, OLD_SHEET.replace("3,Gamma,Water,60", "3,Gamma,Water,60\n3,Delta,Water,70"))
        self.assertEqual(len(problems), 1)
        self.assertIn("Delta", problems[0]["row"])
        self.assertEqual(self.files_text(), before)

    def test_rename_of_a_moved_pokemon_is_reported(self):
        before = self.files_text()
        problems = self.run_import(import_sheet, OLD_SHEET.replace("2,Beta,Fire,50", "2,Betty,Fire,50"))
        self.assertEqual(len(problems), 1)
        self.assertEqual(self.files_text(), before)

    def test_rename_of_an_unmoved_pokemon_works(self):
        # Only here nothing was reordered: the same sheet, a species file that kept its number.
        self.numbers(BEFORE)
        self.assertEqual(self.run_import(import_sheet, OLD_SHEET.replace("2,Beta,Fire,50", "2,Betty,Fire,50")), [])
        self.assertEqual(self.species("beta")["name"], "Betty")
        self.assertEqual(self.species("beta")["dex"], 2)

    def test_same_name_on_two_rows_is_reported(self):
        before = self.files_text()
        problems = self.run_import(import_sheet, OLD_SHEET + "4,Alpha,Fire,99\n")
        self.assertEqual(len(problems), 1)       # the extra row is reported, nothing is applied
        self.assertEqual(self.files_text(), before)

    def test_nameless_row_on_a_stale_number_is_reported(self):
        before = self.files_text()
        problems = self.run_import(import_sheet, "Dex #,Name,Type 1,HP\n2,,Fire,99\n")
        self.assertEqual(len(problems), 1)
        self.assertEqual(self.files_text(), before)


class DocTests(Base):
    def setUp(self):
        super().setUp()
        self.run_import(import_doc, OLD_DOC)
        self.numbers(AFTER)

    def test_snapshot_is_keyed_by_id(self):
        snapshot = json.loads(import_doc.SNAPSHOT.read_text(encoding="utf-8"))
        self.assertEqual(set(snapshot), {"alpha", "beta", "gamma"})

    def test_edit_in_stale_line_lands_on_the_right_pokemon(self):
        problems = self.run_import(import_doc, OLD_DOC.replace("#2 Beta (Fire)", "#2 Beta (Fire, Flying)"))
        self.assertEqual(problems, [])
        self.assertEqual(self.species("beta")["types"], ["Fire", "Flying"])
        self.assertEqual(self.species("alpha")["types"], ["Grass"])
        self.assertEqual(self.species("beta")["dex"], 3)

    def test_unchanged_stale_doc_changes_nothing(self):
        before = self.files_text()
        self.assertEqual(self.run_import(import_doc, OLD_DOC), [])
        self.assertEqual(self.files_text(), before)

    def test_new_line_in_open_slot(self):
        self.assertEqual(self.run_import(import_doc, OLD_DOC + "#4 Delta (Water)\n"), [])
        self.assertEqual(self.species("delta")["dex"], 4)

    def test_evolution_follows_the_line_before_not_the_slot_before(self):
        self.run_import(import_doc, OLD_DOC.replace("#2 Beta (Fire)", "#2 Beta (Lv 16) (Fire)"))
        evolutions = self.species("alpha").get("evolutions")      # Alpha is the line before Beta in the doc
        self.assertEqual([e["into"] for e in evolutions], ["beta"])
        self.assertFalse(self.species("gamma").get("evolutions"))  # Gamma is the slot before Beta now

    def test_rename_of_a_moved_pokemon_is_reported(self):
        before = self.files_text()
        problems = self.run_import(import_doc, OLD_DOC.replace("#2 Beta (Fire)", "#2 Betty (Fire)"))
        self.assertEqual(len(problems), 1)
        self.assertEqual(self.files_text(), before)

    def test_new_line_on_a_taken_number_is_reported(self):
        before = self.files_text()
        problems = self.run_import(import_doc, OLD_DOC + "#3 Delta (Water)\n")
        self.assertEqual(len(problems), 1)
        self.assertEqual(self.files_text(), before)

    def test_same_name_on_two_lines_is_reported(self):
        before = self.files_text()
        problems = self.run_import(import_doc, OLD_DOC + "#4 Alpha (Fire)\n")
        self.assertEqual(len(problems), 1)
        self.assertEqual(self.files_text(), before)


class MigrationTests(unittest.TestCase):
    def test_old_snapshots_are_converted_by_name(self):
        species = [("alpha", None, {"name": "Alpha", "dex": 5}), ("beta", None, {"name": "Beta", "dex": 6})]
        sheet, lost = import_sheet.migrate_snapshot({"1": {"dex": "1", "name": "Alpha", "hp": "40"}, "7": {"dex": "7"}}, species)
        self.assertEqual(sheet, {"alpha": {"dex": "1", "name": "Alpha", "hp": "40"}})
        self.assertEqual(len(lost), 1)
        doc, lost = import_doc.migrate_snapshot({"2": "Beta (Fire)", "3": ""}, species)
        self.assertEqual(doc, {"beta": {"dex": 2, "text": "Beta (Fire)"}})
        self.assertEqual(lost, [])
        self.assertEqual(import_sheet.migrate_snapshot(sheet, species)[0], sheet)    # already new: left alone


if __name__ == "__main__":
    unittest.main(warnings="ignore")
