# type: ignore
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from pytest import mark, raises
from yaml import safe_dump

from .common import (
    CorpusGenerator,
    Recipe,
    RecipeError,
    Template,
    is_resolution,
    list_recipes,
    run_tool,
)

SAMPLE_RECIPE = """
base:
  codec: "codec"
  container: "container"
  library: "library"
  medium: "audio"
  tool: "ffmpeg"
  default_flags:
    encoder:
      ["-c:a", "mp3"]

variation:
  vbr:
  - ["-vbr", "1"]
  - ["-vbr", "3"]
  - ["-vbr", "5"]
  cbr:
  - ["-b:a", "64k"]
"""


def test_recipe_01(tmp_path):
    """test Recipe()"""
    recipe_file = tmp_path / "recipe.yml"
    recipe_file.write_text(SAMPLE_RECIPE)
    recipe = Recipe(recipe_file)
    assert recipe.container == "container"
    assert recipe.library == "library"
    assert recipe.medium == "audio"
    assert recipe.codec == "codec"
    assert recipe.tool == "ffmpeg"

    assert len(recipe) == 4

    for active, _, flags in recipe:
        assert active in ("cbr", "vbr")
        assert "-c:a" in flags
        if active == "cbr":
            assert "-b:a" in flags
            assert "-vbr" not in flags
        elif active == "vbr":
            assert "-b:a" not in flags
            assert "-vbr" in flags
        else:
            assert False
        assert len(flags) == 4


@mark.parametrize(
    "data, msg",
    [
        # unsupported tool
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "x",
                    "default_flags": {},
                },
                "variation": {
                    "a": [["-a"]],
                },
            },
            "Recipe tool 'x' unsupported",
        ),
        # unsupported medium
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "x",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {
                    "a": [["-a"]],
                },
            },
            "Recipe medium 'x' unsupported",
        ),
        # missing codec
        (
            {
                "base": {
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {
                    "a": [["-a"]],
                },
            },
            "Recipe missing entry 'codec'",
        ),
        # invalid codec entry
        (
            {
                "base": {
                    "codec": 1,
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {
                    "a": [["-a"]],
                },
            },
            "Recipe 'codec' entry is invalid",
        ),
        # empty codec entry
        (
            {
                "base": {
                    "codec": "",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {
                    "a": [["-a"]],
                },
            },
            "Recipe 'codec' entry is invalid",
        ),
        # missing base
        (
            {
                "variation": {
                    "a": [["-a"]],
                },
            },
            "Recipe missing entry 'base'",
        ),
        # missing variation
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
            },
            "Recipe missing entry 'variation'",
        ),
        # incomplete default flags
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {"a": None, "b": ["-b"]},
                },
                "variation": {
                    "a": [["-a"]],
                },
            },
            "Recipe 'default_flags' 'a' is incomplete",
        ),
        # invalid default flags entry
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {"a": [1]},
                },
                "variation": {
                    "a": [["-a"]],
                },
            },
            "Recipe 'default_flags' 'a' has invalid flags",
        ),
        # invalid empty default flags
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": [],
                },
                "variation": {
                    "a": [["-a"]],
                },
            },
            "Recipe 'default_flags' is invalid",
        ),
        # empty variations
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {},
            },
            "Recipe missing variations",
        ),
        # incomplete variation
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {"a": None, "b": [["-b"]]},
            },
            "Recipe variation 'a' is incomplete",
        ),
        # incomplete variation (entry missing values)
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {"a": [["-a"], []]},
            },
            "Recipe variation 'a' is incomplete",
        ),
        # invalid variation name
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {"B@D!": [["-a"]]},
            },
            "Recipe variation name 'B@D!' is invalid",
        ),
        # invalid variation type
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {"a": {"A": ["-a"]}},
            },
            "Recipe variation 'a' is invalid",
        ),
        # invalid variation type
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {"a": [{"-a": None}]},
            },
            "Recipe variation 'a' is invalid",
        ),
        # variation invalid flags
        (
            {
                "base": {
                    "codec": "codec",
                    "container": "container",
                    "library": "library",
                    "medium": "audio",
                    "tool": "ffmpeg",
                    "default_flags": {},
                },
                "variation": {"a": [[1]]},
            },
            "Recipe variation 'a' has invalid flags",
        ),
        # invalid YAML
        (
            "{",
            "Invalid YAML file",
        ),
        # empty recipe file
        (
            "",
            "Recipe missing entry ",
        ),
    ],
)
def test_recipe_02(tmp_path, data, msg):
    """test Recipe() errors"""
    recipe_file = tmp_path / "recipe.yml"
    with recipe_file.open("w") as out_fp:
        if isinstance(data, dict):
            safe_dump(data, out_fp)
        else:
            out_fp.write(data)
    with raises(RecipeError, match=msg):
        Recipe(recipe_file)


def test_template_01(tmp_path):
    """test Template()"""
    template_file = tmp_path / "testfile"
    template_file.touch()
    template = Template("test_template", template_file)
    assert template.file == template_file
    assert template.name == "test_template"
    template.unlink()
    assert not template_file.is_file()


def test_corpus_generator_01(mocker, tmp_path):
    """test CorpusGenerator()"""

    class SimpleGenerator(CorpusGenerator):
        """Test Generator"""

        def generate(self):
            yield ("test", ["arg1", "arg2"])

    recipe = mocker.Mock(
        spec_set=Recipe,
        codec="h264",
        container="mp4",
        library="libx264",
        medium="video",
    )
    generator = SimpleGenerator(recipe, tmp_path)
    generator.add_template(mocker.Mock(spec_set=Template))
    assert generator.description == "video/libx264/h264/mp4"
    all(generator.generate())


@mark.parametrize(
    "resolution, result",
    [
        ("123x234", True),
        ("", False),
        ("1", False),
        ("0x1", False),
        ("1x1x1", False),
        ("-1x19", False),
        ("foo", False),
    ],
)
def test_is_resolution_01(resolution, result):
    """test is_resolution()"""
    assert is_resolution(resolution) == result


def test_run_tool_01(mocker, tmp_path):
    """test run_tool()"""
    run = mocker.patch("corpus_replicator.common.run", autospec=True)
    log = tmp_path / "log.txt"
    mocker.patch("corpus_replicator.common.TOOL_LOG", log)
    # success
    run_tool(["foo"])
    assert not log.is_file()
    # failure (check error log exists)
    run.side_effect = RuntimeError("foo")
    with raises(RuntimeError):
        run_tool(["foo"])
    assert log.is_file()


def test_list_recipes_01():
    """test list_recipes()"""
    recipes = list(list_recipes())
    assert recipes
    assert all(x.name.endswith(".yml") for x in recipes)
