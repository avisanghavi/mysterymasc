# Jarvis Quick Reference Guide

## Command Line Usage

```bash
# Traditional agent builder
python3 main.py

# Jarvis business mode
python3 main.py --jarvis

# Interactive demos
python3 main.py --demo
```

## Key Code Patterns

### Agent Builder (Existing)
```python
from orchestration.orchestrator import HeyJarvisOrchestrator, OrchestratorConfig

config = OrchestratorConfig(anthropic_api_key="your_key")
orchestrator = HeyJarvisOrchestrator(config)
result = await orchestrator.process_request("Create an email monitor", session_id)
```

### Jarvis Business (New)
```python
from orchestration.jarvis import Jarvis, JarvisConfig

jarvis_config = JarvisConfig(orchestrator_config=config)
jarvis = Jarvis(jarvis_config)
result = await jarvis.process_business_request("Grow sales by 30%", session_id)
```

## When to Use Which

| Agent Builder | Jarvis |
|--------------|--------|
| Technical tasks | Business goals |
| Individual agents | Department coordination |
| Custom integrations | Standard business processes |

## Quick Migration Checklist

- [ ] Existing workflows still work
- [ ] Jarvis configuration added
- [ ] WebSocket modes configured
- [ ] Business context setup
- [ ] Department coordination tested

## Common Patterns

### WebSocket Updates
```python
# Agent builder
await send_agent_created(session_id, agent_spec)

# Jarvis
await websocket_handler.send_department_activated(session_id, "sales", 4)
```

### Business Metrics
```python
# Extract metrics from conversation
manager = JarvisConversationManager(session_id)
metrics = manager.extract_business_metrics("Revenue is $2.5M")
```

### Department Operations
```python
# Sales department activation
from departments.sales.sales_department import SalesDepartment

sales = SalesDepartment(redis_client, session_id)
await sales.initialize()
agents = sales.get_active_agents()  # 4 coordinated agents
```

## Troubleshooting Quick Fixes

### Import Errors
```python
import sys
sys.path.append('/path/to/project')
from orchestration.jarvis import Jarvis
```

### Redis Conflicts
```python
# Use different namespaces
config = OrchestratorConfig(redis_namespace="agent_builder")
jarvis_config = JarvisConfig(redis_namespace="jarvis")
```

### Session Conflicts
```python
# Use prefixed session IDs
agent_session = f"agent_{session_id}"
jarvis_session = f"jarvis_{session_id}"
```

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_api_key

# Optional Jarvis settings
MAX_DEPARTMENTS=5
AUTO_DEPARTMENTS=true
CROSS_DEPT_COORD=true
```

## Testing Commands

```bash
# Run integration tests
python3 run_integration_tests.py

# Test demos
python3 test_jarvis_demos.py

# Migration validation
python3 test_migration.py
```