"""
对话接口测试
"""
import pytest
from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


class TestChatAPI:

    def test_chat_missing_message(self, client):
        """测试缺少 message 参数"""
        response = client.post('/api/v1/chat', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 400

    def test_chat_success(self, client, mocker):
        """测试正常对话（Mock 模型）"""
        # Mock 模型调用
        mock_client = mocker.patch('app.services.chat_service.ModelService.get_model_client')
        mock_client.return_value.invoke.return_value = "这是一条测试回复"
        mock_client.return_value.get_model_name.return_value = "deepseek-chat"

        response = client.post('/api/v1/chat', json={
            'message': '你好',
            'model': 'deepseek',
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['code'] == 200
        assert 'answer' in data['data']
        assert 'conversation_id' in data['data']

    def test_chat_stream(self, client, mocker):
        """测试流式对话"""
        def mock_stream(messages):  # noqa
            yield "你"
            yield "好"

        mock_client = mocker.patch('app.services.chat_service.ModelService.get_model_client')
        mock_client.return_value.stream = mock_stream
        mock_client.return_value.get_model_name.return_value = "deepseek-chat"

        response = client.post('/api/v1/chat/stream', json={
            'message': '你好',
        })

        assert response.status_code == 200
        assert response.mimetype == 'text/event-stream'

    def test_health(self, client):
        """测试健康检查"""
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['status'] == 'ok'
