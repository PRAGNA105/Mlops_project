"""
Generate visualization PNGs for PowerPoint presentation
Saves all charts to outputs/ directory
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import traceback

try:
    # Create output directory
    os.makedirs('outputs', exist_ok=True)

    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (12, 6)
    plt.rcParams['font.size'] = 10

    print("Generating visualizations...")

    # ============================================
    # 1. Event Distribution
    # ============================================
    print("1. Creating event distribution chart...")
    df = pd.read_csv('data/raw/events.csv')
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    event_counts = df['event'].value_counts()
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#2ecc71', '#e74c3c', '#3498db']
    bars = ax.bar(event_counts.index, event_counts.values, color=colors)
    ax.set_title('Event Distribution Across User Actions', fontsize=14, fontweight='bold')
    ax.set_ylabel('Number of Events', fontsize=12)
    ax.set_xlabel('Event Type', fontsize=12)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height):,}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig('outputs/01_event_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Saved: 01_event_distribution.png")

except Exception as e:
    print(f"ERROR: {str(e)}")
    traceback.print_exc()

# ============================================
# 2. Daily Event Volume
# ============================================
print("2. Creating daily event volume chart...")
daily_events = df.set_index('datetime').resample('D').size()
fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(daily_events.index, daily_events.values, linewidth=2.5, color='#3498db', marker='o', markersize=3)
ax.fill_between(daily_events.index, daily_events.values, alpha=0.3, color='#3498db')
ax.set_title('Daily Event Volume Over Time', fontsize=14, fontweight='bold')
ax.set_ylabel('Number of Events', fontsize=12)
ax.set_xlabel('Date', fontsize=12)
ax.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('outputs/02_daily_events.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Saved: 02_daily_events.png")

# ============================================
# 3. User Activity Distribution
# ============================================
print("3. Creating user activity distribution...")
user_events = df.groupby('visitorid').size()
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(user_events.values, bins=50, color='#9b59b6', edgecolor='black', alpha=0.7)
ax.set_title('Distribution of Events per User', fontsize=14, fontweight='bold')
ax.set_xlabel('Number of Events per User', fontsize=12)
ax.set_ylabel('Number of Users', fontsize=12)
ax.axvline(user_events.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {user_events.mean():.1f}')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig('outputs/03_user_activity_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Saved: 03_user_activity_distribution.png")

# ============================================
# 4. Model Evaluation Metrics
# ============================================
print("4. Creating model evaluation metrics...")
with open('data/processed/evaluation_metrics.json', 'r') as f:
    metrics = json.load(f)

# Prepare metrics for visualization
metric_names = ['Precision@5', 'Recall@5', 'Hit Rate@5']
metric_values = [metrics['precision_at_k'], metrics['recall_at_k'], metrics['hit_rate_at_k']]

fig, ax = plt.subplots(figsize=(10, 6))
colors_metrics = ['#e74c3c', '#f39c12', '#2ecc71']
bars = ax.bar(metric_names, metric_values, color=colors_metrics, edgecolor='black', linewidth=1.5)
ax.set_title('Model Evaluation Metrics (Top-5 Recommendations)', fontsize=14, fontweight='bold')
ax.set_ylabel('Score', fontsize=12)
ax.set_ylim(0, max(metric_values) * 1.2)

# Add value labels
for bar, val in zip(bars, metric_values):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.6f}',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.savefig('outputs/04_model_metrics.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Saved: 04_model_metrics.png")

# ============================================
# 5. Event Type Proportion (Pie Chart)
# ============================================
print("5. Creating event type proportion chart...")
event_props = df['event'].value_counts()
fig, ax = plt.subplots(figsize=(10, 8))
colors_pie = ['#2ecc71', '#e74c3c', '#3498db']
wedges, texts, autotexts = ax.pie(event_props.values, 
                                    labels=event_props.index, 
                                    autopct='%1.1f%%',
                                    colors=colors_pie,
                                    startangle=90,
                                    textprops={'fontsize': 12, 'fontweight': 'bold'})
ax.set_title('Event Type Breakdown', fontsize=14, fontweight='bold')

# Make percentage text more visible
for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontsize(12)
    autotext.set_fontweight('bold')

plt.tight_layout()
plt.savefig('outputs/05_event_breakdown.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Saved: 05_event_breakdown.png")

# ============================================
# 6. Interaction Matrix Statistics
# ============================================
print("6. Creating interaction matrix statistics...")
interaction_df = pd.read_csv('data/processed/interaction_matrix.csv')
item_features = pd.read_csv('data/processed/item_features.csv')

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Subplot 1: Interaction score distribution
axes[0].hist(interaction_df['interaction_score'], bins=50, color='#3498db', edgecolor='black', alpha=0.7)
axes[0].set_title('Distribution of Interaction Scores', fontsize=12, fontweight='bold')
axes[0].set_xlabel('Interaction Score', fontsize=11)
axes[0].set_ylabel('Frequency', fontsize=11)
axes[0].grid(True, alpha=0.3, axis='y')

# Subplot 2: Item popularity
top_items = item_features.nlargest(10, 'popularity_score')[['item_id', 'popularity_score']]
axes[1].barh(range(len(top_items)), top_items['popularity_score'].values, color='#e74c3c')
axes[1].set_yticks(range(len(top_items)))
axes[1].set_yticklabels([f"Item {iid}" for iid in top_items['item_id'].values])
axes[1].set_title('Top 10 Most Popular Items', fontsize=12, fontweight='bold')
axes[1].set_xlabel('Popularity Score', fontsize=11)
axes[1].invert_yaxis()

plt.tight_layout()
plt.savefig('outputs/06_interaction_stats.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Saved: 06_interaction_stats.png")

# ============================================
# 7. Project Overview Summary
# ============================================
print("7. Creating project summary...")
summary_text = f"""
ECOMMERCE RECOMMENDATION SYSTEM - PROJECT OVERVIEW

Dataset Statistics:
  • Total Events: {len(df):,}
  • Unique Users: {df['visitorid'].nunique():,}
  • Unique Items: {df['itemid'].nunique():,}
  • Date Range: {df['datetime'].min().date()} to {df['datetime'].max().date()}

Event Breakdown:
  • Views: {(df['event'] == 'view').sum():,} ({(df['event'] == 'view').sum()/len(df)*100:.1f}%)
  • Add to Cart: {(df['event'] == 'addtocart').sum():,} ({(df['event'] == 'addtocart').sum()/len(df)*100:.1f}%)
  • Transactions: {(df['event'] == 'transaction').sum():,} ({(df['event'] == 'transaction').sum()/len(df)*100:.1f}%)

Model Performance (Top-5):
  • Precision@5: {metrics['precision_at_k']:.6f}
  • Recall@5: {metrics['recall_at_k']:.6f}
  • Hit Rate@5: {metrics['hit_rate_at_k']:.6f}

Infrastructure:
  ✓ DVC Pipeline for reproducibility
  ✓ MLflow for experiment tracking
  ✓ FastAPI for real-time recommendations
  ✓ Kafka for event streaming
  ✓ Prometheus for monitoring
  ✓ Docker for containerization
"""

fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111)
ax.axis('off')
ax.text(0.05, 0.95, summary_text, transform=ax.transAxes, fontsize=11,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('outputs/07_project_summary.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓ Saved: 07_project_summary.png")

print("\n" + "="*50)
print("✅ All visualizations generated successfully!")
print("="*50)
print(f"\nOutput directory: outputs/")
print("\nGenerated files:")
print("  1. 01_event_distribution.png")
print("  2. 02_daily_events.png")
print("  3. 03_user_activity_distribution.png")
print("  4. 04_model_metrics.png")
print("  5. 05_event_breakdown.png")
print("  6. 06_interaction_stats.png")
print("  7. 07_project_summary.png")
print("\n📊 Ready for PowerPoint presentation!")
