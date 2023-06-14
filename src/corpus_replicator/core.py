# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from argparse import ArgumentParser, Namespace
from filecmp import cmp
from importlib.metadata import PackageNotFoundError, version
from itertools import product
from logging import DEBUG, INFO, getLogger
from pathlib import Path
from typing import Iterable, List, Optional

from .common import (
    SUPPORTED_MEDIUM,
    TOOL_LOG,
    Recipe,
    RecipeError,
    Template,
    init_logging,
    is_resolution,
    list_recipes,
)
from .generate_corpus import load_generator
from .generate_template import TEMPLATES, generate_audio, generate_image, generate_video
from .tools.ffmpeg import ffmpeg_available

try:
    __version__ = version("corpus-replicator")
except PackageNotFoundError:  # pragma: no cover
    # package is not installed
    __version__ = "unknown"

LOG = getLogger(__name__)


class Replicator:
    """Replicator can generate a corpus from recipes and templates."""

    __slots__ = ("dest", "medium", "recipes", "templates")

    def __init__(self, medium: str, dest: Path, recipes: Iterable[Path]) -> None:
        assert medium in SUPPORTED_MEDIUM
        self.dest = dest
        self.medium = medium
        self.recipes: List[Recipe] = []
        self.templates: List[Template] = []

        # load recipe files
        for recipe_file in set(recipes):
            recipe = Recipe(recipe_file)
            if self.medium == recipe.medium:
                self.recipes.append(recipe)
            else:
                LOG.warning(
                    "'%s' is incompatible with recipe '%s'", self.medium, recipe_file
                )
                LOG.info("Skipping '%s'", recipe_file)

    def __len__(self) -> int:
        return sum(len(x) for x in self.recipes) * len(self.templates)

    def generate_corpus(self) -> None:
        """Generate a corpus from recipes and templates.

        Args:
            None

        Returns:
            None
        """
        for recipe, template in product(self.recipes, self.templates):
            generator = load_generator(recipe, self.dest)
            assert generator is not None
            generator.add_template(template)

            LOG.info(
                "Generating %d '%s' file(s) using template '%s'...",
                len(recipe),
                generator.description,
                template.name,
            )
            all(generator.generate())

    def generate_templates(
        self,
        template_names: Iterable[str],
        duration: float = 1.0,
        frames: int = 0,
        resolution: str = "1280x768",
    ) -> None:
        """Generate template files.

        Args:
            template_names: Name of template.
            duration: Runtime of generated content.
            resolution: Resolution of generated content.

        Returns:
            None
        """
        # TODO: add crop or scale option for templates
        unique_templates = set(template_names)
        self.dest.mkdir(parents=True, exist_ok=True)
        LOG.debug(
            "generating %d '%s' template(s)...", len(unique_templates), self.medium
        )
        for template in unique_templates:
            if self.medium == "audio":
                generated = generate_audio(template, self.dest, duration=duration)
            elif self.medium == "image":
                generated = generate_image(template, self.dest, resolution=resolution)
            elif self.medium in ("animation", "video"):
                generated = generate_video(
                    template,
                    self.dest,
                    duration=duration,
                    frames=frames,
                    resolution=resolution,
                )
            self.templates.append(generated)
        LOG.debug(
            "generated template(s): %s", ", ".join(str(x.file) for x in self.templates)
        )

    def remove_duplicates(self) -> None:
        """Remove duplicate generated corpus files.

        Args:
            None

        Returns:
            None
        """
        removed = set()
        for file_1, file_2 in product(sorted(self.dest.iterdir()), self.dest.iterdir()):
            if file_1 in removed or file_2 in removed or file_1.samefile(file_2):
                continue
            if cmp(file_1, file_2, shallow=False):
                LOG.debug("'%s' matches '%s'", file_1.name, file_2.name)
                file_2.unlink()
                removed.add(file_2)
        LOG.debug("removed %d duplicate(s)", len(removed))

    def remove_templates(self) -> None:
        """Remove template files.

        Args:
            None

        Returns:
            None
        """
        for template in self.templates:
            template.unlink()


def parse_args(argv: Optional[List[str]] = None) -> Namespace:
    """Argument parsing"""
    parser = ArgumentParser(description="Generate a corpus.", prog="corpus-replicator")
    recipes = {x.name: x for x in list_recipes()}
    # common args
    parser.add_argument(
        "recipes",
        nargs="+",
        type=Path,
        help=f"Recipe files to use. Built-in recipes: {', '.join(sorted(recipes))}",
    )
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
        help="Output destination (default: '%(default)s').",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version number.",
    )
    subparsers = parser.add_subparsers(
        dest="medium", required=True, help="Type of files to generate."
    )

    # animation args
    animation = subparsers.add_parser("animation")
    animation.set_defaults(duration=0)
    animation.add_argument(
        "--frames",
        default=5,
        type=int,
        help="Number of frames (default: %(default)s).",
    )
    animation.add_argument(
        "-r",
        "--resolution",
        default="1280x768",
        help="Resolution (default: '%(default)s').",
    )
    animation.add_argument(
        "-t",
        "--templates",
        default=["all"],
        choices=["all"] + list(TEMPLATES["video"]),
        nargs="+",
        help="Template to use (default: all).",
    )
    # audio args
    audio = subparsers.add_parser("audio")
    audio.set_defaults(frames=0, resolution=None)
    audio.add_argument(
        "-d",
        "--duration",
        default=1.0,
        type=float,
        help="Runtime in seconds (default: %(default)ss).",
    )
    audio.add_argument(
        "-t",
        "--templates",
        default=["all"],
        choices=["all"] + list(TEMPLATES["audio"]),
        nargs="+",
        help="Template to use (default: all).",
    )
    # image args
    image = subparsers.add_parser("image")
    image.set_defaults(frames=0, duration=None)
    image.add_argument(
        "-r",
        "--resolution",
        default="1280x768",
        help="Resolution (default: '%(default)s').",
    )
    image.add_argument(
        "-t",
        "--templates",
        default=["all"],
        choices=["all"] + list(TEMPLATES["image"]),
        nargs="+",
        help="Template to use (default: all).",
    )
    # video args
    video = subparsers.add_parser("video")
    video.set_defaults(frames=None)
    video.add_argument(
        "-d",
        "--duration",
        default=1.0,
        type=float,
        help="Runtime in seconds (default: %(default)ss).",
    )
    video.add_argument(
        "--frames",
        default=0,
        type=int,
        help="Number of frames. Use 0 for no limit. (default: %(default)s).",
    )
    video.add_argument(
        "-r",
        "--resolution",
        default="1280x768",
        help="Resolution (default: '%(default)s').",
    )
    video.add_argument(
        "-t",
        "--templates",
        default=["all"],
        choices=["all"] + list(TEMPLATES["video"]),
        nargs="+",
        help="Template to use (default: all).",
    )

    if not ffmpeg_available():
        parser.error("Please install FFmpeg.")

    args = parser.parse_args(argv)

    # look up built-in recipes
    checked_recipes = []
    for recipe in args.recipes:
        if str(recipe) in recipes:
            checked_recipes.append(recipes[str(recipe)])
        elif not recipe.is_file():
            parser.error(f"Recipe file does not exist: '{recipe}'")
        else:
            checked_recipes.append(recipe)
    args.recipes = checked_recipes

    if args.resolution and not is_resolution(args.resolution):
        parser.error(f"argument -r/--resolution: invalid value: {args.resolution!r}")

    # handle 'all' in templates
    if "all" in args.templates:
        # animation shares templates with video
        args.templates = TEMPLATES[
            "video" if args.medium == "animation" else args.medium
        ]

    return args


def main(argv: Optional[List[str]] = None) -> None:
    """Main function"""
    args = parse_args(argv)
    init_logging(args.log_level)

    try:
        replicator = Replicator(args.medium, args.output, args.recipes)
    except RecipeError as exc:
        LOG.error("Error: %s.", exc)
        return

    try:
        LOG.info("Generating templates...")
        replicator.generate_templates(
            args.templates,
            duration=args.duration,
            resolution=args.resolution,
            frames=args.frames,
        )
        LOG.info(
            "%d recipe(s) will be used with %d template(s) to create %d file(s).",
            len(replicator.recipes),
            len(replicator.templates),
            len(replicator),
        )
        replicator.generate_corpus()
        replicator.remove_templates()

        LOG.info("Optimizing corpus, checking for duplicates...")
        replicator.remove_duplicates()

    except KeyboardInterrupt:
        LOG.warning("Aborting...")

    finally:
        tool_log = Path(TOOL_LOG)
        if tool_log.is_file():
            LOG.warning("A tool log is available '%s'.", tool_log.resolve())
        replicator.remove_templates()

    LOG.info("Done.")
