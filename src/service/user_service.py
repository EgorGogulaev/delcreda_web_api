import json
import secrets
from typing import Any, Dict, List, Literal, Optional, Tuple
from urllib.parse import urljoin
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from security import encrypt
from config import ACCESS_TTL, APP_URL, SECRET_KEY
from connection_module import RedisConnector, SignalConnector
from src.models.legal_entity.legal_entity_models import LegalEntity
from src.service.legal_entity.legal_entity_service import LegalEntityService
from src.schemas.user_schema import ClientState, FiltersUsersInfo, OrdersUsersInfo, ResponseAuth, ResponseGetUsersInfo, UpdateUserContactData, UserInfo, UserSchema
from src.models.user_models import UserAccount
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.service.file_store_service import FileStoreService
from src.utils.tz_converter import convert_tz
from src.utils.sanitazer_s3_username import sanitize_s3_username
from src.utils.reference_mapping_data.file_store.mapping import DIRECTORY_TYPE_MAPPING


class UserService:
    @staticmethod
    async def register_client(
        session: AsyncSession,
        
        email: str,
        password: str,
    ) -> None:
        """Самостоятельная регистрация пользователей"""
        assert len(email) >= 3, "Длина логина должна быть больше 2 символов!"
        assert len(password) >= 8, "Длина пароля должна быть больше 7 символов!"
        
        user_exist: bool = await UserQueryAndStatementManager.check_user_account_by_field_value(
            session=session,
            
            value=email,
            field_type="login",
        )
        if user_exist is True:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Пользователь с таким email'ом уже зарегестрирован!")
        
        async with RedisConnector.get_async_redis_session() as redis:
            key_token: str = secrets.token_urlsafe(48)
            exists = await redis.exists(key_token)
            
            while exists:  # проверка на всякий случай, для точного избегания коллизий
                key_token = secrets.token_urlsafe(48)
                exists = await redis.exists(key_token)
            
            user_data = {
                "type": "confirmationnewaccount",
                "email": email,
                "password": password,
            }
            
            data_dump = json.dumps(user_data, ensure_ascii=False)
            await redis.set(key_token, data_dump, expire=ACCESS_TTL)
        
        url = urljoin(APP_URL, "confirmation/" + key_token)
        await SignalConnector.notify_email(  # FIXME тут нужна верствка
            subject="Активация аккаунта",
            body=f"Для активации аккаунта Вам нужно пройти по ссылке:\n{url}\n\n\nНикому не показывайте это сообщение!\nНе нужно отвечать на данное сообщение, оно создано автоматически.",
            emails=[email],
        )
    
    @classmethod
    async def create_user(
        cls,
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        login: str,
        password: str,
        privilege: Literal[2, 3],
        new_user_uuid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Создает нового пользователя"""
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise AssertionError("Вы не можете создать пользователя, у Вас недостаточно прав!")
        
        assert len(login) >= 3, "Длина логина должна быть больше 2 символов!"
        assert len(password) >= 8, "Длина пароля должна быть больше 7 символов!"
        
        if not new_user_uuid:
            new_user_uuid_coro = await SignalConnector.generate_identifiers(target="Пользователь", count=1)
            new_user_uuid = new_user_uuid_coro[0]
        
        assert not await UserQueryAndStatementManager.check_user_account_by_field_value(
            session=session,
            
            value=new_user_uuid,
            field_type="uuid",
        ), "Пользователь с таким uuid уже существует!"
        assert not await UserQueryAndStatementManager.check_user_account_by_field_value(
            session=session,
            
            value=login,
            field_type="login",
        ), "Пользователь с таким логином уже существует!"
        
        # Создание пользователя в S3
        s3_login_sanitized: str = sanitize_s3_username(login + new_user_uuid)
        
        s3_login = s3_login_sanitized[:64]
        s3_password = password[:64]
        await SignalConnector.create_user_s3(
            username=s3_login,
            password=s3_password,
        )
        
        token_info: Dict[str, str|int] = await UserService.create_token(
            session=session,
        )
        
        new_user_contact_id: int = await cls.__create_user_contact(
            session=session,
        )
        
        new_user_id: int = await UserQueryAndStatementManager.register_user(
            session=session,
            
            new_user_uuid=new_user_uuid,
            token_id=token_info["token_id"],
            login=login,
            password=password,
            privilege=privilege,
            contact_id=new_user_contact_id,
            
            s3_login=s3_login,
            s3_password=s3_password,
        )
        user_dir_info: Dict[str, Any] = await FileStoreService.create_directory(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            owner_s3_login=s3_login,
            owner_user_uuid=new_user_uuid,
            directory_type=DIRECTORY_TYPE_MAPPING["Пользовательская директория"],
        )
        return {
            "id": new_user_id,
            "uuid": new_user_uuid,
            "token": token_info["value"],
            "privilege": list(PRIVILEGE_MAPPING)[list(PRIVILEGE_MAPPING.values()).index(privilege)],
            "user_dir": user_dir_info,
            
            "login": login,
            "password": password,
            "s3_login": s3_login,
            "s3_password": s3_password,
        }
        
        
    @staticmethod
    async def create_token(session: AsyncSession,) -> Dict[str, str|int]:
        gen_token = str(uuid4())
        while await UserQueryAndStatementManager.check_user_account_by_field_value(
            session=session,
            
            value=gen_token,
            field_type="token",
        ):  # До тех пор, пока не будет найден свободное значение токена
            gen_token = str(uuid4())
        
        token_id: int = await UserQueryAndStatementManager.register_token(
            session=session,
            
            token=gen_token
        )
        
        return {
            "token_id": token_id,
            "value": gen_token,
        }
    
    @staticmethod
    async def auth_user(
        session: AsyncSession,
        
        login: str,
        password: str,
        for_flet: bool=False,
    ) -> Dict[str, str] | ResponseAuth:
        assert all([login, password,]), "Нужно заполнить поля Логина и Пароля!"
        
        user_token = await UserQueryAndStatementManager.get_user_token(
            session=session,
            
            login=login,
            password=password,
        )
        if user_token is None:
            raise AssertionError("Не верный Логин или Пароль!")
        
        user_data: UserSchema = await UserQueryAndStatementManager.get_current_user_data(            
            token=user_token,
        )
        
        if for_flet:
            data = {
                "encrypt_token": encrypt(plain_text=user_token, secret_key=SECRET_KEY),
                "encrypt_user_id": encrypt(plain_text=str(user_data.user_id), secret_key=SECRET_KEY),
                "encrypt_user_uuid": encrypt(plain_text=user_data.user_uuid, secret_key=SECRET_KEY),
                "encrypt_user_dir_uuid": encrypt(plain_text=user_data.user_dir_uuid, secret_key=SECRET_KEY),
                "encrypt_privilege_id": encrypt(plain_text=str(user_data.privilege_id), secret_key=SECRET_KEY),
            }
        else:
            data = ResponseAuth(
                token=user_token,
                user_id=str(user_data.user_id),
                user_uuid=user_data.user_uuid,
                user_dir_uuid=user_data.user_dir_uuid,
                privilege={v:k for k, v in PRIVILEGE_MAPPING.items()}[user_data.privilege_id],
            )
        
        return data
    
    @staticmethod
    async def get_users_info(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        
        privilege: Literal[2, 3] = None,
        login: Optional[str] = None,
        user_token: Optional[str] = None,
        user_token_ilike: Optional[str] = None,
        uuid: Optional[str] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersUsersInfo] = None,
        order: Optional[OrdersUsersInfo] = None,
        
        tz: Optional[str] = None,
    ) -> ResponseGetUsersInfo:
        if page or page_size:
            assert page and page_size and page > 0 and page_size > 0, "Не корректное разделение на страницы, вывода данных!"
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if any([login, privilege, user_token, user_token_ilike]):
                raise AssertionError("Вы не можете осуществлять поиск инфорамции о Пользователе по Правам, Логину или Токену (или по их комбинации)!")
            if uuid is not None:
                assert requester_user_uuid == uuid, "Вы не можете просмотреть данные о другом Пользователе!"
        
        response_content = ResponseGetUsersInfo(
            data=[],
            count=0,
            total_records=None,
            total_pages=None
        )
        
        # Проверка по идентифицирующим полям
        if user_token:
            exists = await UserQueryAndStatementManager.check_user_account_by_field_value(
                session=session,
                
                value=user_token,
                field_type="token",
            )
            if not exists:
                return response_content
        if uuid:
            exists = await UserQueryAndStatementManager.check_user_account_by_field_value(
                session=session,
                
                value=uuid,
                field_type="uuid",
            )
            if not exists:
                return response_content
        if login:
            exists = await UserQueryAndStatementManager.check_user_account_by_field_value(
                session=session,
                
                value=login,
                field_type="login",
            )
            if not exists:
                return response_content
        
        users_data: Dict[str, List[Optional[Tuple[str, UserAccount,]]]|Optional[int]] = await UserQueryAndStatementManager.get_users_info(
            session=session,
            
            privilege=requester_user_privilege if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else privilege,
            login=login,
            user_token=user_token,
            user_token_ilike=user_token_ilike,
            uuid=requester_user_uuid if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else uuid,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        for user_data in users_data["data"]:
            if len(user_data) >= 3 and user_data[1] and user_data[2]:  # Проверка на наличие данных
                user_account = user_data[1]
                user_contact = user_data[2]
                privilege_name = list(PRIVILEGE_MAPPING)[
                    list(PRIVILEGE_MAPPING.values()).index(user_account.privilege)
                ]
                
                # Создаем UserInfo и добавляем в результат
                response_content.data.append(
                    UserInfo(
                        uuid=user_account.uuid,
                        token=user_data[0],
                        login=user_account.login,
                        password=user_account.password,
                        privilege=privilege_name,
                        is_active=user_account.is_active,
                        contact_id=user_account.contact,
                        
                        s3_login=user_account.s3_login,
                        s3_password=user_account.s3_password,
                        
                        email=user_contact.email,
                        email_notification=user_contact.email_notification,
                        telegram=user_contact.telegram,
                        telegram_notification=user_contact.telegram_notification,
                        
                        last_auth=convert_tz(user_account.last_auth.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=tz) if user_account.last_auth else None,
                        created_at=convert_tz(user_account.created_at.strftime("%d.%m.%Y %H:%M:%S UTC"), tz_city=tz) if user_account.created_at else None,
                    )
                )
                response_content.count += 1
        
        
        response_content.total_records = users_data.get("total_records")
        response_content.total_pages = users_data.get("total_pages")
        
        return response_content
    
    @staticmethod
    async def update_user_info(
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        
        target_token: Optional[str],
        target_user_uuid: Optional[str],
        target_login: Optional[str],
        
        new_login: Optional[str],
        new_password: Optional[str],
        new_user_uuid: Optional[str],
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise AssertionError("Вы не можете обновить информацию пользователя, у Вас недостаточно прав!")
        
        assert new_login or new_password or new_user_uuid, "Нужно указать, что будем изменять!"
        
        user_account_id: Optional[int] = await UserQueryAndStatementManager.check_user_account(
            session=session,
            
            token=target_token,
            uuid=target_user_uuid,
            login=target_login,
        )
        assert user_account_id, "По заданным параметрам, пользователь не найден!"
        if new_login:
            assert 255 >= len(new_login) >= 4, "Длина логина должна быть в диапазоне от 4 до 255 символов!"
        if new_password:
            assert 255 >= len(new_password) >= 4, "Длина пароля должна быть в диапазоне от 5 до 255 символов!"
        if new_user_uuid:
            assert len(new_user_uuid) == 36, f"Длина UUID должна составлять 36 символов! (Например {str(uuid4())})"
        
        await UserQueryAndStatementManager.update_user_info(
            session=session,
            
            user_account_id=user_account_id,
            
            new_login=new_login,
            new_password=new_password,
            new_user_uuid=new_user_uuid,
        )
    
    @classmethod
    async def change_password(
        cls,
        
        session: AsyncSession,
        
        email: str,
        old_password: str,
        new_password: str,
    ) -> None:
        """Изменение пароля ПОЛЬЗОВАТЕЛЕМ с подтверждением через email."""
        
        await cls.auth_user(
            session=session,
            login=email,
            password=old_password,
        )
        
        if old_password == new_password:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Текущий пароль совпадает с новым!")
        
        async with RedisConnector.get_async_redis_session() as redis:
            key_token: str = secrets.token_urlsafe(48)
            exists = await redis.exists(key_token)
            
            while exists:  # проверка на всякий случай, для точного избегания коллизий
                key_token = secrets.token_urlsafe(48)
                exists = await redis.exists(key_token)
            
            change_pass_data = {
                "type": "confirmationnewpassword",
                "email": email,
                "password": new_password,
            }
            
            data_dump = json.dumps(change_pass_data, ensure_ascii=False)
            await redis.set(key_token, data_dump, expire=ACCESS_TTL)
        
        url = urljoin(APP_URL, "confirmation/" + key_token)
        await SignalConnector.notify_email(  # FIXME тут нужна верствка
            subject="Изменение пароля",
            body=f"Для изменени пароля Вам нужно пройти по ссылке:\n{url}\n\n\nНикому не показывайте это сообщение!\nНе нужно отвечать на данное сообщение, оно создано автоматически.",
            emails=[email],
        )
    
    @staticmethod
    async def confirmation(
        session: AsyncSession,
        
        unique_path: str,
    ) -> Dict[str, str]:
        if len(unique_path) != 64:
            return {"type": "notfound"}
        
        async with RedisConnector.get_async_redis_session() as redis:
            data = await redis.get(unique_path)
            if data is None:
                return {"type": "notfound"}
            else:
                try:
                    data_dct: Dict[str, str] = json.loads(data.decode('utf-8'))
                    if not isinstance(data_dct, dict):
                        raise ValueError
                    await redis.delete(unique_path)
                    return data_dct
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                    await redis.delete(unique_path)
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Проблема с десериализацией данных!")
    
    @classmethod
    async def delete_users(
        cls,
        
        session: AsyncSession,
        
        requester_user_id: int, requester_user_uuid: str, requester_user_privilege: int,
        
        with_documents: bool,
        
        tokens: List[str],
        uuids: List[str],
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            raise AssertionError("Вы не можете удалить пользователя, у Вас недостаточно прав!")
        
        user_uuids: List[str] = []
        user_s3_logins: List[str] = []
        
        for token in tokens:
            user_data = await cls.get_users_info(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                
                user_token=token,
            )
            assert user_data.count > 0, f'Информация о пользователе с токеном - "{token}" не была найдена!'
            assert user_data.count == 1, f'Коллизия! Пользователей с токеном - "{token}" было найдено более одного!'
            assert PRIVILEGE_MAPPING[user_data.data[0].privilege] != PRIVILEGE_MAPPING["Admin"], f'Вы не можете удалить Админа! (токен - "{token}")'
            user_uuids.append(user_data.data[0].uuid)
            user_s3_logins.append(user_data.data[0].s3_login)
        
        for uuid in uuids:
            user_data = await cls.get_users_info(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                
                uuid=uuid,
            )
            assert user_data.count > 0, f'Информация о пользователе с UUID - "{uuid}" не была найдена!'
            assert user_data.count == 1, f'Коллизия! Пользователей с UUID - "{uuid}" было найдено более одного!'
            assert PRIVILEGE_MAPPING[user_data.data[0].privilege] != PRIVILEGE_MAPPING["Admin"], f'Вы не можете удалить Админа! (UUID - "{uuid}")'
            user_uuids.append(user_data.data[0].uuid)
        
        
        dir_uuids: List[str] = []
        for user_uuid in user_uuids:
            dirs_info: Dict[str, Any] = await FileStoreService.get_dir_info_from_db(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                owner_user_uuid=user_uuid
            )
            for dir_id in dirs_info["data"]:
                if dirs_info["data"][dir_id]["parent"] is None:
                    dir_uuids.append(dirs_info["data"][dir_id]["uuid"])
            
            le_uuids: List[str] = []
            le_dct: Dict[str, List[Optional[LegalEntity|int|bool]] | List[Optional[Tuple[LegalEntity, bool]]]] = await LegalEntityService.get_legal_entities(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                user_uuid=user_uuid,
            )
            for le in le_dct["data"]:
                le_uuids.append(le.uuid)
            
            try:
                await LegalEntityService.delete_legal_entities(
                    session=session,
                    
                    requester_user_id=requester_user_id,
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    
                    legal_entities_uuids=le_uuids,
                )
            except: ...  # noqa: E722
        
        if with_documents is True:
            for dir_uuid in dir_uuids:
                try:
                    await FileStoreService.delete_doc_or_dir(
                        session=session,
                        
                        requester_user_id=requester_user_id,
                        requester_user_uuid=requester_user_uuid,
                        requester_user_privilege=requester_user_privilege,
                        uuid=dir_uuid,
                        is_document=False,
                    )
                except: ...  # noqa: E722
        
        await UserQueryAndStatementManager.delete_users(
            session=session,
            
            user_uuids=user_uuids,
        )
        
        # TODO тут нужно удалять пользователей из S3 (нужна опция "С удалением" аккаунта-хранилища или "без удаления")
        for s3_login in user_s3_logins:
            await SignalConnector.remove_user_s3(
                username=s3_login,
            )
    
    @staticmethod
    async def get_client_state(
        requester_user_uuid: str, requester_user_privilege: int,
        
        user_uuid: str,
    ) -> ClientState:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            assert user_uuid == requester_user_uuid, "Вы не можете получить состояние другого пользователя!"
        
        data: ClientState = await UserQueryAndStatementManager.get_client_state(
            client_uuid=user_uuid,
        )
        
        return data
    
    @staticmethod
    async def record_client_states(
        requester_user_uuid: str, requester_user_privilege: int,
        
        client_uuid,
        new_state,
        ttl,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            assert requester_user_uuid == client_uuid, "Вы не можете менять состояние других клиентов, у Вас недостаточно прав!"
        
        await UserQueryAndStatementManager.record_client_states(
            client_uuid=client_uuid,
            new_state=new_state,
            ttl=ttl,
        )
    
    @staticmethod
    async def __create_user_contact(
        session: AsyncSession,
    ) -> int:
        new_user_contact_id: int = await UserQueryAndStatementManager.create_user_contact(
            session=session,
        )
        
        return new_user_contact_id
    
    @classmethod
    async def update_user_contact(
        cls,
        session: AsyncSession,
        
        requester_user_uuid: str, requester_user_privilege: int,
        
        new_user_contact_data: UpdateUserContactData,
        user_uuid: Optional[str] = None,
    ) -> None:
        assert user_uuid, "Для обновление контактный данных пользователя нужно указать его UUID!"
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if user_uuid:
                assert requester_user_uuid == user_uuid, "Вы не можете обновлять контактные данные других пользователей!"
        
        user_info: ResponseGetUsersInfo = await cls.get_users_info(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            
            uuid=user_uuid,
        )
        if user_info.count == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="У пользователя отсутствует запись о контактах!")
        user_contact_id: int = user_info.data[0].contact_id
        
        await UserQueryAndStatementManager.update_user_contact(
            session=session,
            
            user_contact_id=user_contact_id,
            new_user_contact_data=new_user_contact_data,
        )
