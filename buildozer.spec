[app]

title = Almighty Random
package.name = almightyrandom
package.domain = org.almighty
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,wav,ogg,mp3,json,glsl,txt,zip
source.include_patterns = assets/*, screens/*, components/*, locales/*
source.exclude_dirs = .buildozer,.venv,__pycache__,bin
version = 1.0.1
orientation = portrait

# ========== ИКОНКА ПРИЛОЖЕНИЯ (обычная) ==========
icon.filename = assets/app_icon.png
# ==================================================

requirements = python3,kivy==2.3.0,requests,numpy,chardet,charset_normalizer,pillow,android,sdl2,pyjnius,plyer
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, VIBRATE
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True
android.enable_androidx = True
android.gradle = True
android.gradle_version = 8.0.1
android.java_version = 17
android.gradle_plugin_version = 7.2.0

[buildozer]
log_level = 2
warn_on_root = 1