#!/bin/bash

# Colors for better display
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Required files
ENV_FILE=".env"
CONFIG_FILE="config.py"
REQUIREMENTS_FILE="requirements.txt"
SERVICE_NAME="cfbot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
VENV_DIR="venv"

# Show logo function
show_logo() {
    clear
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║         Cloudflare DNS Manager Bot Setup              ║"
    echo "║                 Telegram Bot Manager                  ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Show main menu function
show_main_menu() {
    echo -e "\n${YELLOW}Main Menu:${NC}"
    echo -e "${GREEN}1)${NC} Install Prerequisites"
    echo -e "${GREEN}2)${NC} Initial Configuration"
    echo -e "${GREEN}3)${NC} Edit Settings"
    echo -e "${GREEN}4)${NC} Bot Management"
    echo -e "${GREEN}5)${NC} View Status"
    echo -e "${GREEN}6)${NC} Fix Module Issues"
    echo -e "${GREEN}7)${NC} Quick Fix & Start"
    echo -e "${RED}0)${NC} Exit"
    echo -e "\n${PURPLE}Select an option:${NC} "
}

# Show bot management menu
show_bot_menu() {
    echo -e "\n${YELLOW}Bot Management:${NC}"
    echo -e "${GREEN}1)${NC} Install Bot Service"
    echo -e "${GREEN}2)${NC} Start Bot"
    echo -e "${GREEN}3)${NC} Stop Bot"
    echo -e "${GREEN}4)${NC} Restart Bot"
    echo -e "${GREEN}5)${NC} View Logs"
    echo -e "${GREEN}6)${NC} Service Status"
    echo -e "${RED}0)${NC} Back to Main Menu"
    echo -e "\n${PURPLE}Select an option:${NC} "
}

# Quick fix function
quick_fix() {
    show_logo
    echo -e "${YELLOW}Quick Fix & Start - Resolving all issues...${NC}\n"

    # Step 1: Install system packages
    echo -e "${CYAN}Step 1: Installing system packages...${NC}"
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv

    # Step 2: Create requirements.txt if needed
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        echo -e "\n${CYAN}Step 2: Creating requirements.txt...${NC}"
        cat > "$REQUIREMENTS_FILE" << EOF
python-telegram-bot==20.7
cloudflare==2.11.7
python-dotenv==1.0.0
requests==2.31.0
EOF
    fi

    # Step 3: Remove old venv if exists and create new one
    echo -e "\n${CYAN}Step 3: Creating fresh virtual environment...${NC}"
    if [ -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
    fi
    python3 -m venv "$VENV_DIR"
    
    # Step 4: Install packages in venv
    echo -e "\n${CYAN}Step 4: Installing packages in virtual environment...${NC}"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
    deactivate

    # Step 5: Update service file
    echo -e "\n${CYAN}Step 5: Updating service configuration...${NC}"
    CURRENT_DIR=$(pwd)
    
    cat > /tmp/${SERVICE_NAME}.service << EOF
[Unit]
Description=Cloudflare DNS Manager Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/$VENV_DIR/bin:/usr/bin:/usr/local/bin"
Environment="PYTHONPATH=$CURRENT_DIR"
ExecStart=$CURRENT_DIR/$VENV_DIR/bin/python3 $CURRENT_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo cp /tmp/${SERVICE_NAME}.service $SERVICE_FILE
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}

    # Step 6: Stop and start the service
    echo -e "\n${CYAN}Step 6: Restarting bot service...${NC}"
    sudo systemctl stop ${SERVICE_NAME} 2>/dev/null
    sleep 2
    sudo systemctl start ${SERVICE_NAME}
    sleep 3

    # Check if service is running
    if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
        echo -e "\n${GREEN}✓ Bot is now running successfully!${NC}"
        echo -e "${YELLOW}Service Status:${NC}"
        sudo systemctl status ${SERVICE_NAME} --no-pager | head -n 10
    else
        echo -e "\n${RED}Service failed to start. Checking logs...${NC}"
        sudo journalctl -u ${SERVICE_NAME} -n 20 --no-pager
    fi

    read -p $'\n'"Press Enter to continue..."
}

# Fix module issues function
fix_modules() {
    show_logo
    echo -e "${YELLOW}Fixing Python module issues...${NC}\n"

    # Remove broken venv if present
    if [ -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Removing old virtual environment...${NC}"
        rm -rf "$VENV_DIR"
    fi

    # Create virtual environment
    echo -e "${CYAN}Creating new virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"

    # Activate virtual environment and install packages
    echo -e "${YELLOW}Installing packages in virtual environment...${NC}"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
    deactivate

    # Update service file if it exists
    if [ -f "$SERVICE_FILE" ]; then
        echo -e "\n${YELLOW}Updating service configuration...${NC}"
        install_bot_service
    fi

    echo -e "\n${GREEN}✓ Module issues fixed!${NC}"
    read -p "Press Enter to continue..."
}

# Install requirements function
install_requirements() {
    show_logo
    echo -e "${YELLOW}Checking and installing prerequisites...${NC}\n"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 not found! Installing...${NC}"
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv
    else
        echo -e "${GREEN}✓ Python 3 is installed${NC}"
    fi

    # Check pip
    if ! command -v pip3 &> /dev/null; then
        echo -e "${RED}pip3 not found! Installing...${NC}"
        sudo apt install -y python3-pip
    else
        echo -e "${GREEN}✓ pip3 is installed${NC}"
    fi

    # Check venv
    echo -e "${YELLOW}Installing python3-venv...${NC}"
    sudo apt install -y python3-venv

    # Create requirements.txt if not exists
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        echo -e "\n${YELLOW}Creating requirements.txt...${NC}"
        cat > "$REQUIREMENTS_FILE" << EOF
python-telegram-bot==20.7
cloudflare==2.11.7
python-dotenv==1.0.0
requests==2.31.0
EOF
    fi

    # Create virtual environment
    echo -e "\n${YELLOW}Creating virtual environment...${NC}"
    if [ -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
    fi
    python3 -m venv "$VENV_DIR"

    # Install Python packages in virtual environment
    echo -e "\n${YELLOW}Installing Python packages in virtual environment...${NC}"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
    deactivate

    echo -e "\n${GREEN}✓ All prerequisites installed successfully!${NC}"
    read -p "Press Enter to continue..."
}

# Initial configuration function
initial_config() {
    show_logo
    echo -e "${YELLOW}Initial Bot Configuration${NC}\n"

    # Get Bot Token
    echo -e "${CYAN}Enter your Telegram Bot Token:${NC}"
    read -p "> " bot_token

    # Get Cloudflare API Token
    echo -e "\n${CYAN}Enter your Cloudflare API Token:${NC}"
    read -p "> " cf_token

    # Get Admin IDs
    echo -e "\n${CYAN}Enter admin user IDs (comma separated):${NC}"
    echo -e "${YELLOW}Example: 123456789,987654321${NC}"
    read -p "> " admin_ids

    # Create .env file
    echo -e "\n${YELLOW}Creating configuration file...${NC}"
    cat > "$ENV_FILE" << EOF
BOT_TOKEN=$bot_token
CF_API_TOKEN=$cf_token
ADMIN_IDS=$admin_ids
LOG_LEVEL=INFO
EOF

    # Create config.py file
    cat > "$CONFIG_FILE" << 'EOF'
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
EOF

    echo -e "${GREEN}✓ Configuration completed successfully!${NC}"
    read -p "Press Enter to continue..."
}

# Edit settings function
edit_settings() {
    while true; do
        show_logo
        echo -e "${YELLOW}Edit Settings:${NC}\n"
        echo -e "${GREEN}1)${NC} Change Bot Token"
        echo -e "${GREEN}2)${NC} Change Cloudflare Token"
        echo -e "${GREEN}3)${NC} Manage Admins"
        echo -e "${GREEN}4)${NC} Show Current Settings"
        echo -e "${RED}0)${NC} Back to Main Menu"

        read -p $'\n'"Option: " choice

        case $choice in
            1)
                echo -e "\n${CYAN}Enter new Bot Token:${NC}"
                read -p "> " new_token
                sed -i "s/BOT_TOKEN=.*/BOT_TOKEN=$new_token/" "$ENV_FILE"
                echo -e "${GREEN}✓ Bot token updated${NC}"
                read -p "Press Enter..."
                ;;
            2)
                echo -e "\n${CYAN}Enter new Cloudflare Token:${NC}"
                read -p "> " new_token
                sed -i "s/CF_API_TOKEN=.*/CF_API_TOKEN=$new_token/" "$ENV_FILE"
                echo -e "${GREEN}✓ Cloudflare token updated${NC}"
                read -p "Press Enter..."
                ;;
            3)
                manage_admins
                ;;
            4)
                show_current_settings
                ;;
            0)
                break
                ;;
            *)
                echo -e "${RED}Invalid option!${NC}"
                sleep 1
                ;;
        esac
    done
}

# Manage admins function
manage_admins() {
    while true; do
        show_logo
        echo -e "${YELLOW}Manage Admins:${NC}\n"

        # Show current admins
        current_admins=$(grep "ADMIN_IDS=" "$ENV_FILE" | cut -d'=' -f2)
        echo -e "${CYAN}Current admins: ${NC}$current_admins\n"

        echo -e "${GREEN}1)${NC} Add Admin"
        echo -e "${GREEN}2)${NC} Remove Admin"
        echo -e "${GREEN}3)${NC} Replace All Admins"
        echo -e "${RED}0)${NC} Back"

        read -p $'\n'"Option: " choice

        case $choice in
            1)
                echo -e "\n${CYAN}Enter new admin ID:${NC}"
                read -p "> " new_admin
                if [[ "$current_admins" == "" ]]; then
                    new_list="$new_admin"
                else
                    new_list="$current_admins,$new_admin"
                fi
                sed -i "s/ADMIN_IDS=.*/ADMIN_IDS=$new_list/" "$ENV_FILE"
                echo -e "${GREEN}✓ New admin added${NC}"
                read -p "Press Enter..."
                ;;
            2)
                echo -e "\n${CYAN}Enter admin ID to remove:${NC}"
                read -p "> " remove_admin
                new_list=$(echo "$current_admins" | sed "s/\b$remove_admin\b//g" | sed 's/,,/,/g' | sed 's/^,//;s/,$//')
                sed -i "s/ADMIN_IDS=.*/ADMIN_IDS=$new_list/" "$ENV_FILE"
                echo -e "${GREEN}✓ Admin removed${NC}"
                read -p "Press Enter..."
                ;;
            3)
                echo -e "\n${CYAN}Enter new admin list (comma separated):${NC}"
                read -p "> " new_list
                sed -i "s/ADMIN_IDS=.*/ADMIN_IDS=$new_list/" "$ENV_FILE"
                echo -e "${GREEN}✓ Admin list updated${NC}"
                read -p "Press Enter..."
                ;;
            0)
                break
                ;;
            *)
                echo -e "${RED}Invalid option!${NC}"
                sleep 1
                ;;
        esac
    done
}

# Show current settings function
show_current_settings() {
    show_logo
    echo -e "${YELLOW}Current Settings:${NC}\n"

    if [ -f "$ENV_FILE" ]; then
        echo -e "${CYAN}.env file content:${NC}"
        echo "--------------------------------"
        while IFS= read -r line; do
            if [[ $line == *"TOKEN"* ]]; then
                key=$(echo "$line" | cut -d'=' -f1)
                value=$(echo "$line" | cut -d'=' -f2)
                masked_value="${value:0:10}...${value: -10}"
                echo "$key=$masked_value"
            else
                echo "$line"
            fi
        done < "$ENV_FILE"
        echo "--------------------------------"
    else
        echo -e "${RED}Configuration file not found!${NC}"
    fi

    echo -e "\n${YELLOW}To view full tokens, open the .env file directly${NC}"
    read -p "Press Enter to continue..."
}

# Install bot service function
install_bot_service() {
    show_logo

    # Check required files
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: Configuration file not found!${NC}"
        echo -e "${YELLOW}Please run initial configuration first.${NC}"
        read -p "Press Enter..."
        return
    fi

    if [ ! -f "bot.py" ]; then
        echo -e "${RED}Error: bot.py file not found!${NC}"
        read -p "Press Enter..."
        return
    fi

    # Check if service already exists
    if [ -f "$SERVICE_FILE" ]; then
        echo -e "${YELLOW}Service already exists. Updating...${NC}"
    fi

    CURRENT_DIR=$(pwd)

    # Always use venv Python (create if not exists)
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        pip install --upgrade pip
        pip install -r "$REQUIREMENTS_FILE"
        deactivate
    fi

    PYTHON_PATH="$CURRENT_DIR/$VENV_DIR/bin/python3"

    echo -e "${GREEN}Creating systemd service...${NC}\n"

    # Create service file content
    cat > /tmp/${SERVICE_NAME}.service << EOF
[Unit]
Description=Cloudflare DNS Manager Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/$VENV_DIR/bin:/usr/bin:/usr/local/bin"
Environment="PYTHONPATH=$CURRENT_DIR"
ExecStart=$PYTHON_PATH $CURRENT_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Copy service file (needs sudo)
    echo -e "${YELLOW}Need sudo permission to install service...${NC}"
    sudo cp /tmp/${SERVICE_NAME}.service $SERVICE_FILE
    sudo systemctl daemon-reload

    # Enable service
    sudo systemctl enable ${SERVICE_NAME}

    echo -e "${GREEN}✓ Bot service installed successfully!${NC}"
    echo -e "${YELLOW}You can now start the bot from the menu.${NC}"
    read -p "Press Enter to continue..."
}

# Start bot function
start_bot() {
    show_logo

    # Check if service is installed
    if [ ! -f "$SERVICE_FILE" ]; then
        echo -e "${RED}Service not installed!${NC}"
        echo -e "${YELLOW}Please install the bot service first.${NC}"
        read -p "Press Enter..."
        return
    fi

    echo -e "${GREEN}Starting bot service...${NC}"
    sudo systemctl start ${SERVICE_NAME}

    sleep 2

    # Check status
    if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
        echo -e "${GREEN}✓ Bot service started successfully!${NC}"
    else
        echo -e "${RED}✗ Failed to start bot service!${NC}"
        echo -e "${YELLOW}Check logs for details.${NC}"
    fi

    read -p "Press Enter to continue..."
}

# Stop bot function
stop_bot() {
    show_logo
    echo -e "${YELLOW}Stopping bot service...${NC}"

    if sudo systemctl is-active --quiet ${SERVICE_NAME} 2>/dev/null; then
        sudo systemctl stop ${SERVICE_NAME}
        echo -e "${GREEN}✓ Bot service stopped!${NC}"
    else
        echo -e "${YELLOW}Bot service is not running!${NC}"
    fi

    read -p "Press Enter to continue..."
}

# Restart bot function
restart_bot() {
    show_logo
    echo -e "${YELLOW}Restarting bot service...${NC}"

    sudo systemctl restart ${SERVICE_NAME}

    sleep 2

    if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
        echo -e "${GREEN}✓ Bot service restarted successfully!${NC}"
    else
        echo -e "${RED}✗ Failed to restart bot service!${NC}"
    fi

    read -p "Press Enter to continue..."
}

# View logs function
view_logs() {
    show_logo
    echo -e "${GREEN}Bot Service Logs:${NC}"
    echo "=================================="
    echo -e "${YELLOW}Showing last 50 lines (Press Ctrl+C to exit)...${NC}\n"

    sudo journalctl -u ${SERVICE_NAME} -n 50 -f

    echo
    read -p "Press Enter to continue..."
}

# Service status function
service_status() {
    show_logo
    echo -e "${GREEN}Bot Service Status:${NC}"
    echo "=================================="

    sudo systemctl status ${SERVICE_NAME}

    echo
    read -p "Press Enter to continue..."
}

# Bot management menu
bot_management() {
    while true; do
        show_logo
        show_bot_menu
        read choice

        case $choice in
            1)
                install_bot_service
                ;;
            2)
                start_bot
                ;;
            3)
                stop_bot
                ;;
            4)
                restart_bot
                ;;
            5)
                view_logs
                ;;
            6)
                service_status
                ;;
            0)
                break
                ;;
            *)
                echo -e "${RED}Invalid option!${NC}"
                sleep 1
                ;;
        esac
    done
}

# View status function
show_status() {
    show_logo
    echo -e "${YELLOW}System Status:${NC}\n"

    # Check service status
    if sudo systemctl is-active --quiet ${SERVICE_NAME} 2>/dev/null; then
        echo -e "${GREEN}✓ Bot service is running${NC}"
        echo -e "${CYAN}Service: ${SERVICE_NAME}${NC}"
    else
        echo -e "${RED}✗ Bot service is not running${NC}"
    fi

    # Check bot process
    if pgrep -f "python3 bot.py" > /dev/null; then
        echo -e "${GREEN}✓ Python process is active${NC}"
        pid=$(pgrep -f "python3 bot.py")
        echo -e "${CYAN}PID: $pid${NC}"
    fi

    # Check virtual environment
    if [ -d "$VENV_DIR" ]; then
        echo -e "${GREEN}✓ Virtual environment exists${NC}"
    else
        echo -e "${YELLOW}⚠ Virtual environment not found${NC}"
    fi

    # Check Python modules
    echo -e "\n${YELLOW}Checking Python modules...${NC}"
    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        pip show python-telegram-bot cloudflare python-dotenv > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ All required modules installed in venv${NC}"
        else
            echo -e "${RED}✗ Some modules missing in venv${NC}"
        fi
        deactivate
    else
        echo -e "${RED}✗ Virtual environment is broken${NC}"
    fi

    # Show recent logs
    if [ -f "bot.log" ]; then
        echo -e "\n${YELLOW}Last 10 lines from bot.log:${NC}"
        echo "--------------------------------"
        tail -n 10 bot.log
        echo "--------------------------------"
    fi

    # Show service logs
    echo -e "\n${YELLOW}Last 5 lines from service logs:${NC}"
    echo "--------------------------------"
    sudo journalctl -u ${SERVICE_NAME} -n 5 --no-pager 2>/dev/null || echo "No service logs available"
    echo "--------------------------------"

    read -p $'\n'"Press Enter to continue..."
}

# Main loop
main() {
    while true; do
        show_logo
        show_main_menu
        read choice

        case $choice in
            1)
                install_requirements
                ;;
            2)
                initial_config
                ;;
            3)
                edit_settings
                ;;
            4)
                bot_management
                ;;
            5)
                show_status
                ;;
            6)
                fix_modules
                ;;
            7)
                quick_fix
                ;;
            0)
                echo -e "\n${GREEN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option!${NC}"
                sleep 1
                ;;
        esac
    done
}

# Run the program
main

