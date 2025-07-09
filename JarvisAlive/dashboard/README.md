# HeyJarvis Rich CLI Dashboard

A comprehensive real-time dashboard for monitoring HeyJarvis Sales Department metrics using Rich CLI library.

## Features

### 📊 Real-Time Metrics
- **Key Metrics**: Leads generated, qualified, messages composed, emails sent, responses, meetings
- **Performance Metrics**: Success rates, personalization scores, response rates, execution times
- **Visual Indicators**: Color-coded status indicators and progress bars

### 🔄 Workflow Monitoring
- **Active Workflows**: Real-time status of running sales workflows
- **Progress Tracking**: Visual progress bars with ETA calculations
- **Status Icons**: Clear visual indicators (🟢 Running, ✅ Done, ⏳ Queued, ❌ Failed)

### 📋 Current Task Progress
- **Task Details**: Step-by-step progress of current operations
- **Progress Visualization**: Detailed progress bars and status messages
- **Real-time Updates**: Live updates of task completion

### 💾 Export Capabilities
- **JSON Export**: Complete metrics export with timestamps
- **CSV Export**: Tabular data export for analysis
- **Summary Reports**: Quick snapshot views

## Usage

### Live Dashboard
```bash
# Start live dashboard with Redis
python3 metrics_dashboard.py <session_id>

# Start with mock data (demo mode)
python3 metrics_dashboard.py <session_id> --mock
```

### Quick Operations
```bash
# Export current metrics
python3 metrics_dashboard.py <session_id> --export

# Show summary table
python3 metrics_dashboard.py <session_id> --summary

# Demo mode with mock data
python3 metrics_dashboard.py demo --mock --summary
```

### Test Dashboard
```bash
# Run comprehensive tests
python3 test_dashboard.py
```

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│                🤖 HeyJarvis Sales Dashboard 📊               │
│           Session: demo | Time: 15:06:41 | Uptime: 0:05:23  │
└─────────────────────────────────────────────────────────────┘
┌──────────────────┬──────────────────────────────────────────┐
│  📊 Key Metrics  │           🔄 Active Workflows           │
│                  │                                          │
│ 📈 Leads: 47     │ Lead Generation    🟢 Running  ████░ 70% │
│ 🎯 Qualified: 23 │ Quick Wins         ✅ Done    ██████ 100%│
│ ✉️ Messages: 15  │ Full Outreach      ⏳ Queued  ░░░░░░   0%│
│                  │                                          │
├──────────────────┼──────────────────────────────────────────┤
│ ⚡ Performance   │          📋 Current Task                │
│                  │                                          │
│ ✅ Success: 87%  │ 📋 Scanning SaaS CTOs (In Progress)     │
│ 🎨 Personal: 76% │                                          │
│ 📞 Response: 25% │ Steps: Step 3 of 5                      │
│ ⏱️ Avg: 2.3s     │ Progress: ████████████░░░░░░░░ 60%      │
│                  │                                          │
│                  │ Status: Processing 25 potential leads...│
└──────────────────┴──────────────────────────────────────────┘
│     Controls: Ctrl+C Exit | E Export | R Reset | S Snapshot │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

- Python 3.7+
- Rich library (`pip install rich`)
- Redis (optional, falls back to mock mode)
- redis-py (`pip install redis`) for Redis connectivity

## Integration

The dashboard integrates with:
- **Sales Department**: Real-time workflow monitoring
- **Lead Scanner Agent**: Lead generation metrics
- **Outreach Composer**: Message composition stats
- **Redis**: Persistent metric storage

## Mock Mode

When Redis is unavailable or `--mock` flag is used:
- Realistic demo data is generated
- All dashboard features remain functional
- Perfect for testing and demonstrations
- No external dependencies required