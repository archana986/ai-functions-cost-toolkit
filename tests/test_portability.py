import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((ROOT / "src" / "notebooks").glob("*.ipynb"))
BANNED = [
    "akrishn_fe_dsa",
    "azure-aiquery",
    "adb-7405609619727450",
    "/Users/archana",
    "archana.krishnamurthy",
    "fraud-meeting-demo",
]


def load_notebook(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source(cell):
    value = cell.get("source", [])
    return value if isinstance(value, str) else "".join(value)


class NotebookPolicyTests(unittest.TestCase):
    def test_notebooks_exist(self):
        self.assertEqual(
            [path.name for path in NOTEBOOKS],
            [
                "01_setup.ipynb",
                "02_generate_data.ipynb",
                "03a_run_ai_extract.ipynb",
                "03b_run_ai_query.ipynb",
                "04_reconcile_costs.ipynb",
                "05_adhoc_cost_query.ipynb",
            ],
        )

    def test_every_code_cell_has_explanatory_markdown_immediately_before_it(self):
        for path in NOTEBOOKS:
            cells = load_notebook(path)["cells"]
            self.assertEqual(cells[0]["cell_type"], "markdown", path.name)
            for index, cell in enumerate(cells):
                if cell["cell_type"] == "code":
                    self.assertGreater(index, 0, f"{path.name} cell {index}")
                    self.assertEqual(
                        cells[index - 1]["cell_type"],
                        "markdown",
                        f"{path.name} code cell {index} lacks preceding markdown",
                    )
                    self.assertTrue(source(cells[index - 1]).strip())

    def test_markdown_has_no_horizontal_rule(self):
        for path in NOTEBOOKS:
            for index, cell in enumerate(load_notebook(path)["cells"]):
                if cell["cell_type"] == "markdown":
                    self.assertNotRegex(
                        source(cell),
                        r"(?m)^\s*---\s*$",
                        f"{path.name} markdown cell {index}",
                    )

    def test_notebooks_use_widgets_not_custom_spark_configuration(self):
        pipeline = [p for p in NOTEBOOKS if p.name != "05_adhoc_cost_query.ipynb"]
        for path in pipeline:
            text = path.read_text(encoding="utf-8")
            self.assertIn('dbutils.widgets.text(\\"catalog\\"', text)
            self.assertNotIn("spark.conf.set", text)
        adhoc = (ROOT / "src/notebooks/05_adhoc_cost_query.ipynb").read_text(
            encoding="utf-8"
        )
        self.assertIn("dbutils.widgets.text", adhoc)
        self.assertNotIn("spark.conf.set", adhoc)


class RepositoryContractTests(unittest.TestCase):
    def test_demo_and_reconcile_are_separate_jobs(self):
        demo = (ROOT / "resources/demo.job.yml").read_text(encoding="utf-8")
        reconcile = (ROOT / "resources/reconcile.job.yml").read_text(encoding="utf-8")
        self.assertIn("ai_functions_cost_demo:", demo)
        self.assertNotIn("ai_functions_cost_reconcile_hourly:", demo)
        self.assertIn("ai_functions_cost_reconcile_hourly:", reconcile)
        self.assertIn("pause_status: PAUSED", reconcile)

    def test_bundle_references_existing_assets(self):
        required = [
            ROOT / "databricks.yml",
            ROOT / "resources/demo.job.yml",
            ROOT / "resources/reconcile.job.yml",
            ROOT / "SETUP.md",
            ROOT / "README.md",
            *NOTEBOOKS,
        ]
        for path in required:
            self.assertTrue(path.is_file(), str(path.relative_to(ROOT)))

    def test_portable_files_have_no_personal_workspace_values(self):
        paths = [
            ROOT / "README.md",
            ROOT / "SETUP.md",
            ROOT / "databricks.yml",
            *NOTEBOOKS,
            *sorted((ROOT / "resources").glob("*.yml")),
        ]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for value in BANNED:
                self.assertNotIn(value, text, f"{value} found in {path.relative_to(ROOT)}")

    def test_readme_and_setup_have_no_em_dash(self):
        for name in ("README.md", "SETUP.md", "databricks.yml"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("\u2014", text, name)
            self.assertNotIn("\u2013", text, name)

    def test_readme_does_not_reference_missing_assets(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for relative in re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme):
            if "://" not in relative and not relative.startswith("#"):
                self.assertTrue((ROOT / relative).exists(), relative)

    def test_readme_does_not_claim_actual_dollars(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("NO BILLING DATA YET", readme)
        self.assertIn("Do not quote predicted dollars as spend", readme)


if __name__ == "__main__":
    unittest.main()
