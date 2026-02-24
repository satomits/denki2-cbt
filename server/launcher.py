"""Windows EXE 起動用エントリポイント。

PyInstaller --onedir でパッケージングする際に使用する。
frozen 判定でベースディレクトリを決定し、Flask を別スレッドで起動する。
"""

import os
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path


def get_base_dir() -> Path:
    """frozen（exe）時と通常実行時でベースディレクトリを切り替える。

    PyInstaller バージョン別の挙動:
      5.x --onedir: _MEIPASS 未設定、データは exe 隣に展開
      6.x --onedir: _MEIPASS = exe隣の _internal/、データはそこに展開
    """
    if getattr(sys, "frozen", False):
        # _MEIPASS が存在すれば（PyInstaller 6.x）そちら、なければ exe 隣（5.x）
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        # 通常実行: このファイルの親ディレクトリ (server/)
        return Path(__file__).parent


def main():
    base_dir = get_base_dir()

    # app.py が BASE_DIR 環境変数を参照してパスを解決する
    os.environ["BASE_DIR"] = str(base_dir)

    # server/ を sys.path に追加（通常実行時の models.py 解決）
    server_dir = Path(__file__).parent
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    from app import create_app

    app = create_app()

    port = 5555

    def run_server():
        try:
            app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
        except Exception:
            traceback.print_exc()

    print(f"起動しています... http://localhost:{port}")
    print("終了するにはこのウィンドウを閉じるか Ctrl+C を押してください。")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # サーバー起動を少し待ってからブラウザを開く
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{port}")

    # メインスレッドをブロックし続ける
    # thread.join() は Windows で Ctrl-C を受け付けないため sleep ループを使う
    try:
        while server_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nサーバーを停止します。")
        sys.exit(0)


if __name__ == "__main__":
    main()
