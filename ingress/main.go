package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/nats-io/nats.go"
)

type WebhookPayload struct {
	TenantID      string `json:"tenant_id"`
	CustomerEmail string `json:"customer_email"`
	Message       string `json:"message"`
	OrderID       string `json:"order_id"`
}

func verifyHMAC(body []byte, signature, secret string) bool {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(body)
	expectedMAC := hex.EncodeToString(mac.Sum(nil))
	return hmac.Equal([]byte(expectedMAC), []byte(signature))
}

func main() {
	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		natsURL = nats.DefaultURL
	}

	nc, err := nats.Connect(natsURL)
	if err != nil {
		log.Fatalf("Blad polaczenia z NATS: %v", err)
	}
	defer nc.Close()

	app := fiber.New(fiber.Config{
		DisableStartupMessage: true,
	})

	app.Post("/webhook/incoming-ticket", func(c *fiber.Ctx) error {
		signature := c.Get("X-Ecommerce-Signature")
		dummySecret := "super_secret_key_from_db"

		if !verifyHMAC(c.Body(), signature, dummySecret) {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Niewlasciwy podpis HMAC"})
		}

		var payload WebhookPayload
		if err := c.BodyParser(&payload); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Bledny format JSON"})
		}

		eventData, _ := json.Marshal(payload)

		err := nc.Publish("ticket.incoming", eventData)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Blad brokera wiadomosci"})
		}

		return c.SendStatus(fiber.StatusAccepted)
	})

	log.Println("Ingress Gateway uruchomiony na porcie :3000")
	log.Fatal(app.Listen(":3000"))
}