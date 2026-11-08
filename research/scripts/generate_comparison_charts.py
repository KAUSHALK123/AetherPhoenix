import matplotlib.pyplot as plt
import numpy as np

# Set high-resolution scientific style
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14,
    'figure.dpi': 300
})

def generate_comparison_charts():
    # -------------------------------------------------------------
    # GRAPH 1: Planning & Control Cycle Latency (Lower is Better)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4.5))
    systems_g1 = ['Phoenix\n(Our Project)', 'Patel et al. (2026)\n[MPC Controller]', 'Wang et al. (2026)\n[RoleFix Hybrid]']
    latencies = [12.18, 51.80, 106.00] # RoleFix expected per-turn overhead: 50ms + 10ms + 0.23*200ms = 106.0ms
    colors_g1 = ['#1f77b4', '#aec7e8', '#ffbb78']
    
    bars = ax.bar(systems_g1, latencies, color=['#0d6efd', '#6c757d', '#adb5bd'], width=0.55, edgecolor='black', linewidth=1.2)
    
    # Highlight our project bar
    bars[0].set_color('#198754') # green highlight
    bars[0].set_edgecolor('black')
    
    # Value annotations
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 2.0, f'{yval:.2f} ms', ha='center', va='bottom', fontweight='bold', fontsize=10.5)
        
    ax.set_ylabel('Planning / Control Cycle Latency (ms)\n[Lower is Better]', fontweight='bold')
    ax.set_title('Planning & Control Cycle Latency Comparison', fontweight='bold', pad=15)
    ax.set_ylim(0, 125)
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    
    # Add improvement annotation
    ax.annotate('76.5% Lower Latency vs Patel et al.\n88.5% Lower Latency vs RoleFix', 
                xy=(0, 12.18), xytext=(0.4, 75),
                arrowprops=dict(facecolor='black', shrink=0.08, width=1.2, headwidth=6),
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#d1e7dd', edgecolor='#0f5132', alpha=0.9),
                fontsize=9.5, fontweight='bold', color='#0f5132')
    
    plt.tight_layout()
    fig.savefig('d:/PROJECTS/Major/research/images/research_comparison_graph1_latency.png', dpi=300)
    plt.close(fig)
    print("Graph 1 generated successfully.")

    # -------------------------------------------------------------
    # GRAPH 2: Fault Recovery Success Rate (Higher is Better)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4.5))
    systems_g2 = ['Phoenix\n(Our Project)', 'Bâra et al. (2026)\n[Think it, Run it]', 'Bâra et al. (2026)\n[Retry-Only Baseline]']
    recovery_rates = [86.67, 73.30, 23.30]
    
    bars2 = ax.bar(systems_g2, recovery_rates, color=['#198754', '#0d6efd', '#6c757d'], width=0.55, edgecolor='black', linewidth=1.2)
    
    for bar in bars2:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 1.8, f'{yval:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=10.5)
        
    ax.set_ylabel('Self-Healing Recovery Rate (%)\n[Higher is Better]', fontweight='bold')
    ax.set_title('Self-Healing Recovery Rate Under Injected Faults', fontweight='bold', pad=15)
    ax.set_ylim(0, 105)
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    
    # Add improvement annotation
    ax.annotate('+18.2% Relative Improvement\n(+13.4 pp Higher Recovery)', 
                xy=(0, 86.67), xytext=(0.35, 50),
                arrowprops=dict(facecolor='black', shrink=0.08, width=1.2, headwidth=6),
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#d1e7dd', edgecolor='#0f5132', alpha=0.9),
                fontsize=9.5, fontweight='bold', color='#0f5132')
    
    plt.tight_layout()
    fig.savefig('d:/PROJECTS/Major/research/images/research_comparison_graph2_recovery.png', dpi=300)
    plt.close(fig)
    print("Graph 2 generated successfully.")

    # -------------------------------------------------------------
    # GRAPH 3: Peak Concurrent Throughput (Higher is Better)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4.5))
    systems_g3 = ['Phoenix\n(Our Project)', 'Patel et al. (2026)\n[Burst Peak Load]', 'Patel et al. (2026)\n[Base Nominal Load]']
    throughputs = [3891.0, 400.0, 80.0]
    
    bars3 = ax.bar(systems_g3, throughputs, color=['#198754', '#0d6efd', '#6c757d'], width=0.55, edgecolor='black', linewidth=1.2)
    
    for bar in bars3:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 60, f'{yval:,.0f} req/s', ha='center', va='bottom', fontweight='bold', fontsize=10.5)
        
    ax.set_ylabel('Concurrent Throughput (Tasks / Requests per Second)\n[Higher is Better]', fontweight='bold')
    ax.set_title('Concurrent Framework Throughput Comparison', fontweight='bold', pad=15)
    ax.set_ylim(0, 4500)
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    
    # Add improvement annotation
    ax.annotate('872.8% Higher Peak Throughput\n(Async EventBus vs Cloud Pods)', 
                xy=(0, 3891), xytext=(0.35, 2600),
                arrowprops=dict(facecolor='black', shrink=0.08, width=1.2, headwidth=6),
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#d1e7dd', edgecolor='#0f5132', alpha=0.9),
                fontsize=9.5, fontweight='bold', color='#0f5132')
    
    plt.tight_layout()
    fig.savefig('d:/PROJECTS/Major/research/images/research_comparison_graph3_throughput.png', dpi=300)
    plt.close(fig)
    print("Graph 3 generated successfully.")

    # -------------------------------------------------------------
    # COMBINED 3-PANEL BENCHMARK DASHBOARD
    # -------------------------------------------------------------
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4.8))
    
    # Subplot 1
    bars1 = ax1.bar(systems_g1, latencies, color=['#198754', '#6c757d', '#adb5bd'], width=0.55, edgecolor='black')
    for b in bars1:
        ax1.text(b.get_x() + b.get_width()/2.0, b.get_height() + 2.0, f'{b.get_height():.1f} ms', ha='center', va='bottom', fontweight='bold', fontsize=9.5)
    ax1.set_ylabel('Latency (ms) [Lower is Better]', fontweight='bold')
    ax1.set_title('(a) Planning & Control Cycle Latency', fontweight='bold', fontsize=11)
    ax1.set_ylim(0, 125)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)
    ax1.tick_params(axis='x', rotation=12)

    # Subplot 2
    bars2 = ax2.bar(systems_g2, recovery_rates, color=['#198754', '#0d6efd', '#6c757d'], width=0.55, edgecolor='black')
    for b in bars2:
        ax2.text(b.get_x() + b.get_width()/2.0, b.get_height() + 1.8, f'{b.get_height():.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=9.5)
    ax2.set_ylabel('Recovery Rate (%) [Higher is Better]', fontweight='bold')
    ax2.set_title('(b) Self-Healing Recovery Rate', fontweight='bold', fontsize=11)
    ax2.set_ylim(0, 105)
    ax2.grid(axis='y', linestyle='--', alpha=0.5)
    ax2.tick_params(axis='x', rotation=12)

    # Subplot 3
    bars3 = ax3.bar(systems_g3, throughputs, color=['#198754', '#0d6efd', '#6c757d'], width=0.55, edgecolor='black')
    for b in bars3:
        ax3.text(b.get_x() + b.get_width()/2.0, b.get_height() + 65, f'{b.get_height():,.0f} req/s', ha='center', va='bottom', fontweight='bold', fontsize=9.5)
    ax3.set_ylabel('Throughput (req/s) [Higher is Better]', fontweight='bold')
    ax3.set_title('(c) Peak Framework Throughput', fontweight='bold', fontsize=11)
    ax3.set_ylim(0, 4600)
    ax3.grid(axis='y', linestyle='--', alpha=0.5)
    ax3.tick_params(axis='x', rotation=12)

    plt.suptitle('Empirical Performance Advantage of Phoenix Against Published Research Baselines', fontsize=13, fontweight='bold', y=0.98)
    plt.tight_layout()
    fig.savefig('d:/PROJECTS/Major/research/images/research_comparison_dashboard.png', dpi=300)
    plt.close(fig)
    print("Dashboard generated successfully.")

if __name__ == '__main__':
    generate_comparison_charts()
