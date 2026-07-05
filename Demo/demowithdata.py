import json
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


# -------- STEP 1: LOAD DATA --------
with open("data.json") as f:
    data = json.load(f)


# -------- STEP 2: BUILD GRAPH --------
def create_graph(tx, record):
    tx.run("""
    MERGE (p:Policy {name: $policy})
    MERGE (c:Claim {id: $claim_id, amount: $amount, type: $type})
    MERGE (u:Customer {name: $customer})

    MERGE (p)-[:COVERS]->(c)
    MERGE (c)-[:BELONGS_TO]->(u)
    """,
    policy=record["policy"],
    claim_id=record["claim_id"],
    amount=record["amount"],
    type=record["type"],
    customer=record["customer"]
    )


# -------- STEP 3: INSERT DATA --------
with driver.session() as session:
    for record in data:
        session.execute_write(create_graph, record)


# -------- STEP 4: GRAPH QUERY --------
def query_claim(tx, claim_id):
    result = tx.run("""
    MATCH (p:Policy)-[:COVERS]->(c:Claim {id: $claim_id})-[:BELONGS_TO]->(u:Customer)
    RETURN p.name AS policy, u.name AS customer, c.amount AS amount
    """, claim_id=claim_id)

    return [dict(record) for record in result]


# -------- STEP 5: RAG STYLE FUNCTION --------
def rag_with_graph(query, claim_id):
    with driver.session() as session:
        results = session.execute_read(query_claim, claim_id)

    context = ""
    for r in results:
        context += f"Policy: {r['policy']}, Customer: {r['customer']}, Amount: {r['amount']}\n"

    final_prompt = f"""
Context:
{context}

Question:
{query}

Answer:
"""

    return final_prompt


# -------- STEP 6: RUN --------
if __name__ == "__main__":
    query = "What policy and customer are associated with this claim?"
    claim_id = "CLM001"

    output = rag_with_graph(query, claim_id)

    print(output)

    driver.close()