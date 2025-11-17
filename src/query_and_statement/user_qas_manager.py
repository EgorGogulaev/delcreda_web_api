import json
from typing import Any, Dict, List, Literal, Optional, Tuple

from sqlalchemy import and_, func, or_, select, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from connection_module import async_session_maker, RedisConnector

from src.models.notification_models import Notification
from src.models.chat_models import Message
from src.models.legal_entity.bank_details_models import BankDetails
from src.models.file_store_models import Directory, Document
from src.models.user_models import Token, UserAccount, UserContact, UserPrivilege
from src.schemas.user_schema import ClientState, UpdateUserContactData, UserSchema, FiltersUsersInfo, OrdersUsersInfo



class UserQueryAndStatementManager:
    @staticmethod
    async def get_user_token(
        session: AsyncSession,
        
        login: str,
        password: str,
    ) -> Optional[str]:
        query = (
            select(Token.value)
            .outerjoin(UserAccount, Token.id == UserAccount.token)
            .filter(
                and_(
                    UserAccount.login == login,
                    UserAccount.password == password,
                )
            )
        )
        
        response = await session.execute(query)
        result = response.scalar()
        return result
    
    @staticmethod
    async def get_user_s3_login(
        session: AsyncSession,
        
        user_id: Optional[int] = None,
        user_uuid: Optional[str] = None,
    ) -> Optional[str]:
        if not user_id and not user_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для определения логина в S3, нужно указать либо ID, либо UUID пользователя (можно и то и другое)!")
        
        _filters = []
        if user_id is not None:
            _filters.append(UserAccount.id == user_id)
        if user_uuid is not None:
            _filters.append(UserAccount.uuid == user_uuid)
        
        query = (
            select(UserAccount.s3_login)
            .filter(
                and_(*_filters)
            )
        )
        response = await session.execute(query)
        s3_login = response.scalar()
        
        return s3_login
    
    @staticmethod
    async def get_current_user_data(
        token: str,
    ) -> UserSchema:
        # TODO тут должно быть дешефрование token
        async with async_session_maker() as session:
            query = (
                select(Token, UserAccount, UserPrivilege.id, Directory.uuid)
                .outerjoin(UserAccount, Token.id == UserAccount.token)
                .outerjoin(UserPrivilege, UserAccount.privilege == UserPrivilege.id)
                .outerjoin(Directory, UserAccount.uuid == Directory.owner_user_uuid)
                .filter(
                    and_(
                        Token.value == token,
                        Directory.parent == None,  # noqa: E711
                    )
                )
            )
            response = await session.execute(query)  # аутентификация пользователя
            result = response.one_or_none()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Несуществующий токен или у пользователя отсутствует корневая Директория - {token}!"
                )
            if not result[0].is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Неактивный токен - {token}!"
                )
            if not result[1].is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Неактивный пользователь!"
                )
            if not result[2]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="У пользователя нет прав!"
                )
            if not result[3]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="У пользователя нет своей Директории!"
                )
            
            user_data = UserSchema()
            user_data.user_id = result[1].id
            user_data.user_uuid = result[1].uuid
            user_data.user_dir_uuid = result[3]
            user_data.privilege_id = result[2]
            
            return user_data
    
    @staticmethod
    async def get_user_id_by_uuid(
        session: AsyncSession,
        
        uuid: str
    ) -> Optional[int]:
        query = (
            select(UserAccount.id)
            .filter(UserAccount.uuid == uuid)
        )
        
        response = await session.execute(query)
        result = response.scalar()
        return result
    
    @staticmethod
    async def check_user_account(
        session: AsyncSession,
        
        token: Optional[str]=None,
        uuid: Optional[str]=None,
        login: Optional[str]=None,
    ) -> Optional[int]:
        """Проверка наличия аккаунта по токену+/логину+/uuid."""
        _filters = []
        
        if token:
            _filters.append(Token.value == token)
        if uuid:
            _filters.append(UserAccount.uuid == uuid)
        if login:
            _filters.append(UserAccount.login == login)
        
        query = (
            select(UserAccount, Token)
            .outerjoin(Token, UserAccount.token == Token.id)
            .filter(
                and_(
                    *_filters
                )
            )
        )
        
        response = await session.execute(query)
        result = response.one_or_none()
        
        return result[0].id if result else None
    
    @staticmethod
    async def check_user_account_by_field_value(
        session: AsyncSession,
        
        value: str,
        field_type: Literal["token", "login", "uuid"],
    ) -> bool:
        """Проверка уникальности значений для определенных полей Пользователя. Возвращает Fasle если значение свободно."""
        query = (
            select(Token if field_type == "token" else UserAccount)
            .filter(
                (Token.value if field_type == "token" else UserAccount.login if field_type == "login" else UserAccount.uuid) == value
            )
        )
        response = await session.execute(query)
        result = response.one_or_none()
        if result is None:
            return False
        else:
            return True
    
    @staticmethod
    async def get_client_state(client_uuid: str) -> ClientState:
        async with RedisConnector.get_async_redis_pipe() as pipe:
            pipe.get(client_uuid)
            pipe.ttl(client_uuid)
            data, ttl = await pipe.execute()
            
            return ClientState(
                data=json.loads(data.decode()) if data else {},
                ttl=ttl,  # Значение: -1 => нет TTL; -2 => ключ не существует.
            )
    
    @staticmethod
    async def get_user_contact_data(
        session: AsyncSession,
        
        user_id: Optional[str] = None,
        user_uuid: Optional[str] = None,
    ) -> Optional[UserContact]:
        if not user_id and not user_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для получения ID-контакта требуется указать ID или UUID пользователя (можно и то и другое)!")
        _filters = []
        if user_id:
            _filters.append(UserAccount.id == user_id)
        if user_uuid:
            _filters.append(UserAccount.uuid == user_uuid)
        query = (
            select(UserContact)
            .select_from(UserAccount)
            .outerjoin(UserContact, UserAccount.contact == UserContact.id)
            .filter(
                *_filters
            )
        )
        response = await session.execute(query)
        user_contact_data = response.fetchone()
        
        if user_contact_data:
            return user_contact_data[0]
    
    @staticmethod
    async def register_token(
        session: AsyncSession,
        
        token: str,
    ) -> int:
        """Заводит новый токен и возвращает его id"""
        stmt = (
            insert(Token)
            .values(
                value=token,
                is_active=True,
            )
            .returning(Token.id)
        )
        token_id = await session.execute(stmt)
        await session.commit()
        
        return token_id.scalar()
    
    @staticmethod
    async def register_user(
        session: AsyncSession,
        
        new_user_uuid: str,
        token_id: int,
        login: str,
        password: str,
        contact_id: int,
        s3_login: str,
        s3_password: str,
        privilege: Literal[2, 3] = 2,
    ) -> int:
        """Заводит нового пользователя и возвращает его id"""
        stmt = (
            insert(UserAccount)
            .values(
                uuid=new_user_uuid,
                token=token_id,
                login=login,
                password=password,
                privilege=privilege,
                is_active=True,
                contact=contact_id,
                s3_login=s3_login,
                s3_password=s3_password,
            )
            .returning(UserAccount.id)
        )
        user_id = await session.execute(stmt)
        await session.commit()
        
        return user_id.scalar()
    
    @staticmethod
    async def get_users_info(
        session: AsyncSession,
        
        privilege: Optional[int] = None,
        login: Optional[str] = None,
        user_token: Optional[str] = None,
        user_token_ilike: Optional[str] = None,
        uuid: Optional[str] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersUsersInfo] = None,
        order: Optional[OrdersUsersInfo] = None,
    ) -> Dict[str, List[Optional[Tuple[str, UserAccount,]]]|Optional[int]]:
        _filters = []
        if privilege is not None:
            _filters.append(UserPrivilege.id == privilege)
        if login is not None:
            _filters.append(UserAccount.login == login)
        if user_token is not None:
            _filters.append(Token.value == user_token)
        if uuid is not None:
            _filters.append(UserAccount.uuid == uuid)
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(UserAccount, filter_item.field)
                if filter_item.operator == "eq":
                    cond = column == filter_item.value
                elif filter_item.operator == "ne":
                    cond = column != filter_item.value
                elif filter_item.operator == "gt":
                    cond = column > filter_item.value
                elif filter_item.operator == "lt":
                    cond = column < filter_item.value
                elif filter_item.operator == "ge":
                    cond = column >= filter_item.value
                elif filter_item.operator == "le":
                    cond = column <= filter_item.value
                elif filter_item.operator == "like":
                    value = f"%{filter_item.value}%"
                    cond = column.ilike(value)
                elif filter_item.operator == "in":
                    if isinstance(filter_item.value, str):
                        values = [v.strip() for v in filter_item.value.split(",")]
                    else:
                        values = filter_item.value
                    cond = column.in_(values)
                else:
                    continue
                
                _filters.append(cond)
        
        # ===== сортировка =====
        _order_clauses = []
        if order is not None and order.orders:
            for order_item in order.orders:
                # Получаем атрибут модели для сортировки
                column = getattr(UserAccount, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(UserAccount.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        query = (
            select(Token.value, UserAccount, UserContact)
            .outerjoin(UserAccount, Token.id == UserAccount.token)
            .outerjoin(UserPrivilege, UserAccount.privilege == UserPrivilege.id)
            .outerjoin(UserContact, UserAccount.contact == UserContact.id)
            .filter(and_(*_filters))
        )
        if user_token_ilike is not None:
            query = query.filter(Token.value.ilike(f"%{user_token_ilike}%"))
        
        query = query.order_by(*_order_clauses)
        
        
        
        total_records = None
        total_pages = None
        
        if page is None or (page is not None and page < 1):
            page = 1
        if page_size is None or (page is not None and page_size < 1):
            page_size = 50
            
        query = query.limit(page_size).offset((page - 1) * page_size)
        count_query = (
            select(func.count())
            .select_from(Token)
            .outerjoin(UserAccount, Token.id == UserAccount.token)
            .outerjoin(UserPrivilege, UserAccount.privilege == UserPrivilege.id)
            .outerjoin(UserContact, UserAccount.contact == UserContact.id)
            .filter(and_(*_filters))
        )
        total_records = (await session.execute(count_query)).scalar()
        total_pages = (total_records + page_size - 1) // page_size if total_records else 0
        
        response = await session.execute(query)
        data = [(item[0], item[1], item[2]) for item in response.fetchall()]
        return {
            "data": data,
            "total_records": total_records,
            "total_pages": total_pages,
        }
    
    @staticmethod
    async def update_user_info(
        session: AsyncSession,
        
        user_account_id: int,
        
        new_login: Optional[str],
        new_password: Optional[str],
        new_user_uuid: Optional[str],
    ) -> None:
        values = {}
        
        if new_login:
            values["login"] = new_login
        if new_password:
            values["password"] = new_password
        if new_user_uuid:
            values["uuid"] = new_user_uuid
        
        stmt = (
            update(UserAccount)
            .filter(UserAccount.id == user_account_id)
            .values(values)
        )
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def record_client_states(
        client_uuid: str,
        new_state: Dict,
        ttl: Optional[int] = None,
    ) -> None:
        async with RedisConnector.get_async_redis_session() as session:
            serialized_state = json.dumps(new_state)
            if ttl and isinstance(ttl, int) and ttl >= 1:
                await session.setex(client_uuid, ttl, serialized_state)
            else:
                await session.set(client_uuid, serialized_state)
    
    # TODO нужно удалять также все смс и прочие связанные сущности!
    @staticmethod
    async def delete_users(
        session: AsyncSession,
        
        user_uuids: List[str],
    ) -> None:
        stmt_delete_messages = (
            delete(Message)
            .filter(Message.user_uuid.in_(user_uuids))
        )
        stmt_delete_notifications = (
            delete(Notification)
            .filter(
                or_(
                    Notification.initiator_user_uuid.in_(user_uuids),
                    Notification.recipient_user_uuid.in_(user_uuids)
                )
            )
        )
        stmt_delete_bank_details = (
            delete(BankDetails)
            .filter(BankDetails.user_uuid.in_(user_uuids))
        )
        
        await session.execute(stmt_delete_messages)
        await session.execute(stmt_delete_notifications)
        await session.execute(stmt_delete_bank_details)
        
        query = (
            select(UserAccount.id, Token.id, UserContact.id)
            .outerjoin(Token, UserAccount.token == Token.id)
            .outerjoin(UserContact, UserAccount.contact == UserContact.id)
            .filter(UserAccount.uuid.in_(user_uuids))
        )
        
        user_account_id_token_id_contact_id_response = await session.execute(query)
        user_account_id_token_id_contact_id_result = user_account_id_token_id_contact_id_response.fetchall()
        
        for user_account_id_token_id_contact_id in user_account_id_token_id_contact_id_result:
            stmt_delete_docs = (
                delete(Document)
                .filter(Document.owner_user_id == user_account_id_token_id_contact_id[0])
            )
            stmt_delete_dirs = (
                delete(Directory)
                .filter(Directory.owner_user_id == user_account_id_token_id_contact_id[0])
            )
            
            stmt_delete_user_account = (
                delete(UserAccount)
                .filter(UserAccount.id == user_account_id_token_id_contact_id[0])
            )
            stmt_delete_token = (
                delete(Token)
                .filter(Token.id == user_account_id_token_id_contact_id[1])
            )
            stmt_delete_contact = (
                delete(UserContact)
                .filter(UserContact.id == user_account_id_token_id_contact_id[2])
            )
            
            await session.execute(stmt_delete_docs)
            await session.execute(stmt_delete_dirs)
            await session.execute(stmt_delete_user_account)
            await session.execute(stmt_delete_token)
            await session.execute(stmt_delete_contact)
        
        await session.commit()
    
    @staticmethod
    async def create_user_contact(
        session: AsyncSession,
    ) -> int:
        stmt = (
            insert(UserContact)
            .values(
                email=None,
                telegram=None,
            ).returning(UserContact.id)
        )
        response = await session.execute(stmt)
        user_contact_id: int = response.scalar_one()
        await session.commit()
        
        return user_contact_id
    
    @staticmethod
    async def update_user_contact(
        session: AsyncSession,
        
        user_contact_id: int,
        new_user_contact_data: UpdateUserContactData,
    ) -> None:
        new_user_contact_data_dict: Dict[str, Any] = new_user_contact_data.model_dump()
        values_for_update = {
            "email": new_user_contact_data_dict["new_email"],
            "email_notification": new_user_contact_data_dict["email_notification"],
            "telegram": new_user_contact_data_dict["new_telegram"],
            "telegram_notification": new_user_contact_data_dict["telegram_notification"],
        }
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        
        stmt = (
            update(UserContact)
            .filter(UserContact.id == user_contact_id)
            .values(**new_values)
        )
        
        await session.execute(stmt)
        await session.commit()
