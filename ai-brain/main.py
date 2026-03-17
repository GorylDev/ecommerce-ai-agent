import asyncio
import json
import os
from typing import TypedDict
from nats.aio.client import Client as NATS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
import psycopg2

class TicketState(TypedDict):
    tenant_id: str
    customer_email: str
    message: str
    policy_context: str
    decision: str
    final_response: str

# 1. Inicjalizacja LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

# 2. Inicjalizacja modelu wektorowego
embeddings_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

nats_client = NATS()
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:supersecretpassword@postgres:5432/saas_db")

def fetch_policy(state: TicketState) -> TicketState:
    tenant_id = state["tenant_id"]
    print(f"[{tenant_id}] Tworzenie wektora z maila: {state['message'][:40]}...")
    
    try:
        query_vector = embeddings_model.embed_query(state["message"])
        
        print(f"[{tenant_id}] Wyszukiwanie...")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT content 
            FROM knowledge_base 
            WHERE tenant_id = %s 
            ORDER BY embedding <=> %s::vector 
            LIMIT 2
            """,
            (tenant_id, query_vector)
        )
        
        results = cursor.fetchall()
        
        if results:
            state["policy_context"] = " ".join([row[0] for row in results])
            print(f"[{tenant_id}] Znaleziono odpowiedni regulamin")
        else:
            state["policy_context"] = "Brak specyficznego regulaminu dla tego sklepu."
            
    except Exception as e:
        print(f"[{tenant_id}] Błąd bazy danych: {e}")
        state["policy_context"] = "Błąd pobierania"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        
    return state

def decide_action(state: TicketState) -> TicketState:
    system_prompt = SystemMessage(
        content=f"Jesteś agentem obsługi zwrotów. Regulamin sklepu: {state['policy_context']}. "
                f"Zdecyduj o akcji: ZWROT_AKCEPTACJA, ZWROT_ODRZUCONY, BRAK_DANYCH."
    )
    user_prompt = HumanMessage(content=state["message"])
    
    response = llm.invoke([system_prompt, user_prompt])
    state["decision"] = response.content
    return state

def generate_reply(state: TicketState) -> TicketState:
    prompt = SystemMessage(
        content=f"Napisz oficjalną, uprzejmą wiadomość e-mail do klienta informującą o decyzji: {state['decision']}."
    )
    response = llm.invoke([prompt, HumanMessage(content=state["message"])])
    state["final_response"] = response.content
    return state

workflow = StateGraph(TicketState)
workflow.add_node("fetch_policy", fetch_policy)
workflow.add_node("decide_action", decide_action)
workflow.add_node("generate_reply", generate_reply)

workflow.set_entry_point("fetch_policy")
workflow.add_edge("fetch_policy", "decide_action")
workflow.add_edge("decide_action", "generate_reply")
workflow.add_edge("generate_reply", END)

app_graph = workflow.compile()

async def process_message(msg):
    data = json.loads(msg.data.decode())
    print(f"\nNOWE ZGŁOSZENIE")
    print(f"Od: {data['customer_email']}")
    
    initial_state = TicketState(
        tenant_id=data["tenant_id"],
        customer_email=data["customer_email"],
        message=data["message"],
        policy_context="",
        decision="",
        final_response=""
    )
    
    final_state = app_graph.invoke(initial_state)
    
    print(f"Decyzja Agenta: {final_state['decision']}")
    print(f"Wygenerowana odpowiedź: {final_state['final_response']}\n")

async def main():
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    await nats_client.connect(nats_url)
    await nats_client.subscribe("ticket.incoming", cb=process_message)
    print("Agent start. Listening NATS...")
    
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())