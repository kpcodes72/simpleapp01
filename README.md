# Fullstack Mini

## Running and closing

If an agent or LLM is instructed to **run the app**, start the local server from this directory and leave it running:

```text
python app.py
```

It serves http://127.0.0.1:8080. If that server is already running, do not start a second copy.

If an agent or LLM is instructed to **close the app**, shut that local server down. Stop the `python app.py` process. Leave `app.db` in place.

## Architecture

The app is a local process and a few files on disk. There is no package install, no build step, and no separate client store.

| File | Role |
| --- | --- |
| `app.py` | HTTP server, schema, and SQL. Python standard library only. |
| `index.html` | The page. Interactivity is HTMX attributes on the forms. |
| `app.db` | SQLite database, created on first run. This is the application state. |

SQLite is the only state. A request writes a row, reads the table back, and returns HTML for that result. HTMX swaps the returned markup into `#board`. The screen is the latest query, not a second copy of the list kept in JavaScript.

`GET /` reads `index.html` and fills the `<!--BOARD-->` marker with the current list. `GET /todos` returns that list fragment alone. `POST /todos`, `POST /todos/<id>/toggle`, and `POST /todos/<id>/delete` change the database and then render the list again. When the request comes from HTMX (`HX-Request: true`), the response is the fragment. Otherwise the server answers `303` back to `/`, so the forms still work without JavaScript.

User text is HTML-escaped. SQL values are bound parameters. The database uses WAL mode, so the file can be read while the server is running. The first run also creates `app.db-wal` and `app.db-shm`.

HTMX 2.0.11 is loaded from jsDelivr. To keep the app fully offline, save that script next to these files and point the script tag at the local copy.

## To-do example

The sample app is a to-do list: add a task, toggle it done, delete it, or refresh the list from the database. Open http://127.0.0.1:8080 after starting the server.
