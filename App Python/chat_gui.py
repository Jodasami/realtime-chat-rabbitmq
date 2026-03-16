import os
import queue
import threading
import time
import datetime
from collections import deque

import tkinter as tk
from tkinter import ttk

import pika
import psycopg                          # Para conectarse a PostgreSQL
from dotenv import load_dotenv

# -- Importar logica de pythonBD.py --------------------------
from pythonBD import send_to_queue, start_consumer, fetch_history

load_dotenv()


# ============================================================
#  METRICAS
# ============================================================

class Metrics:
    def __init__(self):
        self._lock      = threading.Lock()
        self.sent       = 0
        self.received   = 0
        self.errors     = 0
        self._latencies = deque(maxlen=1000)

    def record_sent(self):
        with self._lock: self.sent += 1

    def record_received(self):
        with self._lock: self.received += 1

    def record_error(self):
        with self._lock: self.errors += 1

    def record_latency(self, ms: float):
        with self._lock: self._latencies.append(ms)

    def snapshot(self):
        with self._lock:
            lats = list(self._latencies)
        avg = (sum(lats) / len(lats)) if lats else 0
        p95 = sorted(lats)[int(len(lats) * 0.95) - 1] if len(lats) >= 20 else 0
        return {
            "sent":     self.sent,
            "received": self.received,
            "errors":   self.errors,
            "avg_ms":   round(avg, 2),
            "p95_ms":   round(p95, 2),
        }


METRICS = Metrics()


# ============================================================
#  PALETA DE COLORES
# ============================================================

C = {
    "bg":          "#0d1117",
    "panel":       "#161b22",
    "surface":     "#1c2128",
    "border":      "#30363d",
    "accent":      "#2f81f7",
    "accent2":     "#3fb950",
    "danger":      "#f85149",
    "warn":        "#d29922",
    "bubble_me":   "#1a3a5c",
    "bubble_peer": "#1e2530",
    "text":        "#e6edf3",
    "subtext":     "#8b949e",
    "input_bg":    "#21262d",
    "send_bg":     "#1f6feb",
    "send_hover":  "#388bfd",
    "stress_bg":   "#2d1f0a",
    "stress_fg":   "#ffa657",
}


# ============================================================
#  WIDGETS REUTILIZABLES
# ============================================================

class FlatButton(tk.Label):
    def __init__(self, parent, text, command,
        bg, fg="#fff", hover=None,
                 font=None, padx=14, pady=7, **kw):
        self._bg    = bg
        self._hover = hover or bg
        self._cmd   = command
        super().__init__(parent, text=text, bg=bg, fg=fg,
        font=font or ("Segoe UI", 10, "bold"),
        padx=padx, pady=pady, cursor="hand2", **kw)
        self.bind("<Enter>",    lambda e: self.config(bg=self._hover))
        self.bind("<Leave>",    lambda e: self.config(bg=self._bg))
        self.bind("<Button-1>", lambda e: self._cmd())


class StatusDot(tk.Canvas):
    def __init__(self, parent, size=10, **kw):
        super().__init__(parent, width=size, height=size,
                         bg=C["panel"], highlightthickness=0, **kw)
        self._oval = self.create_oval(
            1, 1, size-1, size-1, fill=C["warn"], outline="")

    def set_color(self, color):
        self.itemconfig(self._oval, fill=color)


# ============================================================
#  VENTANA PRINCIPAL
# ============================================================

class ChatApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("ChatPyssage  Python <-> Java  |  RabbitMQ + PostgreSQL")
        self.geometry("1060x700")
        self.minsize(860, 540)
        self.configure(bg=C["bg"])

        self._inbox       = queue.Queue()
        self._msg_counter = 0

        self._build_ui()
        self._init_services()
        self._poll_inbox()

    # --------------------------------------------------------
    #  CONSTRUCCION DE LA UI
    # --------------------------------------------------------

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = tk.Frame(self, bg=C["panel"], width=240)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

        main = tk.Frame(self, bg=C["bg"])
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        self._build_topbar(main)
        self._build_chat_area(main)
        self._build_input_area(main)

    # -- Sidebar ---------------------------------------------

    def _build_sidebar(self, p):
        hdr = tk.Frame(p, bg=C["panel"], padx=14, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ChatPyssage",
        font=("Segoe UI", 14, "bold"),
        fg=C["accent"], bg=C["panel"]).pack(anchor="w")
        tk.Label(hdr, text="Python  <->  Java  |  RabbitMQ",
        font=("Segoe UI", 9),
        fg=C["subtext"], bg=C["panel"]).pack(anchor="w")

        self._divider(p)

        cf = tk.Frame(p, bg=C["panel"], padx=10, pady=6)
        cf.pack(fill="x")
        tk.Label(cf, text="CONTACTO", font=("Segoe UI", 7, "bold"),
        fg=C["subtext"], bg=C["panel"]).pack(anchor="w", pady=(0,4))
        card = tk.Frame(cf, bg=C["surface"], padx=10, pady=8)
        card.pack(fill="x")
        tk.Label(card, text="JB", font=("Segoe UI", 16),
        bg=C["surface"], fg=C["text"]).pack(side="left")
        info = tk.Frame(card, bg=C["surface"])
        info.pack(side="left", padx=(8,0))
        tk.Label(info, text="Java Backend",
        font=("Segoe UI", 11, "bold"),
        fg=C["text"], bg=C["surface"]).pack(anchor="w")
        self._java_lbl = tk.Label(info, text="esperando...",
        font=("Segoe UI", 8),
        fg=C["warn"], bg=C["surface"])
        self._java_lbl.pack(anchor="w")

        self._divider(p)

        sf = tk.Frame(p, bg=C["panel"], padx=14, pady=6)
        sf.pack(fill="x")
        tk.Label(sf, text="CONEXIONES", font=("Segoe UI", 7, "bold"),
        fg=C["subtext"], bg=C["panel"]).pack(anchor="w", pady=(0,6))
        self._dot_pg, self._lbl_pg = self._conn_row(sf, "PostgreSQL")
        self._dot_mq, self._lbl_mq = self._conn_row(sf, "RabbitMQ")

        self._divider(p)

        mf = tk.Frame(p, bg=C["panel"], padx=14, pady=6)
        mf.pack(fill="x")
        tk.Label(mf, text="METRICAS EN VIVO", font=("Segoe UI", 7, "bold"),
        fg=C["subtext"], bg=C["panel"]).pack(anchor="w", pady=(0,6))
        self._mvars = {}
        for key, label in [
            ("sent",     "Enviados"),
            ("received", "Recibidos"),
            ("errors",   "Errores"),
            ("avg_ms",   "Lat. avg (ms)"),
            ("p95_ms",   "Lat. p95 (ms)"),
        ]:
            row = tk.Frame(mf, bg=C["panel"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, font=("Segoe UI", 8),
            fg=C["subtext"], bg=C["panel"]).pack(side="left")
            var = tk.StringVar(value="0")
            tk.Label(row, textvariable=var, font=("Consolas", 8),
            fg=C["accent2"], bg=C["panel"]).pack(side="right")
            self._mvars[key] = var

        self._divider(p)

        bf = tk.Frame(p, bg=C["panel"], padx=10, pady=6)
        bf.pack(fill="x")
        FlatButton(bf, "Ver historial BD",
        self._show_history,
        bg=C["surface"], fg=C["text"], hover=C["border"],
        font=("Segoe UI", 9)).pack(fill="x", pady=2)
        FlatButton(bf, "Prueba de estres",
        self._stress_test,
        bg=C["stress_bg"], fg=C["stress_fg"], hover="#3d2810",
        font=("Segoe UI", 9)).pack(fill="x", pady=2)
        FlatButton(bf, "Reconectar",
        self._reconnect,
        bg=C["surface"], fg=C["text"], hover=C["border"],
        font=("Segoe UI", 9)).pack(fill="x", pady=2)

    def _conn_row(self, parent, label):
        row = tk.Frame(parent, bg=C["panel"])
        row.pack(fill="x", pady=3)
        dot = StatusDot(row)
        dot.pack(side="left", padx=(0,6))
        tk.Label(row, text=label, font=("Segoe UI", 8),
        fg=C["subtext"], bg=C["panel"]).pack(side="left")
        lbl = tk.Label(row, text="--", font=("Segoe UI", 8),
        fg=C["warn"], bg=C["panel"])
        lbl.pack(side="right")
        return dot, lbl

    def _divider(self, parent):
        tk.Frame(parent, bg=C["border"], height=1).pack(
            fill="x", padx=10, pady=4)

    # -- Topbar ----------------------------------------------

    def _build_topbar(self, parent):
        bar = tk.Frame(parent, bg=C["panel"], height=50, padx=16)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.columnconfigure(0, weight=1)

        left = tk.Frame(bar, bg=C["panel"])
        left.grid(row=0, column=0, sticky="w", pady=10)
        tk.Label(left, text="Java Backend",
        font=("Segoe UI", 12, "bold"),
        fg=C["text"], bg=C["panel"]).pack(side="left")
        tk.Label(left, text="   RabbitMQ  PostgreSQL",
        font=("Segoe UI", 8),
        fg=C["subtext"], bg=C["panel"]).pack(side="left")

        right = tk.Frame(bar, bg=C["panel"])
        right.grid(row=0, column=1, sticky="e", pady=10)
        self._clock_lbl = tk.Label(right, text="",
        font=("Consolas", 9), fg=C["subtext"], bg=C["panel"])
        self._clock_lbl.pack()
        self._tick()

    def _tick(self):
        self._clock_lbl.config(
            text=datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.after(1000, self._tick)

    # -- Area de chat ----------------------------------------

    def _build_chat_area(self, parent):
        frame = tk.Frame(parent, bg=C["bg"])
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(frame, bg=C["bg"],
                                  highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(frame, orient="vertical",
        command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._msg_frame = tk.Frame(self._canvas, bg=C["bg"])
        self._cw = self._canvas.create_window(
            (0, 0), window=self._msg_frame, anchor="nw")

        self._msg_frame.bind("<Configure>", lambda e:
            self._canvas.configure(
                scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e:
            self._canvas.itemconfig(self._cw, width=e.width))
        self._canvas.bind_all("<MouseWheel>", lambda e:
            self._canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    # -- Input -----------------------------------------------

    def _build_input_area(self, parent):
        bar = tk.Frame(parent, bg=C["panel"], padx=14, pady=10)
        bar.grid(row=2, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)

        self._entry = tk.Text(
            bar, height=2, font=("Segoe UI", 11),
            fg=C["text"], bg=C["input_bg"],
            insertbackground=C["text"],
            relief="flat", bd=0, padx=10, pady=8, wrap="word"
        )
        self._entry.grid(row=0, column=0, sticky="ew", padx=(0,10))
        self._entry.bind("<Return>",       self._on_enter)
        self._entry.bind("<Shift-Return>", lambda e: None)

        FlatButton(bar, "  Enviar  ->  ",
        self._send_message,
        bg=C["send_bg"], hover=C["send_hover"],
        font=("Segoe UI", 10, "bold"),
        pady=10).grid(row=0, column=1)

        tk.Label(bar,
        text="Enter = enviar  |  Shift+Enter = nueva linea",
        font=("Segoe UI", 8), fg=C["subtext"],
        bg=C["panel"]).grid(row=1, column=0,
        sticky="w", pady=(4,0))

    # --------------------------------------------------------
    #  SERVICIOS
    # --------------------------------------------------------

    def _init_services(self):
        self._system_msg("Verificando conexiones...")

        def _check():
            # ------------------------------------------- POSTGRESQL (PARAMETROS) -------------------------------------------
            try:
                conn = psycopg.connect(
                    host=os.getenv("PG_HOST",     "localhost"),
                    port=os.getenv("PG_PORT",     "5432"),
                    dbname=os.getenv("PG_DB",     "Chat_DB"),
                    user=os.getenv("PG_USER",     "postgres"),
                    password=os.getenv("PG_PASSWORD", "admin"),
                    connect_timeout=5
                )
            # ---------------------------------------------------------------------------------------------------------------
                conn.close()
                self.after(0, lambda: (
                    self._dot_pg.set_color(C["accent2"]),
                    self._lbl_pg.config(text="conectado", fg=C["accent2"])
                ))
                self.after(0, self._load_history)
            except Exception as e:
                err = f"PostgreSQL error: {e!r}"

                self.after(0, lambda: (
                    self._dot_pg.set_color(C["danger"]),
                    self._lbl_pg.config(text="error", fg=C["danger"])
                ))
                self.after(0, lambda: self._system_msg(err))

            # -- RabbitMQ --
            try:
                params = pika.ConnectionParameters(
                    host=os.getenv("RABBITMQ_HOST", "localhost"),
                    heartbeat=30,
                    blocked_connection_timeout=300
                )
                test = pika.BlockingConnection(params)
                test.close()
                self.after(0, lambda: (
                    self._dot_mq.set_color(C["accent2"]),
                    self._lbl_mq.config(text="conectado", fg=C["accent2"]),
                    self._java_lbl.config(text="en linea", fg=C["accent2"])
                ))
                start_consumer(self._on_incoming)   # <- pythonBD.py
                self.after(0, lambda: self._system_msg(
                    "Consumidor RabbitMQ activo - escuchando mensajes de Java"))
            except Exception as e:
                err = f"RabbitMQ error: {e!r}"

                self.after(0, lambda: (
                    self._dot_mq.set_color(C["danger"]),
                    self._lbl_mq.config(text="error", fg=C["danger"])
                ))
                self.after(0, lambda: self._system_msg(err))

        threading.Thread(target=_check, daemon=True).start()

    def _reconnect(self):
        self._system_msg("Reconectando...")
        self._init_services()

    def _load_history(self):
        rows = fetch_history(30)    # <- pythonBD.py
        if rows:
            self._system_msg(
                f"Historial cargado ({len(rows)} mensajes)")
            for r in rows:
                is_me = (r[1] == "Python")
                ts    = str(r[5])[:19] if r[5] else ""
                self._bubble(r[1], r[3], is_me=is_me,
                meta=ts, animate=False)
        self._scroll_bottom()

    # --------------------------------------------------------
    #  MENSAJERIA
    # --------------------------------------------------------

    def _on_incoming(self, sender: str, message: str):
        self._inbox.put((sender, message))

    def _poll_inbox(self):
        try:
            while True:
                sender, message = self._inbox.get_nowait()
                self._bubble(sender, message, is_me=False)
                self._java_lbl.config(text="activo", fg=C["accent2"])
                METRICS.record_received()
        except queue.Empty:
            pass
        self._update_metrics()
        self.after(200, self._poll_inbox)

    def _send_message(self):
        text = self._entry.get("1.0", "end").strip()
        if not text:
            return
        self._entry.delete("1.0", "end")
        self._msg_counter += 1
        mid = f"msg_{self._msg_counter}"
        self._bubble("Python", text, is_me=True, meta="enviando...")

        def _do():
            try:
                send_to_queue(text)    # <- pythonBD.py
                METRICS.record_sent()
                self.after(0, lambda: self._system_msg(
                    "Guardado en PostgreSQL · publicado en RabbitMQ"))
            except Exception as e:
                METRICS.record_error()
                err = f"Error al enviar: {e!r}"
                self.after(0, lambda: self._system_msg(err))

        threading.Thread(target=_do, daemon=True).start()

    def _on_enter(self, event):
        self._send_message()
        return "break"

    # --------------------------------------------------------
    #  BURBUJAS DE CHAT
    # --------------------------------------------------------

    def _bubble(self, sender, text, is_me=True, meta="", animate=True):
        outer = tk.Frame(self._msg_frame, bg=C["bg"])
        outer.pack(fill="x", padx=16, pady=5,
        anchor="e" if is_me else "w")

        bg     = C["bubble_me"]  if is_me else C["bubble_peer"]
        border = C["accent"]     if is_me else C["subtext"]

        wrapper = tk.Frame(outer, bg=C["bg"])
        wrapper.pack(side="right" if is_me else "left")

        if not is_me:
            tk.Label(wrapper, text=f"Java  {sender}",
        font=("Segoe UI", 8, "bold"),
        fg=C["accent"], bg=C["bg"]).pack(
        anchor="w", padx=10, pady=(0,2))

        bubble = tk.Frame(wrapper, bg=bg,
        highlightbackground=border,
        highlightthickness=1,
        padx=14, pady=8)
        bubble.pack()

        tk.Label(bubble, text=text,
        font=("Segoe UI", 10),
        fg=C["text"], bg=bg,
        wraplength=420, justify="left").pack(anchor="w")

        ts  = datetime.datetime.now().strftime("%H:%M:%S")
        tag = f"{ts}  {meta}" if meta else ts
        tk.Label(bubble, text=tag,
        font=("Consolas", 7),
        fg=C["subtext"], bg=bg).pack(anchor="e", pady=(4,0))

        if animate:
            self.after(30, self._scroll_bottom)

    def _system_msg(self, text: str):
        f = tk.Frame(self._msg_frame, bg=C["bg"])
        f.pack(fill="x", pady=4)
        tk.Label(f, text=text, font=("Consolas", 8),
        fg=C["subtext"], bg=C["bg"]).pack()
        self.after(30, self._scroll_bottom)

    def _scroll_bottom(self):
        self._canvas.yview_moveto(1.0)

    def _update_metrics(self):
        snap = METRICS.snapshot()
        for k, var in self._mvars.items():
            var.set(str(snap.get(k, 0)))

    # --------------------------------------------------------
    #  HISTORIAL
    # --------------------------------------------------------

    def _show_history(self):
        rows = fetch_history(100)   # <- pythonBD.py
        win  = tk.Toplevel(self)
        win.title("Historial - PostgreSQL")
        win.geometry("820x440")
        win.configure(bg=C["bg"])

        tk.Label(win, text="Historial de mensajes en PostgreSQL",
        font=("Segoe UI", 12, "bold"),
        fg=C["accent"], bg=C["bg"]).pack(
        pady=(12,2), padx=14, anchor="w")
        tk.Label(win, text=f"{len(rows)} registros encontrados",
        font=("Segoe UI", 9),
        fg=C["subtext"], bg=C["bg"]).pack(padx=14, anchor="w")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("H.Treeview",
                        background=C["surface"], foreground=C["text"],
                        fieldbackground=C["surface"],
                        rowheight=26, font=("Consolas", 9))
        style.configure("H.Treeview.Heading",
                        background=C["panel"], foreground=C["accent"],
                        font=("Segoe UI", 9, "bold"))

        cols  = ("id","sender","receiver","message","status","timestamp")
        frame = tk.Frame(win, bg=C["bg"])
        frame.pack(fill="both", expand=True, padx=14, pady=8)

        vsb  = ttk.Scrollbar(frame, orient="vertical")
        tree = ttk.Treeview(frame, columns=cols, show="headings",
        style="H.Treeview",
        yscrollcommand=vsb.set)
        vsb.config(command=tree.yview)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

        widths = {"id":40,"sender":80,"receiver":80,
        "message":280,"status":70,"timestamp":160}
        for c in cols:
            tree.heading(c, text=c.upper())
            tree.column(c, width=widths[c], anchor="w")

        for r in rows:
            tag = "me" if r[1] == "Python" else "peer"
            tree.insert("", "end", values=list(r), tags=(tag,))

        tree.tag_configure("me",   background="#1a3a5c")
        tree.tag_configure("peer", background=C["surface"])

        if not rows:
            tk.Label(win, text="Sin registros en la base de datos.",
            font=("Segoe UI", 10),
            fg=C["subtext"], bg=C["bg"]).pack(pady=20)

    # --------------------------------------------------------
    #  PRUEBA DE ESTRES
    # --------------------------------------------------------

    def _stress_test(self):
        win = tk.Toplevel(self)
        win.title("Prueba de Estres")
        win.geometry("480x360")
        win.configure(bg=C["bg"])
        win.resizable(False, False)

        tk.Label(win, text="Prueba de Estres",
        font=("Segoe UI", 14, "bold"),
        fg=C["stress_fg"], bg=C["bg"]).pack(pady=(16,4))
        tk.Label(win,
        text="Envia N mensajes y mide latencia / throughput",
        font=("Segoe UI", 9),
        fg=C["subtext"], bg=C["bg"]).pack(pady=(0,12))

        row1 = tk.Frame(win, bg=C["bg"])
        row1.pack()
        tk.Label(row1, text="Cantidad de mensajes:",
        font=("Segoe UI", 10),
        fg=C["text"], bg=C["bg"]).pack(side="left", padx=(0,8))
        n_var = tk.IntVar(value=50)
        tk.Spinbox(row1, from_=10, to=500, increment=10,
        textvariable=n_var, width=6,
        font=("Consolas", 11),
        bg=C["input_bg"], fg=C["text"],
        buttonbackground=C["surface"],
        relief="flat").pack(side="left")

        result_var = tk.StringVar(value="")
        tk.Label(win, textvariable=result_var,
        font=("Consolas", 10),
        fg=C["accent2"], bg=C["bg"],
        justify="left").pack(pady=12, padx=20)

        prog_var = tk.DoubleVar(value=0)
        ttk.Progressbar(win, variable=prog_var,
                        maximum=100, length=400).pack(pady=6)

        def _run():
            n  = n_var.get()
            t0 = time.time()
            ok = err = 0
            for i in range(1, n+1):
                txt = (f"[stress] msg_{i:04d} "
                f"@ {datetime.datetime.now().isoformat()}")
                try:
                    send_to_queue(txt) # <- pythonBD.py
                    METRICS.record_sent()
                    ok += 1
                except Exception:
                    METRICS.record_error()
                    err += 1
                prog_var.set(i / n * 100)
                win.update_idletasks()

            elapsed    = time.time() - t0
            throughput = ok / elapsed if elapsed > 0 else 0
            snap       = METRICS.snapshot()
            result_var.set(
                f"  Enviados   : {ok}   |  Errores : {err}\n"
                f"  Tiempo     : {elapsed:.2f} s\n"
                f"  Throughput : {throughput:.1f} msg/s\n"
                f"  Lat. avg   : {snap['avg_ms']} ms\n"
                f"  Lat. p95   : {snap['p95_ms']} ms"
            )

        FlatButton(win, "Iniciar prueba",
        lambda: threading.Thread(
        target=_run, daemon=True).start(),
        bg=C["stress_bg"], fg=C["stress_fg"],
        hover="#3d2810",
        font=("Segoe UI", 11, "bold"),
        pady=10).pack(pady=6)




