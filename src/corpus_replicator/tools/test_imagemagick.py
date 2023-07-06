# type: ignore
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from ..common import Recipe, Template
from .imagemagick import ImageMagickGenerator, imagemagick_available

SAMPLE_IMAGE_RECIPE = """
base:
  codec: "jpeg"
  container: "jpg"
  library: "imagemagick"
  medium: "image"
  tool: "imagemagick"
  default_flags:
    param:
      ["overwrite-me"]

variation:
  param:
  - ["flags-1"]
  - ["flags-2"]
"""


def test_imagemagick_available_01(mocker):
    """test imagemagick_available()"""
    which = mocker.patch("corpus_replicator.tools.imagemagick.which", autospec=True)
    which.return_value = True
    assert imagemagick_available()
    which.return_value = None
    assert not imagemagick_available()


def test_imagemagick_generator_01(mocker, tmp_path):
    """test ImagemagickGenerator()"""
    mocker.patch("corpus_replicator.tools.imagemagick.run_tool", autospec=True)

    recipe_file = tmp_path / "recipe.yml"
    recipe_file.write_text(SAMPLE_IMAGE_RECIPE)

    template_file = tmp_path / "template.bin"
    template_file.touch()

    generator = ImageMagickGenerator(Recipe(recipe_file), tmp_path / "output")
    generator.add_template(Template("template01", template_file))
    generator.add_template(Template("template02", template_file))

    corpus = list(x.name for x in generator.generate())
    assert len(corpus) == 4
    assert "image-jpeg-imagemagick-template01-param-00.jpg" in corpus
    assert "image-jpeg-imagemagick-template01-param-01.jpg" in corpus
    assert "image-jpeg-imagemagick-template02-param-00.jpg" in corpus
    assert "image-jpeg-imagemagick-template02-param-01.jpg" in corpus
