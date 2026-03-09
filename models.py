from datetime import datetime
from zoneinfo import ZoneInfo
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


def agora_brasil():
    return datetime.now(ZoneInfo("America/Fortaleza")).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="gestor")
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=agora_brasil)

    jornadas = db.relationship("Jornada", backref="usuario", lazy=True)
    localizacoes = db.relationship("Localizacao", backref="usuario", lazy=True)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)


class Jornada(db.Model):
    __tablename__ = "jornadas"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    inicio = db.Column(db.DateTime, default=agora_brasil)
    fim = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="ativa")


class Localizacao(db.Model):
    __tablename__ = "localizacoes"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    latitude = db.Column(db.String(50), nullable=False)
    longitude = db.Column(db.String(50), nullable=False)
    cidade = db.Column(db.String(120), nullable=True)
    estado = db.Column(db.String(120), nullable=True)
    data_hora = db.Column(db.DateTime, default=agora_brasil)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))