import datetime
from typing import List, Optional

from sqlalchemy import and_, select, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bank_details_models import BankDetails
from src.schemas.bank_details_schema import CreateBanksDetailsSchema


class BankDetailsQueryAndStatementManager:
    @staticmethod
    async def create_banks_details(
        session: AsyncSession,
        
        new_banks_details: CreateBanksDetailsSchema,
    ) -> None:
        new_bank_details_objects = []
        
        for new_bank_details in new_banks_details.new_banks_details:
            data = new_bank_details.model_dump()
            new_bank_details_objects.append(data)
        
        stmt = (
            insert(BankDetails)
            .values(new_bank_details_objects)
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def get_banks_details(
        session: AsyncSession,
        
        bank_details_ids: Optional[List[int]] = None,
        legal_entity_uuid: Optional[str] = None,
        user_uuid: Optional[str] = None,
    ) -> List[Optional[BankDetails]]:
        _filters = []
        
        if bank_details_ids:
            _filters.append(BankDetails.id.in_(bank_details_ids))
        
        if legal_entity_uuid:
            _filters.append(BankDetails.legal_entity_uuid == legal_entity_uuid)
        
        if user_uuid:
            _filters.append(BankDetails.user_uuid == user_uuid)
        
        query = (
            select(BankDetails)
            .filter(
                and_(
                    *_filters
                )
            )
        )
        
        response = await session.execute(query)
        result = [item[0] for item in response.all()]
        return result
    
    @staticmethod
    async def update_bank_details(
        session: AsyncSession,
        
        bank_details_id: int,
        
        user_uuid: Optional[str],
        from_customer: Optional[str | bool],
        legal_entity_uuid: Optional[str],
        name_latin: Optional[str],
        name_national: Optional[str],
        organizational_and_legal_form: Optional[str],
        SWIFT: Optional[str],
        BIC: Optional[str],
        IBAN: Optional[str],
        banking_messaging_system: Optional[str],
        CIPS: Optional[str],
        registration_identifier: Optional[str],
        current_account_rub: Optional[str],
        current_account_eur: Optional[str],
        current_account_usd: Optional[str],
        current_account_cny: Optional[str],
        current_account_chf: Optional[str],
        correspondence_account: Optional[str],
        address: Optional[str],
    ) -> None:
        values_for_update = {
            "user_uuid": user_uuid,
            "from_customer": from_customer,
            "legal_entity_uuid": legal_entity_uuid,
            "name_latin": name_latin,
            "name_national": name_national,
            "organizational_and_legal_form": organizational_and_legal_form,
            "SWIFT": SWIFT,
            "BIC": BIC,
            "IBAN": IBAN,
            "banking_messaging_system": banking_messaging_system,
            "CIPS": CIPS,
            "registration_identifier": registration_identifier,
            "current_account_rub": current_account_rub,
            "current_account_eur": current_account_eur,
            "current_account_usd": current_account_usd,
            "current_account_cny": current_account_cny,
            "current_account_chf": current_account_chf,
            "correspondence_account": correspondence_account,
            "address": address,
            
            "updated_at": datetime.datetime.now(tz=datetime.timezone.utc)
        }
        new_values = {k: v for k, v in values_for_update.items() if v != "~"}
        
        stmt = (
            update(BankDetails)
            .filter(BankDetails.id == bank_details_id)
            .values(**new_values)
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_banks_details(
        session: AsyncSession,
        
        bank_details_ids: List[int],
    ) -> None:
        stmt = (
            delete(BankDetails)
            .filter(BankDetails.id.in_(bank_details_ids))
        )
        
        await session.execute(stmt)
        await session.commit()
