# Muhammad Hassan — AI Engineer & LLM Builder

Production-ready Flask portfolio CMS combining the polished portfolio architecture from the original project with Muhammad Hassan's AI/LLM content, projects, certifications, achievements, and branding.

## Features
- Dynamic portfolio managed from `/admin`
- Projects, skills, education, experience, certifications and messages
- AI/LLM-focused project case studies
- RAG, ML and automation project content
- Responsive dark portfolio UI
- Contact form with CSRF protection and rate limiting
- SEO metadata, sitemap and robots.txt
- Secure image/PDF upload validation

## Personal data included
- Name: Muhammad Hassan
- Role: AI Engineer & LLM Builder
- Email: mhassanawan66521@gmail.com
- GitHub: https://github.com/mhassan619
- LinkedIn: https://www.linkedin.com/in/mhassanaiengineer

## Setup
1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Create your `.env` (a production `.env` is already pre-configured with secure keys).
4. Run locally with: `python app.py`.
5. Test email delivery: `flask test-email`.
6. Create an admin account: `flask create-admin hassan mhassanawan66521@gmail.com`.
7. Open `/admin` to manage your portfolio, view contact messages, and upload CV/images.

## Deployment to PythonAnywhere
Detailed step-by-step instructions with free-tier email delivery configuration are provided in:
👉 [PYTHONANYWHERE_DEPLOY_GUIDE.md](PYTHONANYWHERE_DEPLOY_GUIDE.md)

## Email Notifications (PythonAnywhere Free Tier)
- PythonAnywhere free accounts block standard SMTP ports.
- The portfolio is integrated with **Resend HTTP API** (which is officially allowlisted by PythonAnywhere).
- Sign up free at [resend.com](https://resend.com) with `mhassanawan66521@gmail.com`, paste your API key in `.env` as `RESEND_API_KEY=re_...`, and test with `flask test-email`.
- Incoming contact messages arrive in your inbox in real time with a 1-click reply button.
- All inquiries are also saved in `portfolio.db` and accessible in the Admin panel at `/admin/messages`.
