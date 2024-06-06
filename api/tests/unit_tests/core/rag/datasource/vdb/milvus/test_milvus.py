import pytest
from pydantic.error_wrappers import ValidationError

from core.rag.datasource.vdb.milvus.milvus_vector import MilvusConfig


def test_default_value():
    valid_config = {
        'host': 'localhost',
        'port': 19530,
        'user': 'root',
        'password': 'Milvus'
    }

    for key in valid_config:
        config = valid_config.copy()
        del config[key]
        with pytest.raises(ValidationError) as e:
            MilvusConfig(**config)
        assert e.value.errors()[1]['msg'] == f'config MILVUS_{key.upper()} is required'

    config = MilvusConfig(**valid_config)
    assert config.secure is False
    assert config.database == 'default'
