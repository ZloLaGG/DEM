<!-- filepath: c:\Coding\DEM\REAME.md -->
# DEM — Веб-приложение для заказа грузоперевозок

## Описание

Это простое веб-приложение на Flask для регистрации пользователей, создания и управления заявками на грузоперевозки. Приложение поддерживает роли пользователя и администратора, хранит данные в SQLite и имеет удобный интерфейс для клиентов и администраторов.

## Возможности

- Регистрация и вход пользователей
- Создание заявок на перевозку груза (клиенты)
- Просмотр своих заявок (клиенты)
- Просмотр всех заявок, изменение статуса (администратор)
- Оставление отзывов к заявкам, отзывы видны всем пользователям
- Валидация данных на стороне сервера (в том числе формат номера: +7(900)-000-00-00)
- Выбор типа груза из выпадающего списка или ввод собственного варианта
- Хранение данных в SQLite

## Установка

1. Клонируйте репозиторий:
    ```sh
    git clone https://github.com/ZloLaGG/DEM.git
    cd DEM
    ```

2. Установите зависимости:
    ```
    pip install flask
    ```

3. Запустите приложение:
    ```
    python app.py
    ```

4. Откройте в браузере [http://127.0.0.1:5000](http://127.0.0.1:5000)
    - Логин администратора: `admin`
    - Пароль администратора: `gruzovik2024`

## Структура проекта

- `app.py` — основной файл приложения Flask
- `gruz.db` — база данных SQLite (создаётся автоматически)
- `templates/` — HTML-шаблоны (Jinja2)

## Использование

- Зарегистрируйтесь как пользователь или войдите как администратор.
- Клиенты могут создавать заявки на перевозку груза, просматривать их статус и оставлять отзывы к своим и чужим заявкам.
- Администратор может видеть все заявки и менять их статус.
- В отзывах отображается логин пользователя, оставившего отзыв.

## Примечания

- Для смены типа груза выберите вариант из выпадающего списка или укажите свой вариант, выбрав "Другое".
- Формат номера телефона строго: +7(900)-000-00-00.