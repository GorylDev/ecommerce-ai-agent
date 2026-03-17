import os
import psycopg2
from langchain_google_genai import GoogleGenerativeAIEmbeddings

TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:supersecretpassword@postgres:5432/saas_db")

POLICY_CHUNKS = [
    "Zwroty są darmowe i można ich dokonać do 14 dni od daty otrzymania przesyłki.",
    "Zwracany produkt musi znajdować się w oryginalnym opakowaniu i nie nosić śladów użytkowania.",
    "Pieniądze za zatwierdzony zwrot są odsyłane na konto klienta w ciągu 7 dni roboczych.",
    "Produkty personalizowane (np. buty z grawerem na zamówienie) nie podlegają zwrotom.",
    "W przypadku otrzymania uszkodzonego towaru, klient musi załączyć zdjęcia wady w pierwszej wiadomości reklamacyjnej."
]

def main():
    print("Inicjalizacja wektorowej bazy wiedzy (RAG - Google Gemini)...")
    
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM tenants WHERE id = %s", (TENANT_ID,))
        if cursor.fetchone() is None:
            print(f"Tworzenie konta dla sklepu (Tenant ID: {TENANT_ID})...")
            cursor.execute(
                "INSERT INTO tenants (id, name, webhook_secret) VALUES (%s, %s, %s)",
                (TENANT_ID, "Testowy Sklep Obuwniczy", "super_secret_key_from_db")
            )
        
        cursor.execute("DELETE FROM knowledge_base WHERE tenant_id = %s", (TENANT_ID,))

        for chunk in POLICY_CHUNKS:
            print(f"Wektoryzacja: {chunk[:40]}...")
            vector = embeddings_model.embed_query(chunk)
            cursor.execute(
                "INSERT INTO knowledge_base (tenant_id, content, embedding) VALUES (%s, %s, %s)",
                (TENANT_ID, chunk, vector)
            )
        
        conn.commit()
        print("Sukces. Regulamin został zwektoryzowany przez Gemini.")
        
    except Exception as e:
        conn.rollback()
        print(f"Wystąpił błąd bazy danych: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()