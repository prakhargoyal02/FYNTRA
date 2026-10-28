from unittest.mock import MagicMock, patch
import math
import pytest
from cloud_sync import Cloud, SyncConflict, _json_safe
from database import Store


def test_reject_server_secret_and_non_https():
    with pytest.raises(ValueError): Cloud('http://example.com','sb_publishable_example')
    with pytest.raises(ValueError): Cloud('https://example.com','sb_secret_example')


def test_conflict_does_not_advance_revision_or_change_local_data(tmp_path):
    store=Store(tmp_path/'local.db')
    before=store.dump_state()
    with patch('cloud_sync.create_client') as factory:
        cloud=Cloud('https://example.supabase.co','sb_publishable_example')
        cloud.user_id='test-owner'
        cloud.revision=4
        query=factory.return_value.table.return_value.update.return_value
        query.eq.return_value.eq.return_value.execute.return_value.data=[]
        with pytest.raises(SyncConflict): cloud.push(store)
        assert cloud.revision==4
        assert store.dump_state()==before
        assert query.eq.call_args.args==('user_id','test-owner')
        assert query.eq.return_value.eq.call_args.args==('revision',4)


def test_private_pull_validates_before_replacing(tmp_path):
    store=Store(tmp_path/'local.db')
    before=store.dump_state()
    with patch('cloud_sync.create_client') as factory:
        cloud=Cloud('https://example.supabase.co','sb_publishable_example')
        cloud.user_id='test-owner'
        factory.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value.data=[{'state':{'schema_version':999},'revision':9}]
        with pytest.raises(ValueError): cloud.pull(store)
        assert store.dump_state()==before


def test_json_safe_replaces_non_finite_values():
    cleaned=_json_safe({'balance':float('nan'),'nested':[1,float('inf'),float('-inf')]})
    assert cleaned=={'balance':None,'nested':[1,None,None]}
