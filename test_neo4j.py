#!/usr/bin/env python3
"""Test Neo4j connection"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')

print("=== NEO4J CONNECTION TEST ===")
print()
print(f"URI: {uri}")
print(f"User: {user}")
print(f"Password: {'*' * len(password) if password else 'Not set'}")
print()

try:
    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=True)
    
    with driver.session() as session:
        result = session.run("RETURN 'Neo4j connected!' as message")
        msg = result.single()["message"]
        print("✓ Connection successful!")
        print(f"  Message: {msg}")
        print()
        
        # Test organizational data query
        print("Testing organizational data query...")
        result = session.run("""
            MATCH (n:Entity)
            RETURN count(n) as entity_count
            LIMIT 1
        """)
        count = result.single()["entity_count"]
        print(f"✓ Found {count} entities in graph")
    
    driver.close()
    print()
    print("✓✓✓ NEO4J WORKING CORRECTLY ✓✓✓")
    
except Exception as e:
    print(f"✗ Connection failed")
    print(f"  Error: {type(e).__name__}")
    print(f"  Details: {e}")
    print()
    print("⚠️  Neo4j is not accessible - this is OK for local testing")
    print("    The framework will use Graphiti fallback")
