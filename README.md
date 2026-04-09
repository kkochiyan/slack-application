Для запуска с уже существующими данными: 

docker compose up

Для запуска приложения с полного нуля:

docker compose down -v

docker system prune -a

docker compose up --build


После запуска надо в браузере открыть:
фронт: http://localhost:3000
бек swagger: http://localhost:8000/docs