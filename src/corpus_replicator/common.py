# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from abc import ABC, abstractmethod
from logging import DEBUG, basicConfig, getLogger
from pathlib import Path
from re import match
from subprocess import run
from typing import Any, Dict, Iterator, List, Tuple

from yaml import YAMLError, safe_load

LOG = getLogger(__name__)
SUPPORTED_MEDIUM = ("animation", "audio", "image", "video")
SUPPORTED_TOOLS = ("ffmpeg", "imagemagick")
TOOL_LOG: str = "replicator-tool-log.txt"


class RecipeError(Exception):
    """Recipe related errors."""


class ToolError(Exception):
    """Tool related errors."""


class Recipe:
    """A Recipe contains details about how to generate content using tools.
    It stores flags and variations that used to create a corpus based on a template."""

    __slots__ = (
        "_flags",
        "_variations",
        "codec",
        "container",
        "library",
        "medium",
        "tool",
    )

    def __init__(self, file: Path) -> None:  # pylint: disable=too-many-branches
        LOG.debug("loading recipe '%s'", file)
        # load data from yml file
        try:
            data: Dict[str, Any] = safe_load(file.read_text()) or {}
        except (UnicodeDecodeError, YAMLError):
            raise RecipeError("Invalid YAML file") from None

        try:
            self._flags: Dict[str, Any] = data["base"]["default_flags"] or {}
            self._variations: Dict[str, Any] = data["variation"] or {}
            # codec
            self.codec: str = data["base"]["codec"]
            # container type
            self.container: str = data["base"]["container"]
            # encoder library
            self.library: str = data["base"]["library"]
            # content medium
            self.medium: str = data["base"]["medium"]
            # binary tool
            self.tool: str = data["base"]["tool"]
        except KeyError as exc:
            raise RecipeError(f"Recipe missing entry {exc}") from None

        # validate "base" entries
        for key, entry in data["base"].items():
            if key == "default_flags":
                if not isinstance(entry, dict):
                    raise RecipeError("Recipe 'default_flags' is invalid")
                for group, flags in entry.items():
                    if not flags:
                        raise RecipeError(
                            f"Recipe 'default_flags' '{group}' is incomplete"
                        )
                    # all flags must be strings
                    if not all(isinstance(x, str) for x in flags):
                        raise RecipeError(
                            f"Recipe 'default_flags' '{group}' has invalid flags"
                        )
            # check required properties are strings (must be filesystem safe)
            elif not isinstance(entry, str) or not match(r"^[a-zA-Z0-9-]+$", entry):
                raise RecipeError(f"Recipe '{key}' entry is invalid")

        # validate variations
        if not self._variations:
            raise RecipeError("Recipe missing variations")
        for key, entry in self._variations.items():
            # validate "variation" flag group names (must be filesystem safe)
            if not match(r"^[a-zA-Z0-9-]+$", key):
                raise RecipeError(f"Recipe variation name '{key}' is invalid")
            # each "variation" entry must have a flag group with entries
            if not entry:
                raise RecipeError(f"Recipe variation '{key}' is incomplete")
            if not isinstance(entry, list):
                raise RecipeError(f"Recipe variation '{key}' is invalid")
            for flags in entry:
                if not flags:
                    raise RecipeError(f"Recipe variation '{key}' is incomplete")
                if not isinstance(flags, list):
                    raise RecipeError(f"Recipe variation '{key}' is invalid")
                # all flags must be strings
                if not all(isinstance(x, str) for x in flags):
                    raise RecipeError(f"Recipe variation '{key}' has invalid flags")

        if self.medium not in SUPPORTED_MEDIUM:
            raise RecipeError(f"Recipe medium '{self.medium}' unsupported")

        if self.tool not in SUPPORTED_TOOLS:
            raise RecipeError(f"Recipe tool '{self.tool}' unsupported")

    def __iter__(self) -> Iterator[Tuple[str, int, List[str]]]:
        for flag_group, variations in self._variations.items():
            # add default flags
            base_flags = []
            for default_group, default_flags in self._flags.items():
                if default_group != flag_group:
                    base_flags.extend(default_flags)
            # iterate over variations and build commands
            for idx, flags in enumerate(variations):
                yield flag_group, idx, base_flags + flags

    def __len__(self) -> int:
        return sum(True for _ in self)


class Template:
    """A Template contains input data details."""

    __slots__ = ("file", "name")

    def __init__(self, name: str, file: Path) -> None:
        assert file
        assert name
        self.file = file
        self.name = name

    def unlink(self) -> None:
        """Remove template file from filesystem.

        Args:
            None

        Returns:
            None
        """
        LOG.debug("removing template '%s'", self.file)
        self.file.unlink(missing_ok=True)


class CorpusGenerator(ABC):
    """Tool wrapper base class."""

    __slots__ = ("_dest", "_recipe", "_templates")

    def __init__(self, recipe: Recipe, dest: Path) -> None:
        self._dest = dest
        self._recipe = recipe
        self._templates: List[Template] = []

    def add_template(self, template: Template) -> None:
        """Add a Template to the Generator.

        Args:
            template: A template object.

        Returns:
            None
        """
        self._templates.append(template)

    @abstractmethod
    def generate(self) -> Iterator[Path]:
        """Generate corpus files."""

    @property
    def description(self) -> str:
        """Create a description based on the recipe.

        Args:
            None

        Returns:
            Descriptive string.
        """
        return "/".join(
            [
                self._recipe.medium,
                self._recipe.library,
                self._recipe.codec,
                self._recipe.container,
            ]
        )


def init_logging(level: int) -> None:
    """Initialize logging

    Arguments:
        level: logging verbosity level

    Returns:
        None
    """
    if level == DEBUG:
        date_fmt = None
        log_fmt = "%(asctime)s %(levelname).1s %(name)s | %(message)s"
    else:
        date_fmt = "%H:%M:%S"
        log_fmt = "[%(asctime)s] %(message)s"
    basicConfig(format=log_fmt, datefmt=date_fmt, level=level)


def is_resolution(in_res: str) -> bool:
    """Determine whether provided string is a valid resolution.

    Arguments:
        in_res: string to evaluate.

    Returns:
        True is provided string is a valid resolution otherwise False.
    """
    try:
        x_res, y_res = in_res.lower().split("x")
        if int(x_res) > 0 and int(y_res) > 0:
            return True
    except ValueError:
        pass
    return False


def list_recipes() -> Iterator[Path]:
    """List built-in Recipe files.

    Args:
        None

    Yields:
        Recipes files.
    """
    path = Path(__file__).parent.resolve() / "recipes"
    if path.is_dir():
        for recipe in path.iterdir():
            if recipe.suffix.lower().endswith(".yml"):
                yield recipe


def run_tool(cmd: List[str]) -> None:
    """Wrapper for subprocess.run.

    Arguments:
        cmd: command to pass to run.

    Returns:
        None
    """
    log_file = Path(TOOL_LOG)
    with log_file.open("wb") as log_fp:
        LOG.debug("running '%s'", " ".join(cmd))
        # use a timeout in case (frame or time) limit flags are forgotten
        # typically this should finish in a few seconds
        run(cmd, check=True, stderr=log_fp, stdout=log_fp, timeout=600)
    # on success we don't need the log so remove it
    log_file.unlink()
