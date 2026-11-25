# -*- coding: utf-8 -*-
"""
知识库数据模型
==============
三个模型构成多用户知识库系统：
  - KnowledgeBase：知识库本体，归属一个用户（owner）
  - KBDocument：知识库内的文档，保存解析后的纯文本
  - KBShare：分享关系，允许 owner 把知识库共享给其他用户（只读可问）

权限模型：
  - owner：可增删改查、上传文档、管理分享
  - 被分享者：只能查看和基于知识库提问，不能修改
"""
from app.extensions import db
from datetime import datetime
import uuid


class KnowledgeBase(db.Model):
    """知识库本体"""
    __tablename__ = 'knowledge_bases'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), default='')
    user_id = db.Column(db.String(64), nullable=False, index=True)  # 拥有者
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def create(cls, name, description, user_id):
        kb = cls(name=name, description=description or '', user_id=user_id)
        db.session.add(kb)
        db.session.commit()
        return kb

    @classmethod
    def list_for_user(cls, user_id):
        """返回用户可见的知识库：自己创建的 + 被分享的"""
        from app.models.knowledge_base import KBShare
        owned = cls.query.filter_by(user_id=user_id).all()
        shared_ids = [s.kb_id for s in KBShare.query.filter_by(shared_with=user_id).all()]
        shared = cls.query.filter(cls.id.in_(shared_ids)).all() if shared_ids else []
        result = []
        for kb in owned:
            d = kb.to_dict()
            d['role'] = 'owner'
            result.append(d)
        for kb in shared:
            d = kb.to_dict()
            d['role'] = 'shared'
            result.append(d)
        return result

    @classmethod
    def get_visible(cls, kb_id, user_id):
        """获取用户有权访问的知识库（owner 或被分享者），否则返回 None"""
        from app.models.knowledge_base import KBShare
        kb = cls.query.get(kb_id)
        if not kb:
            return None
        if kb.user_id == user_id:
            return kb
        if KBShare.query.filter_by(kb_id=kb_id, shared_with=user_id).first():
            return kb
        return None

    @classmethod
    def is_owner(cls, kb_id, user_id):
        kb = cls.query.get(kb_id)
        return bool(kb and kb.user_id == user_id)

    def doc_count(self):
        return KBDocument.query.filter_by(kb_id=self.id).count()

    def chunk_count(self):
        from app.models.knowledge_base import KBChunk
        return KBChunk.query.filter_by(kb_id=self.id).count()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'doc_count': self.doc_count(),
            'chunk_count': self.chunk_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def delete_cascade(self):
        """删除知识库及其所有文档、文本块、分享关系和向量集合"""
        try:
            from app.services import kb_vector_service as vs
            vs.delete_kb_collection(self.id)
        except Exception:
            pass
        KBChunk.query.filter_by(kb_id=self.id).delete()
        KBDocument.query.filter_by(kb_id=self.id).delete()
        KBShare.query.filter_by(kb_id=self.id).delete()
        db.session.delete(self)
        db.session.commit()


class KBDocument(db.Model):
    """知识库文档：保存解析后的纯文本"""
    __tablename__ = 'kb_documents'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kb_id = db.Column(db.String(36), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    # MEDIUMTEXT：中文 utf8mb4 每字 3 字节，TEXT 的 64KB 上限约 2 万字就爆
    content = db.Column(db.Text(length=16777215), nullable=False)
    size = db.Column(db.Integer, default=0)
    chunk_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'kb_id': self.kb_id,
            'filename': self.filename,
            'size': self.size,
            'content_preview': self.content[:200] if self.content else '',
            'chunk_count': self.chunk_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def delete_cascade(self):
        try:
            from app.services import kb_vector_service as vs
            vs.delete_document_vectors(self.kb_id, self.id)
        except Exception:
            pass
        KBChunk.query.filter_by(doc_id=self.id).delete()
        db.session.delete(self)
        db.session.commit()


class KBChunk(db.Model):
    """文档切分后的文本块，供检索使用"""
    __tablename__ = 'kb_chunks'
    __table_args__ = {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kb_id = db.Column(db.String(36), nullable=False, index=True)
    doc_id = db.Column(db.String(36), nullable=False, index=True)
    doc_name = db.Column(db.String(255), default='')
    content = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0)  # 块在文档中的顺序
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class KBShare(db.Model):
    """知识库分享关系"""
    __tablename__ = 'kb_shares'
    __table_args__ = (
        db.UniqueConstraint('kb_id', 'shared_with', name='uq_kb_share'),
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kb_id = db.Column(db.String(36), nullable=False, index=True)
    owner_id = db.Column(db.String(64), nullable=False)
    shared_with = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def add(cls, kb_id, owner_id, shared_with):
        existing = cls.query.filter_by(kb_id=kb_id, shared_with=shared_with).first()
        if existing:
            return existing, False
        share = cls(kb_id=kb_id, owner_id=owner_id, shared_with=shared_with)
        db.session.add(share)
        db.session.commit()
        return share, True

    def to_dict(self):
        from app.models.user import User
        user = User.find_by_id(self.shared_with)
        return {
            'id': self.id,
            'kb_id': self.kb_id,
            'shared_with': self.shared_with,
            'username': user.username if user else '',
            'nickname': user.nickname if user else '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
