def test_refactor_code_generator_imports():
    import nodes.refactor_code_generator as m
    assert hasattr(m, "handle")
