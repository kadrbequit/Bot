import os
import json
import time
import logging
from datetime import datetime
from flask import Flask, send_file, abort
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler


BOT_TOKEN = "8885929210:AAFeZn3_dXmSbqixrkcupHPTq0-x8u6iqRo"
ADMIN_ID = 8960531687


BASE_URL = "BASE_URL = "https://bot-td5t.onrender.com""  # ⚠️ SONRA DEĞİŞTİR!

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"files": {}, "stats": {"total_uploads": 0, "total_downloads": 0}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route('/download/<file_id>')
def download_file(file_id):
    if file_id not in data["files"]:
        return "❌ Dosya bulunamadı!", 404
    
    file_info = data["files"][file_id]
    file_path = os.path.join(UPLOAD_DIR, file_info["filename"])
    
    if not os.path.exists(file_path):
        return "❌ Dosya mevcut değil!", 404
    
    data["stats"]["total_downloads"] += 1
    file_info["download_count"] = file_info.get("download_count", 0) + 1
    file_info["last_download"] = datetime.now().isoformat()
    save_data(data)
    
    return send_file(file_path, as_attachment=True, download_name=file_info["original_name"])

@app.route('/')
def home():
    return "🤖 Dosya Botu Çalışıyor!"

@app.route('/stats')
def stats_page():
    return f"""
    <h1>📊 Bot İstatistikleri</h1>
    <p>Toplam Yüklenen Dosya: {data['stats']['total_uploads']}</p>
    <p>Toplam İndirme: {data['stats']['total_downloads']}</p>
    <p>Aktif Dosya: {len(data['files'])}</p>
    <hr>
    <h3>Son Dosyalar:</h3>
    <ul>
    {''.join([f"<li>{v['original_name']} - {v.get('download_count',0)} indirme</li>" for k,v in list(data['files'].items())[-5:]])}
    </ul>
    """


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🤖 *Dosya Paylaşım Botu*\n\n"
        "📤 Sadece admin dosya yükleyebilir.\n"
        "📥 Herkes linkten dosyayı indirebilir.\n\n"
        "📊 `/stats` - İstatistikleri göster\n"
        "📁 `/list` - Tüm dosyaları listele\n"
        "🗑 `/del <id>` - Dosya sil (admin)",
        parse_mode="Markdown"
    )

async def handle_file(update: Update, context: CallbackContext):
    user = update.effective_user
    
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sadece admin dosya yükleyebilir!")
        return
    
    doc = update.message.document
    file_id = str(int(time.time() * 1000)) + "_" + str(user.id)
    
    file = await context.bot.get_file(doc.file_id)
    original_name = doc.file_name or "dosya"
    file_path = os.path.join(UPLOAD_DIR, file_id)
    await file.download_to_drive(file_path)
    
    data["files"][file_id] = {
        "original_name": original_name,
        "filename": file_id,
        "uploaded_by": user.id,
        "uploaded_at": datetime.now().isoformat(),
        "download_count": 0,
        "file_size": doc.file_size
    }
    data["stats"]["total_uploads"] += 1
    save_data(data)
    
    link = f"{BASE_URL}/download/{file_id}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Dosyayı İndir", url=link)],
        [InlineKeyboardButton("📊 İstatistikler", callback_data=f"stats_{file_id}")]
    ])
    
    await update.message.reply_text(
        f"✅ *Dosya yüklendi!*\n\n"
        f"📄 {original_name}\n"
        f"📦 {doc.file_size // 1024} KB\n"
        f"🔗 {link}\n\n"
        f"Bu linki herkesle paylaşabilirsin.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def stats_command(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bu komut sadece admin içindir.")
        return
    
    msg = f"📊 *Bot İstatistikleri*\n\n"
    msg += f"📁 Toplam Dosya: {data['stats']['total_uploads']}\n"
    msg += f"⬇️ Toplam İndirme: {data['stats']['total_downloads']}\n"
    msg += f"📂 Aktif Dosya: {len(data['files'])}\n\n"
    msg += "*Son 5 Dosya:*\n"
    for fid, finfo in list(data["files"].items())[-5:]:
        msg += f"• {finfo['original_name']} - {finfo.get('download_count',0)} indirme\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def list_command(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bu komut sadece admin içindir.")
        return
    
    if not data["files"]:
        await update.message.reply_text("📭 Henüz hiç dosya yüklenmemiş.")
        return
    
    msg = "📁 *Tüm Dosyalar:*\n\n"
    for fid, finfo in list(data["files"].items())[-20:]:
        msg += f"• {finfo['original_name']}\n"
        msg += f"  ID: `{fid}`\n"
        msg += f"  İndirme: {finfo.get('download_count',0)}\n\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def delete_command(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sadece admin silebilir.")
        return
    
    if not context.args:
        await update.message.reply_text("Kullanım: `/del <dosya_id>`", parse_mode="Markdown")
        return
    
    file_id = context.args[0]
    if file_id not in data["files"]:
        await update.message.reply_text("❌ Dosya bulunamadı.")
        return
    
    file_path = os.path.join(UPLOAD_DIR, data["files"][file_id]["filename"])
    if os.path.exists(file_path):
        os.remove(file_path)
    
    name = data["files"][file_id]["original_name"]
    del data["files"][file_id]
    save_data(data)
    
    await update.message.reply_text(f"✅ `{name}` silindi.", parse_mode="Markdown")

async def stats_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    file_id = query.data.replace("stats_", "")
    if file_id not in data["files"]:
        await query.edit_message_text("❌ Dosya bulunamadı.")
        return
    
    finfo = data["files"][file_id]
    msg = f"📄 *{finfo['original_name']}*\n\n"
    msg += f"⬇️ İndirme: {finfo.get('download_count', 0)}\n"
    msg += f"📅 Yükleme: {finfo['uploaded_at'][:10]}\n"
    msg += f"📦 Boyut: {finfo['file_size'] // 1024} KB"
    
    await query.edit_message_text(msg, parse_mode="Markdown")


if __name__ == "__main__":
    from threading import Thread
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("del", delete_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_handler(CallbackQueryHandler(stats_callback, pattern="^stats_"))
    
    def run_flask():
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    
    Thread(target=run_flask).start()
    
    print("🤖 Bot çalışıyor...")
    print(f"🔗 Base URL: {BASE_URL}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
