# TODO Реализовать

from typing import Optional
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contract_models import Contract
from src.utils.reference_mapping_data.contract.mapping import CONTRACT_TYPE_MAPPING


class ContractQueryAndStatementManager:
    @staticmethod
    async def create_contract(
        session: AsyncSession,
        
        uuid: str,
        name: str,
        type: str,
        user_id: int,
        user_uuid: str,
        counterparty_id: int,
        counterparty_uuid: str,
        application_id: Optional[int],
        application_uuid: Optional[str],
        document_uuid: str,
        start_date: Optional[str],
        expiration_date: Optional[str],
    ) -> None:
        stmt = (
            insert(Contract)
            .values(
                uuid=uuid,
                name=name,
                type=CONTRACT_TYPE_MAPPING[type],
                user_id=user_id,
                user_uuid=user_uuid,
                counterparty_id=counterparty_id,
                counterparty_uuid=counterparty_uuid,
                application_id=application_id,
                application_uuid=application_uuid,
                document_uuid=document_uuid,
                start_date=start_date,
                expiration_date=expiration_date,
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def get_contracts():
        ...  # TODO
    
    @staticmethod
    async def update_contract():
        ...  # TODO
    
    @staticmethod
    async def delete_contracts():
        ...  # TODO
