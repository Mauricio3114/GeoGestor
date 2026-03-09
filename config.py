import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

if not os.path.exists(INSTANCE_DIR):
    os.makedirs(INSTANCE_DIR)

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "geogestor-secret-key")

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_DIR, 'geogestor.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False