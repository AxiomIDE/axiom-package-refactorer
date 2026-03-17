from nodes.source_fetcher import source_fetcher


def test_source_fetcher_imports():
    assert callable(source_fetcher)
