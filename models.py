from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone_number = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("user", "admin"), default="user")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    settings = relationship("UserSetting", back_populates="owner", uselist=False)
    projects = relationship("Project", back_populates="owner")
    notifications = relationship("Notification", back_populates="user")
    support_messages = relationship("SupportMessage", back_populates="user")
    saved_inspirations = relationship("UserSavedInspiration", back_populates="user")


class UserSetting(Base):
    __tablename__ = "usersettings"

    setting_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    language = Column(String(10), default="ar")
    notifications_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="settings")


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(255), nullable=False)
    description = Column(Text)

    projects = relationship("Project", back_populates="category")


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    project_name = Column(String(255), nullable=False)
    project_description = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.category_id", ondelete="SET NULL"))
    target_audience = Column(String(255))

    sector = Column(String(100))
    capital_required = Column(Numeric(15, 2))
    sales_cost = Column(Numeric(15, 2))
    revenue = Column(Numeric(15, 2))
    workers = Column(Integer)
    location = Column(String(100))

    status = Column(Enum("draft", "analyzing", "completed"), default="draft")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="projects")
    category = relationship("Category", back_populates="projects")
    feasibility_result = relationship("FeasibilityResult", back_populates="project", uselist=False)


class FeasibilityResult(Base):
    __tablename__ = "feasibilityresults"

    result_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    financial_summary = Column(Text)
    marketing_summary = Column(Text)
    risks_summary = Column(Text)
    risk_solutions = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="feasibility_result")


class BusinessTip(Base):
    __tablename__ = "businesstips"

    tip_id = Column(Integer, primary_key=True, index=True)
    tip_text = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class InspirationProject(Base):
    __tablename__ = "inspirationprojects"

    inspiration_id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(255), nullable=False)
    image_url = Column(String(255))
    success_rate = Column(Numeric(5, 2))
    story = Column(Text)
    capital_required = Column(Numeric(15, 2))
    results = Column(Text)
    challenges = Column(Text)

    user_interactions = relationship("UserSavedInspiration", back_populates="inspiration")


class UserSavedInspiration(Base):
    __tablename__ = "usersavedinspirations"

    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    inspiration_id = Column(
        Integer,
        ForeignKey("inspirationprojects.inspiration_id", ondelete="CASCADE"),
        primary_key=True,
    )
    liked = Column(Boolean, default=False)
    saved = Column(Boolean, default=False)

    user = relationship("User", back_populates="saved_inspirations")
    inspiration = relationship("InspirationProject", back_populates="user_interactions")


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="notifications")


class SupportMessage(Base):
    __tablename__ = "supportmessages"

    message_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    subject = Column(String(255))
    message_body = Column(Text)
    reply_body = Column(Text)
    status = Column(Enum("pending", "answered", "closed"), default="pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="support_messages")


class SystemSetting(Base):
    __tablename__ = "systemsettings"

    setting_id = Column(Integer, primary_key=True, index=True)
    key_name = Column(String(255), nullable=False)
    value = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class VerificationCode(Base):
    __tablename__ = "verificationcodes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    code = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


