from nodes.refactor_intent_classifier import refactor_intent_classifier


def test_refactor_intent_classifier_imports():
    assert callable(refactor_intent_classifier)
