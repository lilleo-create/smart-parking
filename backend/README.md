# API демонстрационного сайта

Сервер отдаёт сборку Vue, две парковки с демонстрационными статусами и одну парковку с Raspberry Pi. Данные камеры хранятся в SQLite. Для холодного старта достаточно Python 3.10+ и сборки фронтенда.

```sh
cd frontend
npm ci
VITE_PARKING_API=1 npm run build
cd ..
# PARKING_API_TOKEN передаётся через окружение процесса.
python3 backend/demo_server.py --frontend frontend/dist --db /path/to/parking.sqlite3
```

По умолчанию сервер слушает `127.0.0.1:8284`. Для внешнего доступа направьте HTTPS-домен на этот порт через reverse proxy. Токен нужен только процессу на Raspberry Pi и серверу. Его нельзя добавлять в переменные `VITE_*` или в исходники.

## Подключение Raspberry Pi

Запусти распознавание по [инструкции трекера](parking-tracker/README.md). В той же папке запусти отдельный процесс отправки и укажи файл с токеном, полученным у владельца сервера.

```sh
python3 publish_snapshot.py \
  --status output/status.json \
  --url https://smart-park.my-uzel.xyz/api/tracker/snapshot \
  --token-file /path/to/tracker-token
```

Отправщик раз в секунду читает выход трекера. ID и подписанные номера поступают из редактора разметки. Сайт группирует места в ряды по номеру. Переименование сохраняет ID, а добавление и удаление места меняют схему автоматически. Через 15 секунд без свежих кадров схема остаётся видимой, а места показываются как «Нет данных».

## Контракт и проверки

- `GET /api/parkings`, `GET /api/parkings/{id}`, `GET /api/parkings/{id}/occupancy` — [контракт фронтенда](../frontend/README.md#подключение-бэкенда).
- `POST /api/tracker/snapshot` — `Authorization: Bearer <token>` и JSON с `observed_at` (Unix-время кадра в секундах) и `spots` (массив `{id, number, occupied}`). Каждый запрос передаёт всю разметку. Повторный или более старый снимок не меняет состояние.
- `GET /healthz` — проверка доступа к базе.
- `python3 -m unittest discover -s backend/tests` — проверка контракта на изолированной базе.
