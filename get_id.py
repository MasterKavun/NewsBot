import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message

# Токен свого бота встав сюди
TOKEN = "7571403720:AAHze0n8PDBmrv7wrKxE7NFCRdagDgL1wac"

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message()
async def echo_handler(message: Message):
    await message.answer(f"Привіт! Твоє ID: {message.from_user.id}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

