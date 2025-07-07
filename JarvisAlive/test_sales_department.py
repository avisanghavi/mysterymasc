#!/usr/bin/env python3
"""Test the Sales Department functionality."""

import asyncio
import redis.asyncio as redis
from departments.sales.sales_department import SalesDepartment

async def test_sales_department():
    # Initialize Redis connection
    redis_client = redis.from_url("redis://localhost:6379")
    
    try:
        # Create Sales Department
        sales = SalesDepartment(redis_client, "test_session")
        
        # Initialize agents
        print("Initializing agents...")
        success = await sales.initialize_agents()
        print(f"Agent initialization: {'Success' if success else 'Failed'}")
        
        # Execute workflow
        print("\nExecuting lead generation workflow...")
        result = await sales.execute_workflow({"workflow_type": "lead_generation"})
        print(f"Workflow result: {result}")
        
        # Check department status
        print("\nDepartment status:")
        status = await sales.get_status()
        print(f"Status: {status}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await redis_client.close()

if __name__ == "__main__":
    # Make sure Redis is running first!
    print("Testing Sales Department...")
    print("Make sure Redis is running (redis-server)")
    asyncio.run(test_sales_department())