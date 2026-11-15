---
name: demo-capture
description: Скриншоты, GIF и видео демо для README и сдачи — Playwright проходит демо-сценарий, ffmpeg делает GIF и mp4. Используй: «сними демо», «сделай гифку», «скриншоты для README», «запиши видео для жюри».
---

# /demo-capture

## Шаги
1. Возьми демо-сценарий из `docs/SPEC.md` (или спроси пользователя) и запусти приложение локально в фоне (dev или preview).
2. Напиши `scripts/capture-demo.mjs` на Playwright: chromium, headless, для WebGL флаги `--use-angle=swiftshader --enable-unsafe-swiftshader`, viewport 1280×720, `recordVideo` в `docs/media/raw/`. Шаги сценария выполняй кликами и клавишами, с паузами, чтобы зритель успевал читать. Если в проекте нет Node (например, чистый Python): `npm i -D playwright && npx playwright install chromium` во временной папке `tools/`, около 150 МБ — лучше поставить накануне.
3. Скриншоты ключевых моментов сохрани как `docs/media/01-<шаг>.png`, `02-…`.
4. GIF для README (до 10 МБ, около 15 fps, ширина 960):
   `ffmpeg -i in.webm -vf "fps=15,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" -loop 0 docs/media/demo.gif`
5. MP4 для сдачи: `ffmpeg -i in.webm -c:v libx264 -pix_fmt yuv420p -crf 20 docs/media/demo.mp4`
6. Вставь медиа в README (hero-блок и демо-сценарий) и проверь размеры файлов через `du -h`. Сырые записи (`docs/media/raw/`) не коммить.
7. Останови запущенные серверы.

## Видео для жюри (если нужно)
- 2–3 минуты: проблема (15 с) → демо (90 с) → как устроено и цифры (30 с) → что дальше (15 с).
- Экран записываем в QuickTime или OBS, озвучиваем голосом или через TTS, монтируем в Remotion или CapCut.
- Выкладывать видео (YouTube по ссылке, Google Drive) — только с согласия пользователя.
