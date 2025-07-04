#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ===== ایمپورت‌ها =====
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import math

# Telegram imports
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# Cloudflare
import CloudFlare

# تنظیمات
from config import BOT_TOKEN, CF_API_TOKEN, ADMIN_IDS, LOG_LEVEL

# بررسی تنظیمات
if not BOT_TOKEN:
    raise ValueError("لطفا BOT_TOKEN را در config.py تنظیم کنید")
if not CF_API_TOKEN:
    raise ValueError("لطفا CF_API_TOKEN را در config.py تنظیم کنید")
if not ADMIN_IDS:
    raise ValueError("لطفا ADMIN_IDS را در config.py تنظیم کنید")

# ===== تنظیم لاگینگ =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== متغیرهای سراسری =====
user_data = {}
RECORDS_PER_PAGE = 8  # تعداد رکورد در هر صفحه

# ===== State ها برای ConversationHandler =====
(MAIN_MENU, SELECT_DOMAIN, SELECT_RECORD, RECORD_ACTIONS,
 EDIT_CONTENT, ADD_RECORD_DOMAIN, ADD_RECORD_TYPE, 
 ADD_RECORD_NAME, ADD_RECORD_CONTENT, CONFIRM_DELETE,
 SEARCH_QUERY, CHANGE_TYPE_SELECT, CHANGE_TYPE_CONTENT,
 NAVIGATE_RECORDS) = range(14)

# ===== کیبوردها =====
def get_main_keyboard():
    """کیبورد اصلی"""
    keyboard = [
        ["🌐 لیست دامنه‌ها", "➕ رکورد جدید"],
        ["🔍 جستجو", "📊 گزارشات"],
        ["📈 آمار", "❓ راهنما"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    """کیبورد لغو"""
    keyboard = [["❌ لغو عملیات"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_domains_keyboard(domains):
    """کیبورد دامنه‌ها"""
    keyboard = []
    for name, _ in domains:
        keyboard.append([f"🌐 {name}"])
    keyboard.append(["🔙 بازگشت به منو"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_records_keyboard_paginated(records, page=1, records_per_page=RECORDS_PER_PAGE):
    """کیبورد رکوردها با صفحه‌بندی"""
    keyboard = []
    
    # محاسبه تعداد صفحات
    total_pages = math.ceil(len(records) / records_per_page)
    
    # محاسبه ایندکس شروع و پایان
    start_idx = (page - 1) * records_per_page
    end_idx = min(start_idx + records_per_page, len(records))
    
    # گروه‌بندی رکوردها
    grouped = {}
    for record in records:
        record_type = record['type']
        if record_type not in grouped:
            grouped[record_type] = []
        grouped[record_type].append(record)
    
    # شمارنده برای رکوردهای نمایش داده شده
    displayed = 0
    current_records = []
    
    # جمع‌آوری رکوردهای صفحه جاری
    for record_type in sorted(grouped.keys()):
        for record in grouped[record_type]:
            if displayed >= start_idx and displayed < end_idx:
                current_records.append((record_type, record))
            displayed += 1
            if displayed >= end_idx:
                break
        if displayed >= end_idx:
            break
    
    # ایجاد کیبورد
    current_type = None
    for record_type, record in current_records:
        if record_type != current_type:
            keyboard.append([f"━━━ {record_type} Records ━━━"])
            current_type = record_type
        
        proxied = "🟠" if record.get('proxied') else "⚪"
        button_text = f"{proxied} {record['name']}"
        keyboard.append([button_text])
    
    # دکمه‌های ناوبری
    nav_buttons = []
    if page > 1:
        nav_buttons.append("⬅️ صفحه قبل")
    
    nav_buttons.append(f"📄 صفحه {page} از {total_pages}")
    
    if page < total_pages:
        nav_buttons.append("صفحه بعد ➡️")
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # اطلاعات تعداد
    keyboard.append([f"📊 مجموع: {len(records)} رکورد"])
    
    # دکمه بازگشت
    keyboard.append(["🔙 بازگشت به دامنه‌ها"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_record_actions_keyboard(record_type):
    """کیبورد عملیات روی رکورد"""
    keyboard = [
        ["✏️ ویرایش محتوا"],
        ["🔄 تغییر نوع رکورد"],
        ["🗑️ حذف رکورد"]
    ]
    
    if record_type in ['A', 'AAAA', 'CNAME']:
        keyboard.insert(1, ["🔄 تغییر وضعیت Proxy"])
    
    keyboard.append(["🔙 بازگشت به رکوردها"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_record_types_keyboard():
    """کیبورد انواع رکورد"""
    keyboard = [
        ["A", "AAAA", "CNAME"],
        ["MX", "TXT", "NS"],
        ["CAA", "SRV"],
        ["❌ لغو"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_yes_no_keyboard():
    """کیبورد بله/خیر"""
    keyboard = [
        ["✅ بله", "❌ خیر"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# ===== کلاس‌ها =====
class ChangeLogger:
    """لاگ تغییرات"""
    def __init__(self, filename='changes.log'):
        self.filename = filename

    def log_change(self, user_id, username, action, domain, record_name, details):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'user_id': user_id,
            'username': username,
            'action': action,
            'domain': domain,
            'record_name': record_name,
            'details': details
        }
        
        with open(self.filename, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def get_recent_logs(self, limit=10):
        if not os.path.exists(self.filename):
            return []
        
        logs = []
        with open(self.filename, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    logs.append(json.loads(line.strip()))
                except:
                    continue
        
        return logs[-limit:]

class CloudflareManager:
    """مدیریت Cloudflare"""
    def __init__(self, api_token):
        self.cf = CloudFlare.CloudFlare(token=api_token)

    def get_zones(self):
        """دریافت لیست دامنه‌ها"""
        try:
            zones = self.cf.zones.get()
            return [(zone['name'], zone['id']) for zone in zones]
        except Exception as e:
            logger.error(f"Error getting zones: {e}")
            return []

    def get_dns_records(self, zone_id, record_type=None):
        """دریافت رکوردهای DNS"""
        try:
            params = {}
            if record_type:
                params['type'] = record_type
            
            records = self.cf.zones.dns_records.get(zone_id, params=params)
            
            # فیلتر رکوردهای مهم
            important_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'CAA', 'SRV']
            filtered_records = [r for r in records if r['type'] in important_types]
            
            return filtered_records
        except Exception as e:
            logger.error(f"Error getting DNS records: {e}")
            return []

    def get_record_details(self, zone_id, record_id):
        """دریافت جزئیات رکورد"""
        try:
            return self.cf.zones.dns_records.get(zone_id, record_id)
        except Exception as e:
            logger.error(f"Error getting record details: {e}")
            return None

    def update_dns_record(self, zone_id, record_id, data):
        """به‌روزرسانی رکورد"""
        try:
            current = self.get_record_details(zone_id, record_id)
            if not current:
                return False, "رکورد یافت نشد"
            
            update_data = {
                'type': current['type'],
                'name': current['name'],
                'content': data.get('content', current['content']),
                'ttl': data.get('ttl', current.get('ttl', 1)),
                'proxied': data.get('proxied', current.get('proxied', False))
            }
            
            self.cf.zones.dns_records.put(zone_id, record_id, data=update_data)
            return True, "رکورد با موفقیت به‌روزرسانی شد!"
        except Exception as e:
            logger.error(f"Error updating DNS record: {e}")
            return False, f"خطا: {str(e)}"

    def create_dns_record(self, zone_id, data):
        """ایجاد رکورد جدید"""
        try:
            self.cf.zones.dns_records.post(zone_id, data=data)
            return True, "رکورد با موفقیت ایجاد شد!"
        except Exception as e:
            logger.error(f"Error creating DNS record: {e}")
            return False, f"خطا: {str(e)}"

    def delete_dns_record(self, zone_id, record_id):
        """حذف رکورد"""
        try:
            self.cf.zones.dns_records.delete(zone_id, record_id)
            return True, "رکورد با موفقیت حذف شد!"
        except Exception as e:
            logger.error(f"Error deleting DNS record: {e}")
            return False, f"خطا: {str(e)}"

    def search_records(self, search_term):
        """جستجو در تمام رکوردها"""
        results = []
        zones = self.get_zones()
        
        for zone_name, zone_id in zones:
            records = self.get_dns_records(zone_id)
            for record in records:
                if (search_term.lower() in record['name'].lower() or 
                    search_term.lower() in record['content'].lower()):
                    results.append({
                        'zone_name': zone_name,
                        'zone_id': zone_id,
                        'record': record
                    })
        
        return results

# ===== ایجاد instance ها =====
cf_manager = CloudflareManager(CF_API_TOKEN)
change_logger = ChangeLogger()

# ===== دکوریتور چک ادمین =====
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ شما اجازه استفاده از این ربات را ندارید.")
            return ConversationHandler.END
        return await func(update, context)
    return wrapper

# ===== هندلرهای اصلی =====
@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ربات"""
    user = update.effective_user
    
    # پاک کردن داده‌های قبلی
    context.user_data.clear()
    
    await update.message.reply_text(
        f"🌐 **ربات مدیریت Cloudflare**\n\n"
        f"سلام {user.first_name} عزیز! 👋\n\n"
        "از منوی زیر گزینه مورد نظر را انتخاب کنید:",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    
    return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش منوی اصلی"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🌐 لیست دامنه‌ها":
        zones = cf_manager.get_zones()
        if not zones:
            await update.message.reply_text("❌ هیچ دامنه‌ای یافت نشد!")
            return MAIN_MENU
        
        context.user_data['zones'] = zones
        await update.message.reply_text(
            "🔍 دامنه مورد نظر را انتخاب کنید:",
            reply_markup=get_domains_keyboard(zones)
        )
        return SELECT_DOMAIN
    
    elif text == "➕ رکورد جدید":
        zones = cf_manager.get_zones()
        if not zones:
            await update.message.reply_text("❌ هیچ دامنه‌ای یافت نشد!")
            return MAIN_MENU
        
        context.user_data['zones'] = zones
        context.user_data['action'] = 'add_record'
        await update.message.reply_text(
            "دامنه‌ای که می‌خواهید رکورد جدید به آن اضافه کنید را انتخاب کنید:",
            reply_markup=get_domains_keyboard(zones)
        )
        return ADD_RECORD_DOMAIN
    
    elif text == "🔍 جستجو":
        await update.message.reply_text(
            "🔍 عبارت مورد نظر برای جستجو را وارد کنید:\n\n"
            "می‌توانید نام رکورد یا محتوای آن را جستجو کنید.",
            reply_markup=get_cancel_keyboard()
        )
        return SEARCH_QUERY
    
    elif text == "📊 گزارشات":
        logs = change_logger.get_recent_logs(15)
        if not logs:
            await update.message.reply_text(
                "📊 هیچ گزارشی ثبت نشده است!",
                reply_markup=get_main_keyboard()
            )
            return MAIN_MENU
        
        text = "📊 **گزارش تغییرات اخیر:**\n\n"
        for log in logs:
            action_emoji = {
                'CREATE': '➕',
                'UPDATE': '✏️',
                'DELETE': '🗑️',
                'PROXY_TOGGLE': '🔄'
            }.get(log['action'], '📌')
            
            text += f"{action_emoji} {log['timestamp']}\n"
            text += f"👤 {log['username']}\n"
            text += f"🌐 {log['domain']} - {log['record_name']}\n"
            text += f"📝 {log['details']}\n\n"
        
        await update.message.reply_text(
            text,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        return MAIN_MENU
    
    elif text == "📈 آمار":
        zones = cf_manager.get_zones()
        total_records = 0
        
        text = "📈 **آمار کلی سیستم:**\n\n"
        text += f"🌐 تعداد دامنه‌ها: {len(zones)}\n\n"
        
        for zone_name, zone_id in zones:
            records = cf_manager.get_dns_records(zone_id)
            total_records += len(records)
            
            type_counts = {}
            for record in records:
                record_type = record['type']
                type_counts[record_type] = type_counts.get(record_type, 0) + 1
            
            text += f"**{zone_name}:**\n"
            for rtype, count in sorted(type_counts.items()):
                text += f"  • {rtype}: {count}\n"
            text += f"  📊 مجموع: {len(records)}\n\n"
        
        text += f"💠 **مجموع کل رکوردها: {total_records}**"
        
        await update.message.reply_text(
            text,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        return MAIN_MENU
    
    elif text == "❓ راهنما":
        help_text = """
❓ **راهنمای استفاده از ربات**

**دستورات:**
- /start - شروع ربات
- /cancel - لغو عملیات جاری

**قابلیت‌ها:**
🌐 **مدیریت دامنه‌ها:**
- مشاهده لیست دامنه‌ها و رکوردها
- صفحه‌بندی برای نمایش همه رکوردها
- مدیریت کامل رکوردهای DNS

✏️ **ویرایش رکوردها:**
- تغییر محتوای رکورد
- تغییر نوع رکورد
- تغییر وضعیت Proxy

➕ **افزودن رکورد جدید**

🗑️ **حذف رکورد**

🔍 **جستجو در رکوردها**

📊 **گزارشات و آمار**

**نکات:**
- از دکمه‌های ناوبری برای حرکت بین صفحات استفاده کنید
- تمام تغییرات در سیستم ثبت می‌شود
        """
        
        await update.message.reply_text(
            help_text,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        return MAIN_MENU
    
    return MAIN_MENU

async def select_domain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب دامنه"""
    text = update.message.text
    
    if text == "🔙 بازگشت به منو":
        await update.message.reply_text(
            "منوی اصلی:",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    # پیدا کردن دامنه
    zone_name = text.replace("🌐 ", "")
    zones = context.user_data.get('zones', [])
    
    zone_id = None
    for name, id in zones:
        if name == zone_name:
            zone_id = id
            break
    
    if not zone_id:
        await update.message.reply_text("❌ دامنه یافت نشد!")
        return SELECT_DOMAIN
    
    # ذخیره اطلاعات
    context.user_data['current_zone_id'] = zone_id
    context.user_data['current_zone_name'] = zone_name
    context.user_data['current_page'] = 1
    
    # دریافت رکوردها
    records = cf_manager.get_dns_records(zone_id)
    
    if not records:
        await update.message.reply_text(
            "❌ هیچ رکوردی یافت نشد!",
            reply_markup=get_domains_keyboard(zones)
        )
        return SELECT_DOMAIN
    
    context.user_data['records'] = records
    
    await update.message.reply_text(
        f"📋 رکوردهای دامنه **{zone_name}**\n"
        f"تعداد: {len(records)} رکورد\n\n"
        "رکورد مورد نظر را انتخاب کنید:",
        reply_markup=get_records_keyboard_paginated(records, page=1),
        parse_mode='Markdown'
    )
    
    return SELECT_RECORD

async def navigate_records(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ناوبری بین صفحات رکوردها"""
    text = update.message.text
    
    records = context.user_data.get('records', [])
    current_page = context.user_data.get('current_page', 1)
    zone_name = context.user_data.get('current_zone_name', '')
    
    # تغییر صفحه
    if "⬅️ صفحه قبل" in text:
        current_page = max(1, current_page - 1)
    elif "صفحه بعد ➡️" in text:
        total_pages = math.ceil(len(records) / RECORDS_PER_PAGE)
        current_page = min(total_pages, current_page + 1)
    
    context.user_data['current_page'] = current_page
    
    await update.message.reply_text(
        f"📋 رکوردهای دامنه **{zone_name}**\n"
        f"تعداد: {len(records)} رکورد\n\n"
        "رکورد مورد نظر را انتخاب کنید:",
        reply_markup=get_records_keyboard_paginated(records, page=current_page),
        parse_mode='Markdown'
    )
    
    return SELECT_RECORD

async def select_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب رکورد"""
    text = update.message.text
    
    # بررسی دکمه‌های ناوبری
    if "⬅️ صفحه قبل" in text or "صفحه بعد ➡️" in text:
        return await navigate_records(update, context)
    
    if text == "🔙 بازگشت به دامنه‌ها":
        zones = context.user_data.get('zones', [])
        await update.message.reply_text(
            "🔍 دامنه مورد نظر را انتخاب کنید:",
            reply_markup=get_domains_keyboard(zones)
        )
        return SELECT_DOMAIN
    
    if text.startswith("━━━") or text.startswith("📄 صفحه") or text.startswith("📊 مجموع"):
        return SELECT_RECORD
    
    # پیدا کردن رکورد
    record_name = text.replace("🟠 ", "").replace("⚪ ", "")
    records = context.user_data.get('records', [])
    
    selected_record = None
    for record in records:
        if record['name'] == record_name:
            selected_record = record
            break
    
    if not selected_record:
        await update.message.reply_text("❌ رکورد یافت نشد!")
        return SELECT_RECORD
    
    context.user_data['selected_record'] = selected_record
    
    # نمایش جزئیات
    text = f"🔍 **جزئیات رکورد**\n\n"
    text += f"🏷️ نام: `{selected_record['name']}`\n"
    text += f"📌 نوع: `{selected_record['type']}`\n"
    text += f"📋 محتوا: `{selected_record['content']}`\n"
    text += f"⏱️ TTL: {selected_record.get('ttl', 'Auto')}\n"
    
    if selected_record['type'] in ['A', 'AAAA', 'CNAME']:
        proxied_status = "فعال 🟠" if selected_record.get('proxied') else "غیرفعال ⚪"
        text += f"🛡️ Proxy: {proxied_status}\n"
    
    text += "\nعملیات مورد نظر را انتخاب کنید:"
    
    await update.message.reply_text(
        text,
        reply_markup=get_record_actions_keyboard(selected_record['type']),
        parse_mode='Markdown'
    )
    
    return RECORD_ACTIONS

async def record_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عملیات روی رکورد"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🔙 بازگشت به رکوردها":
        records = context.user_data.get('records', [])
        zone_name = context.user_data.get('current_zone_name', '')
        current_page = context.user_data.get('current_page', 1)
        
        await update.message.reply_text(
            f"📋 رکوردهای دامنه **{zone_name}**",
            reply_markup=get_records_keyboard_paginated(records, page=current_page),
            parse_mode='Markdown'
        )
        return SELECT_RECORD
    
    selected_record = context.user_data.get('selected_record')
    if not selected_record:
        await update.message.reply_text("❌ خطا در پردازش!")
        return MAIN_MENU
    
    zone_id = context.user_data.get('current_zone_id')
    zone_name = context.user_data.get('current_zone_name')
    
    if text == "✏️ ویرایش محتوا":
        record_type = selected_record['type']
        examples = {
            'A': "192.168.1.1",
            'AAAA': "2001:db8::1",
            'CNAME': "target.example.com",
            'MX': "10 mail.example.com",
            'TXT': '"v=spf1 include:example.com ~all"',
            'NS': "ns1.example.com",
            'CAA': '0 issue "letsencrypt.org"',
            'SRV': "10 60 5060 sipserver.example.com"
        }
        
        example = examples.get(record_type, "example.com")
        
        await update.message.reply_text(
            f"📝 محتوای جدید را وارد کنید:\n\n"
            f"نوع رکورد: **{record_type}**\n"
            f"مثال: `{example}`",
            reply_markup=get_cancel_keyboard(),
            parse_mode='Markdown'
        )
        return EDIT_CONTENT
    
    elif text == "🔄 تغییر وضعیت Proxy":
        new_proxied = not selected_record.get('proxied', False)
        
        success, message = cf_manager.update_dns_record(
            zone_id,
            selected_record['id'],
            {'proxied': new_proxied}
        )
        
        if success:
            status = "Proxied" if new_proxied else "DNS Only"
            change_logger.log_change(
                user_id,
                update.effective_user.username,
                "PROXY_TOGGLE",
                zone_name,
                selected_record['name'],
                f"Changed to {status}"
            )
            
            await update.message.reply_text(
                f"✅ وضعیت Proxy به {status} تغییر کرد!",
                reply_markup=get_main_keyboard()
            )
            return MAIN_MENU
        else:
            await update.message.reply_text(f"❌ {message}")
            return RECORD_ACTIONS
    
    elif text == "🔄 تغییر نوع رکورد":
        await update.message.reply_text(
            f"🔄 **تغییر نوع رکورد**\n\n"
            f"نوع فعلی: `{selected_record['type']}`\n\n"
            "نوع جدید را انتخاب کنید:",
            reply_markup=get_record_types_keyboard(),
            parse_mode='Markdown'
        )
        return CHANGE_TYPE_SELECT
    
    elif text == "🗑️ حذف رکورد":
        await update.message.reply_text(
            f"⚠️ **آیا از حذف این رکورد مطمئن هستید؟**\n\n"
            f"🏷️ نام: `{selected_record['name']}`\n"
            f"📌 نوع: `{selected_record['type']}`\n"
            f"📋 محتوا: `{selected_record['content']}`\n\n"
            "این عملیات قابل بازگشت نیست!",
            reply_markup=get_yes_no_keyboard(),
            parse_mode='Markdown'
        )
        return CONFIRM_DELETE
    
    return RECORD_ACTIONS

async def edit_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ویرایش محتوا"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "❌ لغو عملیات":
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    selected_record = context.user_data.get('selected_record')
    zone_id = context.user_data.get('current_zone_id')
    zone_name = context.user_data.get('current_zone_name')
    
    success, message = cf_manager.update_dns_record(
        zone_id,
        selected_record['id'],
        {'content': text}
    )
    
    if success:
        change_logger.log_change(
            user_id,
            update.effective_user.username,
            "UPDATE",
            zone_name,
            selected_record['name'],
            f"Content changed from '{selected_record['content']}' to '{text}'"
        )
        
        await update.message.reply_text(
            "✅ رکورد با موفقیت به‌روزرسانی شد!",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    else:
        await update.message.reply_text(
            f"❌ {message}\n\nدوباره امتحان کنید:",
            reply_markup=get_cancel_keyboard()
        )
        return EDIT_CONTENT

async def add_record_domain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب دامنه برای افزودن رکورد"""
    text = update.message.text
    
    if text == "🔙 بازگشت به منو":
        await update.message.reply_text(
            "منوی اصلی:",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    zone_name = text.replace("🌐 ", "")
    zones = context.user_data.get('zones', [])
    
    zone_id = None
    for name, id in zones:
        if name == zone_name:
            zone_id = id
            break
    
    if not zone_id:
        await update.message.reply_text("❌ دامنه یافت نشد!")
        return ADD_RECORD_DOMAIN
    
    context.user_data['add_zone_id'] = zone_id
    context.user_data['add_zone_name'] = zone_name
    
    await update.message.reply_text(
        "📝 نوع رکورد جدید را انتخاب کنید:",
        reply_markup=get_record_types_keyboard()
    )
    
    return ADD_RECORD_TYPE

async def add_record_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب نوع رکورد جدید"""
    text = update.message.text
    
    if text == "❌ لغو":
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    if text not in ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'CAA', 'SRV']:
        await update.message.reply_text("❌ نوع رکورد نامعتبر!")
        return ADD_RECORD_TYPE
    
    context.user_data['add_record_type'] = text
    zone_name = context.user_data.get('add_zone_name', '')
    
    await update.message.reply_text(
        f"📝 **ایجاد رکورد {text}**\n\n"
        "نام رکورد را وارد کنید:\n"
        f"مثال: `subdomain` یا `subdomain.{zone_name}`\n\n"
        "برای رکورد اصلی دامنه از @ استفاده کنید",
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    
    return ADD_RECORD_NAME

async def add_record_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام رکورد جدید"""
    text = update.message.text
    
    if text == "❌ لغو عملیات":
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    context.user_data['add_record_name'] = text
    record_type = context.user_data.get('add_record_type')
    
    examples = {
        'A': "192.168.1.1",
        'AAAA': "2001:db8::1",
        'CNAME': "target.example.com",
        'MX': "10 mail.example.com",
        'TXT': '"v=spf1 include:example.com ~all"',
        'NS': "ns1.example.com",
        'CAA': '0 issue "letsencrypt.org"',
        'SRV': "10 60 5060 sipserver.example.com"
    }
    
    example = examples.get(record_type, "example.com")
    
    await update.message.reply_text(
        f"📝 محتوای رکورد {record_type} را وارد کنید:\n\n"
        f"مثال: `{example}`",
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    
    return ADD_RECORD_CONTENT

async def add_record_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت محتوای رکورد جدید"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "❌ لغو عملیات":
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    zone_id = context.user_data.get('add_zone_id')
    zone_name = context.user_data.get('add_zone_name')
    record_type = context.user_data.get('add_record_type')
    record_name = context.user_data.get('add_record_name')
    
    record_data = {
        'type': record_type,
        'name': record_name,
        'content': text,
        'proxied': False,
        'ttl': 1
    }
    
    if record_type in ['A', 'AAAA', 'CNAME']:
        record_data['proxied'] = True
    
    success, message = cf_manager.create_dns_record(zone_id, record_data)
    
    if success:
        change_logger.log_change(
            user_id,
            update.effective_user.username,
            "CREATE",
            zone_name,
            record_name,
            f"Type: {record_type}, Content: {text}"
        )
        
        await update.message.reply_text(
            f"✅ رکورد جدید با موفقیت ایجاد شد!\n\n"
            f"🌐 دامنه: {zone_name}\n"
            f"🏷️ نام: `{record_name}`\n"
            f"📌 نوع: `{record_type}`\n"
            f"📋 محتوا: `{text}`",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        return MAIN_MENU
    else:
        await update.message.reply_text(
            f"❌ {message}\n\nدوباره امتحان کنید:",
            reply_markup=get_cancel_keyboard()
        )
        return ADD_RECORD_CONTENT

async def change_type_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب نوع جدید رکورد"""
    text = update.message.text
    
    if text == "❌ لغو":
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    if text not in ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'CAA', 'SRV']:
        await update.message.reply_text("❌ نوع رکورد نامعتبر!")
        return CHANGE_TYPE_SELECT
    
    selected_record = context.user_data.get('selected_record')
    old_type = selected_record['type']
    
    if text == old_type:
        await update.message.reply_text(
            "❌ نوع جدید با نوع فعلی یکسان است!",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    context.user_data['new_record_type'] = text
    
    examples = {
        'A': "192.168.1.1",
        'AAAA': "2001:db8::1",
        'CNAME': "target.example.com",
        'MX': "10 mail.example.com",
        'TXT': '"v=spf1 include:example.com ~all"',
        'NS': "ns1.example.com",
        'CAA': '0 issue "letsencrypt.org"',
        'SRV': "10 60 5060 sipserver.example.com"
    }
    
    example = examples.get(text, "example.com")
    
    await update.message.reply_text(
        f"🔄 **تغییر نوع رکورد از {old_type} به {text}**\n\n"
        f"محتوای جدید را برای رکورد نوع {text} وارد کنید:\n"
        f"مثال: `{example}`\n\n"
        "⚠️ توجه: با تغییر نوع رکورد، محتوای قبلی از بین می‌رود.",
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    
    return CHANGE_TYPE_CONTENT

async def change_type_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت محتوای جدید برای تغییر نوع"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "❌ لغو عملیات":
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    selected_record = context.user_data.get('selected_record')
    zone_id = context.user_data.get('current_zone_id')
    zone_name = context.user_data.get('current_zone_name')
    new_type = context.user_data.get('new_record_type')
    
    # حذف رکورد قدیمی
    success, message = cf_manager.delete_dns_record(zone_id, selected_record['id'])
    
    if not success:
        await update.message.reply_text(f"❌ خطا در حذف رکورد قدیمی: {message}")
        return MAIN_MENU
    
    # ایجاد رکورد جدید
    record_data = {
        'type': new_type,
        'name': selected_record['name'],
        'content': text,
        'proxied': False,
        'ttl': 1
    }
    
    if new_type in ['A', 'AAAA', 'CNAME']:
        record_data['proxied'] = selected_record.get('proxied', False)
    
    success, message = cf_manager.create_dns_record(zone_id, record_data)
    
    if success:
        change_logger.log_change(
            user_id,
            update.effective_user.username,
            "UPDATE",
            zone_name,
            selected_record['name'],
            f"Type changed from {selected_record['type']} to {new_type}, New content: {text}"
        )
        
        await update.message.reply_text(
            f"✅ نوع رکورد با موفقیت تغییر کرد!\n\n"
            f"🏷️ نام: `{selected_record['name']}`\n"
            f"📌 نوع جدید: `{new_type}`\n"
            f"📋 محتوای جدید: `{text}`",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        return MAIN_MENU
    else:
        # بازگرداندن رکورد قدیمی در صورت خطا
        cf_manager.create_dns_record(zone_id, {
            'type': selected_record['type'],
            'name': selected_record['name'],
            'content': selected_record['content'],
            'proxied': selected_record.get('proxied', False),
            'ttl': selected_record.get('ttl', 1)
        })
        
        await update.message.reply_text(f"❌ خطا در ایجاد رکورد جدید: {message}")
        return MAIN_MENU

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید حذف رکورد"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "❌ خیر":
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    if text == "✅ بله":
        selected_record = context.user_data.get('selected_record')
        zone_id = context.user_data.get('current_zone_id')
        zone_name = context.user_data.get('current_zone_name')
        
        success, message = cf_manager.delete_dns_record(zone_id, selected_record['id'])
        
        if success:
            change_logger.log_change(
                user_id,
                update.effective_user.username,
                "DELETE",
                zone_name,
                selected_record['name'],
                f"Type: {selected_record['type']}, Content: {selected_record['content']}"
            )
            
            await update.message.reply_text(
                f"✅ رکورد با موفقیت حذف شد!\n\n"
                f"🏷️ نام: `{selected_record['name']}`\n"
                f"📌 نوع: `{selected_record['type']}`",
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
            return MAIN_MENU
        else:
            await update.message.reply_text(f"❌ {message}")
            return MAIN_MENU
    
    return CONFIRM_DELETE

async def search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش جستجو"""
    text = update.message.text
    
    if text == "❌ لغو عملیات":
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    results = cf_manager.search_records(text)
    
    if not results:
        await update.message.reply_text(
            "❌ هیچ نتیجه‌ای یافت نشد!",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    response = f"🔍 **نتایج جستجو برای: `{text}`**\n\n"
    
    for i, result in enumerate(results[:10], 1):
        record = result['record']
        zone_name = result['zone_name']
        
        proxied = "🟠" if record.get('proxied') else "⚪"
        
        response += f"{i}. {proxied} **{record['name']}**\n"
        response += f"   🌐 دامنه: {zone_name}\n"
        response += f"   📌 نوع: {record['type']}\n"
        response += f"   📋 محتوا: `{record['content']}`\n\n"
    
    if len(results) > 10:
        response += f"... و {len(results) - 10} نتیجه دیگر"
    
    await update.message.reply_text(
        response,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو عملیات"""
    await update.message.reply_text(
        "عملیات لغو شد.",
        reply_markup=get_main_keyboard()
    )
    return MAIN_MENU

# ===== تنظیم ConversationHandler =====
def get_conversation_handler():
    """ایجاد ConversationHandler"""
    return ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            SELECT_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_domain)],
            SELECT_RECORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_record)],
            RECORD_ACTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, record_actions)],
            EDIT_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_content)],
            ADD_RECORD_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_record_domain)],
            ADD_RECORD_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_record_type)],
            ADD_RECORD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_record_name)],
            ADD_RECORD_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_record_content)],
            CONFIRM_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete)],
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_query)],
            CHANGE_TYPE_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_type_select)],
            CHANGE_TYPE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_type_content)],
            NAVIGATE_RECORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, navigate_records)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

# ===== شروع ربات =====
def main():
    """تابع اصلی"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن هندلرها
    application.add_handler(get_conversation_handler())
    
    # شروع ربات
    print("✅ ربات شروع به کار کرد...")
    print(f"📊 تعداد ادمین‌ها: {len(ADMIN_IDS)}")
    
    application.run_polling()

if __name__ == '__main__':
    main()
