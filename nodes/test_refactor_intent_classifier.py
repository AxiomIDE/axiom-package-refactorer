def test_refactor_intent_classifier_imports():
    import nodes.refactor_intent_classifier as m
    assert hasattr(m, "handle")
