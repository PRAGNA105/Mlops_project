"""
Generate visualization PNGs for PowerPoint presentation - SIMPLIFIED
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import os

# Create output directory
os.makedirs('outputs', exist_ok=True)

print("Loading data...")
df = pd.read_csv('data/raw/events.csv')
df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

print("1. Event Distribution...")
fig = plt.figure(figsize=(10, 6))
event_counts = df['event'].value_counts()
plt.bar(event_counts.index, event_counts.values, color=['#2ecc71', '#e74c3c', '#3498db'])
plt.title('Event Distribution Across User Actions', fontsize=14, fontweight='bold')
plt.ylabel('Number of Events', fontsize=12)
plt.xlabel('Event Type', fontsize=12)
plt.grid(axis='y', alpha=0.3)
plt.savefig('outputs/01_event_distribution.png', dpi=200, bbox_inches='tight')
plt.close()
print("✓ Saved: 01_event_distribution.png")

print("2. Daily Event Volume...")
fig = plt.figure(figsize=(14, 5))
daily_events = df.set_index('datetime').resample('D').size()
plt.plot(daily_events.index, daily_events.values, linewidth=2, color='#3498db')
plt.fill_between(daily_events.index, daily_events.values, alpha=0.3, color='#3498db')
plt.title('Daily Event Volume Over Time', fontsize=14, fontweight='bold')
plt.ylabel('Number of Events', fontsize=12)
plt.xlabel('Date', fontsize=12)
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('outputs/02_daily_events.png', dpi=200, bbox_inches='tight')
plt.close()
print("✓ Saved: 02_daily_events.png")

print("3. User Activity Distribution...")
fig = plt.figure(figsize=(10, 6))
user_events = df.groupby('visitorid').size()
plt.hist(user_events.values, bins=40, color='#9b59b6', edgecolor='black', alpha=0.7)
plt.title('Distribution of Events per User', fontsize=14, fontweight='bold')
plt.xlabel('Number of Events per User', fontsize=12)
plt.ylabel('Number of Users', fontsize=12)
plt.grid(True, alpha=0.3, axis='y')
plt.savefig('outputs/03_user_activity_distribution.png', dpi=200, bbox_inches='tight')
plt.close()
print("✓ Saved: 03_user_activity_distribution.png")

print("4. Event Type Breakdown (Pie)...")
fig = plt.figure(figsize=(10, 8))
event_props = df['event'].value_counts()
colors = ['#2ecc71', '#e74c3c', '#3498db']
plt.pie(event_props.values, labels=event_props.index, autopct='%1.1f%%', colors=colors, startangle=90)
plt.title('Event Type Breakdown', fontsize=14, fontweight='bold')
plt.savefig('outputs/04_event_breakdown.png', dpi=200, bbox_inches='tight')
plt.close()
print("✓ Saved: 04_event_breakdown.png")

print("5. Model Evaluation Metrics...")
fig = plt.figure(figsize=(10, 6))
with open('data/processed/evaluation_metrics.json', 'r') as f:
    metrics = json.load(f)

metric_names = ['Precision@5', 'Recall@5', 'Hit Rate@5']
metric_values = [metrics['precision_at_k'], metrics['recall_at_k'], metrics['hit_rate_at_k']]
colors_m = ['#e74c3c', '#f39c12', '#2ecc71']
plt.bar(metric_names, metric_values, color=colors_m, edgecolor='black', linewidth=1.5)
plt.title('Model Evaluation Metrics (Top-5 Recommendations)', fontsize=14, fontweight='bold')
plt.ylabel('Score', fontsize=12)
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('outputs/05_model_metrics.png', dpi=200, bbox_inches='tight')
plt.close()
print("✓ Saved: 05_model_metrics.png")

print("6. Dataset Statistics...")
fig = plt.figure(figsize=(12, 8))
plt.axis('off')
stats_text = f"""
ECOMMERCE RECOMMENDATION SYSTEM - DATASET OVERVIEW

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

MLOps Infrastructure:
  ✓ DVC Pipeline for reproducibility
  ✓ MLflow for experiment tracking
  ✓ FastAPI for real-time recommendations
  ✓ Kafka for event streaming
  ✓ Prometheus for monitoring
  ✓ Docker for containerization
"""
plt.text(0.05, 0.95, stats_text, transform=plt.gca().transAxes, 
         fontsize=11, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))
plt.savefig('outputs/06_dataset_summary.png', dpi=200, bbox_inches='tight')
plt.close()
print("✓ Saved: 06_dataset_summary.png")

print("\n" + "="*60)
print("✅ All visualizations generated successfully!")
print("="*60)
print(f"\n📁 Location: outputs/")
print("\n📊 Generated files:")
print("   1. 01_event_distribution.png - Bar chart of event types")
print("   2. 02_daily_events.png - Time series of daily activity")
print("   3. 03_user_activity_distribution.png - User engagement histogram")
print("   4. 04_event_breakdown.png - Pie chart of event proportions")
print("   5. 05_model_metrics.png - Model performance metrics")
print("   6. 06_dataset_summary.png - Project statistics and overview")
print("\n🎯 Ready for PowerPoint presentation!")
