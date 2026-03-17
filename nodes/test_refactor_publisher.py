from nodes.refactor_publisher import refactor_publisher


def test_refactor_publisher_imports():
    assert callable(refactor_publisher)

def test_bump_version():
    from nodes.refactor_publisher import _bump_version
    assert _bump_version("0.1.0") == "0.1.1"
    assert _bump_version("1.2.3") == "1.2.4"
