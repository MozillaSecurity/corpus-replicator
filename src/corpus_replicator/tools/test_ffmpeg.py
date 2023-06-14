# type: ignore
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from ..common import Recipe, Template
from .ffmpeg import FFmpegGenerator, ffmpeg_available

SAMPLE_VIDEO_RECIPE = """
base:
  codec: "h264"
  container: "mp4"
  library: "libx264"
  medium: "video"
  tool: "ffmpeg"
  default_flags:
    param:
      ["overwrite-me"]

variation:
  param:
  - ["flags-1"]
  - ["flags-2"]
"""


def test_ffmpeg_available_01(mocker):
    """test ffmpeg_available()"""
    which = mocker.patch("corpus_replicator.tools.ffmpeg.which", autospec=True)
    which.return_value = True
    assert ffmpeg_available()
    which.return_value = None
    assert not ffmpeg_available()


def test_ffmpeg_generator_01(mocker, tmp_path):
    """test FFmpegGenerator()"""
    mocker.patch("corpus_replicator.tools.ffmpeg.run_tool", autospec=True)

    recipe_file = tmp_path / "recipe.yml"
    recipe_file.write_text(SAMPLE_VIDEO_RECIPE)

    template_file = tmp_path / "template.bin"
    template_file.touch()

    generator = FFmpegGenerator(Recipe(recipe_file), tmp_path / "output")
    generator.add_template(Template("template01", template_file))
    generator.add_template(Template("template02", template_file))

    corpus = list(x.name for x in generator.generate())
    assert len(corpus) == 4
    assert "video-h264-libx264-template01-param-00.mp4" in corpus
    assert "video-h264-libx264-template01-param-01.mp4" in corpus
    assert "video-h264-libx264-template02-param-00.mp4" in corpus
    assert "video-h264-libx264-template02-param-01.mp4" in corpus
