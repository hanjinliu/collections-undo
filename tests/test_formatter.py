from collections_undo import fmt

def test_object_mapping():
    assert fmt.map_object(1) == "1"
    assert fmt.map_object("") == "''"
    assert fmt.map_object(None) == "None"
    assert fmt.map_object(()) == "()"
    assert fmt.map_object((1,)) == "(1,)"
    assert fmt.map_object([(), (1,), set()]) == "[(), (1,), set()]"
    assert fmt.map_object(True) == "True"
    assert fmt.map_object(1 - 3j) == "(1-3j)"
    assert fmt.map_object(bytes("a", encoding="utf-8")) == "b'a'"
    assert fmt.map_object({"a": [1, 2], "b": [0.1, 0.2]}) == "{'a': [1, 2], 'b': [0.1, 0.2]}"
    assert fmt.map_object(set()) == "set()"
    assert fmt.map_object({1, 2, 3}) == "{1, 2, 3}"
    assert fmt.map_object(frozenset()) == "frozenset([])"
    assert fmt.map_object(frozenset([1, 2])) == "frozenset([1, 2])"
