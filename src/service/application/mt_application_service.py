import datetime
from typing import Any, Dict, List, Optional, Tuple, Literal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import SignalConnector
from src.query_and_statement.application.application_qas_manager import ApplicationQueryAndStatementManager
from src.schemas.application.application_schema import FiltersApplications, OrdersApplications
from src.service.chat_service import ChatService
from src.service.file_store_service import FileStoreService
from src.models.application.application_models import Application
from src.models.application.mt_models import MTApplicationData
from src.query_and_statement.legal_entity.legal_entity_qas_manager import LegalEntityQueryAndStatementManager
from src.query_and_statement.application.mt_application_qas_manager import MTApplicationQueryAndStatementManager
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.file_store.mapping import DIRECTORY_TYPE_MAPPING
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING


class MTApplicationService:
    @staticmethod
    async def create_application(
        session: AsyncSession,
        
        # requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        user_uuid: str,
        legal_entity_uuid: str,
        new_directory_uuid: Optional[str],
        
        # ApplicationData
        order_name: Optional[str],
        payment_deadline_not_earlier_than: Optional[datetime.date],
        payment_deadline_no_later_than: Optional[datetime.date],
        invoice_date: Optional[datetime.date],
        
        type: int,
        
        invoice_currency: Optional[int],
        invoice_amount: Optional[float | int],
        payment_amount: Optional[float | int],
        payment_amount_in_words: Optional[str],
        partial_payment_allowed: Optional[bool],
        invoice_number: Optional[str],
        
        amount_to_withdraw: Optional[float | int],
        amount_to_replenish: Optional[float | int],
        amount_to_principal: Optional[float | int],
        amount_credited: Optional[float | int],
        is_amount_different: Optional[bool],
        source_bank: Optional[str],
        target_bank: Optional[str],
        source_currency: Optional[int],
        target_currency: Optional[int],
        amount: Optional[float | int],
        subagent_bank: Optional[str],
        
        payment_purpose_ru: Optional[str],
        payment_purpose_en: Optional[str],
        payment_category_golomt: Optional[str],
        payment_category_td: Optional[str],
        goods_description_en: Optional[str],
        
        contract_date: Optional[datetime.date],
        contract_name: Optional[str],
        contract_number: Optional[str],
        vat_exempt: Optional[bool],
        vat_percentage: Optional[float | int],
        vat_amount: Optional[float | int],
        priority: Optional[str],
        company_name_latin: Optional[str],
        company_name_national: Optional[str],
        company_legal_form: Optional[str],
        company_address_latin: Optional[str],
        company_registration_number: Optional[str],
        company_tax_number: Optional[str],
        company_internal_identifier: Optional[str],
        recipient_first_name: Optional[str],
        recipient_last_name: Optional[str],
        recipient_id_number: Optional[str],
        recipient_phone: Optional[str],
        recipient_website: Optional[str],
        transaction_confirmation_type: Optional[str],
        
        recipient_bank_name_latin: Optional[str],
        recipient_bank_name_national: Optional[str],
        recipient_bank_legal_form: Optional[str],
        recipient_bank_registration_number: Optional[str],
        recipient_account_or_iban: Optional[str],
        recipient_swift: Optional[str],
        recipient_bic: Optional[str],
        recipient_bank_code: Optional[str],
        recipient_bank_branch: Optional[str],
        spfs: Optional[str],
        cips: Optional[str],
        recipient_bank_address: Optional[str],
        
        sender_company_name_latin: Optional[str],
        sender_company_name_national: Optional[str],
        sender_company_legal_form: Optional[str],
        sender_country: Optional[int],
        
        comment: Optional[str],
    ) -> Tuple[Tuple[Application, MTApplicationData], Dict[str, str|int]]:
        if requester_user_privilege == PRIVILEGE_MAPPING["Client"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if requester_user_uuid != user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете создать Заявку для другого Пользователя!")
        
        le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            legal_entity_uuid=legal_entity_uuid,
            
            for_create_application=True,
        )
        if le_check_access_response_object is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь владельцем данной записи о ЮЛ или её не существует или же ЮЛ не активно!")
        
        legal_entity_id = le_check_access_response_object[0]
        
        # TODO тут можно добавить проверок для отлова отсутствия данных (нужна валидация на frontend)
        
        user_id: int = await UserQueryAndStatementManager.get_user_id_by_uuid(
            session=session,
            
            uuid=user_uuid
        )
        
        user_dirs: Dict[str, Any] = await FileStoreService.get_dir_info_from_db(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            owner_user_uuid=requester_user_uuid if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else user_uuid,
            visible=True,
        )
        if not user_dirs["count"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не найдена ни одна директория по указанным данным Пользователя!")
        parent_directory_uuid = None
        for dir_id in user_dirs["data"]:
            if user_dirs["data"][dir_id]["type"] == DIRECTORY_TYPE_MAPPING["Пользовательская директория"]:
                parent_directory_uuid = user_dirs["data"][dir_id]["uuid"]
        if not parent_directory_uuid:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="У Пользователя нет пользовательской Директории!")
        
        user_s3_login: str = await UserQueryAndStatementManager.get_user_s3_login(
            session=session,
            
            user_id=user_id,
        )
        
        new_application_dir_data: Dict[str, Any] = await FileStoreService.create_directory(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            owner_s3_login=user_s3_login,
            owner_user_uuid=requester_user_uuid if requester_user_privilege != PRIVILEGE_MAPPING["Admin"] else user_uuid,
            directory_type=DIRECTORY_TYPE_MAPPING["Директория заявки"],
            new_directory_uuid=new_directory_uuid,
            parent_directory_uuid=parent_directory_uuid,
        )
        
        new_application_uuid_coro = await SignalConnector.generate_identifiers(target="Заявка", count=1)
        new_application_uuid = new_application_uuid_coro[0]
        
        new_application_with_data: Tuple[Application, MTApplicationData] = await MTApplicationQueryAndStatementManager.create_application(
            session=session,
            
            name=None,  # Значение генерируется само на уровне БД
            user_id=user_id,
            user_uuid=user_uuid,
            new_application_uuid=new_application_uuid,
            legal_entity_id=legal_entity_id,
            legal_entity_uuid=legal_entity_uuid,
            directory_id=new_application_dir_data["id"],
            directory_uuid=new_application_dir_data["uuid"],
            
            # MTApplicationData
            order_name=order_name,
            payment_deadline_not_earlier_than=payment_deadline_not_earlier_than,
            payment_deadline_no_later_than=payment_deadline_no_later_than,
            invoice_date=invoice_date,
            
            type=type,
            
            invoice_currency=invoice_currency,
            invoice_amount=invoice_amount,
            payment_amount=payment_amount,
            payment_amount_in_words=payment_amount_in_words,
            partial_payment_allowed=partial_payment_allowed,
            invoice_number=invoice_number,
            
            amount_to_withdraw=amount_to_withdraw,
            amount_to_replenish=amount_to_replenish,
            amount_to_principal=amount_to_principal,
            amount_credited=amount_credited,
            is_amount_different=is_amount_different,
            source_bank=source_bank,
            target_bank=target_bank,
            source_currency=source_currency,
            target_currency=target_currency,
            amount=amount,
            subagent_bank=subagent_bank,
            
            payment_purpose_ru=payment_purpose_ru,
            payment_purpose_en=payment_purpose_en,
            payment_category_golomt=payment_category_golomt,
            payment_category_td=payment_category_td,
            goods_description_en=goods_description_en,
            contract_date=contract_date,
            
            contract_name=contract_name,
            contract_number=contract_number,
            vat_exempt=vat_exempt,
            vat_percentage=vat_percentage,
            vat_amount=vat_amount,
            priority=priority,
            company_name_latin=company_name_latin,
            company_name_national=company_name_national,
            company_legal_form=company_legal_form,
            company_address_latin=company_address_latin,
            company_registration_number=company_registration_number,
            company_tax_number=company_tax_number,
            company_internal_identifier=company_internal_identifier,
            recipient_first_name=recipient_first_name,
            recipient_last_name=recipient_last_name,
            recipient_id_number=recipient_id_number,
            recipient_phone=recipient_phone,
            recipient_website=recipient_website,
            transaction_confirmation_type=transaction_confirmation_type,
            
            recipient_bank_name_latin=recipient_bank_name_latin,
            recipient_bank_name_national=recipient_bank_name_national,
            recipient_bank_legal_form=recipient_bank_legal_form,
            recipient_bank_registration_number=recipient_bank_registration_number,
            recipient_account_or_iban=recipient_account_or_iban,
            recipient_swift=recipient_swift,
            recipient_bic=recipient_bic,
            recipient_bank_code=recipient_bank_code,
            recipient_bank_branch=recipient_bank_branch,
            spfs=spfs,
            cips=cips,
            recipient_bank_address=recipient_bank_address,
            
            sender_company_name_latin=sender_company_name_latin,
            sender_company_name_national=sender_company_name_national,
            sender_company_legal_form=sender_company_legal_form,
            sender_country=sender_country,
            
            comment=comment,
        )
        
        new_chat = await ChatService.create_chat(
            session=session,
            
            chat_subject="Заявка",
            subject_uuid=new_application_uuid,
        )
        
        return new_application_with_data, new_chat
    
    @staticmethod
    async def get_applications(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        user_uuid: Optional[str],
        legal_entity_uuid: Optional[str],
        
        extended_output: bool = False,
        
        user_login_ilike: Optional[str] = None,
        legal_entity_name: Optional[str] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersApplications] = None,
        order: Optional[OrdersApplications] = None,
    ) -> Dict[str, List[Optional[Application]]|Optional[int]]:
        if requester_user_privilege == PRIVILEGE_MAPPING["Client"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав!")
        
        if page or page_size:
            if (isinstance(page, int) and page <= 0) or (isinstance(page_size, int) and page_size <= 0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не корректное разделение на страницы, запрошенных данных!")
        if extended_output is False and any(
            [
                user_login_ilike,
                legal_entity_name,
            ]
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Параметры поиска по логину/наименованию ЮЛ доступны только с extended_output==true!")
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if not legal_entity_uuid and not user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть все Заявки не являясь Адмиинистратором!")
            if user_uuid != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть заказы других пользователей!")
            
            if legal_entity_uuid:
                le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    legal_entity_uuid=legal_entity_uuid,
                )
                if le_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь владельцем данной записи о ЮЛ или её не существует!")
        
        applications: Dict[str, List[Optional[Application]]|Optional[int]] = await MTApplicationQueryAndStatementManager.get_applications(
            session=session,
            
            user_uuid=user_uuid,
            legal_entity_uuid=legal_entity_uuid,
            
            extended_output=extended_output,
            
            user_login_ilike=user_login_ilike,
            legal_entity_name=legal_entity_name,
            
            page=page,
            page_size=page_size,
            
            filter=filter,
            order=order,
        )
        
        return applications
    
    @staticmethod
    async def get_applications_data(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        application_uuid_list: List[Optional[str]],
        legal_entity_uuid: Optional[str],
    ) -> List[Optional[MTApplicationData]]:
        if requester_user_privilege == PRIVILEGE_MAPPING["Client"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if not application_uuid_list and not legal_entity_uuid:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужно указать хотябы один UUID-Заявки или UUID-ЮЛ по которому будут запрошены данные Заявки!")
            if legal_entity_uuid:
                le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    legal_entity_uuid=legal_entity_uuid,
                )
                if le_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не являетесь владельцем данной записи о ЮЛ или её не существует!")
            
            if application_uuid_list:
                applications: Dict[str, List[Optional[Application]]|Optional[int]] = await MTApplicationQueryAndStatementManager.get_applications(
                    session=session,
                    
                    user_uuid=requester_user_uuid,
                    legal_entity_uuid=legal_entity_uuid,
                    application_uuid_list=application_uuid_list,
                )
                user_uuid: Tuple[str] = tuple({application.user_uuid for application in applications["data"]})
                if len(user_uuid) != 1 or user_uuid[0] != requester_user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просматривать Данные Заявок других Пользователей!")
        
        applications_data: List[Optional[MTApplicationData]] = await MTApplicationQueryAndStatementManager.get_applications_data(
            session=session,
            
            application_uuid_list=application_uuid_list,
            legal_entity_uuid=legal_entity_uuid,
        )
        
        return applications_data
    
    @staticmethod
    async def update_application_data(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        application_uuid: str,
        
        order_name: Optional[str],
        payment_deadline_not_earlier_than: Optional[str],
        payment_deadline_no_later_than: Optional[str],
        invoice_date: Optional[str],
        invoice_currency: Optional[str],
        invoice_amount: Optional[str],
        payment_amount: Optional[str],
        payment_amount_in_words: Optional[str],
        partial_payment_allowed: Optional[bool|str],
        invoice_number: Optional[str],
        amount_to_withdraw: Optional[str],
        amount_to_replenish: Optional[str],
        amount_to_principal: Optional[str],
        amount_credited: Optional[str],
        is_amount_different: Optional[bool|str],
        source_bank: Optional[str],
        target_bank: Optional[str],
        source_currency: Optional[str],
        target_currency: Optional[str],
        amount: Optional[str],
        subagent_bank: Optional[str],
        payment_purpose_ru: Optional[str],
        payment_purpose_en: Optional[str],
        payment_category_golomt: Optional[str],
        payment_category_td: Optional[str],
        goods_description_en: Optional[str],
        contract_date: Optional[str],
        contract_name: Optional[str],
        contract_number: Optional[str],
        vat_exempt: Optional[str],
        vat_percentage: Optional[str],
        vat_amount: Optional[str],
        priority: Optional[str],
        end_customer_company_name: Optional[str],
        end_customer_company_legal_form: Optional[str],
        end_customer_company_registration_country: Optional[str],
        company_name_latin: Optional[str],
        company_name_national: Optional[str],
        company_legal_form: Optional[str],
        company_address_latin: Optional[str],
        company_registration_number: Optional[str],
        company_tax_number: Optional[str],
        company_internal_identifier: Optional[str],
        recipient_first_name: Optional[str],
        recipient_last_name: Optional[str],
        recipient_id_number: Optional[str],
        recipient_phone: Optional[str],
        recipient_website: Optional[str],
        transaction_confirmation_type: Optional[str],
        recipient_bank_name_latin: Optional[str],
        recipient_bank_name_national: Optional[str],
        recipient_bank_legal_form: Optional[str],
        recipient_bank_registration_number: Optional[str],
        recipient_account_or_iban: Optional[str],
        recipient_swift: Optional[str],
        recipient_bic: Optional[str],
        recipient_bank_code: Optional[str],
        recipient_bank_branch: Optional[str],
        spfs: Optional[str],
        cips: Optional[str],
        recipient_bank_address: Optional[str],
        sender_company_name_latin: Optional[str],
        sender_company_name_national: Optional[str],
        sender_company_legal_form: Optional[str],
        sender_country: Optional[Literal[*COUNTRY_MAPPING, "~"]], # type: ignore
        comment: Optional[str],
    ) -> None:
        if requester_user_privilege == PRIVILEGE_MAPPING["Client"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав!")
        
        application_check_access_response_object: Optional[Tuple[int, int, str]] = await ApplicationQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            application_uuid=application_uuid,
            for_update_or_delete_application=True,
        )
        if application_check_access_response_object is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете обновлять данные Заявок других Пользователей или же доступ к редактирования данной Заявки ограничен!")
        
        if all(field == "~" for field in [
                    order_name,
                    payment_deadline_not_earlier_than,
                    payment_deadline_no_later_than,
                    invoice_date,
                    invoice_currency,
                    invoice_amount,
                    payment_amount,
                    payment_amount_in_words,
                    partial_payment_allowed,
                    invoice_number,
                    amount_to_withdraw,
                    amount_to_replenish,
                    amount_to_principal,
                    amount_credited,
                    is_amount_different,
                    source_bank,
                    target_bank,
                    source_currency,
                    target_currency,
                    amount,
                    subagent_bank,
                    payment_purpose_ru,
                    payment_purpose_en,
                    payment_category_golomt,
                    payment_category_td,
                    goods_description_en,
                    contract_date,
                    contract_name,
                    contract_number,
                    vat_exempt,
                    vat_percentage,
                    vat_amount,
                    priority,
                    end_customer_company_name,
                    end_customer_company_legal_form,
                    end_customer_company_registration_country,
                    company_name_latin,
                    company_name_national,
                    company_legal_form,
                    company_address_latin,
                    company_registration_number,
                    company_tax_number,
                    company_internal_identifier,
                    recipient_first_name,
                    recipient_last_name,
                    recipient_id_number,
                    recipient_phone,
                    recipient_website,
                    transaction_confirmation_type,
                    recipient_bank_name_latin,
                    recipient_bank_name_national,
                    recipient_bank_legal_form,
                    recipient_bank_registration_number,
                    recipient_account_or_iban,
                    recipient_swift,
                    recipient_bic,
                    recipient_bank_code,
                    recipient_bank_branch,
                    spfs,
                    cips,
                    recipient_bank_address,
                    sender_company_name_latin,
                    sender_company_name_national,
                    sender_company_legal_form,
                    sender_country,
                    comment,
                ]
            ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Хотя бы одно поле должно быть изменено для обновления данных Заявки!")
        
        await MTApplicationQueryAndStatementManager.update_application_data(
            session=session,
            
            application_data_id=application_check_access_response_object[1],
            
            order_name=order_name,
            payment_deadline_not_earlier_than=payment_deadline_not_earlier_than,
            payment_deadline_no_later_than=payment_deadline_no_later_than,
            invoice_date=invoice_date,
            invoice_currency=invoice_currency,
            invoice_amount=invoice_amount,
            payment_amount=payment_amount,
            payment_amount_in_words=payment_amount_in_words,
            partial_payment_allowed=partial_payment_allowed,
            invoice_number=invoice_number,
            amount_to_withdraw=amount_to_withdraw,
            amount_to_replenish=amount_to_replenish,
            amount_to_principal=amount_to_principal,
            amount_credited=amount_credited,
            is_amount_different=is_amount_different,
            source_bank=source_bank,
            target_bank=target_bank,
            source_currency=source_currency,
            target_currency=target_currency,
            amount=amount,
            subagent_bank=subagent_bank,
            payment_purpose_ru=payment_purpose_ru,
            payment_purpose_en=payment_purpose_en,
            payment_category_golomt=payment_category_golomt,
            payment_category_td=payment_category_td,
            goods_description_en=goods_description_en,
            contract_date=contract_date,
            contract_name=contract_name,
            contract_number=contract_number,
            vat_exempt=vat_exempt,
            vat_percentage=vat_percentage,
            vat_amount=vat_amount,
            priority=priority,
            end_customer_company_name=end_customer_company_name,
            end_customer_company_legal_form=end_customer_company_legal_form,
            end_customer_company_registration_country=end_customer_company_registration_country,
            company_name_latin=company_name_latin,
            company_name_national=company_name_national,
            company_legal_form=company_legal_form,
            company_address_latin=company_address_latin,
            company_registration_number=company_registration_number,
            company_tax_number=company_tax_number,
            company_internal_identifier=company_internal_identifier,
            recipient_first_name=recipient_first_name,
            recipient_last_name=recipient_last_name,
            recipient_id_number=recipient_id_number,
            recipient_phone=recipient_phone,
            recipient_website=recipient_website,
            transaction_confirmation_type=transaction_confirmation_type,
            recipient_bank_name_latin=recipient_bank_name_latin,
            recipient_bank_name_national=recipient_bank_name_national,
            recipient_bank_legal_form=recipient_bank_legal_form,
            recipient_bank_registration_number=recipient_bank_registration_number,
            recipient_account_or_iban=recipient_account_or_iban,
            recipient_swift=recipient_swift,
            recipient_bic=recipient_bic,
            recipient_bank_code=recipient_bank_code,
            recipient_bank_branch=recipient_bank_branch,
            spfs=spfs,
            cips=cips,
            recipient_bank_address=recipient_bank_address,
            sender_company_name_latin=sender_company_name_latin,
            sender_company_name_national=sender_company_name_national,
            sender_company_legal_form=sender_company_legal_form,
            sender_country=sender_country,
            comment=comment,
        )
