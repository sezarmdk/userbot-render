import os
import asyncio
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateStatusRequest

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
STRING_SESSION = os.environ.get("STRING_SESSION", "")

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

ACTIONS = ['typing', 'record-audio', 'record-round', 'photo', 'document']
active_chats = set()

@client.on(events.NewMessage)
async def handle_new_message(event):
    if not event.is_private:
        return
    
    chat_id = event.chat_id
    active_chats.add(chat_id)

    if event.incoming:
        try:
            await event.mark_read()
        except Exception:
            pass

async def keep_online_loop():
    while True:
        try:
            await client(UpdateStatusRequest(offline=False))
        except Exception:
            pass
        await asyncio.sleep(40)

async def target_action_loop():
    action_idx = 0
    while True:
        if active_chats:
            current_action = ACTIONS[action_idx % len(ACTIONS)]
            for chat_id in list(active_chats):
                try:
                    async with client.action(chat_id, current_action):
                        await asyncio.sleep(1)
                except Exception:
                    pass
            action_idx += 1
        await asyncio.sleep(3)

async def start_web_server():
    app = web.Application()
    async def ping_handler(request):
        return web.Response(text="Bot active")
    app.router.add_get("/", ping_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await client.start()
    print("Userbot online!")
    asyncio.create_task(start_web_server())
    asyncio.create_task(keep_online_loop())
    asyncio.create_task(target_action_loop())
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
