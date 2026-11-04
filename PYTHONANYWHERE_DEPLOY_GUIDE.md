# 🚀 PythonAnywhere Deployment & Email Setup Guide
### Muhammad Hassan Portfolio — AI Engineer & LLM Builder

This comprehensive guide explains how to deploy this portfolio website on **PythonAnywhere** and ensure that whenever someone submits the contact form, an email is delivered **directly to your Gmail inbox (`mhassanawan66521@gmail.com`)**.

---

## 📑 Table of Contents
1. [Important: How Email Works on PythonAnywhere](#1-important-how-email-works-on-pythonanywhere)
2. [Step 1: Upload Your Code to PythonAnywhere](#step-1-upload-your-code-to-pythonanywhere)
3. [Step 2: Create Virtual Environment & Install Requirements](#step-2-create-virtual-environment--install-requirements)
4. [Step 3: Configure Environment Variables (.env)](#step-3-configure-environment-variables-env)
5. [Step 4: Configure the Web App on PythonAnywhere](#step-4-configure-the-web-app-on-pythonanywhere)
6. [Step 5: Configure the WSGI File](#step-5-configure-the-wsgi-file)
7. [Step 6: Configure Static Files Mapping](#step-6-configure-static-files-mapping)
8. [Step 7: Test & Verify Email Delivery](#step-7-test--verify-email-delivery)
9. [Step 8: Admin Panel Credentials & Management](#step-8-admin-panel-credentials--management)
10. [Troubleshooting & FAQs](#troubleshooting--faqs)

---

## 1. Important: How Email Works on PythonAnywhere

> [!IMPORTANT]
> **Free PythonAnywhere Accounts block direct SMTP ports (587, 465, 25).**  
> If you try to use standard Gmail SMTP (`smtp.gmail.com:587`), PythonAnywhere's firewall blocks it with `Connection refused`.  
>  
> **The Solution (Already Built In):**  
> PythonAnywhere allows outbound HTTP requests to domains on their allowlist.  
> **Resend API (`api.resend.com`) is officially on PythonAnywhere's allowlist!**  
>  
> We configured your app to send emails via **Resend's HTTP API** with automatic fallback to **SMTP**. With Resend, you get **3,000 free emails/month** and messages land in your Gmail inbox in under 2 seconds!

---

## Step 1: Upload Your Code to PythonAnywhere

1. Log in to [PythonAnywhere](https://www.pythonanywhere.com/).
2. Open a **Bash Console** from the Dashboard.
3. Clone your repository into your home directory:
   ```bash
   git clone https://github.com/mhassan619/<your-repo-name>.git Muhammad-Hassan-Portfolio
   cd Muhammad-Hassan-Portfolio
   ```
   *(Alternatively, zip your project folder, upload it via the Files tab, and unzip it with `unzip archive.zip`)*.

---

## Step 2: Create Virtual Environment & Install Requirements

In the same PythonAnywhere Bash console:

```bash
cd ~/Muhammad-Hassan-Portfolio

# 1. Create a Python 3.10 virtual environment
python3.10 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install all dependencies
pip install -r requirements.txt
```

---

## Step 3: Configure Environment Variables (`.env`)

1. Copy the template or edit `.env`:
   ```bash
   cp .env.example .env
   nano .env
   ```
2. Get your free **Resend API Key**:
   - Go to [resend.com](https://resend.com) and create a free account using `mhassanawan66521@gmail.com`.
   - Go to **API Keys** → Click **Create API Key** → Copy the key (starts with `re_...`).
3. In your `.env` file, make sure the following lines are set:
   ```ini
   FLASK_APP=app.py
   FLASK_ENV=production
   SECRET_KEY=d4365537e016e5c02b81a6d8b6ee15a46168d02150ac31d9f8d78c3ec9f41d38

   CONTACT_RECIPIENT_EMAIL=mhassanawan66521@gmail.com
   ALLOWED_ADMIN_EMAILS=mhassanawan66521@gmail.com

   # Resend API Key for PythonAnywhere free tier
   RESEND_API_KEY=re_your_actual_key_here
   RESEND_FROM_EMAIL=Muhammad Hassan Portfolio <onboarding@resend.dev>
   ```
   Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit `nano`.

> [!TIP]
> With `onboarding@resend.dev`, Resend sends emails straight to the email address you signed up with (`mhassanawan66521@gmail.com`).  
> The contact form automatically sets `Reply-To: <visitor's email>`, so when you open the email in Gmail and hit **Reply**, you will be replying directly to the visitor!

---

## Step 4: Configure the Web App on PythonAnywhere

1. In PythonAnywhere, navigate to the **Web** tab.
2. Click **Add a new web app**.
3. Choose **Manual configuration** (do NOT choose standard Flask template, as we already have our production app).
4. Select **Python 3.10**.
5. Once created, in the Web tab configure the following paths:
   - **Source code:** `/home/<your-username>/Muhammad-Hassan-Portfolio`
   - **Working directory:** `/home/<your-username>/Muhammad-Hassan-Portfolio`
   - **Virtualenv:** `/home/<your-username>/Muhammad-Hassan-Portfolio/.venv`

---

## Step 5: Configure the WSGI File

1. In the **Web** tab, click the link under **Code** labeled **WSGI configuration file** (e.g. `/var/www/<username>_pythonanywhere_com_wsgi.py`).
2. Delete everything inside that file and paste this clean code:

```python
import sys
import os

# 1. Path to your project
project_home = '/home/<your-username>/Muhammad-Hassan-Portfolio'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 2. Load .env environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# 3. Import WSGI application
from wsgi import application
```
*(Replace `<your-username>` with your actual PythonAnywhere username!)*

3. Click **Save** in the top right.

---

## Step 6: Configure Static Files Mapping

In the **Web** tab, scroll down to the **Static files** section and add this entry:

| URL | Directory |
|---|---|
| `/static/` | `/home/<your-username>/Muhammad-Hassan-Portfolio/static/` |

This enables PythonAnywhere's high-speed Nginx server to serve your images, CSS, JavaScript, and PDF resume directly.

---

## Step 7: Test & Verify Email Delivery

### Method A: Test via Bash Console (Fastest)
In your PythonAnywhere Bash console:
```bash
cd ~/Muhammad-Hassan-Portfolio
source .venv/bin/activate
flask test-email
```
You will see:
```text
Initiating email delivery diagnostic test...
Target recipient: mhassanawan66521@gmail.com
Dispatching email via Resend API to mhassanawan66521@gmail.com...
Resend email dispatched successfully! ID: 018...
SUCCESS: Email dispatched via Resend API!
Please check your inbox (mhassanawan66521@gmail.com) and spam folder.
```
Now open your Gmail (`mhassanawan66521@gmail.com`), and verify the message!

### Method B: Test via Website
1. Click the green **Reload <username>.pythonanywhere.com** button in the Web tab.
2. Open your website: `https://<username>.pythonanywhere.com`.
3. Scroll down to the **Contact** section.
4. Fill in:
   - **Full Name:** Test User
   - **Email:** test@example.com
   - **Subject:** Hello Hassan!
   - **Message:** Testing my portfolio email notification system.
5. Click **Send Message**.
6. You will see: `✅ Thank you! Your message has been received.`
7. Check your Gmail inbox: you will receive the notification with full sender details and a 1-click **Reply** button!

---

## Step 8: Admin Panel Credentials & Management

Your portfolio includes a full CMS Admin Panel.

### Initializing Database & Admin Account
In the Bash console:
```bash
cd ~/Muhammad-Hassan-Portfolio
source .venv/bin/activate

# Initialize and seed database (if not done already)
flask init-db

# Create your admin account:
flask create-admin hassan mhassanawan66521@gmail.com
```
It will prompt you to enter a secure password.

### Accessing Admin Panel
1. Visit: `https://<username>.pythonanywhere.com/admin/login`
2. Enter your username and password.
3. In the admin dashboard:
   - View and manage all incoming contact messages under **Messages** (`/admin/messages`).
   - Edit Projects, Skills, Education, Experience, and Certifications.
   - Update your headline, bio, profile picture, and CV.

---

## 10. Troubleshooting & FAQs

### Q: What if an email fails to send?
- **Zero Data Loss:** Every message submitted via the contact form is **always saved to the database first** (`portfolio.db`). You will never lose an inquiry even if your email API key is expired or the network is down. You can see all messages inside `/admin/messages`.
- Check the application log for details:
  ```bash
  cat ~/Muhammad-Hassan-Portfolio/logs/portfolio.log
  ```

### Q: Why not Gmail SMTP on PythonAnywhere?
- PythonAnywhere free accounts block ports 25, 465, and 587. Gmail SMTP only works on paid PythonAnywhere accounts.
- **Resend API works on free accounts** because it connects via HTTP/HTTPS (`api.resend.com`), which is explicitly allowlisted by PythonAnywhere!

### Q: How do I reply to someone who contacts me?
- Just click **Reply** in Gmail. The email's `Reply-To` header is set to the visitor's email address automatically.
