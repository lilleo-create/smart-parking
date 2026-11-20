# Как работать с репозиторием

Все задачи находятся во вкладке **Issues**. Для каждой задачи создаём отдельную ветку.

## 1. Начало работы

Клонируй репозиторий (только при первом запуске):

```bash
git clone https://github.com/lilleo-create/smart-parking.git
cd smart-parking
```

## 2. Создание ветки

Перед новой задачей обнови `develop` и создай свою ветку:

```bash
git switch develop
git pull origin develop
git switch -c feature/12-task-name
```

Вместо `12` укажи номер GitHub Issue, вместо `task-name` — название задачи на английском.

## 3. Отправка изменений

После завершения работы:

```bash
git add .
git commit -m "Описание изменений"
git push -u origin feature/12-task-name
```

## 4. Pull Request

На GitHub открой **Pull requests → New pull request**.

Выбери:
- `base: develop`
- `compare: твоя ветка`

Кратко опиши изменения и укажи номер Issue.

Проверь, что всё работает, затем объедини PR в `develop`.

## Важно

- Не отправляем изменения напрямую в `main` и `develop`.
- В `main` переносим только проверенную версию проекта.
- Если возникли ошибки или конфликты, обсуждаем их с командой до слияния.
