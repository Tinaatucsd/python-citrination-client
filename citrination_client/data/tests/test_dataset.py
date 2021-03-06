from citrination_client.data import Dataset

def test_can_crud_name():
    """
    Tests that full get/set/delete functionality is
    available for the name property
    """
    d =  Dataset(1)
    name = "name"
    assert d.name is None
    d.name = name
    assert d.name is name
    del(d.name)
    assert d.name is None

def test_can_crud_description():
    """
    Tests that full get/set/delete functionality is
    available for the description property
    """
    d =  Dataset(1)
    description = "description"
    assert d.description is None
    d.description = description
    assert d.description is description
    del(d.description)
    assert d.description is None

def test_can_crud_created_at():
    """
    Tests that full get/set/delete functionality is
    available for the created_at property
    """
    d =  Dataset(1)
    created_at = "created_at"
    assert d.created_at is None
    d.created_at = created_at
    assert d.created_at is created_at
    del(d.created_at)
    assert d.created_at is None