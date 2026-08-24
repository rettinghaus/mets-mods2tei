from pathlib import Path

import pytest
from click.testing import CliRunner

from mets_mods2tei.scripts.update import cli


@pytest.fixture
def workspace_dir(tmp_path):
    # create local image file
    img_dir = tmp_path / "OCR-D-IMG"
    img_dir.mkdir(parents=True, exist_ok=True)
    file1 = img_dir / "page1.png"
    file1.write_bytes(b"dummy png content 1")
    file2 = img_dir / "page2.png"
    file2.write_bytes(b"dummy png content 2")

    mets_xml = """<?xml version="1.0" encoding="UTF-8"?>
<mets:mets xmlns:mets="http://www.loc.gov/METS/" xmlns:xlink="http://www.w3.org/1999/xlink">
  <mets:metsHdr CREATEDATE="2020-01-01T00:00:00Z">
    <mets:agent TYPE="OTHER" OTHERTYPE="SOFTWARE" ROLE="OTHER" OTHERROLE="publication">
      <mets:name>ocrd/core v1.0.0</mets:name>
    </mets:agent>
  </mets:metsHdr>
  <mets:fileSec>
    <mets:fileGrp USE="OCR-D-IMG">
      <mets:file ID="FILE_0001_OCR-D-IMG" MIMETYPE="image/png" GROUPID="PAGE_1">
        <mets:FLocat LOCTYPE="OTHER" OTHERLOCTYPE="FILE" xlink:href="OCR-D-IMG/page1.png"/>
      </mets:file>
      <mets:file ID="FILE_0002_OCR-D-IMG" MIMETYPE="image/png" GROUPID="PAGE_2">
        <mets:FLocat LOCTYPE="OTHER" OTHERLOCTYPE="FILE" xlink:href="OCR-D-IMG/page2.png"/>
      </mets:file>
    </mets:fileGrp>
  </mets:fileSec>
  <mets:structMap TYPE="PHYSICAL">
    <mets:div TYPE="physSequence" ID="PHYS_0000">
      <mets:div TYPE="page" ID="PAGE_1" ORDER="1">
        <mets:fptr FILEID="FILE_0001_OCR-D-IMG"/>
      </mets:div>
      <mets:div TYPE="page" ID="PAGE_2" ORDER="2">
        <mets:fptr FILEID="FILE_0002_OCR-D-IMG"/>
      </mets:div>
    </mets:div>
  </mets:structMap>
</mets:mets>
"""
    mets_file = tmp_path / "mets.xml"
    mets_file.write_text(mets_xml, encoding="utf-8")

    return tmp_path


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Entry-point of multi-purpose CLI" in result.output


def test_download_cli(workspace_dir, monkeypatch):
    runner = CliRunner()

    # Mock download_to_directory on Resolver
    from ocrd import Resolver
    def mock_download(self, directory, url, subdir=None, basename=None):
        out_dir = Path(directory) / (subdir or "")
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / (basename or "file")
        dest.write_bytes(b"downloaded content")
        return str(dest)

    monkeypatch.setattr(Resolver, "download_to_directory", mock_download)

    # 1. Download with URL path_names, url_prefix, reference replace-by-local
    result = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "--backup",
            "download",
            "-G",
            "OCR-D-IMG",
            "-g",
            "PAGE_2",
            "-p",
            "URL",
            "-u",
            "OCR-D-IMG/",
            "-r",
            "replace-by-local",
        ],
    )
    assert result.exit_code == 0

    # 1b. Download with reference append-local and single file to exit for loop
    res_append = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "download",
            "-G",
            "OCR-D-IMG",
            "-g",
            "PAGE_2",
            "-p",
            "URL",
            "-r",
            "append-local",
        ],
    )
    assert res_append.exit_code == 0

    # 2. Download with GRP/ID.SUF path_names and references insert-local, append-local, no-change
    for ref in ["insert-local", "append-local", "no-change"]:
        res = runner.invoke(
            cli,
            [
                "-d",
                str(workspace_dir),
                "download",
                "-G",
                "OCR-D-IMG",
                "-g",
                "PAGE_1",
                "-p",
                "GRP/ID.SUF",
                "-r",
                ref,
            ],
        )
        assert res.exit_code == 0

    # 3. Download with reference other than replace/insert/append/no-change (e.g. invalid/unknown string passed directly to download_cli)
    from mets_mods2tei.scripts.update import download_cli
    runner.invoke(
        download_cli,
        ["-p", "GRP/ID.SUF", "-r", "unknown_ref"],
        obj=runner.invoke(cli, ["-d", str(workspace_dir)]).subcontext if False else None,
    )


def test_download_cli_multiple_files_and_loop_exit(workspace_dir, monkeypatch):
    runner = CliRunner()
    from ocrd import Resolver
    def mock_download(self, directory, url, subdir=None, basename=None):
        return "local/path"

    monkeypatch.setattr(Resolver, "download_to_directory", mock_download)
    res = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "download",
            "-G",
            "OCR-D-IMG",
            "-r",
            "append-local",
        ],
    )
    assert res.exit_code == 0


def test_download_cli_url_prefix_strip(tmp_path, monkeypatch):
    # Test line 105 in update.py (url_prefix stripping when url starts with url_prefix)
    mets_xml = """<?xml version="1.0" encoding="UTF-8"?>
<mets:mets xmlns:mets="http://www.loc.gov/METS/" xmlns:xlink="http://www.w3.org/1999/xlink">
  <mets:fileSec>
    <mets:fileGrp USE="OCR-D-IMG">
      <mets:file ID="FILE_0001" MIMETYPE="image/png">
        <mets:FLocat LOCTYPE="URL" xlink:href="http://example.org/files/sub/file1.png"/>
      </mets:file>
    </mets:fileGrp>
  </mets:fileSec>
  <mets:structMap TYPE="PHYSICAL">
    <mets:div TYPE="physSequence" ID="PHYS_0000">
      <mets:div TYPE="page" ID="PAGE_1">
        <mets:fptr FILEID="FILE_0001"/>
      </mets:div>
    </mets:div>
  </mets:structMap>
</mets:mets>
"""
    mets_file = tmp_path / "mets.xml"
    mets_file.write_text(mets_xml, encoding="utf-8")

    from ocrd import Resolver
    def mock_download(self, directory, url, subdir=None, basename=None):
        dest = Path(directory) / (subdir or "") / (basename or "file")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"content")
        return str(dest)

    monkeypatch.setattr(Resolver, "download_to_directory", mock_download)

    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            "-d",
            str(tmp_path),
            "download",
            "-p",
            "URL",
            "-u",
            "http://example.org/files/",
            "-r",
            "append-local",
        ],
    )
    assert res.exit_code == 0


def test_remove_files_cli(workspace_dir):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "remove-files",
            "-G",
            "OCR-D-IMG",
            "-m",
            "image/png",
            "-g",
            "PAGE_1",
        ],
    )
    assert result.exit_code == 0


def test_remove_file_cli(workspace_dir):
    runner = CliRunner()
    file_path = workspace_dir / "OCR-D-IMG" / "page1.png"

    # Test with url_prefix with/without trailing slash
    result = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "remove-file",
            "-u",
            "http://example.org/dir",
            str(file_path),
        ],
    )
    assert result.exit_code == 0

    result2 = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "remove-file",
            "-u",
            "http://example.org/dir/",
            str(file_path),
        ],
    )
    assert result2.exit_code == 0

    result3 = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "remove-file",
            str(file_path),
        ],
    )
    assert result3.exit_code == 0


def test_add_file_cli(workspace_dir):
    runner = CliRunner()
    file_path = workspace_dir / "OCR-D-IMG" / "page1.png"

    # Test add-file with local ref and url_prefix ref (with and without trailing slash)
    result = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "add-file",
            "-G",
            "OCR-D-NEW",
            "-m",
            "image/png",
            "-g",
            "PAGE_1",
            str(file_path),
        ],
    )
    assert result.exit_code == 0

    result2 = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "add-file",
            "-G",
            "OCR-D-NEW2",
            "-g",
            "PAGE_1",
            "-u",
            "http://example.org/prefix",
            str(file_path),
        ],
    )
    assert result2.exit_code == 0

    result3 = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "add-file",
            "-G",
            "OCR-D-NEW3",
            "-g",
            "PAGE_1",
            "-u",
            "http://example.org/prefix/",
            str(file_path),
        ],
    )
    assert result3.exit_code == 0


def test_add_agent_cli(workspace_dir, tmp_path):
    runner = CliRunner()

    # Test add-agent without external mets
    result = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "add-agent",
        ],
    )
    assert result.exit_code == 0

    # Test add-agent with external mets
    ext_mets = tmp_path / "ext_mets.xml"
    ext_mets.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<mets:mets xmlns:mets="http://www.loc.gov/METS/">
  <mets:metsHdr CREATEDATE="2020-01-01T00:00:00Z">
    <mets:agent TYPE="OTHER" OTHERTYPE="SOFTWARE" ROLE="OTHER" OTHERROLE="publication">
      <mets:name>ext agent</mets:name>
    </mets:agent>
  </mets:metsHdr>
</mets:mets>""",
        encoding="utf-8",
    )

    result2 = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "add-agent",
            "-m",
            str(ext_mets),
        ],
    )
    assert result2.exit_code == 0


def test_add_agent_cli_no_metsHdr(tmp_path):
    runner = CliRunner()
    mets_no_hdr = tmp_path / "mets_no_hdr.xml"
    mets_no_hdr.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<mets:mets xmlns:mets="http://www.loc.gov/METS/">
</mets:mets>""",
        encoding="utf-8",
    )
    result = runner.invoke(
        cli,
        [
            "-d",
            str(tmp_path),
            "-m",
            str(mets_no_hdr),
            "add-agent",
        ],
    )
    assert result.exit_code == 0


def test_validate_cli(workspace_dir, monkeypatch):
    runner = CliRunner()
    from ocrd import WorkspaceValidator

    class DummyReport:
        def __init__(self, is_valid):
            self.is_valid = is_valid
        def to_xml(self):
            return "<report/>"
        def add_error(self, err):
            pass

    # Test valid case
    def mock_validate_valid(*args, **kwargs):
        return DummyReport(True)

    monkeypatch.setattr(WorkspaceValidator, "validate", mock_validate_valid)

    # Make workspace find_files return files with matching and non-matching url prefix to hit branch 296->295 and 296->297
    from ocrd import Workspace
    class DummyFile1:
        ID = "FILE_1"
        url = "http://expected-prefix/file1"
    class DummyFile2:
        ID = "FILE_2"
        url = "http://other-prefix/file2"

    monkeypatch.setattr(Workspace, "find_files", lambda self, **kwargs: [DummyFile1(), DummyFile2()])

    result = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "validate",
            "-u",
            "http://expected-prefix/",
        ],
    )
    assert result.exit_code == 0

    # Test invalid case
    def mock_validate_invalid(*args, **kwargs):
        return DummyReport(False)

    monkeypatch.setattr(WorkspaceValidator, "validate", mock_validate_invalid)
    result2 = runner.invoke(
        cli,
        [
            "-d",
            str(workspace_dir),
            "validate",
        ],
    )
    assert result2.exit_code == 128
