# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from argparse import ArgumentParser, Namespace
from logging import DEBUG, INFO, getLogger
from pathlib import Path
from typing import List, Optional

from .common import CorpusGenerator, Recipe, Template, ToolError, init_logging
from .tools.ffmpeg import FFmpegGenerator, ffmpeg_available
from .tools.imagemagick import ImageMagickGenerator, imagemagick_available

LOG = getLogger(__name__)


def load_generator(recipe: Recipe, dest: Path) -> CorpusGenerator:
    """Load a specific generator to use to create the corpus.

    Args:
        recipe: Recipe to use to generate corpus.
        dest: Location to place generated corpus.

    Returns:
        A corpus generator.
    """
    generator: Optional[CorpusGenerator] = None
    if recipe.tool == "ffmpeg":
        if not ffmpeg_available():
            raise ToolError("FFmpeg is not available")
        generator = FFmpegGenerator(recipe, dest)
    elif recipe.tool == "imagemagick":
        if not imagemagick_available():
            raise ToolError("ImageMagick is not available")
        generator = ImageMagickGenerator(recipe, dest)
    else:
        raise ToolError(f"Unsupported tool {recipe.tool!r}")
    assert generator is not None
    return generator


def main(argv: Optional[List[str]] = None) -> None:
    """Main function"""
    args = parse_args(argv)
    init_logging(args.log_level)

    generator = load_generator(Recipe(args.recipe), args.output)
    generator.add_template(Template(args.template_name, args.template_file))
    args.output.mkdir(parents=True, exist_ok=True)
    generator.generate()


def parse_args(argv: Optional[List[str]] = None) -> Namespace:
    """Argument parsing"""
    parser = ArgumentParser(
        description="Generate a corpus from a recipe and template file."
    )
    parser.add_argument("recipe", type=Path, help="Recipe file.")
    parser.add_argument("template_file", type=Path, help="File to use as template.")
    parser.add_argument(
        "--log-level",
        choices=sorted({"INFO": INFO, "DEBUG": DEBUG}),
        default="INFO",
        help="Configure console logging (default: %(default)s).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=Path.cwd() / "generated-corpus",
        type=Path,
        help="Output destination (default: %(default)s).",
    )
    parser.add_argument(
        "-n",
        "--template-name",
        default="custom",
        help="Template name used when naming generated files (default: %(default)s).",
    )

    args = parser.parse_args(argv)

    if not args.recipe.is_file():
        parser.error(f"Recipe file does not exist: '{args.recipe}'")

    if not args.template_file.is_file():
        parser.error(f"Template file does not exist: '{args.template_file}'")

    return args


if __name__ == "__main__":  # pragma: no cover
    main()
