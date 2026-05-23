"""Generate chatbot architecture diagram as PNG."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

fig, ax = plt.subplots(figsize=(14, 18))
ax.set_xlim(0, 14)
ax.set_ylim(0, 18)
ax.axis("off")
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#0d1117")

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "user":    "#1f6feb",
    "api":     "#388bfd",
    "cache":   "#3fb950",
    "embed":   "#a371f7",
    "pinecone":"#58a6ff",
    "grade":   "#f0883e",
    "gen":     "#56d364",
    "route":   "#e3b341",
    "box_bg":  "#161b22",
    "border":  "#30363d",
    "text":    "#e6edf3",
    "subtext": "#8b949e",
    "arrow":   "#484f58",
    "graph_bg":"#0d1117",
    "graph_border": "#21262d",
}

def box(ax, x, y, w, h, label, sublabel="", color="#388bfd", alpha=0.9):
    rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                          boxstyle="round,pad=0.08",
                          facecolor=C["box_bg"], edgecolor=color,
                          linewidth=2, zorder=3)
    ax.add_patch(rect)
    # coloured top bar
    bar = FancyBboxPatch((x - w/2, y + h/2 - 0.22), w, 0.22,
                         boxstyle="round,pad=0.0",
                         facecolor=color, edgecolor=color,
                         linewidth=0, zorder=4, alpha=0.85,
                         clip_on=True)
    ax.add_patch(bar)
    ax.text(x, y + 0.12 if sublabel else y, label,
            ha="center", va="center", fontsize=10, fontweight="bold",
            color=C["text"], zorder=5)
    if sublabel:
        ax.text(x, y - 0.22, sublabel,
                ha="center", va="center", fontsize=7.5,
                color=C["subtext"], zorder=5)

def diamond(ax, x, y, w, h, label, color="#e3b341"):
    pts = [(x, y+h/2), (x+w/2, y), (x, y-h/2), (x-w/2, y)]
    poly = plt.Polygon(pts, closed=True,
                       facecolor=C["box_bg"], edgecolor=color, linewidth=2, zorder=3)
    ax.add_patch(poly)
    ax.text(x, y, label, ha="center", va="center",
            fontsize=8.5, fontweight="bold", color=C["text"], zorder=5)

def arrow(ax, x1, y1, x2, y2, label="", color=None):
    c = color or C["arrow"]
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=c, lw=1.5),
                zorder=2)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx + 0.12, my, label, fontsize=7.5, color=C["subtext"],
                ha="left", va="center", zorder=5)

def section_bg(ax, x, y, w, h, title):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0.1",
                          facecolor="#161b22", edgecolor=C["graph_border"],
                          linewidth=1.5, linestyle="--", zorder=1)
    ax.add_patch(rect)
    ax.text(x + 0.25, y + h - 0.25, title,
            fontsize=8, color=C["subtext"], va="top", zorder=2,
            fontstyle="italic")

# ── Title ─────────────────────────────────────────────────────────────────────
ax.text(7, 17.5, "TFT Set 17 FAQ Chatbot — Architecture",
        ha="center", va="center", fontsize=15, fontweight="bold",
        color=C["text"])

# ── Layer 1: User ─────────────────────────────────────────────────────────────
box(ax, 7, 16.6, 3.0, 0.7, "User", color=C["user"])

# ── Layer 2: FastAPI ──────────────────────────────────────────────────────────
box(ax, 7, 15.3, 3.2, 0.7, "FastAPI  /ask",
    "REST endpoint · input validation", color=C["api"])
arrow(ax, 7, 16.25, 7, 15.65, "question")

# ── Layer 3: LRU Cache ────────────────────────────────────────────────────────
section_bg(ax, 3.8, 13.6, 6.4, 1.35, "LRU Response Cache  (500 slots)")
diamond(ax, 7, 14.3, 2.8, 0.85, "Cache hit?", color=C["cache"])
arrow(ax, 7, 14.95, 7, 14.73)
# HIT path — arrow back up to user (left side)
ax.annotate("", xy=(5.5, 15.3), xytext=(5.6, 14.3),
            arrowprops=dict(arrowstyle="-|>", color=C["cache"], lw=1.5), zorder=2)
ax.text(4.85, 14.82, "HIT  →  return", fontsize=7.5, color=C["cache"], ha="left")

# ── CRAG section background ───────────────────────────────────────────────────
section_bg(ax, 1.0, 2.2, 12.0, 11.1, "CRAG Pipeline  (LangGraph)")

# ── Layer 4: Embed ────────────────────────────────────────────────────────────
box(ax, 7, 12.9, 3.8, 0.72,
    "Embed Query",
    "fastembed · all-MiniLM-L6-v2 · 384-dim", color=C["embed"])
arrow(ax, 7, 13.87, 7, 13.26, "MISS")

# ── Layer 5: Pinecone ─────────────────────────────────────────────────────────
box(ax, 7, 11.65, 3.6, 0.72,
    "Pinecone Vector DB",
    "~500 TFT Set 17 chunks · top-k = 3 · cosine sim", color=C["pinecone"])
arrow(ax, 7, 12.54, 7, 12.01, "vector query")

# ── Layer 6: Grade Documents ──────────────────────────────────────────────────
box(ax, 7, 10.4, 3.8, 0.72,
    "Grade Documents",
    "llama-3.1-8b-instant · relevant / not relevant per chunk", color=C["grade"])
arrow(ax, 7, 11.29, 7, 10.76, "top-3 chunks")

# ── Layer 7: Relevant? diamond ────────────────────────────────────────────────
diamond(ax, 7, 9.3, 3.0, 0.9, "Relevant\ndocs found?", color=C["route"])
arrow(ax, 7, 10.04, 7, 9.75)

# YES path → Generate (right side)
box(ax, 10.8, 8.0, 3.4, 0.72,
    "Generate Answer",
    "llama-3.3-70b-versatile · strict system prompt", color=C["gen"])
ax.annotate("", xy=(10.8, 8.36), xytext=(8.5, 9.3),
            arrowprops=dict(arrowstyle="-|>", color=C["gen"], lw=1.5), zorder=2)
ax.text(9.4, 9.0, "YES", fontsize=7.5, color=C["gen"], ha="center")

# NO path → Rewrite (left side)
box(ax, 3.2, 9.3, 3.0, 0.72,
    "Rewrite Query",
    "llama-3.1-8b-instant · more specific", color=C["grade"])
ax.annotate("", xy=(3.2, 9.66), xytext=(5.5, 9.3),
            arrowprops=dict(arrowstyle="-|>", color=C["grade"], lw=1.5), zorder=2)
ax.text(4.0, 9.55, "NO + retries left", fontsize=7.5, color=C["grade"], ha="center")

# Rewrite → Embed (loop back up)
ax.annotate("", xy=(3.2, 12.9), xytext=(3.2, 9.66),
            arrowprops=dict(arrowstyle="-|>", color=C["grade"], lw=1.5,
                            connectionstyle="arc3,rad=0.0"), zorder=2)
ax.annotate("", xy=(5.1, 12.9), xytext=(3.2, 12.9),
            arrowprops=dict(arrowstyle="-|>", color=C["grade"], lw=1.5), zorder=2)
ax.text(2.3, 11.4, "rewritten\nquery", fontsize=7.5, color=C["grade"], ha="center")

# Max retries → no-context fallback
box(ax, 3.2, 7.4, 3.0, 0.72,
    "No-context Fallback",
    '"I don\'t have Set 17 data…"', color=C["api"])
ax.annotate("", xy=(3.2, 7.76), xytext=(5.5, 8.85),
            arrowprops=dict(arrowstyle="-|>", color=C["api"], lw=1.5), zorder=2)
ax.text(3.8, 8.5, "NO + max retries", fontsize=7.5, color=C["api"], ha="center")

# ── Layer 8: Grade Answer ─────────────────────────────────────────────────────
box(ax, 10.8, 6.6, 3.4, 0.72,
    "Grade Answer",
    "llama-3.1-8b-instant · grounded / hallucinating", color=C["grade"])
arrow(ax, 10.8, 7.64, 10.8, 6.96)

# ── Layer 9: Hallucinating? diamond ──────────────────────────────────────────
diamond(ax, 10.8, 5.5, 3.2, 0.9, "Hallucinating?", color=C["route"])
arrow(ax, 10.8, 6.24, 10.8, 5.95)

# NO → answer out
box(ax, 10.8, 4.2, 3.0, 0.72, "Answer", color=C["gen"])
arrow(ax, 10.8, 5.05, 10.8, 4.56, "NO → grounded")

# YES → rewrite (loop)
ax.annotate("", xy=(3.2, 9.66), xytext=(9.2, 5.5),
            arrowprops=dict(arrowstyle="-|>", color=C["grade"], lw=1.5,
                            connectionstyle="arc3,rad=-0.15"), zorder=2)
ax.text(6.0, 7.0, "YES + retries left", fontsize=7.5, color=C["grade"], ha="center")

# Fallback → answer
ax.annotate("", xy=(9.3, 4.2), xytext=(4.7, 4.2),
            arrowprops=dict(arrowstyle="-|>", color=C["api"], lw=1.5), zorder=2)
ax.text(7.0, 3.95, "fallback answer", fontsize=7.5, color=C["subtext"], ha="center")
# connect fallback box down to 4.2 level
ax.annotate("", xy=(3.2, 4.56), xytext=(3.2, 7.04),
            arrowprops=dict(arrowstyle="-|>", color=C["api"], lw=1.5), zorder=2)
ax.annotate("", xy=(4.7, 4.2), xytext=(3.2, 4.2),
            arrowprops=dict(arrowstyle="-|>", color=C["api"], lw=1.5), zorder=2)

# ── Layer 10: Cache store + return ────────────────────────────────────────────
box(ax, 7, 2.9, 3.2, 0.72,
    "Store in LRU Cache  →  Return",
    "FastAPI responds  ·  X-Cache: MISS", color=C["cache"])
ax.annotate("", xy=(9.3, 2.9), xytext=(10.8, 3.84),
            arrowprops=dict(arrowstyle="-|>", color=C["cache"], lw=1.5), zorder=2)

# ── Footer ────────────────────────────────────────────────────────────────────
ax.text(7, 2.35, "Ingestion (offline): Scrapy scraper  →  fastembed  →  Pinecone upsert",
        ha="center", fontsize=8, color=C["subtext"])

plt.tight_layout(pad=0.5)
plt.savefig("architecture.png", dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print("Saved architecture.png")
