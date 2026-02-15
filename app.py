"""第二種電気工事士 CBT 練習アプリ。"""

import json
import random
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

from models import Attempt, Question, QuizSession, db


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "dev"

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def register_routes(app: Flask):

    @app.route("/")
    def index():
        # 年度・半期一覧
        years = db.session.query(
            Question.year, Question.half
        ).distinct().order_by(Question.year.desc()).all()

        # タグ一覧
        all_tags = set()
        for (tags_json,) in db.session.query(Question.tags_json).all():
            all_tags.update(json.loads(tags_json))
        tags = sorted(all_tags)

        # 直近の成績
        recent_sessions = QuizSession.query.order_by(
            QuizSession.started_at.desc()
        ).limit(10).all()

        return render_template(
            "index.html", years=years, tags=tags, recent_sessions=recent_sessions
        )

    @app.route("/quiz/start", methods=["POST"])
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
            # 間違えた問題のIDを取得
            wrong_ids = [
                a.question_id
                for a in Attempt.query.filter_by(is_correct=False).all()
            ]
            if wrong_ids:
                query = query.filter(Question.id.in_(set(wrong_ids)))

        questions = query.all()
        if not questions:
            return redirect(url_for("index"))

        if len(questions) > count:
            questions = random.sample(questions, count)

        q_ids = [q.id for q in questions]
        session = QuizSession(
            category=f"{year}_{half}" if year else tag or "all",
            total_count=len(q_ids),
            question_ids_json=json.dumps(q_ids),
        )
        db.session.add(session)
        db.session.commit()

        return redirect(url_for("quiz", session_id=session.id, q=0))

    @app.route("/quiz/<int:session_id>")
    def quiz(session_id: int):
        session = QuizSession.query.get_or_404(session_id)
        q_ids = session.question_ids
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
            session=session,
            question=question,
            q_index=q_index,
            q_total=len(q_ids),
            q_ids=q_ids,
            existing=existing,
            answered_map=answered_map,
        )

    @app.route("/api/submit", methods=["POST"])
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
    def result(session_id: int):
        session = QuizSession.query.get_or_404(session_id)
        attempts = Attempt.query.filter_by(session_id=session_id).all()

        # 一括採点（まだ採点されていない場合）
        if not session.finished_at:
            for a in attempts:
                q = a.question
                if q.answer is not None and a.selected is not None:
                    a.is_correct = (a.selected == q.answer)
                else:
                    a.is_correct = False
            session.correct_count = sum(1 for a in attempts if a.is_correct)
            session.finished_at = datetime.now(timezone.utc)
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
            session=session,
            attempts=attempts,
            tag_stats=tag_stats,
        )

    @app.route("/review")
    def review():
        # 間違えた問題一覧（重複排除、最新の回答を優先）
        wrong_attempts = (
            db.session.query(Attempt)
            .filter_by(is_correct=False)
            .order_by(Attempt.created_at.desc())
            .all()
        )

        seen = set()
        unique_wrong = []
        for a in wrong_attempts:
            if a.question_id not in seen:
                seen.add(a.question_id)
                unique_wrong.append(a)

        return render_template("review.html", wrong_attempts=unique_wrong)


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5555)
