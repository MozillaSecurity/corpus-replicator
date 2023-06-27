# type: ignore
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from pytest import mark, raises

from .common import RecipeError
from .core import Replicator, main, parse_args

SAMPLE_VIDEO_RECIPE = """
base:
  codec: "h264"
  container: "mp4"
  library: "libx264"
  medium: "video"
  tool: "ffmpeg"
  default_flags:
    encoder:
      ["-foo", "bar"]
    resolution:
      ["overwrite-me"]

variation:
  resolution:
  - ["-s", "18x32"]
"""


@mark.parametrize(
    "mode, recipes, templates, expected",
    [
        # empty
        ("audio", [], [], 0),
        # empty (coverage)
        # single
        ("video", [SAMPLE_VIDEO_RECIPE], ["noise"], 1),
        # recipe mode mismatch
        ("audio", [SAMPLE_VIDEO_RECIPE], ["noise"], 0),
        # recipe mode mismatch (again for coverage)
        ("image", [SAMPLE_VIDEO_RECIPE], ["noise"], 0),
        # multiple templates
        ("video", [SAMPLE_VIDEO_RECIPE], ["noise", "solid"], 2),
        # multiple recipes
        ("video", [SAMPLE_VIDEO_RECIPE, SAMPLE_VIDEO_RECIPE], ["noise"], 2),
        # multiple recipes and multiple templates
        ("video", [SAMPLE_VIDEO_RECIPE, SAMPLE_VIDEO_RECIPE], ["noise", "solid"], 4),
    ],
)
def test_replicator_01(mocker, tmp_path, mode, recipes, templates, expected):
    """test Replicator()"""
    mocker.patch("corpus_replicator.common.run", autospec=True)
    mocker.patch("corpus_replicator.generate_corpus.ffmpeg_available", autospec=True)
    # create test template files
    recipe_path = tmp_path / "recipes"
    recipe_path.mkdir()
    for idx, recipe in enumerate(recipes):
        (recipe_path / f"recipe-{idx:02d}.yml").write_text(recipe)

    replicator = Replicator(mode, tmp_path / "output", recipe_path.iterdir())
    assert len(replicator) == 0
    replicator.generate_templates(templates)
    assert len(replicator) == expected
    replicator.generate_corpus()
    replicator.remove_templates()


@mark.parametrize(
    "file_data, final_count",
    [
        ([], 0),
        (["test", "test"], 1),
        (["test", "test", "test"], 1),
        (["test1", "test2"], 2),
        (["test1", "test2", "test2"], 2),
        (["test1", "test1", "test2", "test2"], 2),
    ],
)
def test_replicator_02(tmp_path, file_data, final_count):
    """test Replicator.remove_duplicates()"""

    for idx, data in enumerate(file_data):
        (tmp_path / f"{idx}.txt").write_text(data)
    replicator = Replicator("video", tmp_path, [])
    replicator.remove_duplicates()
    assert sum(1 for _ in replicator.dest.iterdir()) == final_count


@mark.parametrize(
    "medium",
    [
        "animation",
        "audio",
        "image",
        "video",
    ],
)
def test_main_01(mocker, tmp_path, medium):
    """test main()"""
    mocker.patch("corpus_replicator.core.ffmpeg_available", autospec=True)
    replicator = mocker.patch("corpus_replicator.core.Replicator", autospec=True)
    empty = tmp_path / "empty"
    empty.touch()
    mocker.patch("corpus_replicator.core.TOOL_LOG", empty)
    main(["-o", str(tmp_path), str(empty), medium])
    assert replicator.return_value.generate_templates.call_count == 1
    assert replicator.return_value.generate_corpus.call_count == 1
    assert replicator.return_value.remove_duplicates.call_count == 1
    assert replicator.return_value.remove_templates.call_count == 2


def test_main_02(mocker, tmp_path):
    """test main()"""
    mocker.patch("corpus_replicator.core.ffmpeg_available", autospec=True)
    replicator = mocker.patch("corpus_replicator.core.Replicator", autospec=True)
    replicator.side_effect = RecipeError("foo")
    empty = tmp_path / "empty"
    empty.touch()
    main(["-o", str(tmp_path), str(empty), "video"])
    assert replicator.return_value.generate_templates.call_count == 0
    assert replicator.return_value.generate_corpus.call_count == 0


def test_parse_args_01(capsys, mocker, tmp_path):
    """test parse_args()"""
    ffmpeg_check = mocker.patch(
        "corpus_replicator.core.ffmpeg_available", autospec=True
    )
    empty = tmp_path / "empty"
    empty.touch()
    # success
    parse_args([str(empty), "video"])
    # missing recipe file
    with raises(SystemExit):
        parse_args(["missing", "video"])
    assert "error: Recipe file does not exist: 'missing'" in capsys.readouterr()[1]
    # invalid resolution
    with raises(SystemExit):
        parse_args([str(empty), "video", "-r", "foo"])
    assert "argument -r/--resolution: invalid value" in capsys.readouterr()[1]
    # missing ffmpeg
    ffmpeg_check.return_value = False
    with raises(SystemExit):
        parse_args([str(empty), "video"])
    assert "Please install FFmpeg." in capsys.readouterr()[1]
