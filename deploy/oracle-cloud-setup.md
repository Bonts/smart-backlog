# Oracle Cloud Free Tier — Smart Backlog Bot Deployment

## Overview

Deploy the Smart Backlog Telegram bot on **Oracle Cloud Always Free** instance.

**What you get for free (forever):**
- **VM.Standard.A1.Flex** (ARM Ampere): up to 4 OCPU + 24 GB RAM
- Up to 200 GB block storage
- 10 TB/month outbound data

---

## Step 1: Create Oracle Cloud Account

1. Go to [cloud.oracle.com](https://cloud.oracle.com/) → **Sign Up**
2. Fill in your details, add a credit card (won't be charged for Always Free resources)
3. Choose a **Home Region** closest to you (e.g., `eu-frankfurt-1`, `us-ashburn-1`)
4. Wait for account activation (usually within minutes)

---

## Step 2: Create an Always Free VM Instance

1. Go to **Compute → Instances → Create Instance**
2. Configure:

| Setting | Value |
|---|---|
| **Name** | `smart-backlog-bot` |
| **Image** | Ubuntu 22.04 (or 24.04) |
| **Shape** | **VM.Standard.A1.Flex** (ARM Ampere, Always Free-eligible) |
| **OCPUs** | 1 |
| **Memory** | 6 GB |
| **Boot volume** | 50 GB (default, within free tier) |

> 6 GB RAM — более чем достаточно для Python-бота. Swap не нужен.

3. **Networking** — нужна виртуальная сеть (VCN) и подсеть (Subnet):

   Если в выпадающем списке **Virtual cloud network** пусто — создай VCN:

   **A. Создай VCN:**
   1. Открой в новой вкладке: **Networking → Virtual Cloud Networks**
   2. Если есть кнопка **Start VCN Wizard** — используй её (проще):
      - Выбери **"Create VCN with Internet Connectivity"** → Name: `smart-backlog-vcn` → **Next → Create**
      - Дождись пока все компоненты станут зелёными, и переходи к пункту **Б.**
   3. Если wizard нет — нажми **Create VCN**:
      - Name: `smart-backlog-vcn`
      - IPv4 CIDR Block: `10.0.0.0/16`
      - Остальное по умолчанию → **Create VCN**

   **Если создавал через Create VCN (без wizard)** — нужны ещё 3 действия на странице VCN:

   4. Слева **Internet Gateways** → **Create Internet Gateway**
      - Name: `smart-backlog-igw` → **Create Internet Gateway**
   5. Слева **Route Tables** → кликни **Default Route Table** → **Add Route Rules**
      - Target Type: **Internet Gateway**
      - Destination CIDR Block: `0.0.0.0/0`
      - Target Internet Gateway: `smart-backlog-igw` → **Add Route Rules**
   6. Слева **Subnets** → **Create Subnet**
      - Name: `public-subnet`
      - Subnet Type: **Regional**
      - IPv4 CIDR Block: `10.0.0.0/24`
      - Route Table: Default Route Table
      - Subnet Access: **Public Subnet**
      - **Create Subnet**

   **Б. Вернись на экран создания инстанса** — заново: **Compute → Instances → Create Instance**
   > ⚠️ НЕ используй F5 — он сбросит всю форму. Просто перейди заново через меню.
   > VCN уже создана — она появится в выпадающих списках.

   7. В **Virtual cloud network** выбери `smart-backlog-vcn`
   8. В **Subnet** выбери `public-subnet` (или `public subnet-smart-backlog-vcn` если через wizard)

   > Бот использует **polling** (не webhooks), поэтому никаких дополнительных портов открывать не нужно.
   > Дефолтная security list (SSH port 22) — достаточно.

4. **SSH Key** — это как электронный ключ от двери сервера:

   > **Что такое SSH-ключи?**
   > Это пара файлов: **private key** (твой личный ключ — как ключ от квартиры) и **public key** (замок — он стоит на сервере).
   > Когда ты подключаешься, SSH проверяет: подходит ли твой ключ к замку. Пароль не нужен.
   > **Private key нельзя никому показывать.** Public key — можно, он бесполезен без private.

   **Что делать на экране Oracle:**

   1. Оставь **"Generate a key pair for me"** (уже выбрано)
   2. Нажми **Download private key** — скачается файл типа `ssh-key-2026-03-27.key`
   3. Нажми **Download public key** — скачается `ssh-key-2026-03-27.key.pub`
   4. **Скачай ОБА файла ДО нажатия Create!** После создания инстанса эта страница закроется, и кнопки Download исчезнут навсегда. Oracle не хранит твой private key — если не скачал сейчас, придётся удалять инстанс и создавать заново

   **Куда положить ключ (Windows):**

   Открой PowerShell и выполни эти 3 команды по одной:

   ```powershell
   # 1. Создать папку .ssh в домашней директории (если её ещё нет)
   mkdir -Force "$env:USERPROFILE\.ssh"

   # 2. Если старый ключ уже есть — удалить (сначала вернуть права на удаление)
   if (Test-Path "$env:USERPROFILE\.ssh\oracle-smart-backlog.key") {
       icacls "$env:USERPROFILE\.ssh\oracle-smart-backlog.key" /grant "${env:USERNAME}:(F)"
       Remove-Item "$env:USERPROFILE\.ssh\oracle-smart-backlog.key" -Force
   }

   # 3. Переместить скачанный ключ из Downloads в .ssh
   Move-Item "$env:USERPROFILE\Downloads\ssh-key-*.key" "$env:USERPROFILE\.ssh\oracle-smart-backlog.key"

   # 4. Защитить файл — сделать доступным только для тебя
   icacls "$env:USERPROFILE\.ssh\oracle-smart-backlog.key" /inheritance:r /grant:r "${env:USERNAME}:(R)"
   ```

   > **Что делает каждая команда:**
   > - `mkdir -Force` — создаёт папку `C:\Users\Ruslan\.ssh\` (если уже есть — не ругается)
   > - `Move-Item` — перемещает `.key` файл из Downloads в `.ssh` с понятным именем
   > - `icacls` — убирает доступ для всех кроме тебя (SSH требует это для безопасности)

   **Как хранить и не потерять:**
   - Ключ хранится локально в `C:\Users\<ИМЯ>\.ssh\oracle-smart-backlog.key`
   - **Сделай бэкап** — скопируй `.key` файл в безопасное место (OneDrive, USB, менеджер паролей)
   - Если нужен доступ с другого компьютера — скопируй `.key` на него в ту же папку `.ssh` и выполни ту же команду `icacls`
   - Если ключ потерян навсегда — зайди в Oracle Console → Instance → **Console Connection** и добавь новый public key

5. Click **Create** — wait ~2 minutes for provisioning

6. Note the **Public IP** from the instance details page

---

## Step 3: Connect via SSH

Теперь подключаемся к серверу через терминал. SSH — это безопасное удалённое подключение (как Remote Desktop, но текстовое).

```powershell
# Windows PowerShell — подключиться к серверу
# Замени <PUBLIC_IP> на IP-адрес из Oracle Console (например, 132.145.67.89)
ssh -i $env:USERPROFILE\.ssh\oracle-smart-backlog.key ubuntu@<PUBLIC_IP>
```

> **Что тут происходит:**
> - `ssh` — программа для подключения (встроена в Windows 10+)
> - `-i ...key` — "используй этот ключ для входа"
> - `ubuntu` — имя пользователя на сервере (для Ubuntu-образов всегда `ubuntu`)
> - `@<PUBLIC_IP>` — адрес сервера
>
> При первом подключении спросит _"Are you sure you want to continue connecting?"_ — введи `yes`
>
> После подключения ты увидишь `ubuntu@smart-backlog-bot:~$` — это терминал сервера.
> Команда `exit` — выйти обратно на свой компьютер.

---

## Step 4: Automated Setup

Upload and run the setup script:

```powershell
# Windows PowerShell — copy the setup script to the server
scp -i $env:USERPROFILE\.ssh\oracle-smart-backlog.key deploy/setup.sh ubuntu@<PUBLIC_IP>:~/setup.sh

# SSH into the server
ssh -i $env:USERPROFILE\.ssh\oracle-smart-backlog.key ubuntu@<PUBLIC_IP>
```

Then on the server:
```bash
chmod +x ~/setup.sh
sudo ~/setup.sh
```

The script installs Python 3.11, ffmpeg, clones the repo, creates a venv, and sets up systemd.

---

## Step 5: Configure Environment

```bash
# Edit the .env file
sudo nano /opt/smart-backlog/.env
```

Fill in your values:

```env
# LLM Provider
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_API_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_DEPLOYMENT_FAST=gpt-4o-mini

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token-here

# Database (default is fine)
DATABASE_PATH=data/smart_backlog.db

# Transcription
TRANSCRIPTION_ENGINE=azure

# OCR
OCR_ENGINE=vision
```

---

## Step 6: Start the Bot

```bash
# Start the service
sudo systemctl start smart-backlog

# Enable auto-start on boot
sudo systemctl enable smart-backlog

# Check status
sudo systemctl status smart-backlog

# View logs
sudo journalctl -u smart-backlog -f
```

---

## Step 7: Copy Existing Database (Optional)

If you have an existing `smart_backlog.db` from local development:

```powershell
# From your local machine (Windows PowerShell)
scp -i $env:USERPROFILE\.ssh\oracle-smart-backlog.key data/smart_backlog.db ubuntu@<PUBLIC_IP>:/tmp/
```

On the server:
```bash
sudo cp /tmp/smart_backlog.db /opt/smart-backlog/data/smart_backlog.db
sudo chown smart-backlog:smart-backlog /opt/smart-backlog/data/smart_backlog.db
sudo systemctl restart smart-backlog
```

---

## Management Commands

```bash
# Stop bot
sudo systemctl stop smart-backlog

# Restart bot
sudo systemctl restart smart-backlog

# View live logs
sudo journalctl -u smart-backlog -f

# View last 100 log lines
sudo journalctl -u smart-backlog -n 100

# Update to latest code
cd /opt/smart-backlog
sudo -u smart-backlog git pull
sudo -u smart-backlog .venv/bin/pip install -r requirements.txt
sudo systemctl restart smart-backlog

# Backup database
sudo cp /opt/smart-backlog/data/smart_backlog.db ~/smart_backlog_backup_$(date +%Y%m%d).db
```

---

## Troubleshooting

### Bot won't start
```bash
# Check logs for errors
sudo journalctl -u smart-backlog -n 50 --no-pager

# Test manually
sudo -u smart-backlog /opt/smart-backlog/.venv/bin/python -m src.interfaces.telegram_bot
```

### "Conflict: terminated by other getUpdates request"
Another instance of the bot is running (e.g., on your local machine). Stop the local one first.

### Instance runs out of memory
With A1.Flex (6 GB RAM) this is unlikely. If it happens:
- Check `free -h` for what's consuming memory
- Ensure no local Whisper model is loaded (`TRANSCRIPTION_ENGINE=azure`)

### SSH connection refused
Check Oracle Cloud **Security List** → ensure port 22 is open for your IP.

---

## Docker Alternative

If you prefer Docker instead of native Python:

```bash
# On the server
cd /opt/smart-backlog
sudo docker build -t smart-backlog .
sudo docker run -d \
  --name smart-backlog \
  --restart unless-stopped \
  --env-file .env \
  -v /opt/smart-backlog/data:/app/data \
  smart-backlog
```

See [Dockerfile](../Dockerfile) for the container definition.

---

## Cost

**$0/month** — Everything used is within Oracle Cloud Always Free tier:
- 1x VM.Standard.A1.Flex (1 OCPU, 6 GB RAM) — free up to 4 OCPU / 24 GB
- 50 GB boot volume (free up to 200 GB)
- Outbound traffic well under 10 TB/month
