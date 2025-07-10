# HubSpot LeadScannerAgent Integration

Enhanced LeadScannerAgent with real HubSpot CRM data integration for superior lead discovery and scoring.

## Features

### 🔗 **Real HubSpot Integration**
- **Live CRM Data**: Access real contacts, companies, and deals
- **Advanced Search**: Filter by title, industry, company size, activity
- **Activity Scoring**: Email engagement, website visits, deal history
- **Secure Credentials**: OAuth token management via Supabase

### 📊 **Enhanced Scoring**
- **Base Scoring**: Industry match, title relevance, company fit
- **Activity Bonus**: Email opens, clicks, page views, recent contact
- **Deal Intelligence**: Open deals, closed won history
- **Lifecycle Stage**: Lead qualification status

### 🚀 **Performance & Reliability**
- **Redis Caching**: 1-hour cache for search results
- **Rate Limiting**: 10 requests/second compliance
- **Graceful Fallback**: Auto-fallback to mock data
- **Error Handling**: Comprehensive retry logic

## Quick Start

### 1. Install Dependencies

```bash
pip install hubspot-api-client redis supabase cryptography tenacity
```

### 2. Set Up Environment

```bash
# Supabase Configuration
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
export ENCRYPTION_KEY="your-base64-fernet-key"

# Redis Configuration
export REDIS_URL="redis://localhost:6379"

# HubSpot OAuth (configured in Supabase)
export HUBSPOT_CLIENT_ID="your-hubspot-client-id"
export HUBSPOT_CLIENT_SECRET="your-hubspot-client-secret"
```

### 3. Initialize with HubSpot Mode

```python
from lead_scanner_implementation import LeadScannerAgent, ScanCriteria

# Initialize with HubSpot integration
agent = LeadScannerAgent(
    mode="hubspot",
    config={
        'user_id': 'your_user_id',  # Must have HubSpot credentials in Supabase
        'supabase_url': 'https://your-project.supabase.co',
        'supabase_key': 'your-anon-key',
        'encryption_key': 'your-encryption-key',
        'redis_url': 'redis://localhost:6379'
    }
)

# Define search criteria
criteria = ScanCriteria(
    industries=["SaaS", "Technology", "Software"],
    titles=["VP Sales", "Director of Sales", "Sales Manager"],
    company_sizes=["51-200", "201-500"],
    min_score=75,
    max_results=20
)

# Scan for leads
leads = await agent.scan_for_leads(criteria)
```

## Usage Examples

### Basic Lead Scanning

```python
# Find VP-level sales contacts at mid-size SaaS companies
criteria = ScanCriteria(
    industries=["SaaS", "Software"],
    titles=["VP Sales", "VP Revenue", "Chief Revenue Officer"],
    company_sizes=["51-200", "201-500"],
    min_score=70,
    max_results=15
)

leads = await agent.scan_for_leads(criteria)

for lead in leads:
    print(f"{lead.contact.full_name} - {lead.contact.title}")
    print(f"Company: {lead.company.name} ({lead.company.employee_count} employees)")
    print(f"Score: {lead.score.total_score}/100")
    print(f"Priority: {lead.outreach_priority}")
    
    # HubSpot-specific data
    if lead.enrichment_data:
        print(f"HubSpot ID: {lead.enrichment_data['hubspot_id']}")
        print(f"Lifecycle: {lead.enrichment_data['lifecycle_stage']}")
        email_data = lead.enrichment_data['email_engagement']
        print(f"Email Opens: {email_data['opens']}")
    print("---")
```

### Advanced Filtering

```python
# Target enterprise CTOs with recent activity
criteria = ScanCriteria(
    industries=["Financial Services", "Healthcare", "Enterprise Software"],
    titles=["CTO", "Chief Technology Officer", "VP Engineering"],
    company_sizes=["501-1000", "1001+"],
    min_score=85,  # High-quality only
    max_results=10
)

leads = await agent.scan_for_leads(criteria)
```

### Mode Comparison

```python
# Compare different modes
modes = ["mock", "hubspot"]
results = {}

for mode in modes:
    agent = LeadScannerAgent(mode=mode, config=config)
    leads = await agent.scan_for_leads(criteria)
    results[mode] = leads
    
    print(f"{mode.title()} Mode: {len(leads)} leads")
    if leads:
        avg_score = sum(l.score.total_score for l in leads) / len(leads)
        print(f"Average Score: {avg_score:.1f}")
```

## Enhanced Scoring

The HubSpot integration enhances lead scoring with real activity data:

### Base Scoring (0-80 points)
- **Industry Match**: 0-30 points
- **Title Relevance**: 0-30 points  
- **Company Size Fit**: 0-20 points

### Activity Bonus (0-20 points)
- **Email Engagement**: Opens, clicks, engagement score
- **Website Activity**: Page views, visits, time on site
- **Recent Contact**: Last contacted date
- **Deal History**: Open deals, closed won deals

### Example Enhanced Score
```python
# Base score from traditional criteria
base_score = 65

# HubSpot activity enhancements
email_opens = 25      # +10 points
recent_contact = 15   # +5 points (contacted 15 days ago)
open_deals = 1        # +10 points
lifecycle = "SQL"     # +5 points

# Enhanced total: 95/100
enhanced_score = min(100, base_score + 30)
```

## Caching Strategy

### Redis Cache Keys
```
hubspot:contacts_search:{hash_of_params}
hubspot:companies:{hash_of_params}
hubspot:contact:{contact_id}
```

### Cache Behavior
- **TTL**: 1 hour (3600 seconds)
- **Invalidation**: On new contact creation
- **Performance**: 10x faster cached searches

### Cache Management
```python
# Clear cache for fresh results
await agent.hubspot_client._invalidate_cache_pattern("contacts_search")

# Check cache status
cache_key = agent.hubspot_client._cache_key("contacts_search", params)
cached_data = await agent.hubspot_client._get_from_cache(cache_key)
is_cached = cached_data is not None
```

## Error Handling

### Graceful Fallbacks
1. **No HubSpot Credentials**: Falls back to mock mode
2. **API Errors**: Retries with exponential backoff
3. **Rate Limits**: Waits for retry-after period
4. **Network Issues**: Uses cached data when available

### Error Examples
```python
try:
    leads = await agent.scan_for_leads(criteria)
except Exception as e:
    # System automatically falls back to mock data
    logger.warning(f"HubSpot error, using mock data: {e}")
```

### Monitoring
```python
# Check current mode
print(f"Current mode: {agent.mode}")

# Verify HubSpot connection
if agent.hubspot_client:
    print("✅ HubSpot connected")
else:
    print("❌ Using mock data")
```

## Performance Optimization

### Best Practices
1. **Use Caching**: First search is slow, subsequent are fast
2. **Batch Operations**: Process multiple leads together
3. **Limit Results**: Use reasonable `max_results` values
4. **Filter Early**: Apply industry/size filters first

### Performance Metrics
```python
import time

start_time = time.time()
leads = await agent.scan_for_leads(criteria)
duration = time.time() - start_time

print(f"Found {len(leads)} leads in {duration:.2f}s")
# First run: ~5-10s (API calls)
# Cached run: ~0.1-0.5s (Redis)
```

## Testing

### Run Test Suite
```bash
python test_hubspot_lead_scanner.py
```

### Test Coverage
- ✅ Mock mode functionality
- ✅ HubSpot mode with credentials
- ✅ Error handling and fallbacks
- ✅ Caching behavior
- ✅ Scoring enhancements
- ✅ Rate limiting compliance

### Manual Testing
```python
# Test different scenarios
test_cases = [
    {"industries": ["SaaS"], "titles": ["CEO"]},
    {"company_sizes": ["1-10"], "min_score": 90},
    {"industries": ["Healthcare"], "titles": ["CTO", "VP Engineering"]},
]

for i, test_case in enumerate(test_cases):
    criteria = ScanCriteria(**test_case, max_results=5)
    leads = await agent.scan_for_leads(criteria)
    print(f"Test {i+1}: {len(leads)} leads")
```

## Integration Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  LeadScanner    │    │    HubSpot       │    │   Supabase      │
│     Agent       │───▶│  Integration     │───▶│  Auth Manager   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                        │
         │                       ▼                        │
         │              ┌─────────────────┐               │
         │              │     Redis       │               │
         │              │    Cache        │               │
         │              └─────────────────┘               │
         │                                                │
         ▼                                                ▼
┌─────────────────┐                            ┌─────────────────┐
│   Mock Data     │                            │  OAuth Tokens   │
│   (Fallback)    │                            │  (Encrypted)    │
└─────────────────┘                            └─────────────────┘
```

## Production Deployment

### Environment Setup
```bash
# Production environment variables
export NODE_ENV=production
export REDIS_URL="redis://production-redis:6379"
export SUPABASE_URL="https://prod-project.supabase.co"
```

### Monitoring
```python
# Add monitoring to track usage
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Track API usage
await agent.auth_manager._track_usage(
    user_id=user_id,
    service="hubspot",
    action="lead_scan"
)

# Monitor performance
logger.info(f"Lead scan completed: {len(leads)} leads in {duration:.2f}s")
```

### Security Considerations
1. **Encrypted Storage**: All tokens encrypted with Fernet
2. **Row Level Security**: Users can only access their own data
3. **Token Rotation**: Automatic refresh of expired tokens
4. **Audit Logging**: All API calls logged for security

## Troubleshooting

### Common Issues

**No leads found**
```python
# Check credentials
credential = await agent.auth_manager.get_credentials(user_id, "hubspot")
if not credential:
    print("❌ No HubSpot credentials found")

# Check API quota
print(f"Rate limiter: {agent.hubspot_client.rate_limiter._value} requests available")
```

**Slow performance**
```python
# Check cache hit rate
cache_hits = 0
total_requests = 0

# Enable cache debugging
import logging
logging.getLogger("hubspot_integration").setLevel(logging.DEBUG)
```

**API errors**
```python
# Check HubSpot API status
try:
    health = await agent.hubspot_client.api_client.crm.contacts.basic_api.get_page(limit=1)
    print("✅ HubSpot API accessible")
except Exception as e:
    print(f"❌ HubSpot API error: {e}")
```

## Future Enhancements

### Planned Features
- [ ] Custom property mapping
- [ ] Workflow automation triggers
- [ ] Lead scoring ML models
- [ ] Multi-portal support
- [ ] Advanced analytics dashboard

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## License

Part of the HeyJarvis project. See main project license.