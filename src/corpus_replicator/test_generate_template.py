# type: ignore
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from pytest import mark, raises

from .generate_template import (
    TEMPLATES,
    generate_audio,
    generate_image,
    generate_video,
    main,
    parse_args,
)


@mark.parametrize("template_name", TEMPLATES["audio"])
def test_generate_audio_01(mocker, tmp_path, template_name):
    """test generate_audio()"""
    mocker.patch("corpus_replicator.generate_template.run_tool", autospec=True)
    template = generate_audio(template_name, tmp_path)
    assert template.name == template_name
    assert template.file.parent == tmp_path


@mark.parametrize("template_name", TEMPLATES["image"])
def test_generate_image_01(mocker, tmp_path, template_name):
    """test generate_image()"""
    mocker.patch("corpus_replicator.generate_template.run_tool", autospec=True)
    template = generate_image(template_name, tmp_path)
    assert template.name == template_name
    assert template.file.parent == tmp_path


@mark.parametrize("template_name", TEMPLATES["video"])
def test_generate_video_01(mocker, tmp_path, template_name):
    """test generate_video()"""
    mocker.patch("corpus_replicator.generate_template.run_tool", autospec=True)
    template = generate_video(template_name, tmp_path)
    assert template.name == template_name
    assert template.file.parent == tmp_path


@mark.parametrize(
    "duration, frames",
    [
        (2.1, 0),
        (1.0, 10),
    ],
)
def test_generate_video_02(mocker, tmp_path, duration, frames):
    """test generate_video()"""
    mocker.patch("corpus_replicator.generate_template.run_tool", autospec=True)
    generate_video("noise", tmp_path, duration=duration, frames=frames)


@mark.parametrize(
    "medium, template",
    [
        ("audio", "noise"),
        ("image", "noise"),
        ("video", "noise"),
    ],
)
def test_main_01(mocker, tmp_path, medium, template):
    """test main()"""
    mocker.patch("corpus_replicator.generate_template.ffmpeg_available", autospec=True)
    mocker.patch("corpus_replicator.generate_template.run_tool", autospec=True)
    main(["-o", str(tmp_path), medium, template])


def test_parse_args_01(mocker, capsys):
    """test parse_args()"""
    ffmpeg_check = mocker.patch(
        "corpus_replicator.generate_template.ffmpeg_available", autospec=True
    )
    # success
    parse_args(["audio", "noise"])
    # invalid resolution
    with raises(SystemExit):
        parse_args(["video", "noise", "-r", "foo"])
    assert "argument -r/--resolution: invalid value" in capsys.readouterr()[1]
    # missing ffmpeg
    ffmpeg_check.return_value = False
    with raises(SystemExit):
        parse_args(["audio", "noise"])
    assert "Please install FFmpeg." in capsys.readouterr()[1]
