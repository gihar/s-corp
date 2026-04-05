FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# For docker-compose / non-Railway deploys: run migrations then start the bot.
# On Railway, the release command in railway.toml handles migrations separately.
CMD ["sh", "-c", "alembic upgrade head && python -m bot.main"]
