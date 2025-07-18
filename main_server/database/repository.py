import datetime
import logging


from typing import Optional, List
from sqlalchemy.orm import Session


from database.models import Servers, WGConfig, User
from dateutil.relativedelta import relativedelta


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseRepository:
    model = None

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, obj_id: int):
        return self.db.query(self.model).filter(self.model.id == obj_id).first()

    def get_all(self):
        return self.db.query(self.model).all()

    def create(self, **kwargs):
        obj = self.model(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        logger.info(f"[{self.__class__.__name__}] Created: {obj.id}")
        return obj

    def update(self, obj_id: int, **kwargs):
        obj = self.get_by_id(obj_id)
        if not obj:
            logger.warning(f"[{self.__class__.__name__}] Not found for update: {obj_id}")
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        self.db.commit()
        logger.info(f"[{self.__class__.__name__}] Updated: {obj.id}")
        return obj

    def update_or_create(self, defaults: Optional[dict] = None, **kwargs):
        if defaults is None:
            defaults = {}

        obj = self.db.query(self.model).filter_by(**kwargs).first()

        if obj:
            for key, value in defaults.items():
                setattr(obj, key, value)
            self.db.commit()
            self.db.refresh(obj)
            logger.info(f"[{self.__class__.__name__}] Updated: {obj.id}")
            return obj, False
        else:
            create_data = {**kwargs, **defaults}
            obj = self.model(**create_data)
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            logger.info(f"[{self.__class__.__name__}] Created: {obj.id}")
            return obj, True

    def delete(self, obj_id: int):
        obj = self.get_by_id(obj_id)
        if not obj:
            logger.warning(f"[{self.__class__.__name__}] Not found for delete: {obj_id}")
            return False
        self.db.delete(obj)
        self.db.commit()
        logger.info(f"[{self.__class__.__name__}] Deleted: {obj.id}")
        return True


class ServerRepository(BaseRepository):
    model = Servers

    def get_by_ip(self, ip: str) -> Optional[Servers]:
        return self.db.query(self.model).filter(self.model.ip == ip).first()

    def get_by_server_id(self, server_id: int):
        return self.db.query(self.model).filter(
            self.model.server_id == server_id
        ).first()

    def get_all_active(self) -> List[Servers]:
        return self.db.query(self.model).filter(
            self.model.status.is_(True),
            self.model.ip != 'bot'
        ).all()

    def add_user(self, server_id: int) -> bool:
        server = self.get_by_id(server_id)
        if not server:
            logger.warning(f"[ServerRepository] Server not found: {server_id}")
            return False
        try:
            server.count_users += 1
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[ServerRepository] Error adding user: {e}")
            return False


class ConfigRepository(BaseRepository):
    model = WGConfig

    def create(
        self,
        user_id: int,
        server_id: int,
        config_name: str,
        months: int
    ) -> WGConfig:
        created_at = datetime.datetime.now(datetime.timezone.utc)
        if months != 0:
            expires_at = created_at + relativedelta(months=months)
        else:
            expires_at = created_at + relativedelta(days=5)
        expires_at = expires_at.replace(hour=23, minute=59, second=59)

        return super().create(
            user_id=user_id,
            server_id=server_id,
            config_name=config_name,
            created_at=created_at,
            expires_at=expires_at
        )

    def get_by_user(self, user_id: int) -> List[WGConfig]:
        return self.db.query(self.model).filter(self.model.user_id == user_id).all()

    def add_expires(self, config_id: int, months: int) -> Optional[WGConfig]:
        config = self.get_by_id(config_id)
        if not config:
            logger.warning(f"[ConfigRepository] Config not found: {config_id}")
            return None

        now = datetime.datetime.now(datetime.timezone.utc)
        if config.expires_at < now:
            config.expires_at = now + relativedelta(months=months)
        else:
            config.expires_at += relativedelta(months=months)

        self.db.commit()
        logger.info(f"[ConfigRepository] Config expires updated: {config.id}")
        return config

    def get_by_user_and_name(self, user_id: int, config_name: str):
        config = self.db.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.config_name == config_name
        ).first()
        if not config:
            logger.warning(f"[ConfigRepository] Config not found: {user_id} {config_name}")
            return None
        return config


class UserRepository(BaseRepository):
    model = User

    def create(self, user_id: int) -> User:
        return super().create(client_id=user_id)

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(self.model).filter(self.model.client_id == user_id).first()