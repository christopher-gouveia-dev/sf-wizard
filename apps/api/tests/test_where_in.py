from sf_wizard.domain.where_in import chunk_values

def test_chunk_values_basic():
    values = [str(i) for i in range(100)]
    chunks = chunk_values(values, max_chars=50)
    assert len(chunks) > 1
    assert sum(len(c) for c in chunks) == 100
