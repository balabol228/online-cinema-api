# Online Cinema API

REST API для сервісу онлайн-кінотеатру. Проєкт реалізує обрану підмножину функцій
повної специфікації Online Cinema — з акцентом на якість (тести, документація),
а не на кількість фіч.

## Обрані функції (7 з 6-8)

| # | Функція | Опис |
|---|---------|------|
| 1 | Автентифікація | Реєстрація, логін, JWT access/refresh токени |
| 2 | Ролі та дозволи | User / Moderator / Admin, захист ендпоінтів |
| 3 | Каталог фільмів | CRUD для адміна, перегляд/фільтри/пагінація для всіх |
| 4 | Кошик покупок | Додавання/видалення фільмів |
| 5 | Замовлення та оплата | Stripe Checkout + webhook |
| 6 | Лайки, рейтинги, коментарі | Вкладені відповіді на коментарі |
| 7 | Обране | Список "подивитись пізніше" |

## Стек технологій

- **FastAPI** — веб-фреймворк, автоматична Swagger/ReDoc документація
- **SQLAlchemy 2.0 (async)** + **asyncpg** — робота з PostgreSQL
- **Alembic** — міграції БД
- **Pydantic v2** — валідація даних
- **JWT (python-jose)** — автентифікація (access + refresh токени)
- **Passlib/bcrypt** — хешування паролів
- **Stripe** — оплата замовлень
- **Docker Compose** — Postgres, Redis, MailHog, застосунок
- **pytest + pytest-asyncio + httpx** — тести (юніт + інтеграційні)

## Швидкий старт

### Через Docker

```bash
cp .env.sample .env
docker compose up --build
```

Застосунок буде доступний на `http://localhost:8000`.

### Локально (без Docker)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.sample .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Документація API

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Кожен кастомний ендпоінт містить опис параметрів, кодів відповіді та бізнес-логіки.

### Реалізовані ендпоінти

| Метод | Шлях | Опис |
|-------|------|------|
| POST | `/api/v1/auth/register` | Реєстрація нового користувача |
| POST | `/api/v1/auth/login` | Логін, повертає access/refresh токени |
| POST | `/api/v1/auth/refresh` | Оновлення access token |
| GET | `/api/v1/users/me` | Профіль поточного користувача |
| GET | `/api/v1/movies` | Каталог фільмів: пагінація, фільтри, сортування |
| GET | `/api/v1/movies/{id}` | Деталі фільму |
| POST | `/api/v1/movies` | Створити фільм (Moderator/Admin) |
| PATCH | `/api/v1/movies/{id}` | Оновити фільм (Moderator/Admin) |
| DELETE | `/api/v1/movies/{id}` | Видалити фільм (тільки Admin) |
| POST | `/api/v1/genres`, `/api/v1/actors` | Наповнення довідників |
| GET/POST/DELETE | `/api/v1/cart`, `/api/v1/cart/items/{id}` | Кошик покупок |
| POST | `/api/v1/orders` | Оформити замовлення (Stripe Checkout) |
| GET | `/api/v1/orders`, `/api/v1/orders/{id}` | Історія та деталі замовлень |
| POST | `/api/v1/payments/webhook` | Stripe webhook |
| POST | `/api/v1/movies/{id}/like` | Лайк/анлайк фільму |
| POST/GET | `/api/v1/movies/{id}/rating` | Оцінити / переглянути рейтинг |
| POST/GET | `/api/v1/movies/{id}/comments` | Коментарі з вкладеними відповідями |
| POST | `/api/v1/movies/{id}/favorite` | Додати/прибрати з обраного |
| GET | `/api/v1/favorites` | Список обраних фільмів |

## Запуск тестів

```bash
pytest app/tests -v --cov=app --cov-report=term-missing
```

76 тестів, 87% покриття (юніт + інтеграційні для всіх фіч).

## Структура проєкту

app/
├── api/v1/endpoints/   # FastAPI роутери
├── core/               # конфігурація, security (JWT, хешування паролів)
├── db/                 # налаштування SQLAlchemy сесії
├── models/             # ORM-моделі
├── schemas/            # Pydantic-схеми
├── services/           # бізнес-логіка
└── tests/
├── unit/
└── integration/

## Git workflow

- `main` — стабільна гілка