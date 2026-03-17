import hmac
import hashlib
import json
import urllib.request
import urllib.error

# Konfiguracja - musi zgadzać się z tym, co mamy w ingress/main.go
SECRET_KEY = b'super_secret_key_from_db'
URL = 'http://localhost:3000/webhook/incoming-ticket'

# Symulacja maila z reklamacją/zwrotem ze sklepu
payload = {
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "customer_email": "jan.biznesowy@example.com",
    "message": "Dzień dobry, kupiłem u państwa buty 5 dni temu. Niestety są za małe. Chciałbym dokonać zwrotu, produkt jest w oryginalnym pudełku. Jakie są kolejne kroki?",
    "order_id": "ORD-2026-8819"
}

# 1. Serializacja do JSON i kodowanie do bajtów
body = json.dumps(payload).encode('utf-8')

# 2. Generowanie sygnatury HMAC-SHA256
signature = hmac.new(SECRET_KEY, body, hashlib.sha256).hexdigest()

print(f"Wysyłam zgłoszenie dla: {payload['customer_email']}")
print(f"Wygenerowana sygnatura: {signature}\n")

# 3. Budowa żądania HTTP
req = urllib.request.Request(URL, data=body, method='POST')
req.add_header('Content-Type', 'application/json')
req.add_header('X-Ecommerce-Signature', signature)

# 4. Egzekucja
try:
    with urllib.request.urlopen(req) as response:
        print(f"Sukces!. Kod odpowiedzi API: {response.status}")
        print("Bramka Go przyjęła żądanie i wrzuciła je na szynę NATS.")
except urllib.error.HTTPError as e:
    print(f"Błąd HTTP: {e.code} - {e.reason}")
except Exception as e:
    print(f"Wystąpił błąd: {e}")