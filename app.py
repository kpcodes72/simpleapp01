"""Local todos. SQLite is the state; responses are HTML."""

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import sqlite3
import urllib.parse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "app.db"
HOST, PORT = "127.0.0.1", 8080
TOGGLE = re.compile(r"^/todos/(\d+)/toggle$")
DELETE = re.compile(r"^/todos/(\d+)/delete$")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def with_db(fn):
    conn = connect()
    try:
        result = fn(conn)
        conn.commit()
        return result
    finally:
        conn.close()


def render_item(row):
    done = bool(row["done"])
    title = escape(row["title"])
    tid = row["id"]
    mark = "✓" if done else "○"
    css = "done" if done else ""
    return f"""<li class="{css}">
  <form method="post" action="/todos/{tid}/toggle"
        hx-post="/todos/{tid}/toggle" hx-target="#board" hx-swap="innerHTML">
    <button class="check" aria-pressed="{"true" if done else "false"}">{mark}</button>
  </form>
  <span>{title}</span>
  <form method="post" action="/todos/{tid}/delete"
        hx-post="/todos/{tid}/delete" hx-target="#board" hx-swap="innerHTML">
    <button class="delete" aria-label="Delete {title}">Delete</button>
  </form>
</li>"""


def board_html():
    rows = with_db(
        lambda c: c.execute("SELECT id, title, done FROM todos ORDER BY id").fetchall()
    )
    open_count = sum(1 for row in rows if not row["done"])
    items = "\n".join(render_item(row) for row in rows) or '<li class="empty">Nothing yet.</li>'
    return f'<p class="count">{open_count} open</p>\n<ul>\n{items}\n</ul>'


def page_html():
    template = (ROOT / "index.html").read_text(encoding="utf-8")
    return template.replace("<!--BOARD-->", board_html())


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            self.respond(200, page_html())
        elif path == "/todos":
            self.respond(200, board_html())
        else:
            self.respond(404, "Not found")

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        form = self.read_form()
        if path == "/todos":
            title = form.get("title", [""])[0].strip()[:200]
            if title:
                with_db(lambda c: c.execute("INSERT INTO todos (title) VALUES (?)", (title,)))
            self.finish_write()
        elif match := TOGGLE.match(path):
            todo_id = int(match.group(1))
            with_db(
                lambda c: c.execute(
                    "UPDATE todos SET done = CASE done WHEN 1 THEN 0 ELSE 1 END WHERE id = ?",
                    (todo_id,),
                )
            )
            self.finish_write()
        elif match := DELETE.match(path):
            todo_id = int(match.group(1))
            with_db(lambda c: c.execute("DELETE FROM todos WHERE id = ?", (todo_id,)))
            self.finish_write()
        else:
            self.respond(404, "Not found")

    def finish_write(self):
        if self.headers.get("HX-Request") == "true":
            self.respond(200, board_html())
        else:
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

    def read_form(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8")
        return urllib.parse.parse_qs(raw)

    def respond(self, status, body):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def main():
    init_db()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"http://{HOST}:{PORT}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
