# HeyJarvis Quick Start Guide

## Prerequisites

1. **Python 3.11+** - Check with: `python --version`
2. **Docker** - Install from [docker.com](https://docker.com)
3. **Redis** - For session storage

## Step 1: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or if you prefer virtual environment:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Start Redis (Required)

Choose one option:

### Option A: Using Docker (Recommended)
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

### Option B: Using Homebrew (Mac)
```bash
brew install redis
brew services start redis
```

### Option C: Using apt (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

## Step 3: Verify Docker is Running

```bash
docker --version
docker ps
```

## Step 4: Run HeyJarvis

### Interactive Chat Mode (Recommended)
```bash
python main.py
```

### Demo Mode (See all features)
```bash
python main.py --demo
```

## Step 5: Test Commands

Once running, try these commands:

```
# Create an email monitoring agent
Monitor my email for urgent messages

# Create a file backup agent
Create a daily backup agent for my documents

# Create a social media agent
Set up social media automation for Twitter

# View sessions
sessions

# Resume interrupted work
continue

# Exit
exit
```

## What Happens When You Run It?

1. **Initialization**: Connects to Redis and OpenAI
2. **Docker Setup**: Builds secure agent containers
3. **Chat Interface**: Interactive conversation with HeyJarvis
4. **Agent Creation**: Converts your requests to working Python code
5. **Sandbox Execution**: Runs agents safely in Docker containers

## Troubleshooting

### "Redis connection failed"
- Start Redis: `docker run -d --name redis -p 6379:6379 redis:latest`
- Check if running: `docker ps`

### "Docker not found"
- Install Docker from docker.com
- Start Docker Desktop
- Verify: `docker --version`

### "Anthropic API error"
- Check your API key in `.env`
- Ensure you have credits: https://console.anthropic.com/settings/billing

### "Permission denied"
- Make sure Docker is running
- Try: `sudo docker ps` (Linux)

## Example Session

```
$ python main.py

💬 HeyJarvis: Hi! I can help you create automation agents. What would you like to automate?

You: Monitor my email for urgent messages

📊 Progress: 20% - 🔍 Understanding your request...
📊 Progress: 40% - 🤔 Analyzing intent...
📊 Progress: 60% - 🔎 Checking existing agents...
📊 Progress: 80% - 🛠️ Creating your agent...
📊 Progress: 100% - 🚀 Deploying agent...

✅ Success! I've created 'Email Monitor Agent' for you.
It will: Monitor Gmail inbox for urgent messages and send alerts
Capabilities:
  • email_monitoring
  • alert_sending

💬 What else would you like to automate?
```

## Advanced Features

- **Session Recovery**: Resume interrupted agent creation
- **Clarification Flow**: HeyJarvis asks questions for unclear requests
- **Resource Monitoring**: Real-time container stats
- **Multi-step Creation**: Build complex agents through conversation
- **Error Handling**: Graceful recovery from failures

## Next Steps

1. Start with simple agents (email monitoring, file backup)
2. Try the demo mode to see all features
3. Experiment with complex multi-capability agents
4. Use `sessions` command to manage multiple agents
5. Check logs in Docker containers for debugging

Happy automating! 🚀