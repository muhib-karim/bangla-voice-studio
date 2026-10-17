from bvs.asr.script import DEVANAGARI_WARNING, bangla_script_warnings, script_counts


def test_counts_each_script() -> None:
    assert script_counts("আমি") == (3, 0)
    assert script_counts("आमी") == (0, 3)
    assert script_counts("hello, world") == (0, 0)


def test_warns_on_devanagari_for_bangla() -> None:
    assert bangla_script_warnings("आमी बाँनाई कोता बोली", "bn") == (DEVANAGARI_WARNING,)


def test_no_warning_for_bengali_script() -> None:
    assert bangla_script_warnings("আমি বাংলায় কথা বলি।", "bn") == ()


def test_no_warning_for_other_languages_or_empty() -> None:
    assert bangla_script_warnings("आमी", "en") == ()
    assert bangla_script_warnings("आमी", None) == ()
    assert bangla_script_warnings("", "bn") == ()
