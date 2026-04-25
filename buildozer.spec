[app]

# Название приложения (будет отображаться на экране телефона)
title = Sports Games

# Пакетное имя (уникальный идентификатор приложения)
package.name = sportsgames
package.domain = org.sportsgames

# Версия приложения
version = 1.0.0

# Описание (необязательно)
description = Collection of sports games: Magic Ball, Coin, Dice, Roulette and more

# Основной файл приложения
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,ogg,mp3,json,ttf

# Требования (библиотеки, которые использует ваше приложение)
# БЕЗ pyjnius! Только то, что реально нужно
requirements = python3,kivy==2.3.0,Pillow,numpy

# Ориентация экрана (portrait - портретная, landscape - альбомная)
orientation = portrait

# Иконка приложения (путь к файлу)
icon.filename = %(source.dir)s/assets/icon.png

# Разрешения для Android
android.permissions = INTERNET, VIBRATE, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# Минимальная версия Android (API 21 = Android 5.0)
android.minapi = 21

# Целевая версия Android
android.targetsdk = 33

# Архитектуры процессора (поддержка старых и новых устройств)
android.archs = arm64-v8a, armeabi-v7a

# Автоматическое принятие лицензий SDK
android.accept_sdk_license = True

# Полноэкранный режим (убирает панель навигации)
fullscreen = 1

# Уровень логгирования (2 - подробный, полезно для отладки)
log_level = 2

# Папка для сборки
build_dir = .buildozer

# Кэш
cache_dir = .buildozer/cache