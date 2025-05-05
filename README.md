# Flask Image Sharing Platform

Платформа для обмена изображениями с возможностью комментирования и оценки.

## Функциональность

- Регистрация и авторизация пользователей
- Загрузка и просмотр изображений
- Комментирование изображений
- Система рейтинга (1-5 звезд)
- Профили пользователей
- Поиск по названиям изображений
- Настройки профиля (аватар, имя пользователя)

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/ваш-username/название-репозитория.git
cd название-репозитория
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл .env и добавьте необходимые переменные окружения:
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///site.db
```

5. Запустите приложение:
```bash
python app.py
```

## Технологии

- Flask
- SQLAlchemy
- Flask-Login
- PostgreSQL (для продакшена)
- Gunicorn (для продакшена)

## Лицензия

MIT 