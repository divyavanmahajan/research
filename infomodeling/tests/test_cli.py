"""CLI integration tests."""

import os

import pytest
from click.testing import CliRunner

from infomodeling.cli import cli

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")
ORG_MODEL = os.path.join(EXAMPLES_DIR, "org_model.yaml")


class TestValidateCommand:
    def test_valid_model_exits_0(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--model", ORG_MODEL])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()
        assert "10 entities" in result.output

    def test_missing_file_exits_nonzero(self, tmp_path):
        runner = CliRunner()
        # Click will catch missing file before we get to parse
        result = runner.invoke(cli, ["validate", "--model", str(tmp_path / "nonexistent.yaml")])
        assert result.exit_code != 0

    def test_invalid_model_exits_1(self, tmp_path):
        bad_model = tmp_path / "bad.yaml"
        bad_model.write_text("version: '1.0'\nname: Test\nentities:\n  - name: Foo\n    attributes: []\n")
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--model", str(bad_model)])
        assert result.exit_code == 1


class TestGenerateCommand:
    def test_generates_files(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate",
            "--model", ORG_MODEL,
            "--output", str(tmp_path),
            "--seed", "42",
        ])
        assert result.exit_code == 0
        assert os.path.exists(os.path.join(str(tmp_path), "dbt_project.yml"))
        assert os.path.exists(os.path.join(str(tmp_path), "sources.yml"))
        assert os.path.exists(os.path.join(str(tmp_path), "models", "staging", "stg_person.sql"))

    def test_dry_run_writes_nothing(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate",
            "--model", ORG_MODEL,
            "--output", str(tmp_path),
            "--dry-run",
        ])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert not os.path.exists(os.path.join(str(tmp_path), "dbt_project.yml"))

    def test_generates_seeds_by_default(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate",
            "--model", ORG_MODEL,
            "--output", str(tmp_path),
            "--seed", "42",
        ])
        assert result.exit_code == 0
        assert os.path.exists(os.path.join(str(tmp_path), "seeds", "person.csv"))

    def test_no_seeds_flag(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "generate",
            "--model", ORG_MODEL,
            "--output", str(tmp_path),
            "--no-seeds",
        ])
        assert result.exit_code == 0
        assert not os.path.exists(os.path.join(str(tmp_path), "seeds"))

    def test_custom_source_name(self, tmp_path):
        runner = CliRunner()
        runner.invoke(cli, [
            "generate",
            "--model", ORG_MODEL,
            "--output", str(tmp_path),
            "--source-name", "bronze",
        ])
        sources_path = os.path.join(str(tmp_path), "sources.yml")
        content = open(sources_path).read()
        assert "bronze" in content

    def test_invalid_model_exits_1(self, tmp_path):
        bad_model = tmp_path / "bad.yaml"
        bad_model.write_text("version: '1.0'\nname: Test\nentities:\n  - name: Foo\n    attributes: []\n")
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--model", str(bad_model), "--output", str(tmp_path / "out")])
        assert result.exit_code == 1


class TestDiffCommand:
    def test_no_changes_after_generate(self, tmp_path):
        runner = CliRunner()
        # Generate first
        runner.invoke(cli, ["generate", "--model", ORG_MODEL, "--output", str(tmp_path), "--no-seeds"])
        # Diff should show no changes for YAML files (always overwritten) and SQL (no edits)
        result = runner.invoke(cli, ["diff", "--model", ORG_MODEL, "--output", str(tmp_path)])
        assert result.exit_code == 0

    def test_diff_on_empty_dir(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["diff", "--model", ORG_MODEL, "--output", str(tmp_path)])
        assert result.exit_code == 0
        assert "+" in result.output  # Files would be new


class TestSeedCommand:
    def test_generates_seed_files(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "seed",
            "--model", ORG_MODEL,
            "--output", str(tmp_path),
            "--rows", "10",
            "--seed", "42",
        ])
        assert result.exit_code == 0
        assert os.path.exists(os.path.join(str(tmp_path), "seeds", "person.csv"))

    def test_dry_run(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "seed",
            "--model", ORG_MODEL,
            "--output", str(tmp_path),
            "--dry-run",
        ])
        assert result.exit_code == 0
        assert "(dry)" in result.output
        assert not os.path.exists(os.path.join(str(tmp_path), "seeds"))

    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
