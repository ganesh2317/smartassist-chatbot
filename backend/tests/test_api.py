import io
import zipfile

from app.chatbot import BotResult, find_predefined_response
import app.main as main_module


def test_health_reports_database_and_ai_state(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['database'] == 'ok'
    assert response.json()['ai_configured'] is False
    assert response.json()['version'] == '3.0.0'
    assert response.headers['x-content-type-options'] == 'nosniff'


def test_register_login_and_me(client):
    created = client.post('/auth/register', json={'username': 'Alice', 'password': 'password123'})
    assert created.status_code == 200
    assert created.json()['username'] == 'alice'
    login = client.post('/auth/login', json={'username': 'alice', 'password': 'password123'})
    assert login.status_code == 200
    token = login.json()['access_token']
    me = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me.status_code == 200
    assert me.json() == {'username': 'alice'}


def test_predefined_greeting(client, auth_headers):
    response = client.post('/chat', json={'message': 'Hello'}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()['source'] == 'predefined'
    assert response.json()['sources'] == []


def test_broad_keyword_does_not_hijack_question():
    assert find_predefined_response('What time is it in Japan?') is None
    assert find_predefined_response('Help me understand neural networks') is None
    assert find_predefined_response('What is a contact lens?') is None


def test_ai_fallback_has_correct_source(client, auth_headers):
    response = client.post('/chat', json={'message': 'Explain neural networks'}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()['source'] == 'fallback'


def test_conversation_history_is_passed_to_model(client, auth_headers, monkeypatch):
    seen_histories = []

    async def fake_process(message, history, knowledge):
        seen_histories.append(list(history))
        return BotResult(f'reply:{message}', 'ai')

    monkeypatch.setattr(main_module, 'process_message', fake_process)
    first = client.post('/chat', json={'message': 'My favorite color is blue'}, headers=auth_headers)
    cid = first.json()['conversation_id']
    second = client.post('/chat', json={'message': 'What is my favorite color?', 'conversation_id': cid}, headers=auth_headers)
    assert second.status_code == 200
    assert seen_histories[0] == []
    assert [item['role'] for item in seen_histories[1]] == ['user', 'bot']
    assert seen_histories[1][0]['content'] == 'My favorite color is blue'


def test_conversation_ownership(client, auth_headers):
    first = client.post('/chat', json={'message': 'Hello'}, headers=auth_headers)
    cid = first.json()['conversation_id']
    other = client.post('/auth/register', json={'username': 'bob', 'password': 'password123'})
    other_headers = {'Authorization': f"Bearer {other.json()['access_token']}"}
    denied = client.get(f'/conversations/{cid}', headers=other_headers)
    assert denied.status_code == 404


def test_message_size_is_limited(client, auth_headers):
    response = client.post('/chat', json={'message': 'x' * 8001}, headers=auth_headers)
    assert response.status_code == 422


def test_new_chat_not_persisted_until_message(client, auth_headers):
    assert client.get('/conversations', headers=auth_headers).json() == []
    sent = client.post('/chat', json={'message': 'Hello'}, headers=auth_headers)
    assert sent.status_code == 200
    assert len(client.get('/conversations', headers=auth_headers).json()) == 1


def test_upload_list_and_delete_text_document(client, auth_headers):
    uploaded = client.post(
        '/documents', headers=auth_headers,
        files={'file': ('policy.txt', b'Annual leave is 24 days. Remote work is allowed on Fridays.', 'text/plain')},
    )
    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body['name'] == 'policy.txt'
    assert body['chunk_count'] >= 1
    listed = client.get('/documents', headers=auth_headers)
    assert listed.status_code == 200
    assert [item['name'] for item in listed.json()] == ['policy.txt']
    deleted = client.delete(f"/documents/{body['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert client.get('/documents', headers=auth_headers).json() == []


def test_docx_upload_extracts_text(client, auth_headers):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>SmartAssist DOCX knowledge works.</w:t></w:r></w:p></w:body></w:document>')
    uploaded = client.post('/documents', headers=auth_headers, files={'file': ('notes.docx', buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
    assert uploaded.status_code == 201
    assert uploaded.json()['char_count'] > 10


def test_unsupported_document_type_is_rejected(client, auth_headers):
    response = client.post('/documents', headers=auth_headers, files={'file': ('virus.exe', b'not really exe', 'application/octet-stream')})
    assert response.status_code == 422
    assert 'Unsupported file type' in response.json()['detail']


def test_document_ownership(client, auth_headers):
    uploaded = client.post('/documents', headers=auth_headers, files={'file': ('private.txt', b'my private knowledge', 'text/plain')})
    doc_id = uploaded.json()['id']
    other = client.post('/auth/register', json={'username': 'bob', 'password': 'password123'})
    other_headers = {'Authorization': f"Bearer {other.json()['access_token']}"}
    assert client.delete(f'/documents/{doc_id}', headers=other_headers).status_code == 404
    assert len(client.get('/documents', headers=auth_headers).json()) == 1


def test_relevant_uploaded_knowledge_is_passed_to_chat(client, auth_headers, monkeypatch):
    client.post('/documents', headers=auth_headers, files={'file': ('handbook.txt', b'The launch code name is Blue Comet. The launch date is October 12.', 'text/plain')})
    seen = {}

    async def fake_process(message, history, knowledge):
        seen['knowledge'] = knowledge
        return BotResult('The code name is Blue Comet [handbook.txt].', 'rag' if knowledge else 'ai')

    monkeypatch.setattr(main_module, 'process_message', fake_process)
    response = client.post('/chat', json={'message': 'What is the launch code name?'}, headers=auth_headers)
    assert response.status_code == 200
    assert seen['knowledge']
    assert seen['knowledge'][0]['name'] == 'handbook.txt'
    assert response.json()['source'] == 'rag'
    assert response.json()['sources'][0]['name'] == 'handbook.txt'
