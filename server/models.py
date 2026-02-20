"""SQLAlchemy モデル定義。"""

import json
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(JST))

    sessions = db.relationship("QuizSession", backref="user", lazy=True)


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(4), nullable=False)
    half = db.Column(db.String(10), nullable=False)  # "upper" or "lower"
    number = db.Column(db.Integer, nullable=False)
    page = db.Column(db.Integer, nullable=False)
    question = db.Column(db.Text, nullable=False)
    choices_json = db.Column(db.Text, nullable=False)  # JSON array
    answer = db.Column(db.Integer, nullable=True)  # 0=イ, 1=ロ, 2=ハ, 3=ニ
    tags_json = db.Column(db.Text, default="[]")  # JSON array
    explanation = db.Column(db.Text, default="")
    section = db.Column(db.String(20), default="一般問題")  # 一般問題 or 配線図
    image = db.Column(db.String(200), default="")  # クロップ画像ファイル名

    __table_args__ = (
        db.UniqueConstraint("year", "half", "number", name="uq_question"),
    )

    @property
    def choices(self) -> list[str]:
        return json.loads(self.choices_json)

    @property
    def tags(self) -> list[str]:
        return json.loads(self.tags_json)

    @property
    def image_path(self) -> str:
        """クロップ画像があればそれを、なければページ全体画像を返す。"""
        if self.image:
            return f"pages/{self.year}_{self.half}/{self.image}"
        return f"pages/{self.year}_{self.half}/page_{self.page:02d}.png"

    @property
    def is_haisen(self) -> bool:
        return self.section == "配線図"

    @property
    def haisen_notes_path(self) -> str:
        return f"pages/{self.year}_{self.half}/haisen_notes.png"

    @property
    def haisen_diagram_path(self) -> str:
        """配線図のページ画像（ブックレットの最後のコンテンツページ）。"""
        return f"pages/{self.year}_{self.half}/page_15.png"


class QuizSession(db.Model):
    __tablename__ = "quiz_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category = db.Column(db.String(100), default="")
    total_count = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(JST))
    finished_at = db.Column(db.DateTime, nullable=True)

    attempts = db.relationship("Attempt", backref="session", lazy=True)

    # セッションに紐づく問題IDリスト (JSON)
    question_ids_json = db.Column(db.Text, default="[]")

    @property
    def question_ids(self) -> list[int]:
        return json.loads(self.question_ids_json)


class Attempt(db.Model):
    __tablename__ = "attempts"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("quiz_sessions.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    selected = db.Column(db.Integer, nullable=True)  # ユーザーの選択 (0-3), null=未回答
    is_correct = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(JST))

    question = db.relationship("Question", lazy=True)
