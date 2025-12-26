import pytest
from pathlib import Path

from powertrack_sdk import utils


def test_camel_to_snake_basic():
    assert utils.camel_to_snake('camelCase') == 'camel_case'
    assert utils.camel_to_snake('HTTPServerError') == 'http_server_error'
    assert utils.camel_to_snake('') == ''


def test_convert_keys_to_snake_case_recursive():
    data = {'firstName': 'Alice', 'nestedList': [{'lastName': 'Two'}], 'inner': {'InnerKey': 1}}
    converted = utils.convert_keys_to_snake_case(data)
    assert 'first_name' in converted
    assert isinstance(converted['nested_list'], list)
    assert converted['nested_list'][0]['last_name'] == 'Two'
    assert converted['inner']['inner_key'] == 1


def test_parse_site_id():
    assert utils.parse_site_id('60308') == 'S60308'
    assert utils.parse_site_id('S60308') == 'S60308'
    with pytest.raises(ValueError):
        utils.parse_site_id('S123')


def test_parse_hardware_id():
    assert utils.parse_hardware_id('123456') == 'H123456'
    assert utils.parse_hardware_id('H123456') == 'H123456'
    with pytest.raises(ValueError):
        utils.parse_hardware_id('ABC')


def test_get_hardware_type_name():
    assert utils.get_hardware_type_name(1).startswith('Inverter')
    assert utils.get_hardware_type_name(None) == 'Unknown'
    assert utils.get_hardware_type_name(999) == 'Type 999'


def test_flatten_dict_and_list():
    data = {'a': {'b': 1}, 'list': [1, 2, 3]}
    flat = utils.flatten_dict(data)
    assert flat['a_b'] == 1
    assert flat['list'] == '1, 2, 3'


def test_safe_get():
    data = {'a': {'b': {'c': 5}}}
    assert utils.safe_get(data, 'a.b.c') == 5
    assert utils.safe_get(data, 'a.b.x', default=0) == 0


def test_validate_site_list_and_normalization():
    src = [{'key': '60308', 'name': 'Site A'}, {'key': 'S70000', 'extra': 'meta'}]
    normalized = utils.validate_site_list(src)
    assert normalized[0]['key'] == 'S60308'
    assert normalized[1]['key'] == 'S70000'

    with pytest.raises(ValueError):
        utils.validate_site_list('not a list')
    with pytest.raises(ValueError):
        utils.validate_site_list([123])


def test_deep_merge_dicts_merge_by_key():
    base = {
        'hardware': [
            {'hardwareKey': 'H1', 'name': 'A', 'value': 1},
            {'hardwareKey': 'H2', 'name': 'B', 'value': 2},
        ],
        'other': {'x': 1}
    }
    updates = {
        'hardware': [
            {'hardwareKey': 'H2', 'value': 20},
            {'hardwareKey': 'H3', 'value': 3},
        ],
        'other': {'y': 2}
    }

    merged = utils.deep_merge_dicts(base, updates, key_field='hardwareKey')
    keys = {item['hardwareKey'] for item in merged['hardware']}
    assert keys == {'H1', 'H2', 'H3'}
    # H2 should have merged value
    h2 = next(item for item in merged['hardware'] if item['hardwareKey'] == 'H2')
    assert h2['value'] == 20
    assert merged['other']['x'] == 1 and merged['other']['y'] == 2
