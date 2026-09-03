"""
ui/plot_utils.py
Shared matplotlib styling helpers used by every chart tab, so all charts
in the app look and behave consistently:
  - apply_graph_paper_grid(ax): fine major+minor gridlines ("graph paper")
    so the user can read exact values off the curve, per explicit request.
  - fix_layout(fig, ...): reserves enough margin so axis labels/ticks are
    never clipped at the edge of the canvas (fixes the "x-axis cut off"
    issue seen in the DVH plots screenshot).
"""
from __future__ import annotations


def apply_graph_paper_grid(ax):
    ax.minorticks_on()
    ax.grid(True, which="major", linestyle="-", linewidth=0.6, alpha=0.55)
    ax.grid(True, which="minor", linestyle=":", linewidth=0.4, alpha=0.35)


def fix_layout(fig, bottom=0.16, top=0.90, left=0.11, right=0.97):
    fig.subplots_adjust(bottom=bottom, top=top, left=left, right=right)
