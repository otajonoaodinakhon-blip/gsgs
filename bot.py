#!/usr/bin/env python3
"""
Universal Media Downloader Bot
YouTube, Instagram, TikTok, Facebook va 1000+ saytdan video yuklab beradi
"""

import os
import sys
import json
import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import traceback

import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode

# ============= KONFIGURATSIYA =============
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    sys.exit("ERROR: BOT_TOKEN environment variable not set!")

PORT = int(os.environ.get("PORT", 8080))
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 50)) * 1024 * 1024  # MB to bytes
WEBHOOK_URL = f"https://{RENDER_HOST}/{BOT_TOKEN}" if RENDER_HOST else None

# ============= LOGGING =============
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============= YT-DLP SOZLAMALARI =============
YDL_OPTIONS = {
    'format': 'best[ext=mp4]/best',
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'no_color': True,
    'extract_flat': False,
    'retries': 3,
    'fragment_retries': 3,
    'file_access_retries': 3,
    'max_filesize': MAX_FILE_SIZE,
}

# ============= YORDAMCHI FUNKSIYALAR =============
def human_readable_size(size: int) -> str:
    """Fayl hajmini o'qishli formatga o'tkazish"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def sanitize_filename(filename: str) -> str:
    """Fayl nomidan maxsus belgilarni olib tashlash"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename[:100]  # Uzunlikni cheklash

# ============= CALLBACK DATA =============
class CallbackData:
    FORMAT_VIDEO = "format_video"
    FORMAT_AUDIO = "format_audio"
    QUALITY_360 = "quality_360"
    QUALITY_720 = "quality_720"
    QUALITY_1080 = "quality_1080"
    CANCEL = "cancel"
    DOWNLOAD_AGAIN = "download_again"

# ============= HANDLERLAR =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start komandasi"""
    user = update.effective_user
    welcome_text = f"""
🎬 <b>Universal Media Downloader Bot</b>

Assalomu alaykum, {user.first_name}! 👋

Men istalgan saytdan video/audio yuklab beraman:
• YouTube, Instagram, TikTok
• Facebook, Twitter, Reddit
• Va 1000+ boshqa saytlar

<b>📤 Qanday ishlatish:</b>
1. Menga link yuboring
2. Format va sifatni tanlang
3. Tayyor faylni yuklab oling

<b>⚡ Imkoniyatlar:</b>
• Video/MP4 | Audio/MP3
• 360p, 720p, 1080p
• 50 MB gacha (bepul server)

<b>👨‍💻 Admin:</b> @username
    """
    
    # Start tugmalari
    keyboard = [
        [InlineKeyboardButton("📥 Link yuborish", switch_inline_query="")],
        [InlineKeyboardButton("📚 Yordam", callback_data="help"),
         InlineKeyboardButton("📊 Stat", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yordam komandasi"""
    help_text = """
<b>📚 Yordam</b>

<b>Qo'llanma:</b>
• Link yuboring -> men yuklab beraman
• /start - Botni qayta ishga tushirish
• /cancel - Yuklab olishni bekor qilish
• /settings - Sozlamalar

<b>Qo'llab-quvvatlanadigan saytlar:</b>
✅ YouTube, Vimeo, Dailymotion
✅ Instagram (post, reel, story)
✅ TikTok, Twitter/X
✅ Facebook, Reddit
✅ Twitch, SoundCloud
✅ Va 1000+ boshqa!

<b>⚠️ Cheklovlar:</b>
• Maksimal hajm: 50 MB
• Yuklab olish vaqti: 5 daqiqa
• Fayl formati: MP4, MP3

<b>📞 Aloqa:</b> @admin
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yuklab olishni bekor qilish"""
    user_id = update.effective_user.id
    
    if 'download_task' in context.user_data:
        task = context.user_data['download_task']
        if not task.done():
            task.cancel()
            await update.message.reply_text("✅ Yuklab olish bekor qilindi")
        del context.user_data['download_task']
    else:
        await update.message.reply_text("❌ Faol yuklab olish yo'q")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tugmalar bosilganda ishlaydi"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "help":
        await help_command(update, context)
    
    elif data == "back_to_main":
        await start(update, context)
    
    elif data == "stats":
        stats_text = """
📊 <b>Bot statistikasi</b>

👥 Foydalanuvchilar: 1234
📥 Yuklab olishlar: 5678
💾 Saqlangan trafik: 45 GB
⚡ Holat: 🟢 Online
        """
        await query.edit_message_text(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")
            ]])
        )
    
    elif data == CallbackData.CANCEL:
        await query.edit_message_text("❌ Bekor qilindi")
    
    elif data == CallbackData.DOWNLOAD_AGAIN:
        await query.edit_message_text("Qayta yuklab olish uchun link yuboring")

async def get_video_info(url: str) -> Optional[Dict[str, Any]]:
    """Video haqida ma'lumot olish"""
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Noma\'lum'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Noma\'lum'),
                'view_count': info.get('view_count', 0),
                'filesize_approx': info.get('filesize_approx', 0),
                'formats': info.get('formats', [])
            }
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return None

async def download_with_progress(url: str, file_path: str, format_type: str, quality: str, message, context):
    """Progress bilan yuklab olish"""
    try:
        # Yt-dlp options
        ydl_opts = YDL_OPTIONS.copy()
        ydl_opts['outtmpl'] = file_path
        
        if format_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:  # video
            if quality == '1080':
                ydl_opts['format'] = 'best[height<=1080][ext=mp4]/best[height<=1080]'
            elif quality == '720':
                ydl_opts['format'] = 'best[height<=720][ext=mp4]/best[height<=720]'
            elif quality == '360':
                ydl_opts['format'] = 'best[height<=360][ext=mp4]/best[height<=360]'
            else:
                ydl_opts['format'] = 'best[ext=mp4]/best'
        
        # Progress hook
        def progress_hook(d):
            if d['status'] == 'downloading':
                if d.get('total_bytes'):
                    percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                    asyncio.create_task(
                        message.edit_text(f"📥 Yuklab olinmoqda: {percent:.1f}%")
                    )
        
        ydl_opts['progress_hooks'] = [progress_hook]
        
        # Yuklab olish
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await message.edit_text("⏳ Yuklab olinmoqda...")
            ydl.download([url])
        
        return True
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi xabarlarini qayta ishlash"""
    # Faqat linklarni qabul qilish
    text = update.message.text
    if not text.startswith(('http://', 'https://')):
        await update.message.reply_text(
            "❌ Iltimos, to'g'ri link yuboring!\n"
            "Misol: https://youtube.com/watch?v=..."
        )
        return
    
    url = text.strip()
    user_id = update.effective_user.id
    
    # Yuklab olish boshlanganini bildirish
    status_msg = await update.message.reply_text("🔍 Ma'lumot olinmoqda...")
    
    try:
        # Video ma'lumotini olish
        info = await get_video_info(url)
        if not info:
            await status_msg.edit_text("❌ Video ma'lumotlarini olishda xatolik")
            return
        
        # Format tanlash tugmalari
        keyboard = [
            [
                InlineKeyboardButton("🎬 Video (MP4)", callback_data=CallbackData.FORMAT_VIDEO),
                InlineKeyboardButton("🎵 Audio (MP3)", callback_data=CallbackData.FORMAT_AUDIO)
            ],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data=CallbackData.CANCEL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Video haqida ma'lumot
        duration = info['duration']
        duration_str = f"{duration//60}:{duration%60:02d}" if duration else "Noma'lum"
        
        info_text = f"""
📹 <b>Video topildi!</b>

<b>Nomi:</b> {info['title'][:50]}
<b>Muallif:</b> {info['uploader']}
<b>Davomiyligi:</b> {duration_str}
<b>Ko'rishlar:</b> {info['view_count']:,}
<b>Taxminiy hajm:</b> {human_readable_size(info['filesize_approx'])}

Formatni tanlang:
        """
        
        # Saqlash
        context.user_data['url'] = url
        context.user_data['info'] = info
        
        await status_msg.edit_text(
            info_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error: {traceback.format_exc()}")
        await status_msg.edit_text(f"❌ Xatolik: {str(e)[:100]}")

async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Format tanlangandan keyin"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data in [CallbackData.FORMAT_VIDEO, CallbackData.FORMAT_AUDIO]:
        # Formatni saqlash
        context.user_data['format'] = 'video' if data == CallbackData.FORMAT_VIDEO else 'audio'
        
        # Sifat tanlash tugmalari
        keyboard = []
        if data == CallbackData.FORMAT_VIDEO:
            keyboard = [
                [
                    InlineKeyboardButton("360p", callback_data=CallbackData.QUALITY_360),
                    InlineKeyboardButton("720p", callback_data=CallbackData.QUALITY_720),
                    InlineKeyboardButton("1080p", callback_data=CallbackData.QUALITY_1080)
                ],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data=CallbackData.CANCEL)]
            ]
        else:  # Audio
            # Audio uchun to'g'ridan-to'g'ri yuklab olish
            await start_download(update, context, quality='audio')
            return
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📊 Sifatni tanlang:",
            reply_markup=reply_markup
        )
    
    elif data in [CallbackData.QUALITY_360, CallbackData.QUALITY_720, CallbackData.QUALITY_1080]:
        quality = data.split('_')[1]
        await start_download(update, context, quality=quality)

async def start_download(update: Update, context: ContextTypes.DEFAULT_TYPE, quality: str):
    """Yuklab olishni boshlash"""
    query = update.callback_query
    await query.answer()
    
    url = context.user_data.get('url')
    format_type = context.user_data.get('format', 'video')
    user_id = update.effective_user.id
    
    if not url:
        await query.edit_message_text("❌ Xatolik: Link topilmadi")
        return
    
    # Yuklab olish boshlanganini bildirish
    await query.edit_message_text("⏳ Yuklab olinmoqda, biroz kuting...")
    
    # Vaqtinchalik fayl nomi
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4' if format_type == 'video' else '.mp3') as tmp_file:
        file_path = tmp_file.name
    
    try:
        # Yuklab olish
        success = await download_with_progress(url, file_path, format_type, quality, query.message, context)
        
        if not success:
            await query.edit_message_text("❌ Yuklab olishda xatolik")
            return
        
        # Fayl hajmini tekshirish
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            await query.edit_message_text(f"❌ Fayl juda katta ({human_readable_size(file_size)}). Maksimal: 50 MB")
            return
        
        # Faylni yuborish
        await query.edit_message_text("📤 Fayl tayyor, yuborilyapti...")
        
        with open(file_path, 'rb') as f:
            caption = f"✅ {context.user_data['info']['title'][:30]}..."
            if format_type == 'video':
                await context.bot.send_video(
                    chat_id=update.effective_user.id,
                    video=f,
                    caption=caption,
                    supports_streaming=True
                )
            else:
                await context.bot.send_audio(
                    chat_id=update.effective_user.id,
                    audio=f,
                    caption=caption
                )
        
        # Faylni o'chirish
        os.remove(file_path)
        
        # Qayta yuklash tugmasi
        keyboard = [[InlineKeyboardButton("📥 Qayta yuklash", callback_data=CallbackData.DOWNLOAD_AGAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✅ Yuklab olish tugadi!",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Download error: {traceback.format_exc()}")
        await query.edit_message_text(f"❌ Xatolik: {str(e)[:100]}")
        if os.path.exists(file_path):
            os.remove(file_path)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xatoliklarni qayta ishlash"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Texnik xatolik yuz berdi. Iltimos qaytadan urinib ko'ring."
            )
    except:
        pass

# ============= ASOSIY FUNKSIYA =============
def main() -> None:
    """Botni ishga tushirish"""
    logger.info("Starting bot...")
    logger.info(f"Max file size: {MAX_FILE_SIZE / 1024 / 1024} MB")
    
    # Bot yaratish
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(help|back_to_main|stats)$"))
    app.add_handler(CallbackQueryHandler(format_callback))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Webhook yoki polling
    if RENDER_HOST:
        logger.info(f"Starting webhook on port {PORT}")
        logger.info(f"Webhook URL: {WEBHOOK_URL}")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=WEBHOOK_URL
        )
    else:
        logger.info("Starting polling...")
        app.run_polling()

if __name__ == "__main__":
    main()
