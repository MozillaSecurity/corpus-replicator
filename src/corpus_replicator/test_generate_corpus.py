# type: ignore
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pytest import mark, raises

from .common import Recipe, ToolError
from .generate_corpus import load_generator, main, parse_args


@mark.parametrize(
    "tool, available, raised",
    [
        # ffmpeg exists
        ("ffmpeg", True, False),
        # ffmpeg not available
        ("ffmpeg", False, True),
        # unknown tool
        ("unknown", False, True),
    ],
)
def test_load_generator_01(mocker, tmp_path, tool, available, raised):
    """test load_generator()"""
    mocker.patch(
        "corpus_replicator.generate_corpus.ffmpeg_available",
        return_value=available,
        autospec=True,
    )
    recipe = mocker.Mock(spec_set=Recipe, tool=tool)

    if raised:
        with raises(ToolError):
            load_generator(recipe, tmp_path)
    else:
        load_generator(recipe, tmp_path)


def test_main_01(mocker, tmp_path):
    """test main()"""
    mocker.patch("corpus_replicator.generate_corpus.load_generator", autospec=True)
    mocker.patch("corpus_replicator.generate_corpus.Recipe", autospec=True)
    empty = tmp_path / "empty"
    empty.touch()
    main(["-o", str(tmp_path), str(empty), str(empty)])


def test_parse_args_01(capsys, tmp_path):
    """test parse_args()"""
    empty = tmp_path / "empty"
    empty.touch()
    # success
    parse_args([str(empty), str(empty)])
    # missing template file
    with raises(SystemExit):
        parse_args([str(empty), "missing"])
    assert "error: Template file does not exist: 'missing'" in capsys.readouterr()[1]
    # missing recipe file
    with raises(SystemExit):
        parse_args(["missing", str(empty)])
    assert "error: Recipe file does not exist: 'missing'" in capsys.readouterr()[1]
