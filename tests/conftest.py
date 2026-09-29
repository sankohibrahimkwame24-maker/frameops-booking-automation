import os
os.environ["ENVIRONMENT"]="test"
os.environ["CALENDLY_WEBHOOK_SIGNING_KEY"]="test-secret"
os.environ["DATABASE_URL"]="sqlite:///./test_frameops.db"
os.environ["OWNER_EMAIL"]="owner@example.com"
os.environ["RESEND_API_KEY"]="re_test"
os.environ["EMAIL_FROM"]="FrameOps <test@example.com>"
os.environ["ADMIN_PASSWORD"]="a"*20

from app.main import engine
from app.database import Base
Base.metadata.create_all(engine)
