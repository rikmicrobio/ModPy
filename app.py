"""
ModPy — Homology Modelling Pipeline
Developed by Rik Ganguly, Post Doctoral Fellow @ Hazra Group, IIT Roorkee
"""

import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
import subprocess
import threading
import os
import sys
import time
import math


def resource_path(rel):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# ═══════════════════════════════════════════════════════════════════
#  SPLASH SCREEN
# ═══════════════════════════════════════════════════════════════════
def show_splash():
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.configure(bg="#0a1628")
    splash.attributes("-topmost", True)

    W, H = 520, 620
    sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    splash.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

    # ── Canvas for animated background ──────────────────────────
    canvas = tk.Canvas(splash, width=W, height=H,
                       bg="#0a1628", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # Draw subtle grid dots
    for x in range(0, W, 32):
        for y in range(0, H, 32):
            canvas.create_oval(x-1, y-1, x+1, y+1,
                               fill="#1a2d48", outline="")

    # Draw decorative arcs behind logo area
    cx, cy = W//2, 210
    for r, alpha in [(160, "#0d2240"), (130, "#112a4a"),
                     (105, "#152f52"), (82, "#19365c")]:
        canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                           outline=alpha, width=1)

    # ── Logo ────────────────────────────────────────────────────
    logo_size = 200
    logo_label = tk.Label(canvas, bg="#0a1628", bd=0, highlightthickness=0)
    logo_label.place(x=cx, y=cy, anchor="center")

    try:
        from PIL import Image as PilImage, ImageTk, ImageEnhance
        logo_path = resource_path("logo.png")
        if os.path.isfile(logo_path):
            pil_img = PilImage.open(logo_path).convert("RGBA")
            pil_img = pil_img.resize((logo_size, logo_size), PilImage.LANCZOS)
            logo_tk = ImageTk.PhotoImage(pil_img)
            logo_label.config(image=logo_tk)
            logo_label.image = logo_tk
    except Exception:
        logo_label.config(text="MP", font=("Georgia", 52, "bold"),
                          fg="#00c9a7")

    # ── Title block ─────────────────────────────────────────────
    canvas.create_text(cx, 330, text="MODPY",
                       font=("Georgia", 38, "bold"),
                       fill="#ffffff")

    # Teal underline
    canvas.create_line(cx-80, 350, cx+80, 350,
                       fill="#00c9a7", width=2)

    canvas.create_text(cx, 372, text="Automated Modeling Tool",
                       font=("Helvetica", 12),
                       fill="#00c9a7")

    # ── Divider ─────────────────────────────────────────────────
    canvas.create_line(cx-130, 400, cx+130, 400,
                       fill="#1e3a5f", width=1)

    canvas.create_text(cx, 422,
                       text="Developed by Rik Ganguly",
                       font=("Helvetica", 10, "italic"),
                       fill="#94a3b8")

    canvas.create_text(cx, 444,
                       text="Post Doctoral Fellow  •  Hazra Group, IIT Roorkee",
                       font=("Helvetica", 9),
                       fill="#64748b")

    # ── Progress bar track ──────────────────────────────────────
    BAR_X1, BAR_Y = 80, 510
    BAR_X2        = W - 80
    BAR_H         = 5
    BAR_R         = 3      # corner radius

    # Track
    canvas.create_rectangle(BAR_X1, BAR_Y, BAR_X2, BAR_Y+BAR_H,
                             fill="#1e3a5f", outline="", width=0)

    # Filled bar (starts empty)
    bar_fill = canvas.create_rectangle(BAR_X1, BAR_Y, BAR_X1, BAR_Y+BAR_H,
                                       fill="#00c9a7", outline="")

    # Status text
    status_var = tk.StringVar(value="Initialising…")
    canvas.create_text(cx, BAR_Y+22, text="",
                       font=("Helvetica", 8), fill="#475569",
                       tags="status_text")
    canvas.itemconfig("status_text", text=status_var.get())

    # Version
    canvas.create_text(W-16, H-10, text="v1.0",
                       font=("Helvetica", 7),
                       fill="#334155", anchor="se")

    # ── Animate ─────────────────────────────────────────────────
    STEPS = [
        (0.12, "Loading libraries…"),
        (0.30, "Initialising environment…"),
        (0.52, "Checking MODELLER…"),
        (0.72, "Preparing alignment engine…"),
        (0.88, "Building interface…"),
        (1.00, "Ready!"),
    ]
    BAR_W = BAR_X2 - BAR_X1
    _step_idx = [0]

    def next_step():
        i = _step_idx[0]
        if i < len(STEPS):
            pct, msg = STEPS[i]
            x2 = BAR_X1 + int(BAR_W * pct)
            canvas.coords(bar_fill, BAR_X1, BAR_Y, x2, BAR_Y+BAR_H)
            canvas.itemconfig("status_text", text=msg)
            _step_idx[0] += 1
            delay = 380 if i < len(STEPS)-1 else 500
            splash.after(delay, next_step)
        else:
            splash.after(260, splash.destroy)

    # Fade-in logo
    def fade_in(alpha=0, step=0):
        if step < 12:
            alpha = min(1.0, step / 10)
            # Tkinter doesn't support per-widget alpha, but we can
            # pulse the canvas bg ever so slightly for effect
            splash.after(40, fade_in, alpha, step+1)

    splash.after(80, next_step)
    splash.after(60, fade_in)
    splash.mainloop()


# Show splash before any main window import
show_splash()


# ═══════════════════════════════════════════════════════════════════
#  COLOUR PALETTE
# ═══════════════════════════════════════════════════════════════════
BG       = "#0a1628"
PANEL    = "#0f1f38"
CARD     = "#132340"
ACCENT   = "#00c9a7"
ACCENT2  = "#3b82f6"
TEXT     = "#e2e8f0"
SUBTEXT  = "#94a3b8"
ENTRY_BG = "#0d1c30"
BTN_RUN  = "#059669"
BTN_HOV  = "#047857"
BORDER   = "#1e3a5f"
GOLD     = "#f59e0b"


# ═══════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════
root = tk.Tk()
root.title("ModPy — Homology Modelling Pipeline")
root.geometry("900x740")
root.configure(bg=BG)
root.resizable(True, True)

sty = ttk.Style(root)
sty.theme_use("clam")
sty.configure("TCombobox",
    fieldbackground=ENTRY_BG, background=ENTRY_BG,
    foreground=TEXT, arrowcolor=ACCENT,
    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
sty.map("TCombobox", fieldbackground=[("readonly", ENTRY_BG)])

# Load logo for header
header_logo = None
try:
    from PIL import Image as PilImage, ImageTk
    lp = resource_path("logo.png")
    if os.path.isfile(lp):
        im = PilImage.open(lp).resize((52, 52), PilImage.LANCZOS)
        header_logo = ImageTk.PhotoImage(im)
except Exception:
    pass


# ─────────────────────────────────────────────
# Pipeline execution
# ─────────────────────────────────────────────
dope_scores = {}

def run_pipeline():
    global dope_scores
    dope_scores = {}

    query      = entry_query.get().strip()
    template   = entry_template.get().strip()
    chain      = entry_chain.get().strip() or "A"
    mode       = mode_var.get()
    n_models   = entry_models.get().strip()
    n_loop     = entry_loop_models.get().strip()
    loop_start = entry_loop_start.get().strip()
    loop_end   = entry_loop_end.get().strip()
    output_dir = entry_output.get().strip() or "results"

    if not query or not template:
        messagebox.showerror("Missing Input",
            "Please select both Query FASTA and Template PDB files.")
        return
    if not os.path.isfile(query):
        messagebox.showerror("File Not Found", f"Query FASTA not found:\n{query}")
        return
    if not os.path.isfile(template):
        messagebox.showerror("File Not Found", f"Template PDB not found:\n{template}")
        return

    os.makedirs(output_dir, exist_ok=True)
    script = resource_path("homology_model.py")

    cmd = [sys.executable, script,
           "--mode", mode,
           "--query", query,
           "--template", template, chain,
           "--n-models", n_models,
           "--n-loop-models", n_loop,
           "--loop-start", loop_start,
           "--loop-end", loop_end,
           "--output-dir", output_dir,
           "--run"]

    log(f"\n▶  Running: {' '.join(cmd)}\n\n")
    btn_run.config(state="disabled", text="⏳  Running…")

    def execute():
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                root.after(0, log, line)
                # Parse DOPE scores
                if "DOPE score" in line:
                    try:
                        parts = line.strip().split()
                        dope_scores[parts[0]] = float(parts[-1])
                    except Exception:
                        pass
            proc.wait()
            root.after(0, show_dope_summary)
            root.after(0, log,
                f"\n✅  Finished! Results → {os.path.abspath(output_dir)}\n")
        except FileNotFoundError:
            root.after(0, log,
                "\n❌  homology_model.py not found — place it next to app.py\n")
        except Exception as e:
            root.after(0, log, f"\n❌  ERROR: {e}\n")
        finally:
            root.after(0, lambda: btn_run.config(
                state="normal", text="🚀  Run Pipeline"))

    threading.Thread(target=execute, daemon=True).start()


def show_dope_summary():
    if not dope_scores:
        return
    ranked = sorted(dope_scores.items(), key=lambda x: x[1])
    log("\n" + "─"*52 + "\n")
    log("📊  DOPE SCORE RANKING  (best → worst)\n")
    log("─"*52 + "\n")
    for i, (m, s) in enumerate(ranked, 1):
        prefix = "🏆 " if i == 1 else f"   {i}."
        log(f"{prefix}  {m}   →   {s:.4f}\n")
    log("─"*52 + "\n")


def log(t):
    output_box.insert(tk.END, t)
    output_box.see(tk.END)

def clear_log():
    output_box.delete("1.0", tk.END)

def browse_query():
    f = filedialog.askopenfilename(
        filetypes=[("FASTA", "*.fasta *.fa"), ("All", "*.*")])
    if f: entry_query.delete(0, tk.END); entry_query.insert(0, f)

def browse_template():
    f = filedialog.askopenfilename(
        filetypes=[("PDB", "*.pdb"), ("All", "*.*")])
    if f: entry_template.delete(0, tk.END); entry_template.insert(0, f)

def browse_output():
    d = filedialog.askdirectory()
    if d: entry_output.delete(0, tk.END); entry_output.insert(0, d)


# ═══════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════
header = tk.Frame(root, bg=PANEL, height=72)
header.pack(fill="x")
header.pack_propagate(False)

if header_logo:
    tk.Label(header, image=header_logo, bg=PANEL,
             bd=0).pack(side="left", padx=(16, 10), pady=10)

htext = tk.Frame(header, bg=PANEL)
htext.pack(side="left", pady=12)
tk.Label(htext, text="ModPy",
         font=("Georgia", 22, "bold"),
         fg=ACCENT, bg=PANEL).pack(anchor="w")
tk.Label(htext, text="Homology Modelling Pipeline",
         font=("Helvetica", 9), fg=SUBTEXT, bg=PANEL).pack(anchor="w")

tk.Label(header,
         text="Rik Ganguly  •  Post Doctoral Fellow  •  Hazra Group, IIT Roorkee",
         font=("Helvetica", 7, "italic"),
         fg=SUBTEXT, bg=PANEL).pack(side="right", padx=16)

# Accent bar
tk.Frame(root, height=2, bg=ACCENT).pack(fill="x")


# ═══════════════════════════════════════════════
#  INPUT SECTION
# ═══════════════════════════════════════════════
def _lbl(p, t, r):
    tk.Label(p, text=t, font=("Helvetica", 9, "bold"),
             fg=SUBTEXT, bg=CARD, anchor="e"
             ).grid(row=r, column=0, padx=(12, 6), pady=6, sticky="e")

def _ent(p, r, w=46, d=""):
    e = tk.Entry(p, width=w, bg=ENTRY_BG, fg=TEXT,
                 insertbackground=ACCENT, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT, font=("Consolas", 9))
    if d: e.insert(0, d)
    e.grid(row=r, column=1, padx=4, pady=6, sticky="ew")
    return e

def _brw(p, r, cmd):
    tk.Button(p, text="Browse", command=cmd,
              bg=ACCENT2, fg="white", relief="flat",
              font=("Helvetica", 8), padx=10, cursor="hand2",
              activebackground="#2563eb"
              ).grid(row=r, column=2, padx=(4, 12), pady=6)

# Card frame
inp_card = tk.Frame(root, bg=CARD, padx=0, pady=6)
inp_card.pack(fill="x", padx=14, pady=(10, 4))
inp_card.columnconfigure(1, weight=1)

_lbl(inp_card, "Query FASTA",      0); entry_query    = _ent(inp_card, 0); _brw(inp_card, 0, browse_query)
_lbl(inp_card, "Template PDB",     1); entry_template = _ent(inp_card, 1); _brw(inp_card, 1, browse_template)
_lbl(inp_card, "Output Directory", 2); entry_output   = _ent(inp_card, 2, d="results"); _brw(inp_card, 2, browse_output)


# ═══════════════════════════════════════════════
#  PARAMETERS
# ═══════════════════════════════════════════════
par_card = tk.Frame(root, bg=CARD, pady=6)
par_card.pack(fill="x", padx=14, pady=4)

def _prm(p, lbl, dv, col):
    tk.Label(p, text=lbl, font=("Helvetica", 8, "bold"),
             fg=SUBTEXT, bg=CARD).grid(row=0, column=col*2,
                                        padx=(14, 4), pady=6, sticky="e")
    e = tk.Entry(p, width=6, bg=ENTRY_BG, fg=TEXT,
                 insertbackground=ACCENT, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT, font=("Consolas", 9))
    e.insert(0, dv)
    e.grid(row=0, column=col*2+1, padx=(0, 4), pady=6, sticky="w")
    return e

tk.Label(par_card, text="Chain", font=("Helvetica", 8, "bold"),
         fg=SUBTEXT, bg=CARD).grid(row=0, column=0, padx=(14, 4), pady=6, sticky="e")
entry_chain = tk.Entry(par_card, width=4, bg=ENTRY_BG, fg=TEXT,
                       insertbackground=ACCENT, relief="flat",
                       highlightthickness=1, highlightbackground=BORDER,
                       highlightcolor=ACCENT, font=("Consolas", 9))
entry_chain.insert(0, "A")
entry_chain.grid(row=0, column=1, padx=(0, 4), pady=6, sticky="w")

tk.Label(par_card, text="Mode", font=("Helvetica", 8, "bold"),
         fg=SUBTEXT, bg=CARD).grid(row=0, column=2, padx=(14, 4), pady=6, sticky="e")
mode_var = tk.StringVar(value="full")
ttk.Combobox(par_card, textvariable=mode_var,
             values=["single", "multi", "loop", "full"],
             width=9, state="readonly"
             ).grid(row=0, column=3, padx=(0, 4), pady=6, sticky="w")

entry_models      = _prm(par_card, "N Models",    "5",  2)
entry_loop_models = _prm(par_card, "Loop Models", "4",  3)
entry_loop_start  = _prm(par_card, "Loop Start",  "1",  4)
entry_loop_end    = _prm(par_card, "Loop End",    "10", 5)


# ═══════════════════════════════════════════════
#  BUTTONS
# ═══════════════════════════════════════════════
bf = tk.Frame(root, bg=BG)
bf.pack(pady=10)

btn_run = tk.Button(bf, text="🚀  Run Pipeline", command=run_pipeline,
                    bg=BTN_RUN, fg="white",
                    font=("Helvetica", 11, "bold"),
                    relief="flat", padx=22, pady=9, cursor="hand2",
                    activebackground=BTN_HOV, activeforeground="white")
btn_run.pack(side="left", padx=8)

tk.Button(bf, text="🗑  Clear Log", command=clear_log,
          bg="#1e3a5f", fg=TEXT, font=("Helvetica", 10),
          relief="flat", padx=14, pady=9, cursor="hand2",
          activebackground="#254d7a"
          ).pack(side="left", padx=8)


# ═══════════════════════════════════════════════
#  CONSOLE
# ═══════════════════════════════════════════════
con_hdr = tk.Frame(root, bg=BG)
con_hdr.pack(fill="x", padx=14)
tk.Label(con_hdr, text="●", font=("Helvetica", 9),
         fg="#ef4444", bg=BG).pack(side="left")
tk.Label(con_hdr, text="●", font=("Helvetica", 9),
         fg=GOLD, bg=BG).pack(side="left", padx=3)
tk.Label(con_hdr, text="●", font=("Helvetica", 9),
         fg=ACCENT, bg=BG).pack(side="left")
tk.Label(con_hdr, text="  Console Output",
         font=("Helvetica", 9, "bold"),
         fg=SUBTEXT, bg=BG).pack(side="left", padx=6)

output_box = scrolledtext.ScrolledText(
    root, height=17,
    bg="#060e1a", fg="#a3e635",
    font=("Consolas", 9),
    insertbackground=ACCENT,
    relief="flat", borderwidth=0,
    highlightthickness=1,
    highlightbackground=BORDER,
    selectbackground="#1e3a5f",
    selectforeground=TEXT)
output_box.pack(fill="both", expand=True, padx=14, pady=(2, 4))

# Footer
tk.Frame(root, height=1, bg=BORDER).pack(fill="x", padx=14)
tk.Label(root,
         text="ModPy v1.0   •   Hazra Group, IIT Roorkee   •   Homology Modelling Suite",
         font=("Helvetica", 7), fg="#334155", bg=BG).pack(pady=4)

log("ModPy — Homology Modelling Pipeline ready.\n")
log("Select your input files and click  🚀  Run Pipeline  to begin.\n\n")

root.mainloop()
