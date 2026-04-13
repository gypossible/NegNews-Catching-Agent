"""
NegNews-Catching Agent — Flask Web Server
本地: python app.py  →  http://localhost:5000
线上: Render 自动通过 gunicorn 启动
"""

import io
import os
import sys
import json
import queue
import threading
import uuid
from pathlib import Path

# 确保项目根目录在 sys.path 中（gunicorn 启动时可能不包含）
BASE_DIR = Path(__file__).parent.resolve()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from flask import Flask, request, jsonify, send_file, Response

import config
from modules.excel_handler import load_workbook, iter_entities, save_workbook
from modules.result_writer import write_results
from modules.searchers.baidu_searcher import BaiduSearcher
from modules.searchers.sina_searcher import SinaSearcher
from modules.searchers.court_searcher import CourtSearcher
from modules.searchers.qichacha_searcher import QiChaChaSearcher
from utils.http_client import build_session

BASE_DIR = Path(__file__).parent.resolve()

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")

# task_id -> {"queue": Queue, "result": bytes, "filename": str}
_tasks: dict[str, dict] = {}


def _run_task(task_id: str, file_bytes: bytes, original_filename: str):
    q = _tasks[task_id]["queue"]

    def emit(msg: dict):
        q.put(f"data: {json.dumps(msg, ensure_ascii=False)}\n\n")

    try:
        wb = load_workbook(io.BytesIO(file_bytes))
        session = build_session()
        searchers = [
            BaiduSearcher(session, config),
            SinaSearcher(session, config),
            CourtSearcher(session, config),
            QiChaChaSearcher(session, config),
        ]

        entities = list(iter_entities(wb))
        total = len(entities)
        emit({"type": "start", "total": total})

        for idx, (sheet, row_idx, entity) in enumerate(entities, 1):
            emit({"type": "progress", "current": idx, "total": total,
                  "entity": entity, "sheet": sheet.title})

            all_results = []
            for keyword in config.KEYWORDS:
                for searcher in searchers:
                    try:
                        results = searcher.search(entity, keyword)
                        all_results.extend(results)
                    except Exception as e:
                        emit({"type": "warn",
                              "msg": f"{searcher.__class__.__name__} 失败 ({keyword}): {e}"})

            seen, unique = set(), []
            for r in all_results:
                key = r.get("url") or r.get("title", "")
                if key and key not in seen:
                    seen.add(key)
                    unique.append(r)
            unique = unique[: config.MAX_RESULTS_PER_ENTITY]

            write_results(sheet, row_idx, unique)
            emit({"type": "entity_done", "entity": entity,
                  "count": len(unique), "current": idx, "total": total})

        # 保存到内存 buffer
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        _tasks[task_id]["result"] = buf.read()
        _tasks[task_id]["filename"] = f"result_{original_filename}"

        emit({"type": "done", "file": f"result_{original_filename}"})

    except Exception as e:
        emit({"type": "error", "msg": str(e)})
    finally:
        q.put(None)


@app.route("/")
def index():
    return send_file(str(BASE_DIR / "index.html"))


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or not f.filename.endswith((".xlsx", ".xls")):
        return jsonify({"error": "请上传 .xlsx 或 .xls 文件"}), 400

    task_id = uuid.uuid4().hex
    file_bytes = f.read()
    _tasks[task_id] = {"queue": queue.Queue(), "result": None, "filename": None}

    t = threading.Thread(target=_run_task,
                         args=(task_id, file_bytes, f.filename), daemon=True)
    t.start()
    return jsonify({"task_id": task_id})


@app.route("/progress/<task_id>")
def progress(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        return jsonify({"error": "task not found"}), 404

    def generate():
        q = task["queue"]
        while True:
            msg = q.get()
            if msg is None:
                break
            yield msg

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/download/<task_id>")
def download(task_id: str):
    task = _tasks.get(task_id)
    if not task or not task["result"]:
        return jsonify({"error": "结果文件未找到，请先执行任务"}), 404

    return send_file(
        io.BytesIO(task["result"]),
        as_attachment=True,
        download_name=task["filename"],
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, port=port, threaded=True)
