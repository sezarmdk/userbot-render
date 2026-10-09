import os
import time
import asyncio
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.tl.types import (
    SendMessageTypingAction,
    SendMessageRecordAudioAction,
    SendMessageRecordRoundAction,
    SendMessageUploadPhotoAction,
    SendMessageUploadDocumentAction
)

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
STRING_SESSION = os.environ.get("STRING_SESSION", "")

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

START_TIME = time.time()

CONFIG = {
    "online": True,
    "read": True,
}

active_tasks = {}

ACTIONS = [
    SendMessageTypingAction(),
    SendMessageRecordAudioAction(),
    SendMessageRecordRoundAction(),
    SendMessageUploadPhotoAction(progress=1),
    SendMessageUploadDocumentAction(progress=1)
]

# 1. AUTO-READ
@client.on(events.NewMessage(incoming=True))
async def auto_read_handler(event):
    if CONFIG["read"] and event.is_private:
        try:
            await event.mark_read()
        except Exception:
            pass

# 2. DOIMIY ONLINE LOOP (Telegram talabiga mos 40 soniyalik oraliq)
async def keep_online_loop():
    while True:
        if CONFIG["online"]:
            try:
                await client(UpdateStatusRequest(offline=False))
            except Exception:
                pass
        await asyncio.sleep(40)

# 3. CHAT ACTION LOOP (To'xtovsiz harakatlar)
async def run_chat_action(cid):
    idx = 0
    while True:
        cur_act = ACTIONS[idx % len(ACTIONS)]
        try:
            await client.send_chat_action(cid, cur_act)
        except Exception:
            pass
        idx += 1
        await asyncio.sleep(2)

# 4. BUYRUQLAR
@client.on(events.NewMessage(outgoing=True))
async def commands_handler(event):
    text = (event.raw_text or "").strip()
    cid = event.chat_id

    if text == ".ping":
        t0 = time.time()
        msg = await event.edit("<code>Ping tekshirilmoqda...</code>")
        diff = round((time.time() - t0) * 1000)
        await msg.edit(f"<b>PING:</b> <code>{diff} ms</code>", parse_mode="html")
        return

    if text == ".on":
        CONFIG["online"] = True
        try:
            await client(UpdateStatusRequest(offline=False))
        except Exception:
            pass
        await event.edit("<b>AUTO-ONLINE:</b> <code>YOQILDI [ON]</code>", parse_mode="html")
        return

    if text == ".off":
        CONFIG["online"] = False
        try:
            await client(UpdateStatusRequest(offline=True))
        except Exception:
            pass
        await event.edit("<b>AUTO-ONLINE:</b> <code>OCHIRILDI [OFF]</code>", parse_mode="html")
        return

    if text == ".read":
        CONFIG["read"] = True
        await event.edit("<b>AUTO-READ:</b> <code>YOQILDI [ON]</code>", parse_mode="html")
        return

    if text == ".unread":
        CONFIG["read"] = False
        await event.edit("<b>AUTO-READ:</b> <code>OCHIRILDI [OFF]</code>", parse_mode="html")
        return

    # .typ
    if text == ".typ":
        if cid not in active_tasks:
            active_tasks[cid] = asyncio.create_task(run_chat_action(cid))
            await event.edit("<b>CHAT STATUS ANIMATSIYASI:</b> <code>YOQILDI</code>\n<i>(Yozmoqda, audio, video, rasm, fayl...)</i>", parse_mode="html")
        else:
            await event.edit("<b>STATUS ANIMATSIYASI:</b> <code>ALLAQACHON ISHLAYAPTI</code>", parse_mode="html")
        return

    # .untyp
    if text == ".untyp":
        if cid in active_tasks:
            task = active_tasks.pop(cid)
            task.cancel()
            await event.edit("<b>CHAT STATUS ANIMATSIYASI:</b> <code>TOXTATILDI</code>", parse_mode="html")
        else:
            await event.edit("<b>STATUS ANIMATSIYASI:</b> <code>YOQILMAGAN</code>", parse_mode="html")
        return

    # .info
    if text == ".info":
        uptime_sec = int(time.time() - START_TIME)
        hours = uptime_sec // 3600
        mins = (uptime_sec % 3600) // 60
        secs = uptime_sec % 60
        uptime_str = f"{hours}s {mins}m {secs}s"

        on_st = "YONIQ" if CONFIG["online"] else "OCHIQ"
        rd_st = "YONIQ" if CONFIG["read"] else "OCHIQ"
        act_cnt = len(active_tasks)

        table_text = (
            "<b>┌─────────────────────────┐</b>\n"
            "<b>│    USERBOT BOSHQARUV    │</b>\n"
            "<b>├─────────────────────────┤</b>\n"
            f"<b>│ AUTO-ONLINE :</b> <code>{on_st:<10}</code><b>│</b>\n"
            f"<b>│ AUTO-READ   :</b> <code>{rd_st:<10}</code><b>│</b>\n"
            f"<b>│ FAOL CHATLAR:</b> <code>{act_cnt:<10}</code><b>│</b>\n"
            f"<b>│ UPTIME      :</b> <code>{uptime_str:<10}</code><b>│</b>\n"
            "<b>└─────────────────────────┘</b>\n"
            "<b>Buyruqlar:</b> <code>.on</code> <code>.off</code> <code>.typ</code> <code>.untyp</code> <code>.read</code> <code>.unread</code> <code>.ping</code>"
        )
        await event.edit(table_text, parse_mode="html")
        return

# 5. RENDER WEB SERVER (Uptime monitor uchun port)
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
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
