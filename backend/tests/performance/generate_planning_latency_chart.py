"""
Generates the IEEE-style grayscale planning latency comparison chart (PDF & PNG).

Data sources:
- Phoenix Deterministic Planning: 14.85 ms (measured in test_performance_benchmarks.py)
- ReAct-style LLM agent: 450 ms (documented GPT-3.5 single API round-trip latency)
- AutoGen conversational agent: 800 ms (multi-agent orchestration benchmarks - aimultiple.com 2026)
- Full LLM replanning agent: 1200 ms (documented GPT-4 single reasoning turn latency)
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Set serif typography and IEEE formatting standards
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif", "Computer Modern Roman", "serif"]
plt.rcParams["font.size"] = 9
plt.rcParams["axes.labelsize"] = 9
plt.rcParams["axes.titlesize"] = 9.5
plt.rcParams["xtick.labelsize"] = 8
plt.rcParams["ytick.labelsize"] = 8

systems = [
    "Phoenix Deterministic\nPlanning",
    "ReAct-style\nLLM Agent",
    "AutoGen\nConversational Agent",
    "Full LLM\nReplanning Agent",
]

latencies = [14.85, 450.0, 800.0, 1200.0]
labels = ["14.85 ms", "450 ms", "800 ms", "1200 ms"]

# Figure size: 3.4 in x 2.8 in (IEEE single column width)
fig, ax = plt.subplots(figsize=(3.4, 2.8), dpi=300)

x = range(len(systems))
bars = []

for i in range(len(systems)):
    if i == 0:
        # Phoenix bar: solid black fill
        bar = ax.bar(x[i], latencies[i], width=0.55, color="black", edgecolor="black", linewidth=1.0)
    else:
        # Literature bars: gray fill with hatching
        bar = ax.bar(
            x[i],
            latencies[i],
            width=0.55,
            color="#888888",
            hatch="//",
            edgecolor="black",
            linewidth=1.0,
        )
    bars.append(bar)

# Log scale formatting
ax.set_yscale("log")
ax.set_ylim(5, 3500)
ax.set_ylabel("Planning Latency (ms, log scale)", fontsize=9, fontweight="bold")
ax.set_xticks(list(x))
ax.set_xticklabels(systems, fontsize=7.5)

# Annotate measured/documented values above bars
for i, (val, txt) in enumerate(zip(latencies, labels)):
    y_pos = val * 1.25 if i > 0 else val * 1.35
    ax.text(
        i,
        y_pos,
        txt,
        ha="center",
        va="bottom",
        fontsize=7.5,
        fontweight="bold" if i == 0 else "normal",
        color="black",
    )

ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.6, color="#888888")
ax.set_axisbelow(True)

plt.title("Goal Decomposition / Planning Latency Comparison", fontsize=9.5, fontweight="bold", pad=8)

# Footnote below chart
footnote_text = (
    "* Literature values are documented lower-bound estimates, not measured\n"
    "   under identical conditions. See cited sources in Section V."
)
fig.text(0.04, 0.015, footnote_text, fontsize=7, style="italic", color="#333333")

plt.subplots_adjust(left=0.18, right=0.96, top=0.90, bottom=0.25)

pdf_path = RESULTS_DIR / "planning_latency_comparison.pdf"
png_path = RESULTS_DIR / "planning_latency_comparison.png"

plt.savefig(pdf_path, format="pdf", dpi=300)
plt.savefig(png_path, format="png", dpi=300)
plt.close()

print(f"[SUCCESS] PDF generated at: {pdf_path}")
print(f"[SUCCESS] PNG generated at: {png_path}")
