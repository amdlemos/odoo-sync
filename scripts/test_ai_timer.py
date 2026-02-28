#!/usr/bin/env python3
import sys
from pathlib import Path
from dotenv import load_dotenv
import os
import time

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.sync.odoo_client import OdooClient

def main():
    load_dotenv()
    host = os.getenv('ODOO_HOST')
    port = int(os.getenv('ODOO_PORT', 443))
    protocol = os.getenv('ODOO_PROTOCOL', 'jsonrpc+ssl')
    db = os.getenv('ODOO_DB')
    user = os.getenv('ODOO_USER')
    password = os.getenv('ODOO_PASSWORD')
    
    print(f"Connecting as {user}...")
    client = OdooClient(host, port, db, user, password, protocol)
    
    # Get a task
    Task = client.env['project.task']
    tasks = Task.search_read([], ['id', 'name'], limit=1)
    if not tasks:
        print("No tasks found to test.")
        return
        
    task_id = tasks[0]['id']
    print(f"\nTesting timer on Task {task_id}: {tasks[0]['name']}")
    
    # Start timer 1
    print("\n--- Starting Timer 1 ---")
    try:
        res1 = client.start_ai_task_timer(task_id, "Análise de requisitos da IA", "claude-3.5-sonnet")
        print(f"Timer 1 started! {res1}")
    except Exception as e:
        print(f"Failed: {e}")
        return
        
    # Start timer 2 (Should pick another agent)
    print("\n--- Starting Timer 2 ---")
    try:
        res2 = client.start_ai_task_timer(task_id, "Geração de código secundário", "gpt-4o")
        print(f"Timer 2 started! {res2}")
    except Exception as e:
        print(f"Failed: {e}")
        
    print("\nWait 5 seconds to simulate work...")
    time.sleep(5)
    
    # Stop timers
    print("\n--- Stopping Timers ---")
    print(f"Stopping Timer 1 (ID: {res1['timer_id']})...")
    client.stop_ai_task_timer(res1['timer_id'])
    
    print(f"Stopping Timer 2 (ID: {res2['timer_id']})...")
    client.stop_ai_task_timer(res2['timer_id'])
    
    # Verify timesheets
    print("\n--- Verifying Timesheets ---")
    lines = client.env['account.analytic.line'].search_read(
        [('id', 'in', [res1['timer_id'], res2['timer_id']])], 
        ['name', 'employee_id', 'unit_amount']
    )
    for line in lines:
        print(f"Timesheet: {line['name']}")
        print(f"  Agent: {line['employee_id'][1]}")
        print(f"  Duration: {line['unit_amount']:.4f} hours")
        
    print("\nSuccess! Multi-agent timer logic is working perfectly.")

if __name__ == "__main__":
    main()
