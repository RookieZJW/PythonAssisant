"""
数据模型测试
"""
import pytest
from app import create_app
from app.extensions import db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User


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


class TestConversationModel:

    def test_create_conversation(self, app):
        """测试创建会话"""
        with app.app_context():
            conversation = Conversation.create(title="测试会话", model="deepseek")
            assert conversation.id is not None
            assert conversation.title == "测试会话"
            assert conversation.model == "deepseek"
            assert conversation.is_deleted is False

    def test_get_or_create_existing(self, app):
        """测试获取已存在的会话"""
        with app.app_context():
            conv1 = Conversation.create(title="已存在的会话")
            conv2 = Conversation.get_or_create(conv1.id)
            assert conv1.id == conv2.id

    def test_get_or_create_new(self, app):
        """测试不存在时创建新会话"""
        with app.app_context():
            conv = Conversation.get_or_create("")
            assert conv is not None
            assert conv.title == "新对话"

    def test_soft_delete(self, app):
        """测试软删除"""
        with app.app_context():
            conv = Conversation.create()
            conv.soft_delete()
            assert conv.is_deleted is True

    def test_get_list(self, app):
        """测试获取会话列表"""
        with app.app_context():
            Conversation.create(title="会话1")
            Conversation.create(title="会话2")
            result = Conversation.get_list(page=1, page_size=10)
            assert result['total'] >= 2
            assert len(result['items']) >= 2


class TestMessageModel:

    def test_create_message(self, app):
        """测试创建消息"""
        with app.app_context():
            conv = Conversation.create()
            msg = Message.create(conv.id, "user", "你好")
            assert msg.id is not None
            assert msg.role == "user"
            assert msg.content == "你好"

    def test_get_history(self, app):
        """测试获取历史消息"""
        with app.app_context():
            conv = Conversation.create()
            Message.create(conv.id, "user", "第1条消息")
            Message.create(conv.id, "assistant", "回复1")
            Message.create(conv.id, "user", "第2条消息")

            history = Message.get_history(conv.id, limit=10)
            assert len(history) == 3
            assert history[0]['role'] == 'user'
            assert history[1]['role'] == 'assistant'


class TestConversationAPI:

    def test_create_conversation_api(self, client):
        """测试创建会话接口"""
        response = client.post('/api/v1/conversations', json={
            'title': 'API测试会话',
            'model': 'deepseek',
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['title'] == 'API测试会话'

    def test_list_conversations_api(self, client, app):
        """测试获取会话列表接口"""
        with app.app_context():
            Conversation.create(title="测试1")
            Conversation.create(title="测试2")

        response = client.get('/api/v1/conversations')
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data['data']

    def test_delete_conversation_api(self, client, app):
        """测试删除会话接口"""
        with app.app_context():
            conv = Conversation.create(title="待删除")

        response = client.delete(f'/api/v1/conversations/{conv.id}')
        assert response.status_code == 200
