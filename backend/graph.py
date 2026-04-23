import os
from neo4j import AsyncGraphDatabase

class GraphDatabaseAdapter:
    def __init__(self):
        # We use environment variables for connections in a production-level system
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        await self.driver.close()

    async def upsert_pod(self, pod_name, namespace, status):
        """Merges a Pod node in the graph."""
        query = """
        MERGE (p:Pod {name: $pod_name, namespace: $namespace})
        SET p.status = $status
        """
        async with self.driver.session() as session:
            await session.run(query, pod_name=pod_name, namespace=namespace, status=status)

    async def delete_pod(self, pod_name, namespace):
        """Removes a Pod node from the graph when it is deleted in the cluster."""
        query = """
        MATCH (p:Pod {name: $pod_name, namespace: $namespace})
        DETACH DELETE p
        """
        async with self.driver.session() as session:
            await session.run(query, pod_name=pod_name, namespace=namespace)

    async def link_service_to_pod(self, service_name, pod_name, namespace):
        """Creates a relationship from a Service to a Pod."""
        query = """
        MERGE (s:Service {name: $service_name, namespace: $namespace})
        MERGE (p:Pod {name: $pod_name, namespace: $namespace})
        MERGE (s)-[:ROUTES_TO]->(p)
        """
        async with self.driver.session() as session:
            await session.run(query, service_name=service_name, pod_name=pod_name, namespace=namespace)

    async def initialize_ecommerce_topology(self):
        """Seeds the unified UI with dependencies so AI root-cause analysis is accurate."""
        print("Seeding Neo4j graph with relationships...")
        query = """
        MERGE (payment:Service {name: "payment-service"})
        MERGE (product:Service {name: "product-service"})
        MERGE (inventory:Service {name: "inventory-service"})
        MERGE (shipping:Service {name: "shipping-service"})
        MERGE (user:Service {name: "user-service"})

        MERGE (payment)-[:DEPENDS_ON]->(product)
        MERGE (payment)-[:DEPENDS_ON]->(inventory)
        MERGE (payment)-[:DEPENDS_ON]->(shipping)
        MERGE (payment)-[:DEPENDS_ON]->(user)
        """
        async with self.driver.session() as session:
            await session.run(query)

    async def get_status(self):
        """Returns the specific services and dependencies mapped in the graph."""
        node_query = "MATCH (n:Service) RETURN n.name as name"
        rel_query = "MATCH (a:Service)-[r:DEPENDS_ON]->(b:Service) RETURN a.name as from_svc, b.name as to_svc"
        
        services = []
        dependencies = []
        
        async with self.driver.session() as session:
            # Cleanup legacy pods so AI doesn't get confused
            await session.run("MATCH (p:Pod) DETACH DELETE p")
            
            node_result = await session.run(node_query)
            async for record in node_result:
                services.append(record["name"])
                
            rel_result = await session.run(rel_query)
            async for record in rel_result:
                dependencies.append({"from": record["from_svc"], "to": record["to_svc"]})
            
        return {
            "services": services,
            "dependencies": dependencies
        }

    async def get_topology(self):
        """Fetches the cluster topology for the 3D UI."""
        # This is a simple query returning nodes and simple links.
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
        """
        nodes = {}
        links = []
        async with self.driver.session() as session:
            result = await session.run(query)
            async for record in result:
                n = record["n"]
                if n:
                    nodes[n.element_id] = {
                        "id": n.element_id, 
                        "labels": list(n.labels), 
                        "properties": dict(n.items())
                    }
                
                m = record["m"]
                if m:
                    nodes[m.element_id] = {
                        "id": m.element_id, 
                        "labels": list(m.labels), 
                        "properties": dict(m.items())
                    }
                
                r = record["r"]
                if r:
                    links.append({
                        "source": r.start_node.element_id,
                        "target": r.end_node.element_id,
                        "type": r.type
                    })
        return {
            "nodes": list(nodes.values()),
            "links": links
        }

graph_db = GraphDatabaseAdapter()
