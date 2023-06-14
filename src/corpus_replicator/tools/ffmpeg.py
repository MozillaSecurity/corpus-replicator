# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from pathlib import Path
from shutil import which
from typing import Iterator

from ..common import CorpusGenerator, run_tool

FFMPEG_BIN = "ffmpeg"


class FFmpegGenerator(CorpusGenerator):
    """FFmpeg wrapper."""

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
            base_cmd = [FFMPEG_BIN, "-i", str(template.file), "-y"]
            for flag, idx, variation in self._recipe:
                # build dest file name 'video-h264-library-noise-resolution-##.mp4'
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


def ffmpeg_available() -> bool:
    """Check FFmpeg if is installed.

    Args:
        None

    Return:
        True if FFmpeg installed otherwise False.
    """
    # TODO: check version and flags for available features?
    return which(FFMPEG_BIN) is not None
