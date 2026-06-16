"""
pytest 配置文件
"""
import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope='session')
def app():
    """创建测试应用"""
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope='function')
def db(app):
    """每个测试函数独立的数据库事务"""
    with app.app_context():
        yield _db
        _db.session.rollback()
