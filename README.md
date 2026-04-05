# Protocol Bot

Telegram bot for composing meeting protocols/minutes.

**Goal:** 10,000 users, 100 RUB/month subscription.

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.11 | Fast iteration, great bot ecosystem |
| Bot framework | aiogram 3.x | Async, FSM support, production-ready |
| Database | PostgreSQL | Relational model fits meetings/protocols |
| ORM | SQLAlchemy 2.0 async | Type-safe, async-first |
| LLM | Claude API (Anthropic) | Best summarization quality |
| Hosting | Railway.app | Simple git-push deploys, managed Postgres |

## Local Development

1. Copy env file and fill in your values:
   ```bash
   cp .env.example .env
   ```

2. Start the database:
   ```bash
   docker-compose up db -d
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the bot:
   ```bash
   python -m bot.main
   ```

## Docker (full stack)

```bash
cp .env.example .env
# Edit .env with your BOT_TOKEN
docker-compose up --build
```

## Project Structure

```
bot/
├── main.py          # Entry point
├── config.py        # Settings (pydantic-settings)
├── handlers/
│   └── common.py    # /start, /help
└── database/
    ├── models.py    # ORM models (User, Meeting)
    └── session.py   # Async session factory
```

## Roadmap

- [x] Phase 1: Scaffold — /start, /help, DB models
- [ ] Phase 2: Protocol flow — start meeting, add notes, generate protocol
- [ ] Phase 3: Monetization — YooKassa subscription
- [ ] Phase 4: Growth — analytics, CMO hire
