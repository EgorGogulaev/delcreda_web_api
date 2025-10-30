from typing import Any, List, Tuple

from sqlalchemy import text, Table
from sqlalchemy.dialects.postgresql import insert

from connection_module import sync_session_maker


def prepare_reference(table: Table, reference_data: List[Tuple[Any]], first_iteration: bool):
    with sync_session_maker() as session:
        # Вставляем данные, игнорируя конфликты
        stmt = insert(table).values(reference_data).on_conflict_do_nothing()
        session.execute(stmt)
        session.commit()
        
        # Получаем текущее значение последовательности
        sequence_name = f"{table.__tablename__}_id_seq"
        stmt_current_value = text(f"SELECT last_value FROM {sequence_name};")
        current_value = session.execute(stmt_current_value).scalar()
        
        # Определяем, нужно ли обновлять последовательность
        if current_value <= len(reference_data):
            new_start_value = len(reference_data) + 1
            stmt_sequence = text(f"ALTER SEQUENCE {sequence_name} RESTART WITH {new_start_value};")
            session.execute(stmt_sequence)
            session.commit()
        
        if first_iteration:
            # функция для триггера, обновления состояния важности 
            session.execute(
                text(
                    """
                    CREATE OR REPLACE FUNCTION check_and_toggle_notification_important_status()
                    RETURNS void AS $$
                    BEGIN
                        UPDATE notification
                        SET is_important = NOT is_important,
                            time_importance_change = NULL
                        WHERE 
                            time_importance_change IS NOT NULL
                            AND time_importance_change <= NOW();
                    END;
                    $$ LANGUAGE plpgsql;
                    """
                )
            )
            session.commit()
