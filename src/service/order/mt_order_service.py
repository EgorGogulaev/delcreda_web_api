import datetime
from typing import Any, Dict, List, Optional, Tuple, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from connection_module import SignalConnector
from src.query_and_statement.order.order_qas_manager import OrderQueryAndStatementManager
from src.schemas.order.order_schema import FiltersOrders, OrdersOrders
from src.service.chat_service import ChatService
from src.service.file_store_service import FileStoreService
from src.models.order.order_models import Order
from src.models.order.mt_models import MTOrderData
from src.query_and_statement.legal_entity.legal_entity_qas_manager import LegalEntityQueryAndStatementManager
from src.query_and_statement.order.mt_order_qas_manager import MTOrderQueryAndStatementManager
from src.query_and_statement.user_qas_manager import UserQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.file_store.mapping import DIRECTORY_TYPE_MAPPING
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING


class MTOrderService:
    @staticmethod
    async def create_order(
        session: AsyncSession,
        
        # requester_user_id: int,
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        user_uuid: str,
        legal_entity_uuid: str,
        new_directory_uuid: Optional[str],
        
        # OrderData
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
    ) -> Tuple[Tuple[Order, MTOrderData], Dict[str, str|int]]:
        
        assert requester_user_uuid == user_uuid, "Вы не можете создать Поручение для другого Пользователя!"
        
        le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            legal_entity_uuid=legal_entity_uuid,
            
            for_create_order=True,
        )
        assert le_check_access_response_object, "Вы не являетесь владельцем данной записи о ЮЛ или её не существует или же ЮЛ не активно!"
        
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
            owner_user_uuid=requester_user_uuid,
            visible=True,
        )
        assert user_dirs["count"], "Не найдена ни одна директория по указанным данным Пользователя!"
        parent_directory_uuid = None
        for dir_id in user_dirs["data"]:
            if user_dirs["data"][dir_id]["type"] == DIRECTORY_TYPE_MAPPING["Пользовательская директория"]:
                parent_directory_uuid = user_dirs["data"][dir_id]["uuid"]
        assert parent_directory_uuid, "У Пользователя нет пользовательской Директории!"
        new_order_dir_data: Dict[str, Any] = await FileStoreService.create_directory(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege ,
            owner_user_uuid=requester_user_uuid,
            directory_type=DIRECTORY_TYPE_MAPPING["Директория поручения"],
            new_directory_uuid=new_directory_uuid,
            parent_directory_uuid=parent_directory_uuid,
        )
        
        new_order_uuid_coro = await SignalConnector.generate_identifiers(target="Поручение", count=1)
        new_order_uuid = new_order_uuid_coro[0]
        
        new_order_with_data: Tuple[Order, MTOrderData] = await MTOrderQueryAndStatementManager.create_order(
            session=session,
            
            name=None,  # TODO тут будет идентификатор из DELCREDIX
            user_id=user_id,
            user_uuid=user_uuid,
            new_order_uuid=new_order_uuid,
            legal_entity_id=legal_entity_id,
            legal_entity_uuid=legal_entity_uuid,
            directory_id=new_order_dir_data["id"],
            directory_uuid=new_order_dir_data["uuid"],
            
            # MTOrderData
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
            
            chat_subject="Поручение",
            subject_uuid=new_order_uuid,
        )
        
        return new_order_with_data, new_chat
    
    @staticmethod
    async def get_orders(
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
        
        filter: Optional[FiltersOrders] = None,
        order: Optional[OrdersOrders] = None,
    ) -> Dict[str, List[Optional[Order]]|Optional[int]]:
        if page or page_size:
            assert page and page_size and page > 0 and page_size > 0, "Не корректное разделение на страницы, вывода данных!"
        if extended_output is False and any(
            [
                user_login_ilike,
                legal_entity_name,
            ]
        ):
            raise AssertionError("Параметры поиска по логину/наименованию ЮЛ доступны только с extended_output==true!")
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            assert legal_entity_uuid or user_uuid, "Вы не можете просмотреть все Поручения не являясь Адмиинистратором!"
            assert user_uuid == requester_user_uuid, "Вы не можете просмотреть заказы других пользователей!"
            if legal_entity_uuid:
                le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    legal_entity_uuid=legal_entity_uuid,
                )
                assert le_check_access_response_object, "Вы не являетесь владельцем данной записи о ЮЛ или её не существует!"
        
        orders: Dict[str, List[Optional[Order]]|Optional[int]] = await MTOrderQueryAndStatementManager.get_orders(
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
        
        return orders
    
    @staticmethod
    async def get_orders_data(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        order_uuid_list: List[Optional[str]],
        legal_entity_uuid: Optional[str],
    ) -> List[Optional[MTOrderData]]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            assert order_uuid_list or legal_entity_uuid, "Нужно указать хотябы один uuid-Поручения или uuid-ЮЛ по которому будут запрошены данные Поручений!"
            if legal_entity_uuid:
                le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    legal_entity_uuid=legal_entity_uuid,
                )
                assert le_check_access_response_object, "Вы не являетесь владельцем данной записи о ЮЛ или её не существует!"
            if order_uuid_list:
                orders: Dict[str, List[Optional[Order]]|Optional[int]] = await MTOrderQueryAndStatementManager.get_orders(
                    session=session,
                    
                    user_uuid=requester_user_uuid,
                    legal_entity_uuid=legal_entity_uuid,
                    order_uuid_list=order_uuid_list,
                )
                user_uuid: Tuple[str] = tuple({order.user_uuid for order in orders["data"]})
                assert len(user_uuid) == 1 and user_uuid[0] == requester_user_uuid, "Вы не можете просматривать Данные Поручений других Пользователей!"
        
        orders_data: List[Optional[MTOrderData]] = await MTOrderQueryAndStatementManager.get_orders_data(
            session=session,
            
            order_uuid_list=order_uuid_list,
            legal_entity_uuid=legal_entity_uuid,
        )
        
        return orders_data
    
    @staticmethod
    async def update_order_data(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        order_uuid: str,
        
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
        order_check_access_response_object: Optional[Tuple[int, int, str]] = await OrderQueryAndStatementManager.check_access(
            session=session,
            
            requester_user_uuid=requester_user_uuid,
            requester_user_privilege=requester_user_privilege,
            order_uuid=order_uuid,
            for_update_or_delete_order=True,
        )
        assert order_check_access_response_object, "Вы не можете обновлять данные Поручений других Пользователей или же доступ к редактирования данного Поручения ограничен!"
        assert list(
            filter(
                lambda x: x != "~",
                [
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
            )
        ), "Хотя бы одно поле должно быть изменено для обновления данных о Поручении!"
        
        await MTOrderQueryAndStatementManager.update_order_data(
            session=session,
            
            order_data_id=order_check_access_response_object[1],
            
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
