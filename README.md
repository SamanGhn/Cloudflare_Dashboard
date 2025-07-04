<div align=“center”>

A powerful Telegram bot for managing Cloudflare DNS records with Persian (Farsi) interface.

</div>

✨ Features
🌐 Complete DNS Management - View, add, edit, and delete DNS records
🔍 Smart Search - Search across all domains and records
📊 Statistics & Reports - View domain statistics and change logs
🔐 Admin Control - Multi-admin support with secure access
🟠 Proxy Management - Toggle Cloudflare proxy for A, AAAA, and CNAME records
📝 Record Types - Support for A, AAAA, CNAME, MX, TXT, NS, CAA, SRV records
🔄 Automatic Service - Systemd service for 24/7 operation
📱 User-Friendly Interface - Clean Persian interface with inline keyboards
📋 Requirements
Ubuntu/Debian based Linux server
Python 3.8 or higher
Root or sudo access
Telegram Bot Token (from @BotFather)
Cloudflare API Token with DNS edit permissions
🚀 Quick Installation
One-Command Install

content_copy
bash
git clone https://github.com/yourusername/cloudflare-dns-bot.git
cd cloudflare-dns-bot
chmod +x menu.sh
./menu.sh
Step-by-Step Installation
Clone the repository:

content_copy
bash
git clone https://github.com/yourusername/cloudflare-dns-bot.git
cd cloudflare-dns-bot
Make the setup script executable:

content_copy
bash
chmod +x menu.sh
Run the setup menu:

content_copy
bash
./menu.sh
Follow the menu options:
Select 1 to install prerequisites
Select 2 for initial configuration
Select 4 → 1 to install bot service
Select 4 → 2 to start the bot
🔧 Configuration
Getting Required Tokens
Telegram Bot Token:
Open @BotFather in Telegram
Send /newbot and follow instructions
Copy the token provided
Cloudflare API Token:
Log in to Cloudflare Dashboard
Go to “My Profile” → “API Tokens”
Click “Create Token”
Use “Edit zone DNS” template
Select specific zones or all zones
Create and copy the token
Finding Your Telegram User ID:
Send a message to @userinfobot
Copy your numerical user ID
Configuration Files
The bot uses two configuration files:

.env - Contains sensitive credentials:


content_copy
env
BOT_TOKEN=your_telegram_bot_token
CF_API_TOKEN=your_cloudflare_api_token
ADMIN_IDS=123456789,987654321
LOG_LEVEL=INFO
config.py - Loads environment variables:


content_copy
python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
📱 Bot Commands
/start - Start the bot and show main menu
/cancel - Cancel current operation
/help - Show help message
🎮 Menu Structure
Main Menu

├── 🌐 Domain List

│ └── View and manage DNS records

├── ➕ New Record

│ └── Add new DNS records

├── 🔍 Search

│ └── Search in all records

├── 📊 Reports

│ └── View change logs

├── 📈 Statistics

│ └── Domain and record statistics

└── ❓ Help

└── Usage guide

🛠️ Management Menu
The menu.sh script provides a complete management interface:

Install Prerequisites - Install Python, pip, and required packages
Initial Configuration - Set up bot tokens and admin IDs
Edit Settings - Modify tokens and admin list
Bot Management - Start, stop, restart, view logs
View Status - Check bot and service status
Fix Module Issues - Reinstall Python modules
Quick Fix & Start - Automated troubleshooting
🔧 Troubleshooting
Bot not starting?
If the bot doesn’t start after following the standard installation, use the Quick Fix option:


content_copy
bash
./menu.sh
# Select option 7 (Quick Fix & Start)
This will:

Reinstall all system dependencies
Create a fresh virtual environment
Install all Python packages
Update the systemd service
Restart the bot automatically
Common Issues
ModuleNotFoundError:

Run option 6 (Fix Module Issues) from the menu
Or use option 7 (Quick Fix & Start)
Service fails to start:

Check logs: sudo journalctl -u cfbot -n 50
Verify tokens in .env file
Ensure bot.py has execute permissions
Permission denied:

Run the script with sudo: sudo ./menu.sh
Check file ownership: ls -la
Manual Service Control

content_copy
bash
# Check service status
sudo systemctl status cfbot

# View logs
sudo journalctl -u cfbot -f

# Restart service
sudo systemctl restart cfbot

# Stop service
sudo systemctl stop cfbot

📁 Project Structure
Cloudflare_Dashboard/

├── bot.py # Main bot application

├── config.py # Configuration loader

├── menu.sh # Setup
