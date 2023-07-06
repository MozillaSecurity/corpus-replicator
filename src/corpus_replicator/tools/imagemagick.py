# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from pathlib import Path
from shutil import which
from typing import Iterator

from ..common import CorpusGenerator, run_tool

IMAGEMAGICK_BIN = "convert"


class ImageMagickGenerator(CorpusGenerator):
    """ImageMagick wrapper."""

    def generate(self) -> Iterator[Path]:
        """Generate corpus. Templates are combined with Recipes to create variations
        based on parameters defined in the Recipes.

        Args:
            recipe: Recipe to use to generate a corpus.
            dest: Location to place generated corpus.

        Yields:
            A corpus generator.
        """
        for template in self._templates:
            base_cmd = [IMAGEMAGICK_BIN, str(template.file)]
            for flag, idx, variation in self._recipe:
                # build dest file name 'img-jpeg-library-noise-resolution-##.mp4'
                dest_file = self._dest / "-".join(
                    [
                        self._recipe.medium,
                        self._recipe.codec,
                        self._recipe.library,
                        template.name,
                        flag,
                        f"{idx:02d}.{self._recipe.container}",
                    ]
                )
                run_tool(base_cmd + variation + [str(dest_file)])
                yield dest_file


def imagemagick_available() -> bool:
    """Check if ImageMagick is installed.

    Args:
        None

    Return:
        True if installed otherwise False.
    """
    # TODO: check version and flags for available features?
    return which(IMAGEMAGICK_BIN) is not None
