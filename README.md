SlackApplication

Pet-проект — упрощённый аналог Slack.

Поддерживает рабочие пространства, каналы, сообщения и звонки.

⸻

🚀 Возможности

	•	Workspaces
	•	Public / Private каналы
	•	Управление участниками
	•	Сообщения (long polling)
	•	1-to-1 звонки
	•	JWT аутентификация

⸻

🧱 Стек

Backend:

	•	FastAPI
	•	PostgreSQL
	•	SQLAlchemy (async)
	•	Redis
	•	WebSocket

Frontend:

	•	Flutter

Инфраструктура:

	•	Docker / Docker Compose

⸻

⚙️ Запуск

```commandline
git clone <your-repo-url>
cd slack-application
docker-compose up --build
```

После запуска:

	•	http://localhost:3000 - frontend
	•	http://localhost:8000/docs - backend-swagger

⸻

📡 API (кратко)

	•	Auth: /auth/*
	•	Workspaces: /workspaces
	•	Channels: /channels
	•	Members: workspace / channel
	•	Messages: /messages
	•	Calls: /ws/calls (WebSocket)

⸻

🧠 Архитектура

	•	api/ — роуты
	•	services/ — бизнес-логика
	•	repositories/ — работа с БД
	•	models/ — ORM

⸻

🔄 Сообщения

Используется:

	•	Redis Pub/Sub
	•	Long polling

Даёт почти real-time обновления.

⸻

📞 Звонки

WebSocket signaling:

	•	invite
	•	accept
	•	reject
	•	end

Без медиа (только сигналинг).

⸻

⚠️ Ограничения

	•	Нет полноценного realtime
	•	Нет групповых звонков
	•	Нет файлов

⸻

👤 Автор

Pet-проект для практики разработки.