from typing import List
import aiohttp

from config import TG_BOT_TOKEN


def __split_tg_msg(text, max_length=4096) -> List[str]:
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

async def send_telegram_message(chat_id: int, message: str) -> bool:
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    
    async with aiohttp.ClientSession() as session:
        for chunk in __split_tg_msg(message):
            payload = {
                "chat_id": chat_id,
                "text": chunk,
            }
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    continue
                else:
                    return False
        return True
