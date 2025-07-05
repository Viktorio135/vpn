from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from main_server.database.models import Servers, Tokens, WGConfig, User
import datetime
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)


class BaseRepository:
    def __init__(self, db: Session):
        self.db = db


class ServerRepository(BaseRepository):

    def get_by_ip(self, ip: str) -> Optional[Servers]:
        return self.db.query(Servers).filter(Servers.ip == ip).first()

    def get_by_id(self, server_id: int) -> Optional[Servers]:
        return self.db.query(Servers).filter(Servers.id == server_id).first()

    def get_all_active(self) -> List[Servers]:
        return self.db.query(Servers).filter(Servers.status.is_(True)).all()

    def add_user(self, server_id: int) -> bool:
        try:
            server = self.get_by_id(server_id)
            if server:
                server.count_users += 1
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"[ServerRepository] Error adding user: {e}")
            self.db.rollback()
            return False

    def create(
        self,
        country: str,
        server_id: int,
        name: str,
        ip: str,
        max_count_users: int
    ) -> Servers:
        server = Servers(
            country=country,
            server_id=server_id,
            name=name,
            ip=ip,
            max_count_users=max_count_users,
            status=True
        )
        self.db.add(server)
        self.db.commit()
        self.db.refresh(server)
        logger.info(f"[ServerRepository] Server created: {server.id}")
        return server

    def update(
        self,
        country: str,
        server_id: int,
        name: str,
        ip: str,
        max_count_users: int
    ) -> Optional[Servers]:
        server = (
            self.db.query(Servers)
            .filter(Servers.server_id == server_id)
            .first()
        )
        if server:
            server.country = country
            server.name = name
            server.ip = ip
            server.max_count_users = max_count_users
            server.status = True
            self.db.commit()
            logger.info(
                f"[ServerRepository] Server updated: {server.id}"
            )
            return server
        logger.warning(
            f"[ServerRepository] Server not found for update: {server_id}"
        )
        return None


class TokenRepository(BaseRepository):

    def create(self, server_id: int, token: str) -> Optional[Tokens]:
        try:
            server = (
                self.db.query(Servers)
                .filter(Servers.id == server_id)
                .first()
            )
            if not server:
                logger.error(
                    f"[TokenRepository] Server not found: {server_id}"
                )
                return None

            obj_token = Tokens(server=server.id, token=token)
            self.db.add(obj_token)
            self.db.commit()
            self.db.refresh(obj_token)
            logger.info(
                f"[TokenRepository] Token created for server {server_id}: "
                f"{obj_token.id}"
            )
            return obj_token

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"[TokenRepository] IntegrityError: {e}")
            return None
        except Exception as e:
            self.db.rollback()
            logger.error(f"[TokenRepository] Error creating token: {e}")
            return None

    def get_by_server(self, server_id: int) -> Optional[Tokens]:
        return self.db.query(Tokens).filter(Tokens.server == server_id).first()


class ConfigRepository(BaseRepository):

    def create(
        self,
        user_id: int,
        server_id: int,
        config_name: str,
        months: int
    ) -> WGConfig:
        created_at = datetime.datetime.now(datetime.timezone.utc)
        expires_at = created_at + relativedelta(months=months)
        expires_at = expires_at.replace(hour=23, minute=59, second=59)

        config = WGConfig(
            user_id=user_id,
            server_id=server_id,
            config_name=config_name,
            created_at=created_at,
            expires_at=expires_at
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        logger.info(f"[ConfigRepository] Config created: {config.id}")
        return config

    def get_by_id(self, config_id: int) -> Optional[WGConfig]:
        return self.db.query(WGConfig).filter(WGConfig.id == config_id).first()

    def get_by_user(self, user_id: int) -> List[WGConfig]:
        return (
            self.db.query(WGConfig)
            .filter(WGConfig.user_id == user_id)
            .all()
        )

    def add_expires(
        self,
        config_id: int,
        months: int
    ) -> Optional[WGConfig]:
        config = self.get_by_id(config_id)
        if not config:
            logger.warning(f"[ConfigRepository] Config not found: {config_id}")
            return None

        if config.expires_at < datetime.datetime.now():
            config.expires_at = datetime.datetime.now() + datetime.timedelta(
                days=30*months
            )
        else:
            config.expires_at += datetime.timedelta(days=30*months)

        self.db.commit()
        logger.info(f"[ConfigRepository] Config expires updated: {config.id}")
        return config


class UserRepository(BaseRepository):

    def create(self, user_id: int) -> User:
        user = User(client_id=user_id)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info(f"[UserRepository] User created: {user.id}")
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.client_id == user_id).first()
