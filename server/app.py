"""第二種電気工事士 CBT 練習アプリ。"""

import functools
import json
import os
import random
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from models import JST, Attempt, Question, QuizSession, User, db


def create_app(test_config=None):
    if "BASE_DIR" in os.environ:
        # frozen exe 時: launcher.py がセットした絶対パスを使う
        base_dir = Path(os.environ["BASE_DIR"])
        instance_dir = base_dir / "instance"
        instance_dir.mkdir(exist_ok=True)
        # Windows ローカルパスを SQLite URI 形式に変換（as_posix でスラッシュ統一）
        db_uri = f"sqlite:///{(instance_dir / 'app.db').as_posix()}"
        flask_kwargs = {
            "template_folder": str(base_dir / "templates"),
            "static_folder": str(base_dir / "static"),
        }
    else:
        # 通常起動時: Flask のデフォルト（instance/app.db 相対パス）をそのまま使う
        db_uri = "sqlite:///app.db"
        flask_kwargs = {}

    app = Flask(__name__, **flask_kwargs)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "dev"

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        # 既存DBにuser_idカラムがない場合に追加
        with db.engine.connect() as conn:
            columns = [row[1] for row in conn.execute(db.text("PRAGMA table_info(quiz_sessions)"))]
            if "user_id" not in columns:
                conn.execute(db.text("ALTER TABLE quiz_sessions ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                conn.commit()

    register_routes(app)

    return app


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def register_routes(app: Flask):

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            if not username:
                return render_template("login.html", error="ユーザー名を入力してください。")
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
                db.session.add(user)
                db.session.commit()
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def index():
        # 年度・半期一覧
        years = db.session.query(
            Question.year, Question.half
        ).distinct().order_by(Question.year.desc()).all()

        # タグ一覧と分野ごとの問題数
        tag_counts: dict[str, int] = {}
        for (tags_json,) in db.session.query(Question.tags_json).all():
            for tag in json.loads(tags_json):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        tags = sorted(tag_counts.keys())

        # 直近の成績
        recent_sessions = QuizSession.query.filter_by(
            user_id=session["user_id"]
        ).order_by(
            QuizSession.started_at.desc()
        ).limit(10).all()

        return render_template(
            "index.html", years=years, tags=tags, tag_counts=tag_counts, recent_sessions=recent_sessions
        )

    @app.route("/quiz/start", methods=["POST"])
    @login_required
    def quiz_start():
        year = request.form.get("year", "")
        half = request.form.get("half", "")
        tag = request.form.get("tag", "")
        count = int(request.form.get("count", 50))
        mode = request.form.get("mode", "normal")  # normal or review

        query = Question.query

        if year and half:
            query = query.filter_by(year=year, half=half)
        if tag:
            query = query.filter(Question.tags_json.contains(tag))

        if mode == "review":
            from_session_id = request.form.get("from_session_id", "")
            if from_session_id:
                # 指定セッションの間違い問題のみ
                from_session = QuizSession.query.get(int(from_session_id))
                if from_session and from_session.user_id == session["user_id"]:
                    wrong_ids = [
                        a.question_id
                        for a in Attempt.query.filter_by(
                            session_id=from_session.id, is_correct=False
                        ).all()
                    ]
                else:
                    wrong_ids = _get_wrong_question_ids(session["user_id"])
            else:
                # 全履歴から最新回答が不正解の問題
                wrong_ids = _get_wrong_question_ids(session["user_id"])
            if wrong_ids:
                query = query.filter(Question.id.in_(set(wrong_ids)))

        questions = query.all()
        if not questions:
            return redirect(url_for("index"))

        if len(questions) > count:
            questions = random.sample(questions, count)

        q_ids = [q.id for q in questions]
        quiz_session = QuizSession(
            user_id=session["user_id"],
            category=f"{year}_{half}" if year else tag or "all",
            total_count=len(q_ids),
            question_ids_json=json.dumps(q_ids),
        )
        db.session.add(quiz_session)
        db.session.commit()

        return redirect(url_for("quiz", session_id=quiz_session.id, q=0))

    @app.route("/quiz/<int:session_id>")
    @login_required
    def quiz(session_id: int):
        quiz_session = QuizSession.query.get_or_404(session_id)
        if quiz_session.user_id and quiz_session.user_id != session["user_id"]:
            return redirect(url_for("index"))
        q_ids = quiz_session.question_ids
        q_index = int(request.args.get("q", 0))

        if q_index >= len(q_ids):
            return redirect(url_for("result", session_id=session_id))

        question = Question.query.get(q_ids[q_index])

        # 既存の回答を取得
        existing = Attempt.query.filter_by(
            session_id=session_id, question_id=question.id
        ).first()

        # 各問題の回答状況
        answered_map = {}
        for a in Attempt.query.filter_by(session_id=session_id).all():
            answered_map[a.question_id] = a.selected

        return render_template(
            "quiz.html",
            quiz_session=quiz_session,
            question=question,
            q_index=q_index,
            q_total=len(q_ids),
            q_ids=q_ids,
            existing=existing,
            answered_map=answered_map,
        )

    @app.route("/api/submit", methods=["POST"])
    @login_required
    def submit_answer():
        """回答を保存する（採点は結果表示時に一括で行う）。"""
        data = request.get_json()
        session_id = data["session_id"]
        question_id = data["question_id"]
        selected = data["selected"]  # 0-3

        existing = Attempt.query.filter_by(
            session_id=session_id, question_id=question_id
        ).first()

        if existing:
            existing.selected = selected
        else:
            attempt = Attempt(
                session_id=session_id,
                question_id=question_id,
                selected=selected,
            )
            db.session.add(attempt)

        db.session.commit()

        return jsonify({"ok": True})

    @app.route("/result/<int:session_id>")
    @login_required
    def result(session_id: int):
        quiz_session = QuizSession.query.get_or_404(session_id)
        if quiz_session.user_id and quiz_session.user_id != session["user_id"]:
            return redirect(url_for("index"))
        attempts = Attempt.query.filter_by(session_id=session_id).all()

        # 一括採点（まだ採点されていない場合）
        if not quiz_session.finished_at:
            for a in attempts:
                q = a.question
                if q.answer is not None and a.selected is not None:
                    a.is_correct = (a.selected == q.answer)
                else:
                    a.is_correct = False
            quiz_session.correct_count = sum(1 for a in attempts if a.is_correct)
            quiz_session.finished_at = datetime.now(JST)
            db.session.commit()

        # タグ別成績
        tag_stats: dict[str, dict] = {}
        for a in attempts:
            q = a.question
            for tag in q.tags:
                if tag not in tag_stats:
                    tag_stats[tag] = {"total": 0, "correct": 0}
                tag_stats[tag]["total"] += 1
                if a.is_correct:
                    tag_stats[tag]["correct"] += 1

        return render_template(
            "result.html",
            quiz_session=quiz_session,
            attempts=attempts,
            tag_stats=tag_stats,
        )

    def _get_wrong_question_ids(user_id: int) -> list[int]:
        """最新の回答が不正解の問題IDを返す。"""
        all_attempts = (
            db.session.query(Attempt)
            .join(QuizSession)
            .filter(QuizSession.user_id == user_id)
            .order_by(Attempt.created_at.desc())
            .all()
        )
        latest: dict[int, Attempt] = {}
        for a in all_attempts:
            if a.question_id not in latest:
                latest[a.question_id] = a
        return [qid for qid, a in latest.items() if not a.is_correct]

    @app.route("/review")
    @login_required
    def review():
        # 最新の回答が不正解の問題一覧（自分の回答のみ）
        all_attempts = (
            db.session.query(Attempt)
            .join(QuizSession)
            .filter(QuizSession.user_id == session["user_id"])
            .order_by(Attempt.created_at.desc())
            .all()
        )

        seen = set()
        unique_wrong = []
        for a in all_attempts:
            if a.question_id not in seen:
                seen.add(a.question_id)
                if not a.is_correct:
                    unique_wrong.append(a)

        return render_template("review.html", wrong_attempts=unique_wrong)


# Gunicorn 用エントリポイント: gunicorn app:app
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5555)
