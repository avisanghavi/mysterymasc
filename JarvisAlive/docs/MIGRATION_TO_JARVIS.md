# Migrating to Jarvis Business Orchestration

## Overview

Jarvis adds business-level orchestration on top of the existing HeyJarvis agent builder, transforming how you automate business processes. Instead of creating individual agents one-by-one, Jarvis coordinates entire departments to achieve business goals.

### What Changes

- **Agent Builder**: Remains fully functional for technical automation
- **Jarvis Layer**: Adds business-level orchestration and department coordination
- **Dual Operation**: Both systems coexist and complement each other

### Key Benefits

| Traditional Agent Builder | Jarvis Business Orchestration |
|--------------------------|------------------------------|
| Individual agent creation | Department-level coordination |
| Technical task focus | Business outcome focus |
| Manual agent coordination | Automatic multi-agent workflows |
| Limited business context | Rich business intelligence |
| Single-purpose automation | Strategic business automation |

## For Existing Users

**Good news: Your current workflows remain completely unchanged.**

All existing functionality continues to work exactly as before:

```python
# Your existing agent builder workflows work unchanged
from orchestration.orchestrator import HeyJarvisOrchestrator

orchestrator = HeyJarvisOrchestrator(config)
result = await orchestrator.process_request("Create an email monitor", session_id)
```

**What's new:** You can now also use business-level orchestration:

```python
# New Jarvis business orchestration
from orchestration.jarvis import Jarvis

jarvis = Jarvis(jarvis_config)
result = await jarvis.process_business_request("Grow sales by 30%", session_id)
```

## Migration Path

### Phase 1: Continue Current Usage (No Changes Required)

Your existing setup works without modification:

```bash
# Continue using as before
python3 main.py

# All existing commands and workflows unchanged
```

### Phase 2: Enable Jarvis (Optional)

Enable business-level orchestration when ready:

```bash
# New: Access Jarvis business mode
python3 main.py --jarvis

# Or use both systems
python3 main.py  # Traditional agent builder
python3 main.py --jarvis  # Business orchestration
```

### Phase 3: Gradual Department Adoption

Migrate individual agents to department-based workflows over time:

```python
# Migration example: Email monitoring
# BEFORE: Individual email agent
from orchestration.orchestrator import HeyJarvisOrchestrator

orchestrator = HeyJarvisOrchestrator(config)
result = await orchestrator.process_request(
    "Create an email monitoring agent that checks for urgent messages every 5 minutes",
    session_id
)

# AFTER: Part of Sales department coordination
from orchestration.jarvis import Jarvis

jarvis = Jarvis(jarvis_config)
result = await jarvis.process_business_request(
    "Set up sales lead tracking and email monitoring for urgent prospects",
    session_id
)
```

## Code Examples for Migration

### Converting Individual Agents to Department Workflows

#### Example 1: Email Monitoring Migration

**Before (Individual Agent):**
```python
# Creating standalone email monitor
email_request = "Monitor my email for urgent messages and send Slack alerts"

# Traditional approach
orchestrator = HeyJarvisOrchestrator(config)
result = await orchestrator.process_request(email_request, session_id)

# Result: Single email monitoring agent
agent_spec = result['agent_spec']
print(f"Created: {agent_spec['name']}")  # "Email Monitor Agent"
```

**After (Department Integration):**
```python
# Email monitoring as part of business workflow
business_request = "Set up sales pipeline monitoring and customer communication tracking"

# Jarvis approach
jarvis = Jarvis(jarvis_config)
result = await jarvis.process_business_request(business_request, session_id)

# Result: Sales department with coordinated agents including email monitoring
departments = result['activated_departments']
print(f"Activated: {departments}")  # ['sales'] with multiple coordinated agents
```

#### Example 2: Data Processing Migration

**Before (Individual Agent):**
```python
# Single-purpose data processor
data_request = "Create a CSV processor that analyzes sales data daily"

result = await orchestrator.process_request(data_request, session_id)
# Creates one agent focused on CSV processing
```

**After (Business Integration):**
```python
# Data processing as part of business intelligence
business_request = "Analyze sales performance and identify growth opportunities"

result = await jarvis.process_business_request(business_request, session_id)
# Creates coordinated analytics workflow with multiple agents
```

### Configuration Examples

#### Setting Up Business Context

```python
# Configure Jarvis with business context
from orchestration.jarvis import Jarvis, JarvisConfig
from orchestration.orchestrator import OrchestratorConfig

# Base configuration (same as before)
orchestrator_config = OrchestratorConfig(
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    max_retries=3,
    session_timeout=3600
)

# New: Jarvis business configuration
jarvis_config = JarvisConfig(
    orchestrator_config=orchestrator_config,
    max_concurrent_departments=5,
    enable_autonomous_department_creation=True,
    enable_cross_department_coordination=True
)

jarvis = Jarvis(jarvis_config)
await jarvis.initialize()
```

#### Configuring Department Workflows

```python
# Sales department configuration
from departments.sales.sales_department import SalesDepartment

# Initialize department
sales_dept = SalesDepartment(jarvis.redis_client, session_id)
await sales_dept.initialize()

# Department automatically includes:
# - Lead Scanner Agent
# - Outreach Composer Agent  
# - Meeting Scheduler Agent
# - Pipeline Tracker Agent

# All agents coordinate automatically
agents = sales_dept.get_active_agents()
print(f"Coordinated agents: {len(agents)}")  # 4 agents working together
```

#### Mapping Business Goals to Metrics

```python
# Business goal tracking
from conversation.jarvis_conversation_manager import JarvisConversationManager

# Enhanced conversation management with business context
jarvis_conv = JarvisConversationManager(session_id=session_id)

# Add business goal
jarvis_conv.add_user_message("Increase revenue by 30% this quarter")

# Automatic business intelligence extraction
metrics = jarvis_conv.extract_business_metrics("Current revenue is $2.5M, target $3.25M")
print(f"Extracted metrics: {metrics}")

# Generate business summary
summary = jarvis_conv.generate_executive_summary()
print(f"Executive summary: {summary}")
```

## Parallel Operation Guide

### How Both Systems Coexist

The agent builder and Jarvis operate independently but can complement each other:

```python
# Same session, different approaches
session_id = "hybrid_session_001"

# Technical automation via agent builder
technical_result = await orchestrator.process_request(
    "Create a file backup agent that runs weekly",
    session_id
)

# Business automation via Jarvis
business_result = await jarvis.process_business_request(
    "Implement data security and backup protocols for customer information",
    session_id
)

# Both results coexist and can coordinate
```

### When to Use Which System

| Use Agent Builder When | Use Jarvis When |
|----------------------|-----------------|
| Creating specific technical tools | Achieving business outcomes |
| Individual automation tasks | Department-level coordination |
| Custom integration projects | Standard business processes |
| Technical experimentation | Strategic business automation |
| Single-purpose agents | Multi-agent workflows |

#### Decision Matrix

```python
def choose_system(request: str) -> str:
    """Helper to choose between agent builder and Jarvis"""
    business_keywords = [
        'sales', 'revenue', 'customers', 'growth', 'efficiency', 
        'costs', 'profit', 'department', 'business', 'performance'
    ]
    
    technical_keywords = [
        'create agent', 'monitor', 'integration', 'api', 'webhook',
        'file', 'database', 'sync', 'backup', 'custom'
    ]
    
    request_lower = request.lower()
    
    business_score = sum(1 for kw in business_keywords if kw in request_lower)
    technical_score = sum(1 for kw in technical_keywords if kw in request_lower)
    
    if business_score > technical_score:
        return "jarvis"  # Business orchestration
    else:
        return "agent_builder"  # Technical automation
```

### Gradual Transition Strategy

#### Week 1-2: Evaluation Phase
```python
# Run both systems in parallel for comparison
def compare_approaches(request: str):
    # Traditional approach
    start_time = time.time()
    agent_result = await orchestrator.process_request(request, session_id + "_agent")
    agent_time = time.time() - start_time
    
    # Jarvis approach  
    start_time = time.time()
    jarvis_result = await jarvis.process_business_request(request, session_id + "_jarvis")
    jarvis_time = time.time() - start_time
    
    return {
        "agent_builder": {"result": agent_result, "time": agent_time},
        "jarvis": {"result": jarvis_result, "time": jarvis_time}
    }
```

#### Week 3-4: Selective Migration
```python
# Migrate high-value business processes first
priority_migrations = [
    "sales pipeline management",
    "customer service optimization", 
    "operational cost reduction",
    "marketing campaign coordination"
]

for process in priority_migrations:
    # Test Jarvis approach
    result = await jarvis.process_business_request(process, session_id)
    if result['success']:
        print(f"✅ Migrated: {process}")
    else:
        print(f"⏳ Keep using agent builder for: {process}")
```

#### Week 5+: Full Integration
```python
# Use both systems based on request type
async def unified_request_handler(request: str, session_id: str):
    system = choose_system(request)
    
    if system == "jarvis":
        return await jarvis.process_business_request(request, session_id)
    else:
        return await orchestrator.process_request(request, session_id)
```

## Environment Configuration

### Environment Variables

```bash
# .env file - all existing variables remain the same
ANTHROPIC_API_KEY=your_api_key
REDIS_URL=redis://localhost:6379
MAX_RETRIES=3
SESSION_TIMEOUT=3600

# New optional Jarvis-specific settings
MAX_DEPARTMENTS=5
AUTO_DEPARTMENTS=true
CROSS_DEPT_COORD=true
JARVIS_MODE=business  # or hybrid
```

### Configuration Files

Create `jarvis_config.json` for advanced settings:

```json
{
  "business_context": {
    "company_stage": "growth",
    "industry": "saas",
    "team_size": "50-200",
    "primary_goals": ["revenue_growth", "operational_efficiency"]
  },
  "department_settings": {
    "sales": {
      "auto_activation": true,
      "coordination_level": "high",
      "metrics_tracking": true
    },
    "marketing": {
      "auto_activation": false,
      "coordination_level": "medium"
    }
  },
  "integration_settings": {
    "websocket_updates": true,
    "real_time_metrics": true,
    "cross_department_messaging": true
  }
}
```

## WebSocket Integration Migration

### Before: Individual Agent Updates
```python
# Old WebSocket pattern
from conversation.websocket_handler import send_agent_created, send_progress_update

# Individual agent notifications
await send_agent_created(session_id, agent_spec)
await send_progress_update(session_id, 100, "Agent deployed")
```

### After: Business-Level Updates
```python
# New WebSocket patterns
from conversation.websocket_handler import websocket_handler

# Department-level notifications
await websocket_handler.send_department_activated(session_id, "sales", 4, {
    "agents": ["Lead Scanner", "Outreach Composer", "Meeting Scheduler", "Pipeline Tracker"],
    "estimated_impact": "30% sales growth"
})

# Business metrics updates
await websocket_handler.send_business_metric_updated(session_id, "revenue", 2500000, change=15.2)

# Cross-department coordination
await websocket_handler.send_agent_coordination(
    session_id, "Sales Department", "Marketing Department", 
    "High-quality leads ready for nurturing", {"lead_count": 25}
)
```

## Testing Migration

### Validation Scripts

Create `test_migration.py`:

```python
#!/usr/bin/env python3
"""Test migration between agent builder and Jarvis."""

import asyncio
from orchestration.orchestrator import HeyJarvisOrchestrator, OrchestratorConfig
from orchestration.jarvis import Jarvis, JarvisConfig

async def test_parallel_operation():
    """Test that both systems work in parallel."""
    # Setup both systems
    base_config = OrchestratorConfig(anthropic_api_key="test")
    orchestrator = HeyJarvisOrchestrator(base_config)
    
    jarvis_config = JarvisConfig(orchestrator_config=base_config)
    jarvis = Jarvis(jarvis_config)
    
    # Test requests
    technical_request = "Create a file backup agent"
    business_request = "Improve operational efficiency"
    
    # Both should work without interference
    agent_result = await orchestrator.process_request(technical_request, "test_agent")
    jarvis_result = await jarvis.process_business_request(business_request, "test_jarvis")
    
    assert agent_result is not None
    assert jarvis_result is not None
    print("✅ Parallel operation test passed")

if __name__ == "__main__":
    asyncio.run(test_parallel_operation())
```

### Migration Checklist

- [ ] Existing agent builder workflows still function
- [ ] Jarvis business requests process correctly
- [ ] WebSocket updates work for both systems
- [ ] Configuration files properly structured
- [ ] Environment variables correctly set
- [ ] Department coordination functioning
- [ ] Business metrics tracking active
- [ ] Cross-system session management working

## Troubleshooting Common Migration Issues

### Issue 1: Import Errors After Migration

**Problem:**
```python
ImportError: cannot import name 'Jarvis' from 'orchestration.jarvis'
```

**Solution:**
```python
# Ensure proper import paths
import sys
sys.path.append('/path/to/project')

# Use absolute imports
from orchestration.jarvis import Jarvis, JarvisConfig
```

### Issue 2: Redis Connection Conflicts

**Problem:**
Both systems trying to use the same Redis keys.

**Solution:**
```python
# Use different Redis namespaces
orchestrator_config = OrchestratorConfig(
    redis_namespace="agent_builder"
)

jarvis_config = JarvisConfig(
    redis_namespace="jarvis_business"
)
```

### Issue 3: Session ID Conflicts

**Problem:**
Sessions overlap between agent builder and Jarvis.

**Solution:**
```python
# Use prefixed session IDs
agent_session = f"agent_{session_id}"
jarvis_session = f"jarvis_{session_id}"

# Or use separate session managers
from uuid import uuid4
agent_session = f"agent_{uuid4().hex[:8]}"
jarvis_session = f"jarvis_{uuid4().hex[:8]}"
```

### Issue 4: WebSocket Message Conflicts

**Problem:**
Clients receive messages from both systems.

**Solution:**
```python
# Use mode-based message filtering
from conversation.websocket_handler import OperatingMode

# Agent builder connections
await handler.add_connection(websocket, mode=OperatingMode.AGENT_BUILDER)

# Jarvis connections  
await handler.add_connection(websocket, mode=OperatingMode.JARVIS)

# Messages automatically filtered by mode
```

### Issue 5: Configuration Override Issues

**Problem:**
Jarvis settings interfere with agent builder.

**Solution:**
```python
# Use separate configuration objects
agent_config = OrchestratorConfig.from_env()
jarvis_config = JarvisConfig(
    orchestrator_config=agent_config,
    # Jarvis-specific settings don't affect agent builder
    enable_autonomous_department_creation=True
)
```

### Issue 6: Department vs Agent Overlap

**Problem:**
Individual agents conflict with department agents.

**Solution:**
```python
# Check for existing agents before department activation
async def safe_department_activation(department_name: str):
    existing_agents = await get_active_agents(session_id)
    
    # Avoid conflicts
    department_agents = get_department_agent_types(department_name)
    conflicts = [agent for agent in existing_agents 
                if agent['type'] in department_agents]
    
    if conflicts:
        logger.warning(f"Department {department_name} conflicts with: {conflicts}")
        return False
    
    # Safe to activate
    return await activate_department(department_name)
```

### Issue 7: Performance Impact

**Problem:**
Running both systems affects performance.

**Solution:**
```python
# Implement resource management
class ResourceManager:
    def __init__(self, max_concurrent_operations=10):
        self.semaphore = asyncio.Semaphore(max_concurrent_operations)
    
    async def process_request(self, system, request, session_id):
        async with self.semaphore:
            if system == "jarvis":
                return await jarvis.process_business_request(request, session_id)
            else:
                return await orchestrator.process_request(request, session_id)
```

## Support and Next Steps

### Getting Help

1. **Documentation**: Check existing docs for agent builder functionality
2. **Examples**: Review demo modes for practical usage patterns
3. **Testing**: Use integration tests to validate migration
4. **Community**: Share migration experiences and solutions

### Best Practices

1. **Start Small**: Migrate one business process at a time
2. **Test Thoroughly**: Validate both systems work as expected
3. **Monitor Performance**: Watch for resource usage changes
4. **Document Changes**: Keep track of what's migrated and why
5. **Train Team**: Ensure team understands when to use which system

### Future Roadmap

The migration path supports gradual adoption:

- **Phase 1**: Parallel operation (current)
- **Phase 2**: Unified interface (planned)
- **Phase 3**: Intelligent routing (future)
- **Phase 4**: Full business orchestration (long-term)

### Migration Success Metrics

Track these metrics to measure migration success:

```python
# Example metrics tracking
migration_metrics = {
    "agent_builder_requests": 150,
    "jarvis_requests": 45,
    "successful_migrations": 12,
    "performance_improvement": "25%",
    "user_satisfaction": "90%",
    "business_value_delivered": "$50K savings/month"
}
```

## Conclusion

Migrating to Jarvis business orchestration is designed to be seamless and gradual. Your existing agent builder workflows continue to work unchanged, while Jarvis adds powerful business-level automation capabilities.

The dual-system approach allows you to:
- Keep using familiar agent builder patterns
- Gradually adopt business orchestration
- Leverage the best of both approaches
- Minimize migration risk and effort

Start with the demo modes to understand the differences, then gradually migrate high-value business processes when ready. The systems are designed to complement each other, not replace existing functionality.