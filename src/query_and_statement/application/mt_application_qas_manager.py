import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Literal

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user_models import UserAccount
from src.models.legal_entity.legal_entity_models import LegalEntity, LegalEntityData
from src.schemas.application.application_schema import FiltersApplications, OrdersApplications
from src.models.application.application_models import Application
from src.models.application.mt_models import MTApplicationData
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING, CURRENCY_MAPPING
from src.utils.reference_mapping_data.application.mapping import APPLICATION_STATUS_MAPPING, APPLICATION_TYPE_MAPPING
from src.utils.bool_converter import bool_converter


class MTApplicationQueryAndStatementManager:
    @staticmethod
    async def create_application(
        session: AsyncSession,
        
        user_id: int,
        user_uuid: str,
        name: Optional[str],
        new_application_uuid: str,
        legal_entity_id: int,
        legal_entity_uuid: str,
        directory_id: int,
        directory_uuid: str,
        
        # MTApplicationData
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
    ) -> Tuple[Application, MTApplicationData]:
        # MTApplicationData
        new_mt_application_data = MTApplicationData(
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
        session.add(new_mt_application_data)
        await session.flush()  # Генерируем ID для MTApplicationData
        
        # Application
        new_application = Application(
            uuid=new_application_uuid,
            name=name if name else f"{datetime.datetime.now().year}-{legal_entity_id}-{new_mt_application_data.id}",
            user_id=user_id,
            user_uuid=user_uuid,
            legal_entity_id=legal_entity_id,
            legal_entity_uuid=legal_entity_uuid,
            directory_id=directory_id,
            directory_uuid=directory_uuid,
            type=APPLICATION_TYPE_MAPPING["MT"],
            status=APPLICATION_STATUS_MAPPING["Запрошен"],
            data_id=new_mt_application_data.id  # Используем сгенерированный ID
        )
        
        session.add(new_application)
        await session.commit()
        
        await session.refresh(new_application)
        await session.refresh(new_mt_application_data)
        
        return (new_application, new_mt_application_data)
    
    @staticmethod
    async def get_applications(
        session: AsyncSession,
        
        user_uuid: Optional[str],
        legal_entity_uuid: Optional[str],
        application_uuid_list: List[Optional[str]] = [],
        
        extended_output: bool = False,
        
        user_login_ilike: Optional[str] = None,
        legal_entity_name: Optional[str] = None,
        
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        
        filter: Optional[FiltersApplications] = None,
        order: Optional[OrdersApplications] = None,
    ) -> Dict[str, List[Optional[Application]]|Optional[int]]:
        _filters = []
        
        if user_uuid:
            _filters.append(Application.user_uuid == user_uuid)
        
        if legal_entity_uuid:
            _filters.append(Application.legal_entity_uuid == legal_entity_uuid)
        
        if application_uuid_list:
            _filters.append(Application.uuid.in_(application_uuid_list))
        
        if filter is not None and filter.filters:
            for filter_item in filter.filters:
                column = getattr(Application, filter_item.field)
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
                column = getattr(Application, order_item.field)
                
                # Добавляем условие сортировки в зависимости от направления
                if order_item.direction == "asc":
                    _order_clauses.append(column.asc().nulls_last())
                else:
                    _order_clauses.append(column.desc().nulls_last())
        
        if not _order_clauses:
            _order_clauses.append(Application.id.asc())
        # ===== КОНЕЦ блока сортировки =====
        
        if extended_output:
            query = (
                select(
                    Application,
                    
                    MTApplicationData.type,
                    MTApplicationData.priority,
                    MTApplicationData.updated_at,
                    MTApplicationData.order_name,
                    
                    UserAccount.login,
                    
                    LegalEntityData.name_latin,
                    LegalEntityData.name_national,
                    # TODO тут можно добавить вывод полей (согласовать с Юрием)
                )
                .outerjoin(MTApplicationData, Application.data_id == MTApplicationData.id)
                .outerjoin(UserAccount, Application.user_id == UserAccount.id)
                .outerjoin(LegalEntity, Application.legal_entity_id == LegalEntity.id)
                .outerjoin(LegalEntityData, LegalEntity.data_id == LegalEntityData.id)
                .filter(and_(*_filters))
                .order_by(*_order_clauses)
            )
            if user_login_ilike is not None:
                query = query.filter(UserAccount.login.ilike(f"%{user_login_ilike}%"))
            if legal_entity_name is not None:
                query = query.filter(
                    or_(
                        LegalEntityData.name_latin.ilike(f"%{legal_entity_name}%"),
                        LegalEntityData.name_national.ilike(f"%{legal_entity_name}%")
                    )
                )
        else:
            query = (
                select(Application)
                .filter(and_(*_filters))
                .order_by(*_order_clauses)
            )
        
        total_records = None
        total_pages = None
        
        if page is None or (page is not None and page < 1):
            page = 1
        if page_size is None or (page is not None and page_size < 1):
            page_size = 50
            
        query = query.limit(page_size).offset((page - 1) * page_size)
        count_query = select(func.count()).select_from(Application).filter(and_(*_filters))
        
        total_records = (await session.execute(count_query)).scalar()
        total_pages = (total_records + page_size - 1) // page_size if total_records else 0
        
        response = await session.execute(query)
        
        if extended_output:
            data = [{
                "application": item[0],
                
                "type": item[1],
                "priority": item[2],
                "updated_at": item[3],
                "order_name": item[4],
                
                "login": item[5],
                "name_latin": item[6],
                "name_national": item[7],
                
                # TODO тут можно добавить вывод полей (согласовать с Юрием)
            } for item in response.fetchall()]
        else:
            data = [item[0] for item in response.fetchall()]
        
        return {
            "data": data,
            "total_records": total_records,
            "total_pages": total_pages,
        }
    
    @staticmethod
    async def get_applications_data(
        session: AsyncSession,
        
        application_uuid_list: List[Optional[int]],
        legal_entity_uuid: Optional[str],
    ) -> List[Optional[MTApplicationData]]:
        _filters = []
        
        if application_uuid_list:
            _filters.append(Application.uuid.in_(application_uuid_list))
        
        if legal_entity_uuid:
            _filters.append(Application.legal_entity_uuid == legal_entity_uuid)
        
        query = (
            select(MTApplicationData)
            .select_from(MTApplicationData)
            .outerjoin(Application, Application.data_id == MTApplicationData.id)
            .where(
                and_(
                    *_filters
                )
            )
        )
        
        response = await session.execute(query)
        result = [item[0] for item in response.all()]
        return result
    
    @staticmethod
    async def update_application_data(
        session: AsyncSession,
        
        application_data_id: int,
        
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
        values_for_update = {
            "order_name": order_name,
            "payment_deadline_not_earlier_than": datetime.datetime.strptime(payment_deadline_not_earlier_than, "%d.%m.%Y").date() if payment_deadline_not_earlier_than and payment_deadline_not_earlier_than != "~" else "~" if payment_deadline_not_earlier_than == "~" else None,
            "payment_deadline_no_later_than": datetime.datetime.strptime(payment_deadline_no_later_than, "%d.%m.%Y").date() if payment_deadline_no_later_than and payment_deadline_no_later_than != "~" else "~" if payment_deadline_no_later_than == "~" else None,
            "invoice_date": datetime.datetime.strptime(invoice_date, "%d.%m.%Y").date() if invoice_date and invoice_date != "~" else "~",
            "invoice_currency": CURRENCY_MAPPING[invoice_currency] if invoice_currency and invoice_currency != "~" else "~",
            "invoice_amount": Decimal(invoice_amount).quantize(Decimal("0.00")) if invoice_amount.isdigit() else "~",
            "payment_amount": Decimal(payment_amount).quantize(Decimal("0.00")) if payment_amount.isdigit() else "~",
            "payment_amount_in_words": payment_amount_in_words,
            "partial_payment_allowed": bool_converter(partial_payment_allowed),
            "invoice_number": invoice_number,
            "amount_to_withdraw": Decimal(amount_to_withdraw).quantize(Decimal("0.00")) if amount_to_withdraw.isdigit() else "~",
            "amount_to_replenish": Decimal(amount_to_replenish).quantize(Decimal("0.00")) if amount_to_replenish.isdigit() else "~",
            "amount_to_principal": Decimal(amount_to_principal).quantize(Decimal("0.00")) if amount_to_principal.isdigit() else "~",
            "amount_credited": Decimal(amount_credited).quantize(Decimal("0.00")) if amount_credited.isdigit() else "~",
            "is_amount_different": bool_converter(is_amount_different),
            "source_bank": source_bank,
            "target_bank": target_bank,
            "source_currency": CURRENCY_MAPPING[source_currency] if source_currency and source_currency != "~" else "~",
            "target_currency": CURRENCY_MAPPING[target_currency] if target_currency and target_currency != "~" else "~",
            "amount": Decimal(amount).quantize(Decimal("0.00")) if amount.isdigit() else "~",
            "subagent_bank": subagent_bank,
            "payment_purpose_ru": payment_purpose_ru,
            "payment_purpose_en": payment_purpose_en,
            "payment_category_golomt": payment_category_golomt,
            "payment_category_td": payment_category_td,
            "goods_description_en": goods_description_en,
            "contract_date": datetime.datetime.strptime(contract_date, "%d.%m.%Y").date() if contract_date and contract_date != "~" else "~" if contract_date == "~" else None,
            "contract_name": contract_name,
            "contract_number": contract_number,
            "vat_exempt": bool_converter(vat_exempt),
            "vat_percentage": Decimal(vat_percentage).quantize(Decimal("0.00")) if vat_percentage.isdigit() else "~",
            "vat_amount": Decimal(vat_amount).quantize(Decimal("0.00")) if vat_amount.isdigit() else "~",
            "priority": priority,
            "end_customer_company_name": end_customer_company_name,
            "end_customer_company_legal_form": end_customer_company_legal_form,
            "end_customer_company_registration_country": COUNTRY_MAPPING[end_customer_company_registration_country] if end_customer_company_registration_country and end_customer_company_registration_country != "~" else "~",
            "company_name_latin": company_name_latin,
            "company_name_national": company_name_national,
            "company_legal_form": company_legal_form,
            "company_address_latin": company_address_latin,
            "company_registration_number": company_registration_number,
            "company_tax_number": company_tax_number,
            "company_internal_identifier": company_internal_identifier,
            "recipient_first_name": recipient_first_name,
            "recipient_last_name": recipient_last_name,
            "recipient_id_number": recipient_id_number,
            "recipient_phone": recipient_phone,
            "recipient_website": recipient_website,
            "transaction_confirmation_type": transaction_confirmation_type,
            "recipient_bank_name_latin": recipient_bank_name_latin,
            "recipient_bank_name_national": recipient_bank_name_national,
            "recipient_bank_legal_form": recipient_bank_legal_form,
            "recipient_bank_registration_number": recipient_bank_registration_number,
            "recipient_account_or_iban": recipient_account_or_iban,
            "recipient_swift": recipient_swift,
            "recipient_bic": recipient_bic,
            "recipient_bank_code": recipient_bank_code,
            "recipient_bank_branch": recipient_bank_branch,
            "spfs": spfs,
            "cips": cips,
            "recipient_bank_address": recipient_bank_address,
            "sender_company_name_latin": sender_company_name_latin,
            "sender_company_name_national": sender_company_name_national,
            "sender_company_legal_form": sender_company_legal_form,
            "sender_country": COUNTRY_MAPPING[sender_country] if sender_country and sender_country != "~" else "~",
            "comment": comment,
            
            "updated_at": datetime.datetime.now(tz=datetime.timezone.utc),
        }
        
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        
        stmt = (
            update(MTApplicationData)
            .filter(MTApplicationData.id == application_data_id)
            .values(**new_values)
        )
        
        await session.execute(stmt)
        await session.commit()
