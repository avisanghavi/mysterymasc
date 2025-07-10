# HeyJarvis Demo Interface

A beautiful, interactive web interface for demonstrating HeyJarvis sales automation capabilities.

## Features

### 🎯 **Core Functionality**
- **Real-time Progress Tracking**: WebSocket-based live updates during processing
- **Interactive Demo Scenarios**: Pre-configured examples for different use cases
- **Beautiful UI**: Modern, responsive design with dark theme
- **Export Capabilities**: Download results in JSON or CSV format
- **Mobile Responsive**: Works on desktop, tablet, and mobile devices

### 📊 **Demo Scenarios**
1. **Quick Lead Generation**: Find 10 qualified B2B SaaS leads
2. **Executive Outreach**: Find and prepare outreach to C-level executives
3. **Quick Wins Analysis**: Identify the 5 best prospects to contact right now
4. **Full Outreach Campaign**: Complete campaign from lead finding to message preparation

### 🛠 **Technical Features**
- **FastAPI Backend**: High-performance async API
- **WebSocket Support**: Real-time bidirectional communication
- **Mock Data Integration**: Realistic demo data generation
- **Progress Visualization**: Step-by-step process tracking
- **Error Handling**: Graceful error handling and user feedback

## Quick Start

### Prerequisites
```bash
pip install fastapi uvicorn websockets pydantic python-multipart
```

### Running the Demo
```bash
# Option 1: Direct run
python3 app.py

# Option 2: Using the runner script
python3 run_demo.py

# Option 3: Using uvicorn directly
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Testing
```bash
python3 test_demo.py
```

## Usage

1. **Open your browser** to `http://localhost:8000`
2. **Choose a demo scenario** from the sidebar or enter a custom request
3. **Click "Process"** to start the demonstration
4. **Watch real-time progress** as the system processes your request
5. **View results** including leads, metrics, and recommendations
6. **Export results** in JSON or CSV format

## API Endpoints



### Core Endpoints
- `GET /` - Main demo interface
- `GET /api/health` - Health check
- `GET /api/scenarios` - Available demo scenarios
- `POST /api/process` - Process a business request
- `GET /api/export/{session_id}` - Export session results
- `WS /ws/{session_id}` - WebSocket for real-time updates

### Example API Usage
```python
import requests

# Get demo scenarios
scenarios = requests.get("http://localhost:8000/api/scenarios").json()

# Process a request
response = requests.post("http://localhost:8000/api/process", json={
    "request": "Find me 10 SaaS leads with 50-200 employees"
})
session_id = response.json()["session_id"]

# Export results (after processing completes)
results = requests.get(f"http://localhost:8000/api/export/{session_id}")
```

## Architecture

### Frontend Components
- **HTML Interface**: Single-page application with modern CSS
- **JavaScript**: WebSocket handling, progress updates, result visualization
- **Responsive Design**: Works on all screen sizes

### Backend Components
- **FastAPI Application**: High-performance async web framework
- **WebSocket Handler**: Real-time communication
- **Mock Data Generator**: Realistic demo data
- **Progress Tracker**: Step-by-step process updates

### Data Flow
1. User submits request through web interface
2. FastAPI receives request and starts background processing
3. Progress updates sent via WebSocket
4. Results generated and displayed in real-time
5. Export functionality available for completed sessions

## Customization

### Adding New Demo Scenarios
Edit the `get_demo_scenarios()` function in `app.py`:

```python
DemoScenario(
    id="custom_scenario",
    name="Custom Scenario",
    description="Your scenario description",
    example_request="Your example request",
    expected_duration="30-45 seconds"
)
```

### Modifying UI Styling
The CSS is embedded in the HTML template. Key classes:
- `.scenario` - Demo scenario cards
- `.progress-step` - Progress tracking steps
- `.result-card` - Result display cards
- `.metric` - Metric display components

### Extending API
Add new endpoints to the FastAPI app:

```python
@app.get("/api/custom")
async def custom_endpoint():
    return {"message": "Custom functionality"}
```

## Integration with Enhanced Jarvis

The demo interface is designed to integrate with the enhanced Jarvis system:

```python
# Enable real Jarvis integration
JARVIS_AVAILABLE = True

# Initialize Jarvis in process_request_background
jarvis = Jarvis(jarvis_config)
await jarvis.initialize()
result = await jarvis.process_sales_request(request, session_id)
```

## Production Deployment

### Environment Variables
```bash
export ANTHROPIC_API_KEY="your_api_key"
export REDIS_URL="redis://localhost:6379"
export PORT=8000
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- Use Redis for session storage instead of in-memory
- Add authentication and rate limiting
- Enable HTTPS with proper SSL certificates
- Use environment-specific configurations
- Add logging and monitoring

## Troubleshooting

### Common Issues
1. **WebSocket connection fails**: Check firewall settings and port availability
2. **Import errors**: Ensure all dependencies are installed
3. **Slow progress updates**: Mock processing includes delays for demonstration
4. **Export not working**: Results are only available after processing completes

### Debug Mode
Set `debug=True` in uvicorn configuration for detailed error messages:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload --debug
```

## License

This demo interface is part of the HeyJarvis project and follows the same licensing terms.