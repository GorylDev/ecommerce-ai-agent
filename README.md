# E-Commerce Agent

Zaawansowany, wielodostępny agent AI do automatyzacji obsługi klienta (zwroty, reklamacje) w e-commerce. Zbudowany z wykorzystaniem LangGraph, Google Gemini i bramki wejściowej napisanej w Go.

---

## Architektura Systemu

Projekt opiera się na mikrousługach asynchronicznych, co zapewnia skalowalnośc i odporność na przeciążenia (np. Black friday)

1. **Ingress Gateway (Go):** Szybki mikroserwis przyjmujący webhooki ze sklepów internetowych. Weryfikuje zabezpieczenia przed spoofingiem i przekazuje wiadomości na szynę.
2. **NATS:** Gwarantuje niezawodne dostarczanie wiadomości między bramką, a logiką AI, będąc buforem bezpieczeństwa.
3. **Baza danych (PostgreSQL + pgvector):** Przechowuje regulaminy sklepów i bilety. Wykorzystuje **Row Level Security** dla sprzętowej izolacji danych między różnymi klientami.
4. **AI (Python + LangGraph):** Agent przetwarzający zgłoszenia w 3etapowym cyklu:
   - **RAG:** Wyszukiwanie odpowiednich punktów regulaminu dla danego sklepu,
   - **Reasoning:** Analiza i decyzja biznesowej przy użyciu `gemini-2.5 flash`.
   - **Generation:** Generowanie spersonalizowanej, uprzejmej odpowiedzi dla klienta.

## 🚀 Technologie

* **Bramka API:** Go, Fiber
* **Logika AI:** Python, LangChain, LangGraph
* **Broker wiadomości:** NATS
* **Baza danych:** PostgreSQL z rozszerzeniem `pgvector`
* **Infrastruktura:** Docker, Docker Compose
