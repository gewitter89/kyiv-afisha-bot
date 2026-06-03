# Руководство по развертыванию на Google Cloud VM (Ubuntu 22.04)

В данном руководстве описан процесс развертывания проекта «Куди піти Київ» (kyiv-event-guide) на вашей виртуальной машине GCP **`alarm-bot`** (ОС Ubuntu 22.04).

---

## 📋 Содержание
1. [Подключение к виртуальной машине по SSH](#1-подключение-к-виртуальной-машине-по-ssh)
2. [Установка Docker и Docker Compose](#2-установка-docker-и-docker-compose)
3. [Перенос и подготовка проекта](#3-перенос-и-подготовка-проекта)
4. [Настройка конфигурации (.env)](#4-настройка-конфигурации-env)
5. [Запуск сервисов](#5-запуск-сервисов)
6. [Настройка брандмауэра (Firewall) в GCP](#6-настройка-брандмауэра-firewall-в-gcp)
7. [Рекомендованная Production-настройка (Nginx + SSL)](#7-рекомендованная-production-настройка-nginx--ssl)

---

## 1. Подключение к виртуальной машине по SSH

1. Перейдите в консоль **Google Cloud Platform** -> **Compute Engine** -> **VM instances**.
2. В строке с инстансом **`alarm-bot`** найдите колонку **Connect**.
3. Нажмите на кнопку **SSH** (или откройте выпадающее меню рядом с ней и выберите *Open in browser window*).
4. Откроется окно веб-терминала, подключенное к вашему серверу.

---

## 2. Установка Docker и Docker Compose

Поскольку проект упакован в Docker-контейнеры, на сервере необходимо установить Docker Engine и плагин Docker Compose.

Выполните следующие команды в терминале SSH:

### Шаг 2.1. Обновление индексов пакетов и установка зависимостей
```bash
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common gnupg lsb-release git
```

### Шаг 2.2. Добавление официального GPG-ключа Docker
```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

### Шаг 2.3. Добавление репозитория Docker в системные источники
```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### Шаг 2.4. Установка Docker компонентов
```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Шаг 2.5. Проверка установки
Убедитесь, что Docker и Docker Compose установлены корректно:
```bash
docker --version
docker compose version
```
*(Обе команды должны вывести версии установленного ПО)*

### Шаг 2.6. Разрешение запуска Docker без sudo (опционально)
Чтобы не писать `sudo` перед каждой командой `docker`:
```bash
sudo usermod -aG docker $USER
```
> [!IMPORTANT]
> Чтобы изменения групп вступили в силу, отключитесь от сессии SSH (`exit`) и подключитесь заново.

---

## 3. Перенос и подготовка проекта

Вы можете перенести код проекта на сервер двумя способами:

### Способ А: Через Git (Рекомендуется)
1. Сделайте ваш локальный репозиторий публичным (или приватным, настроив SSH-ключи доступа на GitHub/GitLab).
2. Склонируйте его на сервере:
   ```bash
   git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ>
   cd бот_инфа
   ```

### Способ Б: Через встроенную утилиту gcloud scp
Если вы используете Google Cloud SDK локально на компьютере, перейдите в папку с проектом на своем ПК и выполните:
```bash
gcloud compute scp --recursive ./ alarm-bot:~/bot_inf/ --zone=us-central1-a
```
Затем зайдите по SSH и перейдите в папку:
```bash
cd ~/bot_inf
```

---

## 4. Настройка конфигурации (.env)

Проекту необходим файл `.env` для корректного запуска контейнеров.

1. Скопируйте шаблон конфигурации:
   ```bash
   cp .env.example .env
   ```
2. Откройте `.env` в консольном текстовом редакторе `nano`:
   ```bash
   nano .env
   ```
3. Отредактируйте параметры:
   - **DATABASE_URL**: оставьте значение для Docker-сети:
     `postgresql+asyncpg://postgres:postgres@postgres:5432/kyiv_events`
   - **REDIS_URL**: оставьте значение для Docker-сети:
     `redis://redis:6379/0`
   - **TELEGRAM_BOT_TOKEN**: ваш токен от BotFather (например, `8953691774:AAH...`).
   - **TELEGRAM_CHANNEL_ID**: юзернейм канала с собачкой (например, `@Kyiv_afisha_channel`) или его числовой ID (например, `-1002447952932`).
   - **AI_PROVIDER**: укажите `deepseek` или `openai`.
   - **DEEPSEEK_API_KEY** / **OPENAI_API_KEY**: введите соответствующий API-ключ.
   - **SECRET_KEY**: сгенерируйте случайную защищенную строку. Для этого в другой вкладке терминала можно выполнить:
     ```bash
     openssl rand -hex 32
     ```
     и скопировать полученную строку в `.env`.
   - **APP_BASE_URL**: укажите адрес внешнего IP вашей VM (например, `http://34.123.45.67:8000`).

4. Сохраните изменения в `nano`: нажмите `Ctrl+O`, затем `Enter` для подтверждения, и выйдите через `Ctrl+X`.

---

## 5. Запуск сервисов

Запустите сборку и старт всех контейнеров в фоновом режиме (флаг `-d`):
```bash
docker compose up -d --build
```

### Проверка статуса запуска
1. Посмотрите список запущенных контейнеров:
   ```bash
   docker compose ps
   ```
   Должны быть запущены 6 контейнеров: `postgres`, `redis`, `backend`, `celery_worker`, `celery_scheduler`, `telegram_bot` и `frontend`.
   
2. Просмотр логов в реальном времени (например, логов бота или бэкенда):
   ```bash
   docker compose logs -f bot
   ```
   или логов бэкенда:
   ```bash
   docker compose logs -f backend
   ```
   *(Для выхода из режима просмотра логов нажмите `Ctrl+C`)*

---

## 6. Настройка брандмауэра (Firewall) в GCP

Чтобы вы могли открыть админ-панель проекта на своем локальном компьютере, необходимо разрешить внешний доступ к портам `5173` (React/Vite) и `8000` (FastAPI) в брандмауэре Google Cloud.

1. Откройте боковое меню консоли GCP и перейдите в **VPC network** -> **Firewall**.
2. Вверху страницы нажмите кнопку **Create Firewall Rule**.
3. Заполните поля правила:
   - **Name**: `allow-event-guide-ports`
   - **Description**: Разрешить входящие подключения для админ-панели и бэкенда
   - **Network**: `default`
   - **Priority**: `1000`
   - **Direction of traffic**: `Ingress`
   - **Action on match**: `Allow`
   - **Targets**: `All instances in the network` (либо `Specified target tags` и укажите тег инстанса)
   - **Source filter**: `IPv4 ranges`
   - **Source IPv4 ranges**: `0.0.0.0/0` (или укажите ваш конкретный IP-адрес для максимальной безопасности)
   - **Protocols and ports**: выберите **Specified protocols and ports**, поставьте галочку напротив **TCP** и введите: `5173, 8000`.
4. Нажмите кнопку **Create** внизу страницы.

После создания правила перейдите по адресу:
- **Админ-панель**: `http://<ВНЕШНИЙ_IP_СЕРВЕРА>:5173`
- **FastAPI Документация (Swagger)**: `http://<ВНЕШНИЙ_IP_СЕРВЕРА>:8000/docs`

---

## 7. Рекомендованная Production-настройка (Nginx + SSL)

Использовать порты `5173` и `8000` напрямую через http в продакшене не рекомендуется. Безопасный и стандартный способ — запустить Nginx как реверс-прокси на стандартных портах 80 (HTTP) и 443 (HTTPS) с бесплатным SSL-сертификатом от Let's Encrypt.

### Шаг 7.1. Установка Nginx на сервере
```bash
sudo apt-get install -y nginx
```

### Шаг 7.2. Сборка фронтенда (Production build)
Для лучшей производительности React-приложение компилируется в статические файлы.
Вместо запуска Vite dev-сервера на порту 5173, соберите проект:
```bash
# Выполнить сборку внутри контейнера frontend
docker compose exec frontend npm run build
```
Статические файлы сборки появятся на сервере в папке `frontend/dist`.

### Шаг 7.3. Настройка конфигурации Nginx
Создайте новый конфигурационный файл:
```bash
sudo nano /etc/nginx/sites-available/kyiv-event-guide
```

Вставьте следующую конфигурацию (замените `yourdomain.com` на ваш домен или используйте внешний IP, если домена нет):

```nginx
server {
    listen 80;
    server_name yourdomain.com; # Укажите ваш домен или внешний IP-адрес

    # Раздача собранного React-фронтенда
    location / {
        root /home/ubuntu/бот_инфа/frontend/dist; # Путь к вашей папке frontend/dist
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    # Проксирование API запросов к FastAPI backend
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте конфигурацию и перезапустите Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/kyiv-event-guide /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default # Удалить стандартную заглушку
sudo nginx -t # Проверить конфигурацию на ошибки
sudo systemctl restart nginx
```

### Шаг 7.4. Получение бесплатного SSL (HTTPS) с Certbot
Если у вас есть доменное имя, вы можете включить HTTPS одной командой:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```
Certbot автоматически перенаправит весь HTTP-трафик на безопасный HTTPS и настроит автопродление сертификата.
При такой схеме порты `5173` и `8000` в брандмауэре GCP открывать не нужно — достаточно открыть стандартные `80` и `443` порты.
