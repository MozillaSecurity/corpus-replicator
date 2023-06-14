# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from argparse import ArgumentParser, Namespace
from logging import DEBUG, INFO, getLogger
from pathlib import Path
from typing import List, Optional

from .common import Template, init_logging, is_resolution, run_tool
from .tools.ffmpeg import FFMPEG_BIN, ffmpeg_available

LOG = getLogger(__name__)

TEMPLATES = {
    "audio": (
        "noise",
        "silence",
        "sine",
        "test",
    ),
    "image": (
        "noise",
        "solid",
        "test",
    ),
    "video": (
        "noise",
        "solid",
        "test",
    ),
}


def generate_audio(template: str, dest: Path, duration: float = 3.0) -> Template:
    """Generate audio template file.

    Args:
        template: Content to generate.
        dest: Location to create file.
        duration: Target playback duration.

    Returns:
        Template containing generated content information.
    """
    assert duration > 0
    assert template in TEMPLATES["audio"]
    cmd = [FFMPEG_BIN, "-y", "-f", "lavfi", "-i"]
    if template == "noise":
        cmd.append("anoisesrc=a=0.1:c=white")
    elif template == "silence":
        cmd.append("anullsrc")
    elif template == "sine":
        cmd.append("sine=frequency=880")
    elif template == "test":
        cmd.append("aevalsrc=sin(2*PI*(360-2.5/2)*t)|sin(2*PI*(360+2.5/2)*t)")
    cmd.extend(["-c:a", "pcm_s16le"])
    cmd.extend(["-t", f"{duration:0.0f}"])
    dst: Path = dest / f"template-audio-{template}.wav"
    cmd.append(str(dst))
    run_tool(cmd)
    return Template(template, dst)


def generate_image(template: str, dest: Path, resolution: str = "1280x768") -> Template:
    """Generate image template file.

    Args:
        template: Content to generate.
        dest: Location to create file.
        resolution: Target content resolution.

    Returns:
        Template containing generated content information.
    """
    assert template in TEMPLATES["image"]
    cmd = [FFMPEG_BIN, "-y", "-f", "lavfi", "-i"]
    if template == "noise":
        cmd.append(f"color=c=gray:s={resolution}, noise=alls=100:allf=t")
    elif template == "solid":
        cmd.append("color=c=red")
    elif template == "test":
        cmd.append(f"testsrc=s={resolution}")
    cmd.extend(["-frames", "1"])
    dst: Path = dest / f"template-image-{template}-{resolution}.png"
    cmd.append(str(dst))
    run_tool(cmd)
    return Template(template, dst)


def generate_video(
    template: str,
    dest: Path,
    duration: float = 2.0,
    frames: int = 0,
    resolution: str = "1280x768",
) -> Template:
    """Generate video template file.

    Args:
        template: Content to generate.
        dest: Location to create file.
        duration: Target playback duration.
        frames: Number of frames to generate.
        resolution: Target content resolution.

    Returns:
        Template containing generated content information.
    """
    assert duration > 0 or frames > 0
    assert template in TEMPLATES["video"]
    cmd = [FFMPEG_BIN, "-y", "-f", "lavfi", "-i"]
    if template == "noise":
        cmd.append(f"color=c=gray:s={resolution}, noise=alls=100:allf=t")
    elif template == "solid":
        cmd.append("color=c=red")
    elif template == "test":
        cmd.append(f"testsrc2=s={resolution}")
    cmd.extend(["-pix_fmt", "yuv420p"])
    cmd.extend(["-c:v", "libx264"])
    if frames > 0:
        cmd.extend(["-frames", str(frames)])
    else:
        cmd.extend(["-t", f"{duration:0.0f}"])
    cmd.extend(["-crf", "17"])
    dst: Path = dest / f"template-video-{template}-{resolution}.mp4"
    cmd.append(str(dst))
    run_tool(cmd)
    return Template(template, dst)


def main(argv: Optional[List[str]] = None) -> None:
    """Main function"""
    args = parse_args(argv)
    init_logging(args.log_level)

    args.output.mkdir(parents=True, exist_ok=True)
    if args.medium == "audio":
        output = generate_audio(args.template, args.output, duration=args.duration)
    elif args.medium == "image":
        output = generate_image(args.template, args.output, resolution=args.resolution)
    elif args.medium == "video":
        output = generate_video(
            args.template,
            args.output,
            duration=args.duration,
            frames=args.frames,
            resolution=args.resolution,
        )
    LOG.info("Created '%s'", output.file)


def parse_args(argv: Optional[List[str]] = None) -> Namespace:
    """Argument parsing"""
    parser = ArgumentParser(description="Generate a template file.")
    # common args
    parser.add_argument(
        "-o",
        "--output",
        default=Path.cwd(),
        type=Path,
        help="Output destination.",
    )
    parser.add_argument(
        "--log-level",
        choices=sorted({"INFO": INFO, "DEBUG": DEBUG}),
        default="INFO",
        help="Configure console logging (default: %(default)s).",
    )
    subparsers = parser.add_subparsers(dest="medium", required=True)
    # audio args
    audio = subparsers.add_parser("audio")
    audio.set_defaults(frames=0, resolution=None)
    audio.add_argument("template", choices=TEMPLATES["audio"])
    audio.add_argument(
        "-d", "--duration", default=2.0, type=float, help="Runtime in seconds."
    )
    # image args
    image = subparsers.add_parser("image")
    image.set_defaults(frames=0, duration=None)
    image.add_argument("template", choices=TEMPLATES["image"])
    image.add_argument("-r", "--resolution", default="1280x768")
    # video args
    video = subparsers.add_parser("video")
    video.add_argument("template", choices=TEMPLATES["video"])
    video.add_argument("--frames", type=int, default=0)
    video.add_argument(
        "-d", "--duration", default=2.0, type=float, help="Runtime in seconds."
    )
    video.add_argument("-r", "--resolution", default="1280x768")

    if not ffmpeg_available():
        parser.error("Please install FFmpeg.")

    args = parser.parse_args(argv)

    if args.resolution and not is_resolution(args.resolution):
        parser.error(f"argument -r/--resolution: invalid value: {args.resolution!r}")

    return args


if __name__ == "__main__":  # pragma: no cover
    main()
