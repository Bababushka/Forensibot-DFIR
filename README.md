# 🕵️ ForensiBot — DFIR Case Automation Telegram Bot

ForensiBot is a Telegram-based **Digital Forensics & Incident Response (DFIR)** automation tool.  
It allows investigators, students, and security analysts to upload digital evidence and automatically generate a forensic report.

This bot simulates real-world DFIR workflows such as file hashing, metadata extraction, log analysis, browser forensics, and timeline generation — all inside a simple Telegram chat.

---

## 🚀 Features

### 🔹 Case Management
- Create an investigation case (`/newcase`)
- Upload individual evidence files or a `.zip`
- Files automatically organized per case

### 🔹 Evidence Processing
- File hashing (MD5, SHA1, SHA256)
- Metadata extraction:
  - EXIF (JPG, PNG)
  - PDF properties
  - DOCX document metadata

### 🔹 Log Analysis
- SSH authentication logs (`auth.log`)
- Apache/Nginx access logs
- Detection of failed logins, suspicious IPs, unusual activity

### 🔹 Browser Forensics
- Chrome/Edge (`History`) SQLite parsing
- Firefox (`places.sqlite`) parsing
- Extraction of visited URLs, timestamps, titles

### 🔹 Timeline Generation
- Combine logs + browser events into a unified event timeline
- Sort chronologically to reconstruct activity flow

### 🔹 Report Generation
- Outputs a clean Markdown forensic report
- Includes:
  - Hash tables
  - Metadata findings
  - Timeline table
  - Summary of events

---

## 📦 Project Structure
ForensiBot/
│
├── bot.py
├── requirements.txt
├── README.md
├── .gitignore
│
└── analysis/
├── init.py
├── hashing.py
├── metadata.py
├── logs.py
├── browser.py
└── timeline.py

## 🔧 Installation & Running ForensiBot (One-Shot Guide)

Follow these steps to install, configure, and run ForensiBot on your machine.

---

### 1️⃣ Install Python & Get the Project

Make sure you have **Python 3.9+** installed.

Clone your GitHub repository:

```bash
git clone https://github.com/YOUR_USERNAME/ForensiBot.git
cd ForensiBot
(If you downloaded a ZIP, extract it and open the folder.)

2️⃣ Install Dependencies
bash
Copy code
pip install -r requirements.txt
This installs all required libraries for Telegram bot interaction and DFIR analysis.

3️⃣ Create Your .env File
Create a file named .env in the project folder:

env
Copy code
TELEGRAM_BOT_TOKEN=your_bot_token_here
⚠️ Never upload your .env file to GitHub.
If your token leaks, regenerate it using BotFather.

4️⃣ Run the Bot
Start the bot using:

bash
Copy code
python bot.py
You should see something like:

arduino
Copy code
Bot is running...
Listening for messages...
Leave this terminal open while using your bot.

5️⃣ Use the Bot in Telegram
Open your bot in Telegram and type:

bash
Copy code
/start
/newcase
Upload files or a .zip, then run:

bash
Copy code
/analyze
The bot will:

Process evidence

Extract metadata

Analyze logs

Parse browser history

Build a forensic timeline

Generate a Markdown report

Send the report back to you




