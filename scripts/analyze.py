"""
Results Processor & Visualization Generator
==============================================================
Cross-Modal Prompt Injection Study | CMPT 479/982 SFU 2026
Authors: Chirajay Aggarwal, Kandisa Agarwal

What this script does:
    1. Loads all response CSVs from responses/chatgpt/ and responses/gemini/
    2. Computes attack success rates (ASR) per experiment, per category,
       per platform, and per technique
    3. Generates publication-ready figures:
       - Overall platform comparison bar chart
       - Per-experiment ASR heatmap (platform × experiment)
       - Per-category breakdown bar chart
       - Per-technique comparison (Exp 2 and Exp 3)
       - Score distribution chart
    4. Saves all figures to analysis/figures/
    5. Prints a full summary stats table

Usage:
    python scripts/analyze_results.py

    Or run interactively in analysis/analysis.ipynb
"""

import os
import warnings
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

warnings.filterwarnings("ignore")
matplotlib.rcParams["font.family"] = "DejaVu Sans"

# PATHS
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESP_DIR   = os.path.join(BASE_DIR, "responses")
FIGURES    = os.path.join(BASE_DIR, "analysis", "figures")

EXPERIMENTS = ["exp1", "exp2", "exp3", "exp4"]
PLATFORMS   = ["chatgpt", "gemini"]

# Colors
COLOR_CHATGPT = "#10a37f"   # OpenAI green
COLOR_GEMINI  = "#4285F4"   # Google blue
COLOR_SUCCESS = "#e53935"   # red  (attack succeeded)
COLOR_PARTIAL = "#fb8c00"   # orange
COLOR_BLOCKED = "#43a047"   # green (model defended)


# LOAD ALL RESPONSES
def load_responses() -> pd.DataFrame:
    """
    Load all response CSVs and combine into one dataframe.
    Adds 'platform' and 'experiment' columns.
    Only includes rows that have been scored (score != '').
    """
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
                # Keep only scored rows
                df = df[df["score"].notna() & (df["score"].astype(str).str.strip() != "")]
                if len(df) == 0:
                    continue
                df["platform"]   = platform
                df["experiment"] = exp
                df["score"]      = pd.to_numeric(df["score"], errors="coerce")
                frames.append(df)
            except Exception as e:
                print(f"  [WARN] Could not load {path}: {e}")

    if not frames:
        print("\n[!] No scored responses found yet.")
        print("    Complete the manual testing and fill in the response CSVs first.")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    print(f"  Loaded {len(combined)} scored responses "
          f"from {combined['platform'].nunique()} platforms, "
          f"{combined['experiment'].nunique()} experiments.")
    return combined


# COMPUTE ATTACK SUCCESS RATE
def attack_success_rate(df: pd.DataFrame, score_col: str = "score") -> float:
    """
    ASR = % of payloads where score >= 1 (partial or full success).
    Full success (score=2) counts as 1.0, partial (score=1) as 0.5.
    Weighted ASR = sum(score) / (2 * n_payloads) * 100
    """
    if len(df) == 0:
        return 0.0
    return (df[score_col].sum() / (2 * len(df))) * 100


def full_success_rate(df: pd.DataFrame, score_col: str = "score") -> float:
    """Full success only (score == 2)."""
    if len(df) == 0:
        return 0.0
    return (df[score_col] == 2).sum() / len(df) * 100


# FIGURE 1 — Overall Platform Comparison
def plot_overall_comparison(df: pd.DataFrame, out_dir: str):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Overall Prompt Injection Attack Success Rate\nChatGPT vs Gemini",
                 fontsize=14, fontweight="bold", y=1.02)

    # Weighted ASR
    asr_data = []
    for platform in PLATFORMS:
        sub = df[df["platform"] == platform]
        asr_data.append({
            "platform": platform.upper(),
            "ASR (weighted)": round(attack_success_rate(sub), 1),
            "Full success":   round(full_success_rate(sub), 1),
        })
    asr_df = pd.DataFrame(asr_data)

    colors_bar = [COLOR_CHATGPT, COLOR_GEMINI]

    # Left: Weighted ASR
    ax1 = axes[0]
    bars = ax1.bar(asr_df["platform"], asr_df["ASR (weighted)"],
                   color=colors_bar, edgecolor="white", linewidth=1.5,
                   width=0.5)
    for bar, val in zip(bars, asr_df["ASR (weighted)"]):
        ax1.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 1, f"{val}%",
                 ha="center", va="bottom", fontsize=12, fontweight="bold")
    ax1.set_title("Weighted Attack Success Rate", fontsize=12)
    ax1.set_ylabel("ASR (%)")
    ax1.set_ylim(0, 100)
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.axhline(50, color="gray", linestyle="--", alpha=0.4, linewidth=1)
    ax1.text(1.5, 51, "50%", color="gray", fontsize=9)

    # Right: Full success only
    ax2 = axes[1]
    bars2 = ax2.bar(asr_df["platform"], asr_df["Full success"],
                    color=colors_bar, edgecolor="white", linewidth=1.5,
                    width=0.5)
    for bar, val in zip(bars2, asr_df["Full success"]):
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 1, f"{val}%",
                 ha="center", va="bottom", fontsize=12, fontweight="bold")
    ax2.set_title("Full Attack Success Rate (Score = 2 only)", fontsize=12)
    ax2.set_ylabel("Full Success Rate (%)")
    ax2.set_ylim(0, 100)
    ax2.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "overall_comparison.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Figure saved → {os.path.relpath(out_path, BASE_DIR)}")


# FIGURE 2 — Per-Experiment Heatmap
def plot_experiment_heatmap(df: pd.DataFrame, out_dir: str):
    exp_labels = {
        "exp1": "Exp 1\nText Injection",
        "exp2": "Exp 2\nVisual Injection",
        "exp3": "Exp 3\nFile Upload",
        "exp4": "Exp 4\nMemory Persistence",
    }
    matrix = {}
    for platform in PLATFORMS:
        matrix[platform.upper()] = {}
        for exp in EXPERIMENTS:
            sub = df[(df["platform"] == platform) & (df["experiment"] == exp)]
            matrix[platform.upper()][exp_labels.get(exp, exp)] = round(
                attack_success_rate(sub), 1
            )

    heat_df = pd.DataFrame(matrix).T

    fig, ax = plt.subplots(figsize=(9, 3.5))
    sns.heatmap(heat_df, annot=True, fmt=".1f", cmap="RdYlGn_r",
                vmin=0, vmax=100, linewidths=0.5, linecolor="white",
                annot_kws={"size": 13, "weight": "bold"},
                cbar_kws={"label": "ASR (%)", "shrink": 0.8},
                ax=ax)
    ax.set_title("Attack Success Rate (%) by Platform and Experiment",
                 fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("")
    ax.set_ylabel("Platform")
    ax.tick_params(axis="x", labelsize=10)
    ax.tick_params(axis="y", labelsize=11)
    plt.tight_layout()
    out_path = os.path.join(out_dir, "experiment_heatmap.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Figure saved → {os.path.relpath(out_path, BASE_DIR)}")


# FIGURE 3 — Score Distribution (stacked bar)
def plot_score_distribution(df: pd.DataFrame, out_dir: str):
    exp_labels = {
        "exp1": "Exp 1\nText", "exp2": "Exp 2\nVisual",
        "exp3": "Exp 3\nFile", "exp4": "Exp 4\nMemory"
    }

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)
    fig.suptitle("Score Distribution per Experiment",
                 fontsize=13, fontweight="bold")

    for ax, platform in zip(axes, PLATFORMS):
        sub = df[df["platform"] == platform]
        counts = {"Blocked (0)": [], "Partial (1)": [], "Success (2)": []}
        labels = []
        for exp in EXPERIMENTS:
            e_sub = sub[sub["experiment"] == exp]
            total = max(len(e_sub), 1)
            counts["Blocked (0)"].append((e_sub["score"] == 0).sum() / total * 100)
            counts["Partial (1)"].append((e_sub["score"] == 1).sum() / total * 100)
            counts["Success (2)"].append((e_sub["score"] == 2).sum() / total * 100)
            labels.append(exp_labels.get(exp, exp))

        x = np.arange(len(labels))
        w = 0.5
        p1 = ax.bar(x, counts["Blocked (0)"],  w, label="Blocked (0)",  color=COLOR_BLOCKED)
        p2 = ax.bar(x, counts["Partial (1)"],  w, label="Partial (1)",  color=COLOR_PARTIAL,
                    bottom=counts["Blocked (0)"])
        p3 = ax.bar(x, counts["Success (2)"],  w, label="Success (2)",  color=COLOR_SUCCESS,
                    bottom=[a + b for a, b in zip(counts["Blocked (0)"], counts["Partial (1)"])])

        ax.set_title(platform.upper(), fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_ylabel("% of payloads")
        ax.set_ylim(0, 105)
        ax.spines[["top", "right"]].set_visible(False)
        if ax == axes[0]:
            ax.legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "score_distribution.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Figure saved → {os.path.relpath(out_path, BASE_DIR)}")


# FIGURE 4 — Category Breakdown (Exp 1)
def plot_category_breakdown(df: pd.DataFrame, out_dir: str):
    exp1 = df[df["experiment"] == "exp1"].copy()
    if "category" not in exp1.columns or len(exp1) == 0:
        print("  [SKIP] No Exp 1 category data available yet.")
        return

    categories = exp1["category"].dropna().unique()
    data = []
    for cat in categories:
        for platform in PLATFORMS:
            sub = exp1[(exp1["category"] == cat) & (exp1["platform"] == platform)]
            data.append({
                "category": cat.replace("_", "\n"),
                "platform": platform.upper(),
                "ASR": round(attack_success_rate(sub), 1),
            })

    if not data:
        return

    plot_df = pd.DataFrame(data)
    pivot   = plot_df.pivot(index="category", columns="platform", values="ASR")

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(pivot.index))
    w = 0.35

    b1 = ax.bar(x - w/2, pivot.get("CHATGPT", [0]*len(x)), w,
                label="ChatGPT", color=COLOR_CHATGPT, alpha=0.9)
    b2 = ax.bar(x + w/2, pivot.get("GEMINI",  [0]*len(x)), w,
                label="Gemini",  color=COLOR_GEMINI,  alpha=0.9)

    ax.set_title("Exp 1 — Text Injection ASR by Category",
                 fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, fontsize=9)
    ax.set_ylabel("ASR (%)")
    ax.set_ylim(0, 105)
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    out_path = os.path.join(out_dir, "exp1_category_breakdown.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Figure saved → {os.path.relpath(out_path, BASE_DIR)}")


# FIGURE 5 — Technique Comparison (Exp 2 & 3)
def plot_technique_comparison(df: pd.DataFrame, out_dir: str):
    for exp, exp_name in [("exp2", "Visual Injection"), ("exp3", "File Upload Injection")]:
        sub_exp = df[df["experiment"] == exp]
        if "technique" not in sub_exp.columns or len(sub_exp) == 0:
            print(f"  [SKIP] No technique data for {exp} yet.")
            continue

        techniques = sub_exp["technique"].dropna().unique()
        data = []
        for tech in techniques:
            for platform in PLATFORMS:
                sub = sub_exp[(sub_exp["technique"] == tech) &
                               (sub_exp["platform"] == platform)]
                data.append({
                    "technique": tech.replace("_", "\n"),
                    "platform":  platform.upper(),
                    "ASR":       round(attack_success_rate(sub), 1),
                })

        if not data:
            continue

        plot_df = pd.DataFrame(data)
        pivot   = plot_df.pivot(index="technique", columns="platform", values="ASR")

        fig, ax = plt.subplots(figsize=(9, 4))
        x = np.arange(len(pivot.index))
        w = 0.35
        ax.bar(x - w/2, pivot.get("CHATGPT", [0]*len(x)), w,
               label="ChatGPT", color=COLOR_CHATGPT, alpha=0.9)
        ax.bar(x + w/2, pivot.get("GEMINI",  [0]*len(x)), w,
               label="Gemini",  color=COLOR_GEMINI,  alpha=0.9)
        ax.set_title(f"{exp.upper()} — {exp_name} ASR by Technique",
                     fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(pivot.index, fontsize=10)
        ax.set_ylabel("ASR (%)")
        ax.set_ylim(0, 105)
        ax.legend()
        ax.spines[["top", "right"]].set_visible(False)
        plt.tight_layout()
        out_path = os.path.join(out_dir, f"{exp}_technique_comparison.png")
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  Figure saved → {os.path.relpath(out_path, BASE_DIR)}")


# SUMMARY STATS TABLE
def print_summary(df: pd.DataFrame):
    print("\n" + "=" * 65)
    print("SUMMARY STATISTICS")
    print("=" * 65)

    rows = []
    for exp in EXPERIMENTS:
        for platform in PLATFORMS:
            sub = df[(df["experiment"] == exp) & (df["platform"] == platform)]
            if len(sub) == 0:
                continue
            rows.append({
                "Experiment": exp.upper(),
                "Platform":   platform.upper(),
                "N payloads": len(sub),
                "Blocked (0)": (sub["score"] == 0).sum(),
                "Partial (1)": (sub["score"] == 1).sum(),
                "Success (2)": (sub["score"] == 2).sum(),
                "Weighted ASR (%)": f"{attack_success_rate(sub):.1f}",
                "Full ASR (%)":     f"{full_success_rate(sub):.1f}",
            })

    if rows:
        summary_df = pd.DataFrame(rows)
        print(summary_df.to_string(index=False))

    print("\n" + "-" * 65)
    print("OVERALL (all experiments combined)")
    print("-" * 65)
    for platform in PLATFORMS:
        sub = df[df["platform"] == platform]
        if len(sub) == 0:
            continue
        print(f"  {platform.upper():10s} | "
              f"N={len(sub):4d} | "
              f"Weighted ASR={attack_success_rate(sub):.1f}% | "
              f"Full ASR={full_success_rate(sub):.1f}%")
    print("=" * 65)


# MAIN
def main():
    print("=" * 60)
    print("ANALYSIS — Results Processor & Visualization Generator")
    print("Cross-Modal Prompt Injection Study | SFU CMPT 479/982")
    print("=" * 60)

    os.makedirs(FIGURES, exist_ok=True)

    print("\nLoading response data...")
    df = load_responses()

    if df.empty:
        print("\nNo data to analyse yet. Run experiments first!")
        print("Once you have filled in response CSVs, re-run this script.")
        return

    print_summary(df)

    print("\nGenerating figures...")
    plot_overall_comparison(df, FIGURES)
    plot_experiment_heatmap(df, FIGURES)
    plot_score_distribution(df, FIGURES)
    plot_category_breakdown(df, FIGURES)
    plot_technique_comparison(df, FIGURES)

    print(f"\n All figures saved to analysis/figures/")
    print("Open analysis/analysis.ipynb for interactive exploration.")


if __name__ == "__main__":
    main()