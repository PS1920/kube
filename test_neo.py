import asyncio
from backend.graph import graph_db

async def main():
    topology = await graph_db.get_topology()
    print(f"Nodes in Neo4j: {len(topology['nodes'])}")
    for node in topology['nodes']:
        print("-", node.get("properties", {}).get("name", "Unknown"))

asyncio.run(main())
