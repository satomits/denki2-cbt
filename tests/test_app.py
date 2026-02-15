"""基本的なアプリテスト。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app import create_app
from models import Question, db


@pytest.fixture
def app():
    app = create_app({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
    })

    with app.app_context():
        db.create_all()
        # テスト用問題を追加
        q = Question(
            year="2024", half="upper", number=1, page=1,
            question="テスト問題",
            choices_json=json.dumps(["イ. A", "ロ. B", "ハ. C", "ニ. D"]),
            answer=0,
            tags_json=json.dumps(["電気理論"]),
        )
        db.session.add(q)
        db.session.commit()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index(client):
    res = client.get("/")
    assert res.status_code == 200


def test_quiz_start(client):
    res = client.post("/quiz/start", data={"count": "1", "mode": "normal"})
    assert res.status_code == 302  # redirect to quiz


def test_submit_and_score(client):
    # セッション開始
    client.post("/quiz/start", data={"count": "1", "mode": "normal"}, follow_redirects=False)
    # 回答を保存（この時点では採点しない）
    res = client.post("/api/submit", json={
        "session_id": 1,
        "question_id": 1,
        "selected": 0,
    })
    data = res.get_json()
    assert data["ok"] is True

    # 結果表示で一括採点
    res = client.get("/result/1")
    assert res.status_code == 200
    assert "1</span>" in res.data.decode()  # correct_count
