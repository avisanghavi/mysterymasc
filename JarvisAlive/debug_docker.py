#!/usr/bin/env python3
"""Debug Docker build issues."""

import docker
import sys
from pathlib import Path

def test_docker_build():
    """Test building the Docker image manually."""
    
    print("🔍 Testing Docker build...")
    
    try:
        client = docker.from_env()
        print("✅ Docker client connected")
        
        # Test basic Docker functionality
        print("🐳 Testing Docker daemon...")
        client.ping()
        print("✅ Docker daemon responding")
        
        # Check if we have the build context
        dockerfile_dir = Path("agent_builder/docker")
        if not dockerfile_dir.exists():
            print(f"❌ Build directory not found: {dockerfile_dir}")
            return False
        
        dockerfile_path = dockerfile_dir / "Dockerfile.agent"
        requirements_path = dockerfile_dir / "requirements.txt"
        base_agent_path = dockerfile_dir / "base_agent.py"
        
        print(f"📁 Build context: {dockerfile_dir}")
        print(f"   Dockerfile: {'✅' if dockerfile_path.exists() else '❌'}")
        print(f"   requirements.txt: {'✅' if requirements_path.exists() else '❌'}")
        print(f"   base_agent.py: {'✅' if base_agent_path.exists() else '❌'}")
        
        if not all([dockerfile_path.exists(), requirements_path.exists(), base_agent_path.exists()]):
            print("❌ Missing required files")
            return False
        
        # Try to build the image
        print("\n🔨 Building Docker image...")
        print("This may take a few minutes...")
        
        image, logs = client.images.build(
            path=str(dockerfile_dir),
            dockerfile="Dockerfile.agent",
            tag="heyjarvis-agent-test:latest",
            rm=True,
            forcerm=True
        )
        
        print("\n📋 Build logs:")
        for log in logs:
            if 'stream' in log:
                print(f"   {log['stream'].strip()}")
            elif 'error' in log:
                print(f"   ERROR: {log['error']}")
        
        print(f"\n✅ Image built successfully: {image.id[:12]}")
        
        # Test running a simple command in the container
        print("\n🧪 Testing container...")
        container = client.containers.run(
            "heyjarvis-agent-test:latest",
            command="python -c 'print(\"Container works!\")'",
            remove=True,
            detach=False
        )
        
        print(f"✅ Container test output: {container.decode().strip()}")
        
        # Cleanup test image
        client.images.remove("heyjarvis-agent-test:latest", force=True)
        print("✅ Test image cleaned up")
        
        return True
        
    except docker.errors.BuildError as e:
        print(f"\n❌ Docker build failed:")
        print(f"Error: {e}")
        
        # Print detailed build logs
        if hasattr(e, 'build_log'):
            print("\n📋 Detailed build logs:")
            for log in e.build_log:
                if 'stream' in log:
                    print(f"   {log['stream'].strip()}")
                elif 'error' in log:
                    print(f"   ERROR: {log['error']}")
        
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def test_requirements():
    """Test if requirements can be installed locally."""
    
    print("\n🐍 Testing requirements locally...")
    
    try:
        import subprocess
        
        # Read requirements
        req_file = Path("agent_builder/docker/requirements.txt")
        if not req_file.exists():
            print("❌ requirements.txt not found")
            return False
        
        with open(req_file) as f:
            requirements = f.read()
        
        print("📦 Requirements to install:")
        for line in requirements.split('\n'):
            if line.strip() and not line.startswith('#'):
                print(f"   {line.strip()}")
        
        # Try to resolve dependencies (dry run)
        print("\n🔍 Testing pip resolution...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '--dry-run', '-r', str(req_file)
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Requirements can be resolved")
        else:
            print("❌ Requirements resolution failed:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Failed to test requirements: {e}")
        return False

if __name__ == "__main__":
    print("🔧 HeyJarvis Docker Debug Tool")
    print("=" * 40)
    
    # Test requirements first
    req_ok = test_requirements()
    
    # Test Docker build
    build_ok = test_docker_build()
    
    print("\n" + "=" * 40)
    if req_ok and build_ok:
        print("🎉 All tests passed! Docker build should work.")
    else:
        print("❌ Some tests failed. Check the output above for details.")
        
        if not req_ok:
            print("\n💡 Try simplifying requirements.txt")
            
        if not build_ok:
            print("\n💡 Suggestions:")
            print("   • Check Docker has enough memory (4GB+ recommended)")
            print("   • Try: docker system prune -f")
            print("   • Check internet connection for package downloads")