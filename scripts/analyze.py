"""
Results Processor & Visualization Generator
==============================================================
Cross-Modal Prompt Injection Study | CMPT 479/982 SFU 2026
Authors: Chirajay Aggarwal, Kandisa Agarwal

This script performs analysis on the responses files and plot graphs.
"""

import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESP_DIR = os.path.join(BASE_DIR, "responses")
FIGURES  = os.path.join(BASE_DIR, "analysis", "figures")

EXPERIMENTS = ["exp1", "exp2", "exp3", "exp4"]
PLATFORMS   = ["chatgpt", "gemini"]

EXP_LABELS = {
    "exp1": "Text\n(n=80)",
    "exp2": "Visual\n(n=24)",
    "exp3": "File Upload\n(n=36)",
    "exp4": "Memory\n(n=8)",
}
EXP_SHORT = {
    "exp1": "Text",
    "exp2": "Visual",
    "exp3": "File Upload",
    "exp4": "Memory",
}

# colors
C_GPT  = "#10A37F"   # OpenAI green
C_GEM  = "#4285F4"   # Google blue
C_SUCC = "#34A853"   # success green
C_PART = "#FBBC05"   # partial yellow
C_FAIL = "#EA4335"   # blocked red
BG     = "#FAFAFA"

plt.rcParams.update({
    "font.family":        "DejaVu Sans",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.facecolor":     BG,
    "figure.facecolor":   "white",
    "axes.grid":          True,
    "grid.alpha":         0.3,
    "grid.linestyle":     "--",
})


# --- data loading & metrics ---

def load_responses() -> pd.DataFrame:
    """Load all response CSVs and return a single combined DataFrame."""
    frames = []
    for platform in PLATFORMS:
        for exp in EXPERIMENTS:
            path = os.path.join(RESP_DIR, platform, f"{exp}_responses.csv")
            if not os.path.exists(path):
                print(f"  [WARN] Missing: {path}")
                continue
            try:
                df = pd.read_csv(path, encoding="utf-8")
                if "score" not in df.columns:
                    continue
                df = df[df["score"].notna() &
                        (df["score"].astype(str).str.strip() != "")]
                if len(df) == 0:
                    continue
                df["platform"]   = platform
                df["experiment"] = exp
                df["score"]      = pd.to_numeric(df["score"], errors="coerce")
                frames.append(df)
            except Exception as e:
                print(f"  [WARN] Could not load {path}: {e}")

    if not frames:
        print("\n[!] No scored responses found. Fill in response CSVs first.")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    print(f"  Loaded {len(combined)} scored responses across "
          f"{combined['platform'].nunique()} platforms and "
          f"{combined['experiment'].nunique()} experiments.")
    return combined


def asr(df: pd.DataFrame) -> float:
    """Weighted Attack Success Rate: sum(score) / (2 * n) * 100."""
    if len(df) == 0:
        return 0.0
    return float(df["score"].sum() / (2 * len(df)) * 100)


def partial_rate(df: pd.DataFrame) -> float:
    """Proportion of test cases that scored exactly 1 (partial compliance)."""
    if len(df) == 0:
        return 0.0
    return float((df["score"] == 1).sum() / len(df) * 100)


def get_asr_matrix(df: pd.DataFrame) -> dict:
    """Return {platform: {exp: asr}} for all platform/experiment combinations."""
    result = {}
    for p in PLATFORMS:
        result[p] = {}
        for e in EXPERIMENTS:
            sub = df[(df["platform"] == p) & (df["experiment"] == e)]
            result[p][e] = round(asr(sub), 1)
    return result


def _save(fig, name: str):
    path = os.path.join(FIGURES, name)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved → analysis/figures/{name}")


# fig 01 - overall comparison bar chart

def plot_overall_comparison(df: pd.DataFrame):
    matrix = get_asr_matrix(df)
    modalities = list(EXP_SHORT.values()) + ["Overall"]

    gpt_vals = [matrix["chatgpt"].get(e, 0) for e in EXPERIMENTS]
    gem_vals = [matrix["gemini"].get(e, 0)  for e in EXPERIMENTS]

    gpt_overall = round(asr(df[df["platform"] == "chatgpt"]), 1)
    gem_overall  = round(asr(df[df["platform"] == "gemini"]),  1)
    gpt_vals.append(gpt_overall)
    gem_vals.append(gem_overall)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(modalities))
    w = 0.38

    b1 = ax.bar(x - w/2, gpt_vals, w, label="ChatGPT (GPT-4o)",
                color=C_GPT, alpha=0.9, edgecolor="white")
    b2 = ax.bar(x + w/2, gem_vals, w, label="Gemini (2.5 Flash)",
                color=C_GEM, alpha=0.9, edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels(modalities, fontsize=11)
    ax.set_ylabel("Attack Success Rate (%)", fontsize=12)
    ax.set_ylim(0, 75)
    ax.set_title("Overall Attack Success Rate Comparison - ChatGPT vs. Gemini",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=11)

    for bar in list(b1) + list(b2):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.0,
                f"{bar.get_height():.1f}%", ha="center", fontsize=10, fontweight="bold")

    for i, (g, m) in enumerate(zip(gpt_vals, gem_vals)):
        diff = m - g
        color = "#DC2626" if diff > 10 else ("#059669" if diff < -10 else "#6B7280")
        sign  = "+" if diff > 0 else ""
        ax.text(i, max(g, m) + 5, f"\u0394{sign}{diff:.1f}%",
                ha="center", fontsize=8.5, color=color, fontweight="bold")

    _save(fig, "overall_comparison.png")


# fig 02 - asr heatmap

def plot_overall_heatmap(df: pd.DataFrame):
    matrix = get_asr_matrix(df)

    gpt_row = [matrix["chatgpt"].get(e, 0) for e in EXPERIMENTS]
    gem_row = [matrix["gemini"].get(e, 0)  for e in EXPERIMENTS]
    data    = np.array([gpt_row, gem_row])

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(data, cmap="RdYlGn", vmin=0, vmax=70, aspect="auto")

    ax.set_xticks(range(4))
    ax.set_xticklabels([EXP_LABELS[e] for e in EXPERIMENTS], fontsize=11)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["ChatGPT\n(GPT-4o)", "Gemini\n(2.5 Flash)"],
                       fontsize=12, fontweight="bold")
    ax.set_title("Attack Success Rate (%) by Modality and Platform",
                 fontsize=13, fontweight="bold", pad=14)

    for i in range(2):
        for j in range(4):
            val = data[i, j]
            tc = "white" if val < 15 or val > 50 else "black"
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                    fontsize=13, fontweight="bold", color=tc)

    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label("ASR (%)", fontsize=10)
    ax.spines[:].set_visible(False)

    for j, (g, m) in enumerate(zip(gpt_row, gem_row)):
        if abs(g - m) > 30:
            ax.add_patch(plt.Rectangle((j - 0.5, -0.5), 1, 2,
                                        fill=False, edgecolor="black",
                                        lw=3, linestyle="--"))
            ax.text(j, 2.1, f"\u0394{abs(g-m):.1f}pp",
                    ha="center", fontsize=9, fontweight="bold", color="#B91C1C")

    _save(fig, "overall_heatmap.png")


# fig 03 - radar chart

def plot_radar_chart(df: pd.DataFrame):
    matrix = get_asr_matrix(df)
    labels = [
        f"Text\n({matrix['chatgpt']['exp1']:.1f} / {matrix['gemini']['exp1']:.1f})",
        f"Visual\n({matrix['chatgpt']['exp2']:.1f} / {matrix['gemini']['exp2']:.1f})",
        f"File Upload\n({matrix['chatgpt']['exp3']:.1f} / {matrix['gemini']['exp3']:.1f})",
        f"Memory\n({matrix['chatgpt']['exp4']:.1f} / {matrix['gemini']['exp4']:.1f})",
    ]
    N      = 4
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    gpt_v = [matrix["chatgpt"][e] for e in EXPERIMENTS] + [matrix["chatgpt"]["exp1"]]
    gem_v = [matrix["gemini"][e]  for e in EXPERIMENTS] + [matrix["gemini"]["exp1"]]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.set_facecolor("#F9FAFB")
    ax.fill(angles, gpt_v, alpha=0.25, color=C_GPT)
    ax.plot(angles, gpt_v, "o-", lw=2.5, color=C_GPT,
            label="ChatGPT (GPT-4o)", markersize=8)
    ax.fill(angles, gem_v, alpha=0.25, color=C_GEM)
    ax.plot(angles, gem_v, "s-", lw=2.5, color=C_GEM,
            label="Gemini (2.5 Flash)", markersize=8)

    ax.set_thetagrids(np.degrees(angles[:-1]), labels, fontsize=10)
    ax.set_ylim(0, 70)
    ax.set_yticks([10, 20, 30, 40, 50, 60, 70])
    ax.set_yticklabels([f"{v}%" for v in [10, 20, 30, 40, 50, 60, 70]],
                       fontsize=8, color="#6B7280")
    ax.set_title("Attack Success Rate Profile\nChatGPT vs. Gemini",
                 fontsize=13, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.15), fontsize=10)

    _save(fig, "radar_chart.png")


# fig 04 - exp1 category breakdown

def plot_exp1_category_breakdown(df: pd.DataFrame):
    exp1 = df[df["experiment"] == "exp1"].copy()
    if "category" not in exp1.columns or len(exp1) == 0:
        print("  [SKIP] exp1_category_breakdown: no category column in Exp 1 data.")
        return

    cats = exp1["category"].dropna().unique()
    cat_labels, gpt_vals, gem_vals = [], [], []
    for cat in cats:
        cat_labels.append(cat.replace("_", "\n"))
        gpt_vals.append(round(asr(exp1[(exp1["category"] == cat) & (exp1["platform"] == "chatgpt")]), 1))
        gem_vals.append(round(asr(exp1[(exp1["category"] == cat) & (exp1["platform"] == "gemini")]),  1))

    x = np.arange(len(cat_labels))
    w = 0.35
    fig, ax = plt.subplots(figsize=(11, 5.5))
    b1 = ax.bar(x - w/2, gpt_vals, w, label="ChatGPT (GPT-4o)",
                color=C_GPT, alpha=0.9, edgecolor="white")
    b2 = ax.bar(x + w/2, gem_vals, w, label="Gemini (2.5 Flash)",
                color=C_GEM, alpha=0.9, edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels(cat_labels, fontsize=9.5)
    ax.set_ylabel("Attack Success Rate (%)", fontsize=11)
    ax.set_title("Experiment 1: Text Injection - ASR by Payload Category",
                 fontsize=13, fontweight="bold")
    ax.set_ylim(0, 62)
    ax.legend(fontsize=10)

    for bar in list(b1) + list(b2):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                f"{bar.get_height():.0f}%", ha="center",
                fontsize=8, fontweight="bold")

    # Highlight encoding categories
    encoding_cats = [i for i, c in enumerate(cat_labels) if "encoding" in c or "base64" in c
                     or "rot13" in c or "leet" in c]
    if encoding_cats:
        lo, hi = min(encoding_cats) - 0.5, max(encoding_cats) + 0.5
        ax.axvspan(lo, hi, alpha=0.06, color="orange")
        mid = (lo + hi) / 2
        ax.text(mid, 57, "Encoding attacks\n(highest ASR)",
                ha="center", fontsize=8.5, color="#D97706", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF7ED",
                          edgecolor="#F59E0B"))

    gpt_overall = round(asr(exp1[exp1["platform"] == "chatgpt"]), 1)
    gem_overall  = round(asr(exp1[exp1["platform"] == "gemini"]),  1)
    ax.axhline(gpt_overall, color=C_GPT, lw=1.5, linestyle="--", alpha=0.7)
    ax.axhline(gem_overall,  color=C_GEM, lw=1.5, linestyle="--", alpha=0.7)
    ax.text(0.99, gpt_overall + 1.5, f"ChatGPT avg ({gpt_overall}%)",
            fontsize=7.5, color="red", ha="right",
            transform=ax.get_yaxis_transform())
    ax.text(0.99, gem_overall + 1.5, f"Gemini avg ({gem_overall}%)",
            fontsize=7.5, color="red", ha="right",
            transform=ax.get_yaxis_transform())
    _save(fig, "exp1_category_breakdown.png")


# fig 05 - exp2 technique x goal heatmap

def plot_exp2_technique_heatmap(df: pd.DataFrame):
    exp2 = df[df["experiment"] == "exp2"].copy()
    if len(exp2) == 0:
        print("  [SKIP] exp2_technique_comparison: no Exp 2 data.")
        return

    tech_col = "technique" if "technique" in exp2.columns else None
    goal_col = "attack_goal" if "attack_goal" in exp2.columns else None
    if not tech_col or not goal_col:
        print("  [SKIP] exp2_technique_comparison: missing technique or attack_goal columns.")
        return

    techniques = sorted(exp2[tech_col].dropna().unique())
    goals      = sorted(exp2[goal_col].dropna().unique())

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, platform, title, mc in zip(
        axes,
        ["chatgpt", "gemini"],
        ["ChatGPT (GPT-4o)", "Gemini (2.5 Flash)"],
        [C_GPT, C_GEM],
    ):
        matrix = np.zeros((len(techniques), len(goals)))
        for i, tech in enumerate(techniques):
            for j, goal in enumerate(goals):
                sub = exp2[(exp2["platform"] == platform) &
                           (exp2[tech_col] == tech) &
                           (exp2[goal_col] == goal)]
                matrix[i, j] = round(asr(sub), 1)

        im = ax.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(goals)))
        ax.set_xticklabels([g.replace("_", "\n") for g in goals], fontsize=8.5)
        ax.set_yticks(range(len(techniques)))
        ax.set_yticklabels([t.replace("_", " ").title() for t in techniques],
                           fontsize=10, fontweight="bold")
        ax.set_title(f"Experiment 2 (Visual) — {title}",
                     fontsize=11, fontweight="bold", color=mc)
        for i in range(len(techniques)):
            for j in range(len(goals)):
                v  = matrix[i, j]
                tc = "white" if v > 65 else "black"
                ax.text(j, i, f"{v:.0f}%", ha="center", va="center",
                        fontsize=9.5, fontweight="bold", color=tc)

    fig.colorbar(im, ax=axes.ravel().tolist(), fraction=0.015, pad=0.02,
                 label="ASR (%)")
    fig.suptitle("Experiment 2: Visual Injection -  ASR by Technique and Attack Goal",
                 fontsize=13, fontweight="bold", y=1.01)
    _save(fig, "exp2_technique_comparison.png")


# fig 06 - exp3 technique x file type

def plot_exp3_technique_filetype(df: pd.DataFrame):
    exp3 = df[df["experiment"] == "exp3"].copy()
    if len(exp3) == 0:
        print("  [SKIP] exp3_technique_comparison: no Exp 3 data.")
        return

    tech_col = "technique"  if "technique"  in exp3.columns else None
    type_col = "file_type"  if "file_type"  in exp3.columns else None
    if not tech_col or not type_col:
        print("  [SKIP] exp3_technique_comparison: missing technique or file_type columns.")
        return

    techniques = sorted(exp3[tech_col].dropna().unique())
    file_types = sorted(exp3[type_col].dropna().unique())
    x = np.arange(len(techniques))
    w = 0.35

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    for ax, platform, title, mc in zip(
        axes,
        ["chatgpt", "gemini"],
        ["ChatGPT (GPT-4o) -  Near-Total Resistance",
         "Gemini (2.5 Flash) - Significant Vulnerability"],
        [C_GPT, C_GEM],
    ):
        ft_colors = ["#34A853", "#4285F4"]  # green for docx, blue for pdf
        bars_list = []
        for k, (ft, fc) in enumerate(zip(file_types, ft_colors)):
            vals = []
            for tech in techniques:
                sub = exp3[(exp3["platform"] == platform) &
                           (exp3[tech_col] == tech) &
                           (exp3[type_col] == ft)]
                vals.append(round(asr(sub), 1))
            offset = (k - 0.5) * w
            bars = ax.bar(x + offset, vals, w, label=ft.upper(),
                          color=fc, alpha=0.85, edgecolor="white")
            bars_list.append((bars, vals))

        for bars, vals in bars_list:
            for bar, v in zip(bars, vals):
                if v > 0.5:
                    ax.text(bar.get_x() + bar.get_width()/2, v + 1.5,
                            f"{v:.1f}%", ha="center", fontsize=9, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels([t.replace("_", "\n").title() for t in techniques], fontsize=10)
        ax.set_ylim(0, 90)
        ax.set_ylabel("ASR (%)", fontsize=11)
        ax.set_title(title, fontsize=11, fontweight="bold", color=mc)
        ax.legend(fontsize=10)

        platform_overall = round(asr(exp3[exp3["platform"] == platform]), 1)
        ax.axhline(platform_overall, color=mc, lw=1.5, linestyle="--", alpha=0.7)
        ax.text(0.99, platform_overall + 1.5, f"{platform.title()} avg ({platform_overall}%)",
                fontsize=8, color=mc, ha="right", fontweight="bold",
                transform=ax.get_yaxis_transform())

    fig.suptitle("Experiment 3: File-Upload Injection - ASR by Technique and File Format",
                 fontsize=13, fontweight="bold")
    _save(fig, "exp3_technique_comparison.png")


# fig 07 - exp4 memory persistence heatmap

def plot_exp4_memory_heatmap(df: pd.DataFrame):
    exp4 = df[df["experiment"] == "exp4"].copy()
    if len(exp4) == 0:
        print("  [SKIP] exp4_memory_heatmap: no Exp 4 data.")
        return

    goal_col = "attack_goal" if "attack_goal" in exp4.columns else None
    if not goal_col:
        print("  [SKIP] exp4_memory_heatmap: missing attack_goal column.")
        return

    goals = sorted(exp4[goal_col].dropna().unique())
    platforms = ["chatgpt", "gemini"]

    fig, ax = plt.subplots(figsize=(13, 3.5))
    matrix = np.zeros((len(platforms), len(goals)))
    
    for i, platform in enumerate(platforms):
        for j, goal in enumerate(goals):
            sub = exp4[(exp4["platform"] == platform) &
                       (exp4[goal_col] == goal)]
            matrix[i, j] = round(asr(sub), 1)

    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(goals)))
    ax.set_xticklabels([g.replace("_", "\n") for g in goals], fontsize=8.5)
    ax.set_yticks(range(len(platforms)))
    ax.set_yticklabels([p.title() for p in platforms], fontsize=11, fontweight="bold")
    ax.set_title("Experiment 4: Memory Persistence - ASR by Attack Goal",
                 fontsize=13, fontweight="bold")
    
    for i in range(len(platforms)):
        for j in range(len(goals)):
            v = matrix[i, j]
            tc = "white" if v > 65 else "black"
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center",
                    fontsize=10, fontweight="bold", color=tc)

    fig.colorbar(im, ax=ax, fraction=0.015, pad=0.02, label="ASR (%)")
    fig.tight_layout()
    _save(fig, "exp4_memory_breakdown.png")


# fig 08 - score distribution

def plot_score_distribution(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)

    for ax, platform, mc in zip(axes, PLATFORMS, [C_GPT, C_GEM]):
        sub = df[df["platform"] == platform]
        exps = EXPERIMENTS
        s0, s1, s2 = [], [], []
        for e in exps:
            es = sub[sub["experiment"] == e]
            n  = max(len(es), 1)
            s0.append((es["score"] == 0).sum() / n * 100)
            s1.append((es["score"] == 1).sum() / n * 100)
            s2.append((es["score"] == 2).sum() / n * 100)

        x = np.arange(len(exps))
        w = 0.55
        ax.bar(x, s0, w, label="Blocked (0)",  color=C_FAIL, alpha=0.85)
        ax.bar(x, s1, w, label="Partial (1)",  color=C_PART, alpha=0.85, bottom=s0)
        im = ax.bar(x, s2, w, label="Success (2)", color=C_SUCC, alpha=0.85,
                    bottom=[a + b for a, b in zip(s0, s1)])

        ax.set_xticks(x)
        ax.set_xticklabels([EXP_LABELS[e] for e in exps], fontsize=10)
        ax.set_ylim(0, 115)
        ax.set_ylabel("Proportion of Test Cases (%)", fontsize=11)
        ax.set_title(platform.upper().replace("CHATGPT", "ChatGPT (GPT-4o)")
                                     .replace("GEMINI", "Gemini (2.5 Flash)"),
                     fontsize=12, fontweight="bold", color=mc)
        ax.legend(fontsize=9, loc="upper right")

        for i, (v0, v1, v2) in enumerate(zip(s0, s1, s2)):
            if v0 > 5:
                ax.text(i, v0/2,        f"{v0:.0f}%", ha="center", va="center",
                        fontsize=8.5, fontweight="bold", color="white")
            if v1 > 5:
                ax.text(i, v0 + v1/2,   f"{v1:.0f}%", ha="center", va="center",
                        fontsize=8.5, fontweight="bold", color="black")
            if v2 > 5:
                ax.text(i, v0+v1+v2/2,  f"{v2:.0f}%", ha="center", va="center",
                        fontsize=8.5, fontweight="bold", color="white")

    fig.suptitle("Score Distribution (Blocked / Partial / Success) by Experiment and Platform",
                 fontsize=13, fontweight="bold")
    _save(fig, "score_distribution.png")


# fig 09 - defense leakage

def plot_defense_leakage(df: pd.DataFrame):
    exps  = EXPERIMENTS
    x = np.arange(len(exps))
    w = 0.38

    gpt_leak = [partial_rate(df[(df["platform"] == "chatgpt") & (df["experiment"] == e)])
                for e in exps]
    gem_leak = [partial_rate(df[(df["platform"] == "gemini")  & (df["experiment"] == e)])
                for e in exps]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    b1 = ax.bar(x - w/2, gpt_leak, w, label="ChatGPT (GPT-4o)",
                color=C_GPT, alpha=0.7, edgecolor=C_GPT, linewidth=1.5, hatch="//")
    b2 = ax.bar(x + w/2, gem_leak, w, label="Gemini (2.5 Flash)",
                color=C_GEM, alpha=0.7, edgecolor=C_GEM, linewidth=1.5, hatch="\\\\")

    ax.set_xticks(x)
    ax.set_xticklabels([EXP_SHORT[e] for e in exps], fontsize=11)
    ax.set_ylabel("Partial-Compliance Rate (% of test cases, score=1)", fontsize=11)
    ax.set_ylim(0, 40)
    ax.set_title("Defense Leakage Analysis - Rate of Partial Model Compliance\n"
                 "(Higher = More Susceptible Even When Not Fully Overridden)",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=10)

    for bar in list(b1) + list(b2):
        if bar.get_height() > 0.5:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f"{bar.get_height():.1f}%", ha="center",
                    fontsize=9.5, fontweight="bold")

    _save(fig, "defense_leakage.png")


# fig 10 - attack goal transferability

def plot_attack_goal_analysis(df: pd.DataFrame):
    goal_col = "attack_goal" if "attack_goal" in df.columns else None
    if goal_col is None:
        print("  [SKIP] attack_goal_analysis: no attack_goal column.")
        return

    # only include goals with enough test cases to be meaningful
    all_goals = sorted(df[goal_col].dropna().unique())
    goals_filtered = []
    for goal in all_goals:
        total_count = len(df[df[goal_col] == goal])
        if total_count >= 8:  # Only include goals with sufficient test cases
            goals_filtered.append(goal)
    
    if not goals_filtered:
        print("  [SKIP] attack_goal_analysis: no goals with sufficient data.")
        return
    
    goals = goals_filtered
    gpt_vals, gem_vals = [], []
    for goal in goals:
        sub_g = df[(df[goal_col] == goal) & (df["platform"] == "chatgpt")]
        sub_m = df[(df[goal_col] == goal) & (df["platform"] == "gemini")]
        gpt_vals.append(round(asr(sub_g), 1))
        gem_vals.append(round(asr(sub_m), 1))

    x = np.arange(len(goals))
    w = 0.35
    fig, ax = plt.subplots(figsize=(14, 6.5))
    b1 = ax.bar(x - w/2, gpt_vals, w, label="ChatGPT (GPT-4o)",
                color=C_GPT, alpha=0.9, edgecolor="white", linewidth=1)
    b2 = ax.bar(x + w/2, gem_vals, w, label="Gemini (2.5 Flash)",
                color=C_GEM, alpha=0.9, edgecolor="white", linewidth=1)

    ax.set_xticks(x)
    ax.set_xticklabels([g.replace("_", " ").title() for g in goals], 
                        fontsize=11, rotation=45, ha="right")
    ax.set_ylabel("Mean ASR across Applicable Modalities (%)", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 100)
    ax.set_title("Attack Goal Transferability - ASR by Objective (Cross-Modal Average)",
                 fontsize=13, fontweight="bold", pad=20)
    ax.legend(fontsize=11, loc="upper left")
    ax.grid(axis="y", alpha=0.3, linestyle="--")

    for bar in list(b1) + list(b2):
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2, height + 1.5,
                    f"{height:.1f}%", ha="center", va="bottom",
                    fontsize=9, fontweight="bold")

    ax.axhspan(60, 100, alpha=0.04, color="red", zorder=0)
    ax.axhspan(0, 25, alpha=0.04, color="green", zorder=0)
    ax.text(7.5, 75, "High Vulnerability", fontsize=10, color="#991B1B",
            fontweight="bold", alpha=0.6, transform=ax.transData, ha="left")
    ax.text(7.5, 20, "Well Defended", fontsize=10, color="#166534",
            fontweight="bold", alpha=0.6, transform=ax.transData, ha="left")

    plt.tight_layout()
    _save(fig, "attack_goal_analysis.png")

# --- summary table ---

def print_summary(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    rows = []
    for exp in EXPERIMENTS:
        for platform in PLATFORMS:
            sub = df[(df["experiment"] == exp) & (df["platform"] == platform)]
            if len(sub) == 0:
                continue
            rows.append({
                "Experiment": exp.upper(),
                "Platform":   platform.upper(),
                "N":          len(sub),
                "Blocked(0)": int((sub["score"] == 0).sum()),
                "Partial(1)": int((sub["score"] == 1).sum()),
                "Success(2)": int((sub["score"] == 2).sum()),
                "ASR (%)":    f"{asr(sub):.1f}",
            })
    if rows:
        print(pd.DataFrame(rows).to_string(index=False))
    print("\n" + "-" * 70)
    print("OVERALL")
    print("-" * 70)
    for platform in PLATFORMS:
        sub = df[df["platform"] == platform]
        if len(sub) == 0:
            continue
        print(f"  {platform.upper():<10} | N={len(sub):4d} | ASR={asr(sub):.1f}%")
    print("=" * 70)



def main():
    print("=" * 60)
    print("Cross-Modal Prompt Injection | Figure Generator")
    print("SFU CMPT 479/982 — Aggarwal & Agarwal 2026")
    print("=" * 60)

    os.makedirs(FIGURES, exist_ok=True)

    print("\nLoading response CSVs...")
    df = load_responses()

    if df.empty:
        print("\nNo scored responses found.")
        print("Fill in the response CSVs under responses/ and re-run.")
        return

    print_summary(df)

    print("\nGenerating figures from data...")
    plot_overall_comparison(df)       # Fig 01
    plot_overall_heatmap(df)          # Fig 02
    plot_radar_chart(df)              # Fig 03
    plot_exp1_category_breakdown(df)  # Fig 04
    plot_exp2_technique_heatmap(df)   # Fig 05
    plot_exp3_technique_filetype(df)  # Fig 06
    plot_exp4_memory_heatmap(df)      # Fig 07
    plot_score_distribution(df)       # Fig 08
    plot_defense_leakage(df)          # Fig 09
    plot_attack_goal_analysis(df)     # Fig 10

    print(f"\nAll 10 figures saved to analysis/figures/")


if __name__ == "__main__":
    main()