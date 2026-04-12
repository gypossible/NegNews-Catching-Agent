"""
NegNews-Catching Agent — Flask Web Server
启动: python app.py
访问: http://localhost:5000
"""

import os
import json
import queue
import threading
import uuid
from pathlib import Path

from flask import Flask, request, jsonify, send_file, Response, send_from_directory

import config
from modules.excel_handler import load_workbook, iter_entities, save_workbook
from modules.result_writer import write_results
from modules.searchers.baidu_searcher import BaiduSearcher
from modules.searchers.sina_searcher import SinaSearcher
from modules.searchers.court_searcher import CourtSearcher
from modules.searchers.qichacha_searcher import QiChaChaSearcher
from utils.http_client import build_session

app = Flask(__name__, static_folder=".", static_url_path="")

UPLOAD_DIR = Path("uploads")
RESULT_DIR = Path("results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# task_id -> queue of SSE messages
_task_queues: dict[str, queue.Queue] = {}


def _run_task(task_id: str, input_path: Path, output_path: Path):
    q = _task_queues[task_id]

    def emit(msg: dict):
        q.put(f"data: {json.dumps(msg, ensure_ascii=False)}\n\n")

    try:
        wb = load_workbook(str(input_path))
        session = build_session()
        searchers = [
            BaiduSearcher(session, config),
            SinaSearcher(session, config),
            CourtSearcher(session, config),
            QiChaChaSearcher(session, config),
        ]

        # 先统计总数
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

            # 去重
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

        save_workbook(wb, str(output_path))
        emit({"type": "done", "file": output_path.name})

    except Exception as e:
        emit({"type": "error", "msg": str(e)})
    finally:
        q.put(None)  # sentinel


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or not f.filename.endswith((".xlsx", ".xls")):
        return jsonify({"error": "请上传 .xlsx 或 .xls 文件"}), 400

    task_id = uuid.uuid4().hex
    input_path = UPLOAD_DIR / f"{task_id}_{f.filename}"
    output_path = RESULT_DIR / f"{task_id}_result_{f.filename}"
    f.save(str(input_path))

    _task_queues[task_id] = queue.Queue()
    t = threading.Thread(target=_run_task,
                         args=(task_id, input_path, output_path), daemon=True)
    t.start()

    return jsonify({"task_id": task_id})


@app.route("/progress/<task_id>")
def progress(task_id: str):
    q = _task_queues.get(task_id)
    if not q:
        return jsonify({"error": "task not found"}), 404

    def generate():
        while True:
            msg = q.get()
            if msg is None:
                break
            yield msg

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/download/<task_id>")
def download(task_id: str):
    matches = list(RESULT_DIR.glob(f"{task_id}_result_*"))
    if not matches:
        return jsonify({"error": "文件未找到"}), 404
    return send_file(str(matches[0]), as_attachment=True,
                     download_name=matches[0].name.split("_result_", 1)[-1])


if __name__ == "__main__":
    app.run(debug=False, port=5000, threaded=True)
