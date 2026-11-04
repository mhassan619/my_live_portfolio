import pytest
from app import create_app
from models import Message, db


@pytest.fixture()
def app():
    app = create_app("testing")
    yield app


def test_homepage(app):
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Muhammad Hassan" in html
        assert "AI Engineer & LLM Builder" in html
        assert "University of Layyah AI Assistant" in html
        assert "Achievements &amp; Awards" in html


def test_project_detail(app):
    with app.test_client() as client:
        response = client.get("/projects/rag-pdf-chatbot")
        assert response.status_code == 200
        assert "Technical Deep Dive" in response.get_data(as_text=True)


def test_seo_endpoints(app):
    with app.test_client() as client:
        assert client.get("/robots.txt").status_code == 200
        assert client.get("/sitemap.xml").status_code == 200


def test_contact_form_submission(app):
    with app.test_client() as client:
        with app.app_context():
            initial_count = Message.query.count()

        payload = {
            "name": "Ahmad Khan",
            "email": "ahmad@example.com",
            "subject": "AI Project Inquiry",
            "message": "Hi Hassan, I loved your RAG project and want to collaborate.",
        }
        response = client.post("/contact", data=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "received" in data["message"].lower()

        # Check that message was stored in database
        with app.app_context():
            assert Message.query.count() == initial_count + 1
            saved = Message.query.filter_by(email="ahmad@example.com").first()
            assert saved is not None
            assert saved.name == "Ahmad Khan"
            assert saved.subject == "AI Project Inquiry"


def test_contact_form_invalid_email(app):
    with app.test_client() as client:
        payload = {
            "name": "Visitor",
            "email": "invalid-email-format",
            "subject": "Hello",
            "message": "Test message.",
        }
        response = client.post("/contact", data=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "valid email" in data["message"].lower()


def test_contact_form_missing_fields(app):
    with app.test_client() as client:
        payload = {
            "name": "",
            "email": "user@example.com",
            "subject": "",
            "message": "",
        }
        response = client.post("/contact", data=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False


def test_admin_login_page(app):
    with app.test_client() as client:
        response = client.get("/admin/login")
        assert response.status_code == 200
        assert "Sign In" in response.get_data(as_text=True)
