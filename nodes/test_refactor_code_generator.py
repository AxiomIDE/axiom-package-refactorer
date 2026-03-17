from nodes.refactor_code_generator import refactor_code_generator


def test_refactor_code_generator_imports():
    assert callable(refactor_code_generator)
