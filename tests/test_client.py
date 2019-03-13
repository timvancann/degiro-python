from degiro.client import DeGiro as victim


def test_account_id():
    assert victim._get_account_id({"intAccount": 666}) == 666
