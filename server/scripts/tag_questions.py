"""JSONL の問題データにキーワード辞書ベースで分野タグを付与する。

使い方:
    python scripts/tag_questions.py data/questions.jsonl
    python scripts/tag_questions.py data/questions.jsonl --tags-file data/tags.json
"""

import argparse
import json
import sys
from pathlib import Path

_DEFAULT_TAGS = str(Path(__file__).resolve().parent.parent.parent / "shared" / "tags.json")


def load_tag_dict(tags_file: str) -> dict[str, list[str]]:
    with open(tags_file, encoding="utf-8") as f:
        return json.load(f)


def tag_question(q: dict, tag_dict: dict[str, list[str]]) -> list[str]:
    """問題文と選択肢からキーワードマッチでタグを返す。"""
    text = q.get("question", "")
    for c in q.get("choices", []):
        text += " " + c

    matched = []
    for tag, keywords in tag_dict.items():
        if any(kw in text for kw in keywords):
            matched.append(tag)

    return matched


def main():
    parser = argparse.ArgumentParser(description="JSONL にタグを付与")
    parser.add_argument("jsonl", help="入力 JSONL ファイル")
    parser.add_argument("--tags-file", default=_DEFAULT_TAGS, help="タグ辞書 JSON")
    args = parser.parse_args()

    tags_file = Path(args.tags_file)
    if not tags_file.exists():
        print(f"Error: {args.tags_file} が見つかりません", file=sys.stderr)
        sys.exit(1)

    tag_dict = load_tag_dict(str(tags_file))

    jsonl_path = Path(args.jsonl)
    lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")

    updated = []
    tag_counts: dict[str, int] = {}
    for line in lines:
        q = json.loads(line)
        tags = tag_question(q, tag_dict)
        q["tags"] = tags
        updated.append(q)
        for t in tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for q in updated:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"{len(updated)} 問にタグを付与しました")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")


if __name__ == "__main__":
    main()
