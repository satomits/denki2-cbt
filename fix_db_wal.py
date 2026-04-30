"""
WAL モードになった SQLite DB を DELETE モード（デフォルト）に戻す修復スクリプト。
EXE と Flask サーバーを両方閉じてから実行してください。

実行方法:
    python fix_db_wal.py
"""
import os
import shutil
import sqlite3
from pathlib import Path

REPO = Path(__file__).parent

DB_PATHS = [
    REPO / "server" / "instance" / "app.db",
    REPO / "dist" / "denki2-cbt" / "_internal" / "instance" / "app.db",
]

TMP = Path("C:/Temp/denki2_fix.db")
TMP.parent.mkdir(exist_ok=True)


def fix_db(db_path: Path):
    if not db_path.exists():
        print(f"  スキップ（存在しない）: {db_path}")
        return

    wal = Path(str(db_path) + "-wal")
    shm = Path(str(db_path) + "-shm")
    tmp_wal = Path(str(TMP) + "-wal")
    tmp_shm = Path(str(TMP) + "-shm")

    print(f"\n修復中: {db_path}")
    try:
        # ローカルにコピー
        shutil.copy2(db_path, TMP)
        if wal.exists():
            shutil.copy2(wal, tmp_wal)
        if shm.exists():
            shutil.copy2(shm, tmp_shm)

        # WAL チェックポイント → DELETE モードへ
        con = sqlite3.connect(str(TMP), timeout=10)
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        mode = con.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        print(f"  journal_mode: {mode}")
        con.close()

        # 元の場所に書き戻し
        shutil.copy2(TMP, db_path)
        print(f"  書き戻し完了")

        # WAL/SHM を削除
        for f in [wal, shm, TMP, tmp_wal, tmp_shm]:
            try:
                f.unlink()
                print(f"  削除: {f.name}")
            except FileNotFoundError:
                pass

    except PermissionError:
        print("  PermissionError: EXE/Flask サーバーがまだ起動中です。閉じてから再実行してください。")
    except Exception as e:
        print(f"  エラー: {e}")


for p in DB_PATHS:
    fix_db(p)

print("\n完了。")
