# Smart Fridge / Умный холодильник

Smart Fridge — Django monolith для учета продуктов, импорта позиций из чеков и писем, определения срока годности по базе знаний и уведомлений о приближающемся истечении срока.

## Стек

- Python 3.11+
- Django 5.x
- PostgreSQL
- Django templates, forms, admin
- Стандартная библиотека Python для IMAP и HTTP-интеграций

Не используются Flask, FastAPI, Django REST Framework, Node.js, React, Vue, Celery, Redis, RabbitMQ и другие компоненты вне указанного стека.

## Структура

```text
smart_fridge/          Django settings и urls
accounts/              регистрация, профиль пользователя
pantry/                продукты и категории
receipts/              чеки, OCR fallback, IMAP импорт
knowledge/             база знаний сроков хранения
notifications/         системные и email-уведомления
templates/             Django templates
static/css/            базовые стили
tests/                 тесты ключевых сценариев
```

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## PostgreSQL

Если PostgreSQL запущен в Docker:

```bash
docker run --name smart-fridge-postgres -e POSTGRES_DB=smart_fridge -e POSTGRES_USER=smart_fridge -e POSTGRES_PASSWORD=smart_fridge -p 5432:5432 -d postgres:16
```

Если у вас уже есть контейнер PostgreSQL, создайте БД и пользователя или укажите существующие значения в `.env`:

```env
POSTGRES_DB=smart_fridge
POSTGRES_USER=smart_fridge
POSTGRES_PASSWORD=smart_fridge
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

## Миграции и запуск

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Приложение будет доступно на http://127.0.0.1:8000/.

## Тесты

```bash
python manage.py test
```

Тесты покрывают регистрацию и вход, создание продукта, парсинг чеков, импорт писем, определение срока годности, уведомления и пользовательские переопределения правил.

## Как пользоваться

1. Зарегистрируйтесь и войдите в систему.
2. Добавляйте продукты вручную на главной странице.
3. Импортируйте чек как текст или загрузите файл. Если OCR не настроен, файл сохранится, а текст можно вставить вручную.
4. Настройте IMAP-источник в разделе почты и запускайте импорт писем от магазинов.
5. Управляйте справочником сроков хранения. Пользовательские правила имеют приоритет над общими.
6. Запускайте уведомления командой:

```bash
python manage.py generate_notifications
```

Эту команду можно поставить в Планировщик задач Windows или cron. Она создает уведомления за 3 дня, за 1 день и после истечения срока. Email отправляется через стандартный Django email backend, если он настроен в `.env`.

## Внешние OCR и LLM

Проект полностью работает без внешних API. Для OCR и LLM предусмотрены безопасные расширения через переменные:

```env
OCR_API_URL=
OCR_API_KEY=
LLM_API_URL=
LLM_API_KEY=
```

Если ключи не заданы или сервис недоступен, импорт чеков работает через ручную вставку текста, а определение срока годности использует правила и похожесть текста внутри Django/PostgreSQL.

## Безопасность

- CSRF включен стандартным middleware Django.
- Секреты читаются из `.env`.
- Пароли и API-ключи не хардкодятся.
- Страницы приложения защищены `login_required`.
- Для IMAP рекомендуется использовать отдельный пароль приложения.
