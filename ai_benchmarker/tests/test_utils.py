from ai_benchmarker.utils import parse_subtitle_text


def test_parse_plain_text_unchanged():
    text = "سلام دنیا این یک متن ساده است"
    assert parse_subtitle_text(text, "ref.txt") == text


def test_parse_srt_extracts_spoken_text():
    srt = """1
00:00:01,000 --> 00:00:04,000
سلام دنیا

2
00:00:05,000 --> 00:00:08,000
این یک تست است
"""
    result = parse_subtitle_text(srt, "sample.srt")
    assert "سلام دنیا" in result
    assert "این یک تست است" in result
    assert "-->" not in result
    assert "00:00" not in result


def test_parse_vtt_skips_header():
    vtt = """WEBVTT

00:00:01.000 --> 00:00:04.000
متن زیرنویس
"""
    result = parse_subtitle_text(vtt, "sample.vtt")
    assert "متن زیرنویس" in result
    assert "WEBVTT" not in result
