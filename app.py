"""
Flask Portfolio CMS — Application Factory
"""
import os
import logging
import click
from datetime import datetime, timezone

from flask import Flask, render_template
from dotenv import load_dotenv

from config import config_map
from extensions import db, csrf, mail, limiter
from utils.security import apply_security_headers

_base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_base_dir, ".env"))


def create_app(env: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    if env is None:
        env = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, instance_relative_config=False)

    # ── Load config ───────────────────────────────────────────────────────────
    cfg = config_map.get(env, config_map["default"])
    app.config.from_object(cfg)

    # ── Production secret key validation ─────────────────────────────────────
    if env == "production":
        try:
            cfg.validate()
        except RuntimeError as e:
            raise RuntimeError(str(e)) from e

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Init extensions ───────────────────────────────────────────────────────
    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # ── Ensure database tables & seed exist ────────────────────────────────────
    import models  # noqa: F401 - Register models with db.metadata before create_all
    with app.app_context():
        try:
            db.create_all()
            _seed_database()
        except Exception as e:
            app.logger.warning("Database auto-init notice: %s", e)

    # ── Jinja Filters & Context Processors ──────────────────────────────────
    import json
    @app.template_filter("from_json")
    def from_json_filter(value):
        try:
            return json.loads(value) if value else []
        except (ValueError, TypeError):
            return []

    @app.context_processor
    def inject_globals():
        return {"now": lambda: datetime.now(timezone.utc)}

    # ── Security headers & ProxyFix ───────────────────────────────────────────
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    app.after_request(apply_security_headers)

    # ── Register blueprints ───────────────────────────────────────────────────
    from blueprints.public import public_bp
    from blueprints.admin import admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    # ── SEO: robots.txt & sitemap.xml ─────────────────────────────────────────
    register_seo_routes(app)

    # ── Error handlers ────────────────────────────────────────────────────────
    register_error_handlers(app)

    # ── CLI commands ──────────────────────────────────────────────────────────
    register_cli_commands(app)

    # ── Logging ───────────────────────────────────────────────────────────────
    configure_logging(app)

    return app


def register_seo_routes(app: Flask) -> None:
    """Register robots.txt and sitemap.xml for Google indexing."""
    from flask import Response, request as flask_request
    from models import Project

    @app.route("/robots.txt")
    def robots_txt():
        host = flask_request.host_url.rstrip("/")
        content = (
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /admin/\n"
            "Disallow: /admin/login\n"
            "\n"
            f"Sitemap: {host}/sitemap.xml\n"
        )
        return Response(content, mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap_xml():
        from datetime import datetime, timezone
        host = flask_request.host_url.rstrip("/")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Static pages
        pages = [
            {"loc": f"{host}/", "priority": "1.0", "changefreq": "weekly"},
            {"loc": f"{host}/#about", "priority": "0.8", "changefreq": "monthly"},
            {"loc": f"{host}/#skills", "priority": "0.8", "changefreq": "monthly"},
            {"loc": f"{host}/#projects", "priority": "0.9", "changefreq": "weekly"},
            {"loc": f"{host}/#education", "priority": "0.7", "changefreq": "monthly"},
            {"loc": f"{host}/#contact", "priority": "0.7", "changefreq": "monthly"},
        ]

        # Dynamic project pages
        try:
            with app.app_context():
                projects = Project.query.filter_by(published=True).all()
                for p in projects:
                    pages.append({
                        "loc": f"{host}/projects/{p.slug}",
                        "priority": "0.8",
                        "changefreq": "monthly",
                    })
        except Exception:
            pass

        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for page in pages:
            xml_lines.append("  <url>")
            xml_lines.append(f"    <loc>{page['loc']}</loc>")
            xml_lines.append(f"    <lastmod>{today}</lastmod>")
            xml_lines.append(f"    <changefreq>{page['changefreq']}</changefreq>")
            xml_lines.append(f"    <priority>{page['priority']}</priority>")
            xml_lines.append("  </url>")
        xml_lines.append("</urlset>")

        return Response("\n".join(xml_lines), mimetype="application/xml")




def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return render_template("errors/404.html"), 405

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Internal server error")
        return render_template("errors/500.html"), 500


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db():
        """Create database tables and seed default content."""
        with app.app_context():
            db.create_all()
            _seed_database()
            click.echo("Database initialized and seeded.")

    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("email")
    @click.password_option()
    def create_admin(username, email, password):
        """Create an admin account."""
        from models import Admin
        with app.app_context():
            db.create_all()
            if Admin.query.filter_by(username=username).first():
                click.echo(f"Admin '{username}' already exists.")
                return
            admin = Admin(username=username, email=email)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            click.echo(f"Admin account '{username}' created successfully.")

    @app.cli.command("reset-password")
    @click.argument("username")
    def reset_password(username):
        """Reset the password and/or username for an existing admin account."""
        from models import Admin, AdminOTP
        from utils.security import send_otp_email
        import click
        with app.app_context():
            admin = Admin.query.filter_by(username=username).first()
            if not admin:
                click.echo(f"Error: Admin user '{username}' not found.")
                return

            past_password = click.prompt("Past password", hide_input=True)
            if not admin.check_password(past_password):
                click.echo("Error: Incorrect past password.")
                return

            click.echo(f"Generating OTP for {admin.email}...")
            otp_code = AdminOTP.generate_otp(admin.id, purpose="cli_reset", valid_minutes=10)
            sent = send_otp_email(admin.email, otp_code, "CLI credential reset")
            if not sent:
                click.echo(f"Warning: SMTP not configured. Generated OTP is: {otp_code}")

            entered_otp = click.prompt("Enter OTP")
            if not AdminOTP.verify_otp(admin.id, entered_otp, purpose="cli_reset"):
                click.echo("Error: Invalid or expired OTP.")
                return

            new_username = click.prompt("New username (leave blank to keep current)", default=admin.username)
            if new_username and new_username != admin.username:
                existing = Admin.query.filter_by(username=new_username).first()
                if existing:
                    click.echo(f"Error: Username '{new_username}' is already taken.")
                    return
                admin.username = new_username

            new_password = click.prompt("New password (leave blank to keep current)", default="", hide_input=True)
            if new_password:
                admin.set_password(new_password)

            db.session.commit()
            click.echo(f"Credentials for admin '{admin.username}' have been updated successfully.")

    @app.cli.command("test-email")
    @click.argument("recipient", required=False)
    def test_email(recipient):
        """Send a test email to verify delivery into your inbox."""
        from utils.email_service import send_test_email
        with app.app_context():
            click.echo("Initiating email delivery diagnostic test...")
            target = recipient or app.config.get("CONTACT_RECIPIENT_EMAIL", "mhassanawan66521@gmail.com")
            click.echo(f"Target recipient: {target}")
            res = send_test_email(to_email=target)
            if res.get("success"):
                click.echo(f"SUCCESS: Email dispatched via {res.get('provider')}! Details: {res.get('details')}")
                click.echo(f"Please check your inbox ({target}) and spam folder.")
            else:
                click.echo(f"WARNING: Email could not be delivered: {res.get('details')}")



def _seed_database() -> None:
    """Seed the portfolio with Muhammad Hassan's content on first run."""
    from models import Admin, Project, Skill, Education, Experience, Certification, SiteSettings
    import json

    settings_obj = SiteSettings.query.first()
    if not settings_obj:
        settings_obj = SiteSettings()
        db.session.add(settings_obj)
        settings_obj.name = "Muhammad Hassan"
        settings_obj.headline = "AI Engineer & LLM Builder"
        settings_obj.bio = ("AI Engineer and LLM Builder focused on production-grade AI systems, "
                        "RAG applications, machine learning pipelines, and AI automation.")
        settings_obj.profile_image = "uploads/profile/muhammad_hassan.png"
        settings_obj.location = "Pakistan"
        settings_obj.contact_email = "mhassanawan66521@gmail.com"
        settings_obj.availability = "Open for Remote Opportunities"
        settings_obj.github_url = "https://github.com/mhassan619"
        settings_obj.linkedin_url = "https://www.linkedin.com/in/muhammad-hassan-python"
        settings_obj.whatsapp_number = "+923357669594"
        settings_obj.resume_url = "uploads/cv/Hassan_Resume.pdf"
        settings_obj.site_title = "Muhammad Hassan | AI Engineer & LLM Builder"
        settings_obj.meta_description = ("Muhammad Hassan is an AI Engineer and LLM Builder building RAG systems, "
                                     "LLM applications, machine learning pipelines, and AI automation tools.")
        settings_obj.hero_description = ("I build production-ready AI systems, LLM-powered applications, RAG pipelines, "
                                     "machine learning solutions, and intelligent automation tools using Python and modern AI tooling.")
        settings_obj.hero_tags = json.dumps(["AI Engineer", "LLM Builder", "RAG & AI Automation"])
        settings_obj.about_domain = "AI Engineering & LLM Applications"
        settings_obj.why_work_with_me = json.dumps([
        "Production-focused RAG and LLM application development",
        "End-to-end machine learning pipelines with Scikit-learn and XGBoost",
        "AI automation, API integration, and practical Python engineering",
        "Live deployment experience with Vercel and Streamlit"
        ])
        settings_obj.projects_badge_count = "8+"
        settings_obj.github_handle = "@mhassan619"

    # Only seed content when the corresponding tables are empty, so admin edits survive restarts.
    if not Skill.query.first():
        skills = [
            ("Large Language Models (LLMs)", "AI & LLM Engineering", 85, "fas fa-brain", ["LLMs", "Prompt Engineering"]),
            ("LangChain & RAG", "AI & LLM Engineering", 85, "fas fa-link", ["LangChain", "RAG", "Retrieval"]),
            ("ChromaDB / Vector Databases", "AI & LLM Engineering", 80, "fas fa-database", ["Embeddings", "Vector Search"]),
            ("Scikit-learn", "Machine Learning", 85, "fas fa-chart-line", ["Classification", "Regression"]),
            ("XGBoost", "Machine Learning", 80, "fas fa-tree", ["Boosting", "Prediction"]),
            ("Python", "Programming", 90, "fab fa-python", ["OOP", "Automation", "APIs"]),
            ("FastAPI & REST APIs", "Backend", 75, "fas fa-server", ["FastAPI", "REST"]),
            ("Streamlit", "Applications", 88, "fas fa-window-maximize", ["Dashboards", "Deployment"]),
            ("Web Scraping", "Automation", 83, "fas fa-globe", ["BeautifulSoup", "Data Collection"]),
            ("Git & GitHub", "Developer Tools", 85, "fab fa-github", ["Git", "GitHub"]),
            ("Vercel", "Deployment", 80, "fas fa-cloud", ["Deployment", "Serverless"]),
            ("Pandas & NumPy", "Data Science", 88, "fas fa-table", ["Data Analysis", "EDA"]),
        ]
        for i,(name,cat,prof,icon,tags) in enumerate(skills,1):
            db.session.add(Skill(name=name, category=cat, proficiency=prof, icon_class=icon, tags=json.dumps(tags), display_order=i))

    if not Education.query.first():
        edu = [
            {"institution":"University of Layyah", "degree":"Bachelor of Science — Computer Science", "level":"2024 – 2028", "start_year":"2024", "end_year":"2028", "score":"3.9/4.0", "score_label":"GPA", "description":"Pursuing Computer Science with a strong focus on programming, algorithms, data structures, and applied AI/ML.", "display_order":1},
            {"institution":"Govt. Degree College Fateh Pur", "degree":"Intermediate — Pre-Medical (FSc)", "level":"2022 – 2024", "start_year":"2022", "end_year":"2024", "score":"82.8%", "score_label":"Grade", "description":"Completed a science-focused intermediate education before moving into Computer Science.", "display_order":2},
            {"institution":"Govt. High School Fateh Pur", "degree":"Matriculation — Science", "level":"2020 – 2022", "start_year":"2020", "end_year":"2022", "score":"97%", "score_label":"Grade", "description":"Strong academic foundation in science and mathematics.", "display_order":3},
        ]
        for e in edu: db.session.add(Education(**e))

    if not Experience.query.first():
        db.session.add(Experience(
            company="Self-Directed · Remote · Pakistan", role="AI Engineer — Independent Projects",
            start_date="Jun 2025", end_date="Present",
            description=("Built and deployed end-to-end AI applications including RAG chatbots, ML dashboards, "
                         "automation tools, and API-integrated applications. Integrated LLMs with LangChain and ChromaDB "
                         "and shipped live applications for real-world use cases."),
            technologies=json.dumps(["Python","LangChain","ChromaDB","Scikit-learn","XGBoost","FastAPI","Streamlit"]), display_order=1))

    if not Project.query.first():
        projects = [
            dict(title="University of Layyah AI Assistant", slug="university-of-layyah-ai-assistant", short_description="Production-deployed RAG chatbot for University of Layyah, giving students and staff conversational access to university information.", description="A live LLM-powered university assistant built around retrieval-augmented generation. The system turns university information into searchable knowledge and returns context-aware conversational answers.", problem_statement="Students and staff need a faster way to find university information without manually searching across documents and pages.", category="AI · RAG · Live", demo_url="https://ul-ai-assistant.vercel.app/", technologies=json.dumps(["LangChain","ChromaDB","RAG","Python","Vercel"]), dataset="University information and knowledge sources.", model_architecture="User query → retrieval → relevant context → LLM generation → answer.", preprocessing="Knowledge-source cleaning, chunking, embeddings, and vector indexing.", results="Live AI application deployed on Vercel.", limitations="Answer quality depends on the coverage and freshness of the indexed knowledge base.", future_improvements="Expand knowledge coverage, improve evaluation, add richer source citations and monitoring.", featured=True,published=True,display_order=1),
            dict(title="RAG PDF ChatBot", slug="rag-pdf-chatbot", short_description="Intelligent document Q&A application that lets users upload PDFs and ask questions using retrieval-augmented generation.", description="A document intelligence application that converts uploaded PDFs into a searchable vector knowledge base and generates context-aware answers to natural-language questions.", problem_statement="Users often need to locate specific information inside long PDF documents without reading them page by page.", category="AI · LLM · Live", demo_url="https://rag-pdf-chatbot-one.vercel.app/", technologies=json.dumps(["LangChain","ChromaDB","Embeddings","RAG","Python","Vercel"]), dataset="User-uploaded PDF documents.", model_architecture="PDF → text extraction → chunking → embeddings → ChromaDB → retrieval → LLM.", preprocessing="Document parsing, chunking, embedding generation, and vector indexing.", results="Live PDF question-answering application.", limitations="Retrieval quality depends on document structure, chunking, and source quality.", future_improvements="Add citations, hybrid search, document collections, and better retrieval evaluation.", featured=True,published=True,display_order=2),
            dict(title="ML Analytics Dashboard", slug="ml-analytics-dashboard", short_description="Interactive Streamlit dashboard combining Student Performance, House Price, and Customer Churn machine learning projects.", description="A unified ML application that exposes multiple trained models through interactive inputs and visual analytics.", problem_statement="Demonstrate how multiple end-to-end machine learning pipelines can be packaged into usable interactive applications.", category="ML · Dashboard · Live", demo_url="https://hassan-saidashboard-awujmtpzvvsekbjzfgb6y5.streamlit.app/", technologies=json.dumps(["Scikit-learn","XGBoost","Streamlit","Pandas","Python"]), dataset="Datasets used by the three component ML projects.", model_architecture="Separate classification/regression pipelines exposed through a shared Streamlit interface.", preprocessing="Data cleaning, feature engineering, encoding, and model-specific preprocessing.", results="Three ML applications available through one interactive dashboard.", limitations="Model quality is bounded by the datasets and assumptions of each component project.", future_improvements="Add model monitoring, automated retraining, richer evaluation, and unified experiment tracking.", featured=True,published=True,display_order=3),
            dict(title="Student Performance Predictor", slug="student-performance-predictor", short_description="Classification model predicting student academic outcomes from study habits, attendance, and behavioral factors.", description="An end-to-end classification project with feature engineering, evaluation, and feature-importance analysis.", problem_statement="Identify patterns associated with academic outcomes and surface students who may need additional support.", category="ML · Classification", github_url="https://github.com/mhassan619/Hassan-s_AI_Dashboard/tree/main/Student%20Performance%20Project", technologies=json.dumps(["Scikit-learn","Classification","Pandas","Python"]), dataset="Student performance data.", model_architecture="Supervised classification pipeline with engineered features and model evaluation.", preprocessing="Cleaning, feature engineering, encoding, and train/test preparation.", results="Interactive predictor included in the ML Analytics Dashboard.", limitations="Predictions depend on dataset quality and should not be treated as deterministic judgments about students.", future_improvements="Add calibration, broader features, and fairness-oriented evaluation.", published=True,display_order=4),
            dict(title="House Price Estimator", slug="house-price-estimator", short_description="Random Forest regression application estimating property prices from location, size, and structural features.", description="An end-to-end regression project covering data preparation, feature engineering, model training, and interactive deployment.", problem_statement="Estimate property prices from structured housing attributes.", category="ML · Regression", github_url="https://github.com/mhassan619/Hassan-s_AI_Dashboard/tree/main/House%20Price%20Prediction", technologies=json.dumps(["Random Forest","Regression","Scikit-learn","Streamlit"]), dataset="House price data with property and location features.", model_architecture="Random Forest regression pipeline.", preprocessing="Cleaning, feature selection, encoding, and train/test preparation.", results="Interactive house price estimator available through the ML dashboard.", limitations="Predictions are dataset-specific and depend on market and location coverage.", future_improvements="Add geospatial features, stronger ensembles, and live market data.", published=True,display_order=5),
            dict(title="Customer Churn Analytics", slug="customer-churn-analytics", short_description="XGBoost-powered churn prediction system identifying at-risk customers and surfacing key churn drivers.", description="A business ML project focused on customer churn classification, probability scoring, and feature importance.", problem_statement="Help businesses identify customers who may be at higher risk of churn so retention efforts can be prioritized.", category="ML · Business AI", github_url="https://github.com/mhassan619/Hassan-s_AI_Dashboard/tree/main/Customer%20Churn%20Prediction", technologies=json.dumps(["XGBoost","Business AI","Pandas","Streamlit"]), dataset="Customer churn dataset.", model_architecture="XGBoost classification pipeline with probability outputs.", preprocessing="Cleaning, feature preparation, encoding, and train/test split.", results="Churn probabilities and feature-importance analysis available in the dashboard.", limitations="Model performance depends on historical customer data and changing business behavior.", future_improvements="Add calibration, drift monitoring, explainability, and retraining workflows.", published=True,display_order=6),
            dict(title="GitHub Analyzer", slug="github-analyzer", short_description="Developer analytics tool using the GitHub API to analyze repositories, languages, activity, and contribution metrics.", description="A Python analytics tool that integrates with GitHub APIs to turn profile and repository data into useful developer insights.", problem_statement="Developers and teams need a concise way to inspect repository statistics and activity patterns.", category="API · Analytics", github_url="https://github.com/mhassan619/AI_Automation_Engineer/blob/main/Day_15/GitHub_Analyzer.py", technologies=json.dumps(["GitHub API","REST APIs","Python","Analytics"]), dataset="GitHub API data.", model_architecture="API client → data extraction → aggregation → analytics/visualization.", preprocessing="API response parsing and normalization.", results="Repository statistics, language breakdowns, and activity insights.", limitations="GitHub API rate limits and available public data constrain analysis.", future_improvements="Add caching, richer visualizations, organization analytics, and scheduled reports.", published=True,display_order=7),
            dict(title="AI Automation Dashboard", slug="ai-automation-dashboard", short_description="Centralized Streamlit dashboard combining file organization, web scraping, weather, news, and other practical automation tools.", description="A collection of practical Python automation utilities packaged into one interactive dashboard.", problem_statement="Reduce repetitive tasks by bringing common automation utilities into one accessible application.", category="Automation · Live", demo_url="https://aiautomationdashboard-cyaeoww9sgapjwm7zlsxg6.streamlit.app/", technologies=json.dumps(["Streamlit","BeautifulSoup","REST APIs","Python"]), dataset="External APIs and web data sources.", model_architecture="Streamlit interface → automation utility → external system/API → structured result.", preprocessing="Input validation, API parsing, scraping cleanup, and data normalization.", results="Multiple automation utilities available through a unified dashboard.", limitations="External websites and APIs can change independently of the application.", future_improvements="Add authentication, job scheduling, reusable connectors, and better error monitoring.", published=True,display_order=8),
        ]
        for pdata in projects: db.session.add(Project(**pdata))

    if not Certification.query.first():
        certs = [
            ("Artificial Intelligence","DigiSkills","", "uploads/certs/Artificial_Intelligence.jpg",1),
            ("Data Visualization","Kaggle","", "uploads/certs/Data_Visualtization.png",2),
            ("Intermediate Machine Learning","Kaggle","", "uploads/certs/Intermediate_Machine_Learning.png",3),
            ("Intro to Machine Learning","Kaggle","", "uploads/certs/Intro_to_Machine_Learning.png",4),
            ("Intro to Programming","Kaggle","", "uploads/certs/Intro_to_Programming.png",5),
            ("Pandas","Kaggle","", "uploads/certs/Pandas.png",6),
            ("Python Machine Learning for Beginners","Mind Luster","", "uploads/certs/Python_Machine_Learning_for_beginners.jpg",7),
        ]
        for title,issuer,date,image,order in certs:
            db.session.add(Certification(title=title,issuer=issuer,issue_date=date,image=image,display_order=order))

    db.session.commit()


def configure_logging(app: Flask) -> None:
    """Configure structured logging — never log passwords or secrets."""
    log_dir = os.path.join(_base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_level = logging.DEBUG if app.debug else logging.INFO

    handler = logging.FileHandler(os.path.join(log_dir, "portfolio.log"), encoding="utf-8")
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)

    # Suppress Flask-Limiter verbose output in production
    if not app.debug:
        logging.getLogger("flask_limiter").setLevel(logging.WARNING)


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    # Binding to 0.0.0.0 is intentional for Docker/container deployment
    app.run(debug=app.config.get("DEBUG", False), host="0.0.0.0", port=5000)  # nosec B104
