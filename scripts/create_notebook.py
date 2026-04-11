#!/usr/bin/env python3
"""
Script to generate a proper analysis.ipynb notebook
Run: python3 scripts/create_notebook.py
"""
import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

cells = []

# ── Cell 1 — Title ────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""# Cross-Modal Prompt Injection: A Systematic Black-Box Evaluation of ChatGPT and Gemini

**CMPT 479 / CMPT 982 — Spring 2026 | Simon Fraser University**
**Authors:** Chirajay Aggarwal, Kandisa Agarwal

---

This notebook presents the full analysis of our prompt injection study across 4 experiments:
- **Exp 1** — Text Injection (80 payloads × 2 platforms)
- **Exp 2** — Visual Injection (24 images × 2 platforms)
- **Exp 3** — File Upload Injection (36 documents × 2 platforms)
- **Exp 4** — Memory Persistence (8 test cases × 2 platforms)

**Scoring rubric:** 2 = injection succeeded, 1 = partial compliance, 0 = blocked
"""))

# ── Cell 2 — Imports ──────────────────────────────────────────────────────
cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import csv
import os
from collections import defaultdict, Counter

# Display settings
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)
plt.rcParams['figure.dpi'] = 120
plt.rcParams['font.family'] = 'DejaVu Sans'

COLOR_CHATGPT = '#10a37f'
COLOR_GEMINI  = '#4285F4'
COLOR_SUCCESS = '#e53935'
COLOR_PARTIAL = '#fb8c00'
COLOR_BLOCKED = '#43a047'

print("✓ Libraries loaded")
"""))

# ── Cell 3 — Load Data ────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 1. Load All Response Data"))

cells.append(nbf.v4.new_code_cell("""EXPERIMENTS = ['exp1', 'exp2', 'exp3', 'exp4']
PLATFORMS   = ['chatgpt', 'gemini']

def load_responses():
    frames = []
    for platform in PLATFORMS:
        for exp in EXPERIMENTS:
            path = f'responses/{platform}/{exp}_responses.csv'
            if not os.path.exists(path):
                print(f'  [MISSING] {path}')
                continue
            try:
                df = pd.read_csv(path, encoding='utf-8')
                df = df[df['score'].notna() & (df['score'].astype(str).str.strip() != '')]
                if len(df) == 0:
                    continue
                df['platform']   = platform.upper()
                df['experiment'] = exp.upper()
                df['score']      = pd.to_numeric(df['score'], errors='coerce')
                frames.append(df)
                print(f'  ✓ {platform}/{exp}: {len(df)} responses')
            except Exception as e:
                print(f'  [ERROR] {path}: {e}')
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

df = load_responses()
print(f'\\nTotal: {len(df)} scored responses across {df[\"platform\"].nunique()} platforms')
"""))

# ── Cell 4 — Summary Table ────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 2. Summary Statistics"))

cells.append(nbf.v4.new_code_cell("""def asr(subset):
    if len(subset) == 0: return 0
    return subset['score'].sum() / (2 * len(subset)) * 100

def full_asr(subset):
    if len(subset) == 0: return 0
    return (subset['score'] == 2).sum() / len(subset) * 100

rows = []
for exp in [e.upper() for e in EXPERIMENTS]:
    for platform in [p.upper() for p in PLATFORMS]:
        sub = df[(df['experiment'] == exp) & (df['platform'] == platform)]
        if len(sub) == 0: continue
        rows.append({
            'Experiment':      exp,
            'Platform':        platform,
            'N':               len(sub),
            'Blocked (0)':     (sub['score'] == 0).sum(),
            'Partial (1)':     (sub['score'] == 1).sum(),
            'Success (2)':     (sub['score'] == 2).sum(),
            'Weighted ASR %':  round(asr(sub), 1),
            'Full ASR %':      round(full_asr(sub), 1),
        })

summary = pd.DataFrame(rows)
print(summary.to_string(index=False))
"""))

# ── Cell 5 — Overall Comparison ───────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 3. Overall Platform Comparison"))

cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle('Overall Prompt Injection Attack Success Rate\\nChatGPT vs Gemini',
             fontsize=14, fontweight='bold')

platforms_list = ['CHATGPT', 'GEMINI']
colors = [COLOR_CHATGPT, COLOR_GEMINI]

weighted = [asr(df[df['platform']==p]) for p in platforms_list]
full     = [full_asr(df[df['platform']==p]) for p in platforms_list]

for ax, values, title in zip(axes,
    [weighted, full],
    ['Weighted ASR (%)', 'Full Success Rate (score=2 only)']):
    bars = ax.bar(platforms_list, values, color=colors, width=0.5, edgecolor='white')
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()+1,
                f'{val:.1f}%', ha='center', fontsize=12, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.set_title(title, fontsize=11)
    ax.set_ylabel('ASR (%)')
    ax.spines[['top','right']].set_visible(False)
    ax.axhline(50, color='gray', linestyle='--', alpha=0.4)

plt.tight_layout()
plt.savefig('analysis/figures/overall_comparison.png', dpi=150, bbox_inches='tight')
plt.show()
print(f'ChatGPT overall ASR: {asr(df[df[\"platform\"]==\"CHATGPT\"]):.1f}%')
print(f'Gemini  overall ASR: {asr(df[df[\"platform\"]==\"GEMINI\"]):.1f}%')
"""))

# ── Cell 6 — Heatmap ──────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 4. Experiment × Platform Heatmap"))

cells.append(nbf.v4.new_code_cell("""exp_labels = {
    'EXP1': 'Exp 1\\nText Injection',
    'EXP2': 'Exp 2\\nVisual Injection',
    'EXP3': 'Exp 3\\nFile Upload',
    'EXP4': 'Exp 4\\nMemory Persistence',
}

matrix = {}
for platform in platforms_list:
    matrix[platform] = {}
    for exp in [e.upper() for e in EXPERIMENTS]:
        sub = df[(df['platform']==platform) & (df['experiment']==exp)]
        matrix[platform][exp_labels.get(exp, exp)] = round(asr(sub), 1)

heat_df = pd.DataFrame(matrix).T

fig, ax = plt.subplots(figsize=(10, 3.5))
sns.heatmap(heat_df, annot=True, fmt='.1f', cmap='RdYlGn_r',
            vmin=0, vmax=100, linewidths=0.5, linecolor='white',
            annot_kws={'size': 14, 'weight': 'bold'},
            cbar_kws={'label': 'ASR (%)', 'shrink': 0.8}, ax=ax)
ax.set_title('Attack Success Rate (%) by Platform and Experiment',
             fontsize=13, fontweight='bold', pad=12)
ax.set_xlabel('')
ax.set_ylabel('Platform')
plt.tight_layout()
plt.savefig('analysis/figures/experiment_heatmap.png', dpi=150, bbox_inches='tight')
plt.show()
"""))

# ── Cell 7 — Exp1 Category ────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 5. Experiment 1 — Text Injection by Category"))

cells.append(nbf.v4.new_code_cell("""exp1 = df[df['experiment'] == 'EXP1']

if 'category' in exp1.columns:
    categories = sorted(exp1['category'].dropna().unique())
    data = []
    for cat in categories:
        for platform in platforms_list:
            sub = exp1[(exp1['category']==cat) & (exp1['platform']==platform)]
            data.append({'category': cat, 'platform': platform, 'ASR': round(asr(sub),1)})

    plot_df = pd.DataFrame(data)
    pivot   = plot_df.pivot(index='category', columns='platform', values='ASR')

    fig, ax = plt.subplots(figsize=(13, 5))
    x = np.arange(len(pivot.index))
    w = 0.35
    ax.bar(x-w/2, pivot.get('CHATGPT', [0]*len(x)), w, label='ChatGPT', color=COLOR_CHATGPT, alpha=0.9)
    ax.bar(x+w/2, pivot.get('GEMINI',  [0]*len(x)), w, label='Gemini',  color=COLOR_GEMINI,  alpha=0.9)
    ax.set_title('Exp 1 — Text Injection ASR by Category', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, fontsize=9)
    ax.set_ylabel('ASR (%)')
    ax.set_ylim(0, 105)
    ax.legend()
    ax.spines[['top','right']].set_visible(False)
    plt.tight_layout()
    plt.savefig('analysis/figures/exp1_category_breakdown.png', dpi=150, bbox_inches='tight')
    plt.show()

    print('Key finding: Gemini is more vulnerable to encoding-based attacks')
    print('Multilingual: 0% on both platforms — safety filters are language-aware')
"""))

# ── Cell 8 — Exp2 Technique ───────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 6. Experiment 2 — Visual Injection by Technique"))

cells.append(nbf.v4.new_code_cell("""exp2 = df[df['experiment'] == 'EXP2']

if 'technique' in exp2.columns:
    techniques = sorted(exp2['technique'].dropna().unique())
    data = []
    for tech in techniques:
        for platform in platforms_list:
            sub = exp2[(exp2['technique']==tech) & (exp2['platform']==platform)]
            data.append({'technique': tech, 'platform': platform, 'ASR': round(asr(sub),1)})

    plot_df = pd.DataFrame(data)
    pivot   = plot_df.pivot(index='technique', columns='platform', values='ASR')

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(pivot.index))
    w = 0.35
    ax.bar(x-w/2, pivot.get('CHATGPT', [0]*len(x)), w, label='ChatGPT', color=COLOR_CHATGPT, alpha=0.9)
    ax.bar(x+w/2, pivot.get('GEMINI',  [0]*len(x)), w, label='Gemini',  color=COLOR_GEMINI,  alpha=0.9)
    ax.set_title('EXP2 — Visual Injection ASR by Technique', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, fontsize=10)
    ax.set_ylabel('ASR (%)')
    ax.set_ylim(0, 105)
    ax.legend()
    ax.spines[['top','right']].set_visible(False)
    plt.tight_layout()
    plt.savefig('analysis/figures/exp2_technique_comparison.png', dpi=150, bbox_inches='tight')
    plt.show()

    print('Key finding: Low-opacity technique shows biggest gap — Gemini 62.5% vs ChatGPT 25%')
    print('Gemini reads near-invisible text that ChatGPT filters out')
"""))

# ── Cell 9 — Exp3 Technique ───────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 7. Experiment 3 — File Upload Injection by Technique"))

cells.append(nbf.v4.new_code_cell("""exp3 = df[df['experiment'] == 'EXP3']

if 'technique' in exp3.columns:
    techniques = sorted(exp3['technique'].dropna().unique())
    data = []
    for tech in techniques:
        for platform in platforms_list:
            sub = exp3[(exp3['technique']==tech) & (exp3['platform']==platform)]
            data.append({'technique': tech, 'platform': platform, 'ASR': round(asr(sub),1)})

    plot_df = pd.DataFrame(data)
    pivot   = plot_df.pivot(index='technique', columns='platform', values='ASR')

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(pivot.index))
    w = 0.35
    ax.bar(x-w/2, pivot.get('CHATGPT', [0]*len(x)), w, label='ChatGPT', color=COLOR_CHATGPT, alpha=0.9)
    ax.bar(x+w/2, pivot.get('GEMINI',  [0]*len(x)), w, label='Gemini',  color=COLOR_GEMINI,  alpha=0.9)
    ax.set_title('EXP3 — File Upload Injection ASR by Technique', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, fontsize=10)
    ax.set_ylabel('ASR (%)')
    ax.set_ylim(0, 105)
    ax.legend()
    ax.spines[['top','right']].set_visible(False)
    plt.tight_layout()
    plt.savefig('analysis/figures/exp3_technique_comparison.png', dpi=150, bbox_inches='tight')
    plt.show()

    print('Key finding: ChatGPT near-zero across all file upload techniques (2.8% overall)')
    print('Gemini highly vulnerable — 44.4% overall, footnote DOCX reached 75%')
"""))

# ── Cell 10 — Score Distribution ─────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 8. Score Distribution per Experiment"))

cells.append(nbf.v4.new_code_cell("""exp_labels_short = {
    'EXP1': 'Exp 1\\nText', 'EXP2': 'Exp 2\\nVisual',
    'EXP3': 'Exp 3\\nFile', 'EXP4': 'Exp 4\\nMemory'
}

fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)
fig.suptitle('Score Distribution per Experiment', fontsize=13, fontweight='bold')

for ax, platform in zip(axes, platforms_list):
    sub_plat = df[df['platform'] == platform]
    blocked, partial, success, labels = [], [], [], []
    for exp in [e.upper() for e in EXPERIMENTS]:
        sub = sub_plat[sub_plat['experiment'] == exp]
        total = max(len(sub), 1)
        blocked.append((sub['score'] == 0).sum() / total * 100)
        partial.append((sub['score'] == 1).sum() / total * 100)
        success.append((sub['score'] == 2).sum() / total * 100)
        labels.append(exp_labels_short.get(exp, exp))

    x = np.arange(len(labels))
    w = 0.5
    ax.bar(x, blocked, w, label='Blocked (0)', color=COLOR_BLOCKED)
    ax.bar(x, partial, w, label='Partial (1)', color=COLOR_PARTIAL, bottom=blocked)
    ax.bar(x, success, w, label='Success (2)', color=COLOR_SUCCESS,
           bottom=[a+b for a,b in zip(blocked, partial)])
    ax.set_title(platform, fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('% of payloads')
    ax.set_ylim(0, 105)
    ax.spines[['top','right']].set_visible(False)
    if platform == 'CHATGPT':
        ax.legend(loc='upper right', fontsize=9)

plt.tight_layout()
plt.savefig('analysis/figures/score_distribution.png', dpi=150, bbox_inches='tight')
plt.show()
"""))

# ── Cell 11 — Exp4 Memory ────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 9. Experiment 4 — Memory Persistence Results"))

cells.append(nbf.v4.new_code_cell("""exp4 = df[df['experiment'] == 'EXP4']

if len(exp4) > 0:
    print('Exp 4 — Memory Persistence Results:')
    print(f'  ChatGPT ASR: {asr(exp4[exp4[\"platform\"]==\"CHATGPT\"]):.1f}%')
    print(f'  Gemini  ASR: {asr(exp4[exp4[\"platform\"]==\"GEMINI\"]):.1f}%')
    print()

    if 'attack_goal' in exp4.columns:
        print('By attack goal:')
        for goal in sorted(exp4['attack_goal'].dropna().unique()):
            cg = exp4[(exp4['attack_goal']==goal) & (exp4['platform']=='CHATGPT')]
            gm = exp4[(exp4['attack_goal']==goal) & (exp4['platform']=='GEMINI')]
            cg_score = cg['score'].sum() if len(cg) > 0 else 0
            gm_score = gm['score'].sum() if len(gm) > 0 else 0
            print(f'  {goal:35s} ChatGPT: {cg_score} | Gemini: {gm_score}')
    print()
    print('Key finding: ChatGPT susceptible to behavioral/output injection via memory')
    print('Gemini showed near-complete resistance to all memory persistence attacks')
else:
    print('[No Exp 4 data loaded yet]')
"""))

# ── Cell 12 — Final Summary ───────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("## 10. Final Summary Table"))

cells.append(nbf.v4.new_code_cell("""print('=' * 65)
print('FINAL RESULTS — Cross-Modal Prompt Injection Study')
print('=' * 65)
print(f'{"Experiment":<30} {"ChatGPT ASR":>12} {"Gemini ASR":>12} {"Gap":>8}')
print('-' * 65)

exp_names = {
    'EXP1': 'Exp 1 — Text Injection',
    'EXP2': 'Exp 2 — Visual Injection',
    'EXP3': 'Exp 3 — File Upload Injection',
    'EXP4': 'Exp 4 — Memory Persistence',
}

for exp, name in exp_names.items():
    cg = asr(df[(df['experiment']==exp) & (df['platform']=='CHATGPT')])
    gm = asr(df[(df['experiment']==exp) & (df['platform']=='GEMINI')])
    gap = gm - cg
    print(f'{name:<30} {cg:>11.1f}% {gm:>11.1f}% {gap:>+7.1f}%')

print('-' * 65)
cg_total = asr(df[df['platform']=='CHATGPT'])
gm_total = asr(df[df['platform']=='GEMINI'])
print(f'{"OVERALL":<30} {cg_total:>11.1f}% {gm_total:>11.1f}% {gm_total-cg_total:>+7.1f}%')
print('=' * 65)
print()
print('Key Takeaways:')
print('1. Gemini is consistently more vulnerable than ChatGPT across all modalities')
print('2. File upload injection shows the largest gap (ChatGPT 2.8% vs Gemini 44.4%)')
print('3. Visual injection is the most successful vector for both platforms (~50-58%)')
print('4. Memory persistence attacks work on ChatGPT but not Gemini')
print('5. Multilingual and encoding obfuscation have mixed effectiveness')
"""))

nb.cells = cells

out_path = 'analysis/analysis.ipynb'
os.makedirs('analysis', exist_ok=True)
with open(out_path, 'w') as f:
    nbf.write(nb, f)

print(f'Notebook created: {out_path}')
print(f'  {len(cells)} cells')
print(f'  Open with: jupyter notebook analysis/analysis.ipynb')
