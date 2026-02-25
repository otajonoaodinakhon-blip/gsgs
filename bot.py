import os, yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))

async def start(update: Update, context):
    await update.message.reply_text("Link yubor:")

async def download(update: Update, context):
    msg = await update.message.reply_text("⏳...")
    try:
        f = f"/tmp/{update.message.from_user.id}.mp4"
        yt_dlp.YoutubeDL({'format':'best','outtmpl':f}).download([update.message.text])
        await update.message.reply_document(open(f,'rb'))
        os.remove(f)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"Xato")

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))

app.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}")
