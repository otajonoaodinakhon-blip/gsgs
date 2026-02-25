import os
import yt_dlp
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Render environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7848692560:AAGn_x-fLq7oReI5SYD4zBvC78cB6sTgj0U")
PORT = int(os.environ.get("PORT", 8080))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Link yuboring, men yuklab beraman")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 Yuklab olyapman...")
    url = update.message.text
    
    try:
        filename = f"video_{update.message.from_user.id}.mp4"
        
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': filename,
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
            with open(filename, 'rb') as f:
                await update.message.reply_document(f)
            
            os.remove(filename)
            
        await msg.delete()
        
    except Exception as e:
        await msg.edit_text(f"Xatolik: {str(e)[:50]}")

def main():
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Webhook for Render
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()