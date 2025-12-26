from powertrack_sdk import auth


def test_auth_manager_get_auth_headers():
    am = auth.AuthManager(cookie='cookie123', ae_s='aes-value', ae_v='0001', base_url='https://example.com')
    headers = am.get_auth_headers(referer='https://ref.example')
    assert headers['cookie'] == 'cookie123'
    assert headers['ae_s'] == 'aes-value'
    assert headers['ae_v'] == '0001'
    assert headers['Referer'] == 'https://ref.example'


def test_auth_manager_base_url():
    am = auth.AuthManager(cookie='c', ae_s='s', base_url='https://api.test')
    assert am.get_base_url() == 'https://api.test'
