# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# 你的專案 import（依你的目錄調整）
from app.core.config import settings
from app.models.base import Base  # Base.metadata 給 Alembic 用

config = context.config

# 讓 Alembic 的 log 設定生效
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def _sync_db_url() -> str:
    """把 async URL 換成同步 URL 給 Alembic 用。"""
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    return url

def run_migrations_offline():
    url = _sync_db_url()
    config.set_main_option("sqlalchemy.url", url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    url = _sync_db_url()
    engine = create_engine(url, pool_pre_ping=True, future=True)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
