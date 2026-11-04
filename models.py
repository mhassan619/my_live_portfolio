"""
SQLAlchemy database models for Portfolio CMS.
All models include timestamps and appropriate constraints.
"""
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─────────────────────────────────────────────────────────────────────────────
# Admin User
# ─────────────────────────────────────────────────────────────────────────────
class Admin(db.Model):
    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    failed_logins = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str) -> None:
        """Hash and store password — plaintext never persisted."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def is_locked(self) -> bool:
        """Check if account is temporarily locked due to failed logins."""
        if self.locked_until and self.locked_until > utcnow():
            return True
        return False

    def record_failed_login(self) -> None:
        """Increment failed logins and lock account if limit exceeded (5 attempts)."""
        self.failed_logins += 1
        if self.failed_logins >= 5:
            from datetime import timedelta
            self.locked_until = utcnow() + timedelta(minutes=15)
        db.session.commit()

    def reset_failed_logins(self) -> None:
        """Reset failed login count upon successful authentication."""
        self.failed_logins = 0
        self.locked_until = None
        db.session.commit()

    def __repr__(self):
        return f"<Admin {self.username}>"


# ─────────────────────────────────────────────────────────────────────────────
# Admin OTP (One-Time Passwords for Security & Verification)
# ─────────────────────────────────────────────────────────────────────────────
import secrets
from datetime import timedelta

class AdminOTP(db.Model):
    __tablename__ = "admin_otp"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin.id"), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(32), nullable=False)  # 'change_credentials' or 'forgot_password'
    created_at = db.Column(db.DateTime, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

    admin = db.relationship("Admin", backref=db.backref("otps", lazy=True))

    @classmethod
    def generate_otp(cls, admin_id: int, purpose: str, valid_minutes: int = 10) -> str:
        """Invalidate existing unused OTPs and generate a fresh 6-digit code."""
        cls.query.filter_by(admin_id=admin_id, purpose=purpose, is_used=False).update({"is_used": True})
        
        code = f"{secrets.randbelow(900000) + 100000}"
        now = utcnow()
        expires = now + timedelta(minutes=valid_minutes)
        otp = cls(
            admin_id=admin_id,
            otp_code=code,
            purpose=purpose,
            created_at=now,
            expires_at=expires,
            is_used=False,
        )
        db.session.add(otp)
        db.session.commit()
        return code

    @classmethod
    def verify_otp(cls, admin_id: int, code: str, purpose: str) -> bool:
        """Verify code against database, checking expiration and single-use flag."""
        now = utcnow()
        otp = cls.query.filter(
            cls.admin_id == admin_id,
            cls.otp_code == str(code).strip(),
            cls.purpose == purpose,
            cls.is_used == False,
            cls.expires_at > now,
        ).first()
        if otp:
            otp.is_used = True
            db.session.commit()
            return True
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Project
# ─────────────────────────────────────────────────────────────────────────────
class Project(db.Model):
    __tablename__ = "project"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    short_description = db.Column(db.String(400), nullable=False, default="")
    description = db.Column(db.Text, default="")
    problem_statement = db.Column(db.Text, default="")
    category = db.Column(db.String(100), default="Machine Learning")

    # Media
    image = db.Column(db.String(300), default="")
    github_url = db.Column(db.String(300), default="")
    demo_url = db.Column(db.String(300), default="")

    # ML Details (stored as JSON strings)
    dataset = db.Column(db.Text, default="")
    model_architecture = db.Column(db.Text, default="")
    preprocessing = db.Column(db.Text, default="")
    metrics = db.Column(db.Text, default="{}")          # JSON: {"accuracy": ..., "f1": ...}
    technologies = db.Column(db.Text, default="[]")     # JSON: ["TensorFlow", "Flask"]
    results = db.Column(db.Text, default="")
    limitations = db.Column(db.Text, default="")
    future_improvements = db.Column(db.Text, default="")

    # Display control
    featured = db.Column(db.Boolean, default=False, nullable=False)
    published = db.Column(db.Boolean, default=False, nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    @property
    def icon_class(self) -> str:
        """Return a tailored FontAwesome icon class matching the project's domain/content."""
        s = f"{self.slug or ''} {self.title or ''} {self.category or ''}".lower()
        if "layyah" in s or "university" in s:
            return "fas fa-graduation-cap"
        if "pdf" in s:
            return "fas fa-file-pdf"
        if "student" in s or "performance" in s:
            return "fas fa-user-graduate"
        if "house" in s or "property" in s or "estate" in s:
            return "fas fa-house-chimney"
        if "churn" in s or "customer" in s or "retention" in s:
            return "fas fa-users-slash"
        if "github" in s or "repo" in s:
            return "fab fa-github"
        if "automation" in s or "bot" in s or "workflow" in s:
            return "fas fa-wand-magic-sparkles"
        if "dashboard" in s or "analytics" in s or "metrics" in s:
            return "fas fa-chart-line"
        if "rag" in s or "llm" in s or "gpt" in s or "chat" in s:
            return "fas fa-brain"
        if "vision" in s or "cv" in s or "image" in s or "mediapipe" in s:
            return "fas fa-eye"
        if "nlp" in s or "text" in s:
            return "fas fa-language"
        if "price" in s or "stock" in s or "finance" in s:
            return "fas fa-chart-pie"
        return "fas fa-laptop-code"

    @property
    def theme_color(self) -> str:
        """Return accent color tailored to the project."""
        s = f"{self.slug or ''} {self.title or ''}".lower()
        if "layyah" in s or "university" in s:
            return "#38bdf8"
        if "pdf" in s:
            return "#f43f5e"
        if "analytics" in s or "dashboard" in s:
            return "#10b981"
        if "student" in s:
            return "#a855f7"
        if "house" in s:
            return "#f59e0b"
        if "churn" in s:
            return "#ef4444"
        if "github" in s:
            return "#6366f1"
        if "automation" in s:
            return "#06b6d4"
        return "#4f8cff"

    def __repr__(self):
        return f"<Project {self.slug}>"


# ─────────────────────────────────────────────────────────────────────────────
# Skill
# ─────────────────────────────────────────────────────────────────────────────
class Skill(db.Model):
    __tablename__ = "skill"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), default="General")   # e.g., "Computer Vision"
    proficiency = db.Column(db.Integer, default=80)            # 0-100 percentage
    icon_class = db.Column(db.String(100), default="fas fa-code")
    tags = db.Column(db.Text, default="[]")                    # JSON list of tag strings
    display_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Skill {self.name}>"


# ─────────────────────────────────────────────────────────────────────────────
# Education
# ─────────────────────────────────────────────────────────────────────────────
class Education(db.Model):
    __tablename__ = "education"

    id = db.Column(db.Integer, primary_key=True)
    institution = db.Column(db.String(200), nullable=False)
    degree = db.Column(db.String(200), nullable=False)
    level = db.Column(db.String(100), default="")         # e.g., "Matric", "ICS", "BSc"
    start_year = db.Column(db.String(10), default="")
    end_year = db.Column(db.String(10), default="")
    score = db.Column(db.String(50), default="")           # CGPA / marks
    score_label = db.Column(db.String(30), default="Score")
    description = db.Column(db.Text, default="")
    display_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Education {self.degree} @ {self.institution}>"


# ─────────────────────────────────────────────────────────────────────────────
# Experience
# ─────────────────────────────────────────────────────────────────────────────
class Experience(db.Model):
    __tablename__ = "experience"

    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.String(20), default="")
    end_date = db.Column(db.String(20), default="Present")
    description = db.Column(db.Text, default="")
    technologies = db.Column(db.Text, default="[]")   # JSON list
    display_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Experience {self.role} @ {self.company}>"


# ─────────────────────────────────────────────────────────────────────────────
# Certification
# ─────────────────────────────────────────────────────────────────────────────
class Certification(db.Model):
    __tablename__ = "certification"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    issuer = db.Column(db.String(200), nullable=False)
    issue_date = db.Column(db.String(30), default="")
    credential_url = db.Column(db.String(300), default="")
    image = db.Column(db.String(300), default="")
    display_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Certification {self.title}>"


# ─────────────────────────────────────────────────────────────────────────────
# Contact Message
# ─────────────────────────────────────────────────────────────────────────────
class Message(db.Model):
    __tablename__ = "message"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    ip_address = db.Column(db.String(45), default="")   # IPv4/IPv6
    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    def __repr__(self):
        return f"<Message from {self.email}>"


# ─────────────────────────────────────────────────────────────────────────────
# Site Settings (singleton row — id=1)
# ─────────────────────────────────────────────────────────────────────────────
class SiteSettings(db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)

    # Profile / About
    name = db.Column(db.String(100), default="Muhammad Hassan")
    headline = db.Column(db.String(200), default="AI Engineer & LLM Builder")
    bio = db.Column(db.Text, default="")
    profile_image = db.Column(db.String(300), default="uploads/profile/muhammad_hassan.png")
    location = db.Column(db.String(100), default="Pakistan")
    contact_email = db.Column(db.String(120), default="")
    availability = db.Column(db.String(100), default="Open for Opportunities")

    # Social Links
    github_url = db.Column(db.String(300), default="")
    linkedin_url = db.Column(db.String(300), default="")
    whatsapp_number = db.Column(db.String(50), default="")
    resume_url = db.Column(db.String(300), default="")

    # SEO
    site_title = db.Column(db.String(200), default="Muhammad Hassan | AI Engineer & LLM Builder")
    meta_description = db.Column(db.Text, default="")

    # Hero Content
    hero_description = db.Column(db.Text, default="")
    # JSON list of strings — the 3 role pills shown in the hero section
    hero_tags = db.Column(db.Text, default='["AI Engineer", "LLM Builder", "AI Automation Engineer"]')

    # About Section
    about_domain = db.Column(db.String(100), default="AI Engineering & LLM Applications")
    # JSON list of strings — the "Why Work With Me" capability bullets
    why_work_with_me = db.Column(db.Text, default='["Production-focused RAG and LLM application development", "End-to-end machine learning pipelines with Scikit-learn and XGBoost", "AI automation, API integration, and practical Python engineering", "Live deployment experience with Vercel and Streamlit"]')
    # The number shown on the projects badge (e.g. "7+")
    projects_badge_count = db.Column(db.String(10), default="7+")
    # The GitHub @handle displayed in the contact section
    github_handle = db.Column(db.String(100), default="@mhassan619")

    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return f"<SiteSettings id={self.id}>"
