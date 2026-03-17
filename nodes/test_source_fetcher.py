def test_source_fetcher_imports():
    import nodes.source_fetcher as m
    assert hasattr(m, "source_fetcher")
