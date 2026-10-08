"""CLI tests: the output a person actually reads must show the source,
and a bad data folder must fail with a clear message, not a traceback."""

import json

from knowledge_system.cli import main


def test_answer_output_shows_answer_then_source(capsys):
    assert main(["Can I work from home on Friday?"]) == 0
    out = capsys.readouterr().out

    assert out.index("Answer:") < out.index("Source:")
    assert "working_arrangements.md — Section 2" in out


def test_not_found_output_offers_closest_sections(capsys):
    main(["How much paternity leave do I get?"])
    out = capsys.readouterr().out

    assert "couldn't find an answer" in out
    assert "Closest sections" in out


def test_json_output_is_valid(capsys):
    main(["--json", "Can I WFH?"])
    data = json.loads(capsys.readouterr().out)

    assert data["status"] == "answered"
    assert data["sources"][0]["file"] == "working_arrangements.md"


def test_missing_data_folder_exits_with_error(tmp_path, capsys):
    assert main(["--data", str(tmp_path / "missing"), "anything"]) == 1
    assert "not found" in capsys.readouterr().err
