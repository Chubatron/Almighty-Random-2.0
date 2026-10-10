import os
import sys
import json
import requests
import threading
import importlib
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.core.window import Window
from kivy.utils import platform
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout


# --- ФУНКЦИЯ ДЛЯ ДИНАМИЧЕСКОГО ИМПОРТА ЭКРАНА ---
def get_screen_class(screen_name, screen_file, class_name):
    """Динамически импортирует класс экрана, всегда загружая свежую версию.

    screen_file может быть как 'menu_screen', так и 'draw.draw_main' —
    importlib корректно разберёт вложенные пути.
    """
    try:
        module_name = f"screens.{screen_file}"

        if module_name in sys.modules:
            del sys.modules[module_name]
            print(f"   🗑️ Удален из кэша: {module_name}")

        module = importlib.import_module(module_name)
        screen_class = getattr(module, class_name)

        print(f"   ✅ Загружен экран: {screen_name}")
        return screen_class
    except Exception as e:
        print(f"   ❌ Ошибка загрузки {screen_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


# --- ЗАПРОС РАЗРЕШЕНИЙ ДЛЯ ANDROID ---
if platform == 'android':
    try:
        from android.permissions import request_permissions, Permission

        request_permissions([
            Permission.INTERNET,
            Permission.WRITE_EXTERNAL_STORAGE,
            Permission.READ_EXTERNAL_STORAGE,
            Permission.VIBRATE
        ])
    except ImportError:
        print("⚠️ Не удалось импортировать android.permissions")
# ------------------------------------

# --- ПРАВИЛЬНАЯ РАБОЧАЯ ДИРЕКТОРИЯ ДЛЯ ANDROID ---
if platform == 'android':
    app_dir = "/data/data/org.almighty.almightyrandom/files/app"

    if os.path.exists(app_dir):
        os.chdir(app_dir)
        print(f"[DEBUG] Working directory set to: {os.getcwd()}")
    else:
        print(f"[ERROR] App directory not found: {app_dir}")

    if os.path.exists('assets'):
        print(f"[DEBUG] Assets folder found!")
    else:
        print(f"[ERROR] Assets folder not found in {os.getcwd()}")

    sync_path = "/data/data/org.almighty.almightyrandom/files/sync"
    if not os.path.exists(sync_path):
        os.makedirs(sync_path)

    if sync_path not in sys.path:
        sys.path.insert(0, sync_path)
# -----------------------------------------

# Импорты менеджеров (они редко меняются)
from language_manager import LanguageManager
from sound_manager import SoundManager
from lucky_token import LuckyToken


def get_settings_path():
    """Возвращает правильный путь для settings.json"""
    if platform == 'android':
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            files_dir = context.getFilesDir().getAbsolutePath()
            settings_path = os.path.join(files_dir, 'settings.json')
            return settings_path
        except Exception as e:
            print(f"⚠️ Ошибка получения пути: {e}")
            return 'settings.json'
    else:
        return 'settings.json'


def load_mute_state():
    """Загружает состояние звука из файла"""
    settings_path = get_settings_path()

    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                is_muted = settings.get('is_muted', False)
                print(f"📁 Загружено состояние звука: muted={is_muted}")
                return is_muted
        except Exception as e:
            print(f"⚠️ Ошибка загрузки: {e}")
            return False
    else:
        try:
            default_settings = {"is_muted": False}
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, indent=4)
            print(f"✅ Создан файл настроек: {settings_path}")
        except Exception as e:
            print(f"❌ Ошибка создания: {e}")
        return False


def save_mute_state(is_muted):
    """Сохраняет состояние звука в файл"""
    settings_path = get_settings_path()
    settings = {}

    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except:
            pass

    settings['is_muted'] = is_muted

    try:
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        print(f"💾 Сохранено состояние звука: muted={is_muted}")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка сохранения: {e}")
        return False


class ScreenParams:
    """Класс для хранения параметров экрана"""

    def __init__(self):
        from kivy.core.window import Window

        if platform == 'android':
            self.width, self.height = Window.system_size
        else:
            if hasattr(Window, 'system_size') and Window.system_size[0] > 0:
                self.width, self.height = Window.system_size
            else:
                self.width, self.height = Window.width, Window.height

        self.aspect_ratio = self.width / self.height
        self.is_phone = platform == 'android'
        self.is_tablet = self.width > 600 if self.is_phone else False

        self.base_width = 400
        self.base_height = 700

        self.scale_x = self.width / self.base_width
        self.scale_y = self.height / self.base_height
        self.scale = min(self.scale_x, self.scale_y)

        print(f"[DEBUG] Screen params: {self.width}x{self.height}, scale={self.scale:.2f}")

    def get_size(self, width, height):
        return (width * self.scale, height * self.scale)

    def get_x(self, x):
        return x * self.scale_x

    def get_y(self, y):
        return y * self.scale_y

    def get_font_size(self, size):
        return size * self.scale


class UpdateManager:
    """Класс для обновления APK через Wi-Fi"""

    def __init__(self, app):
        self.app = app
        self.server_url = "http://192.168.0.50:8000"
        self.current_version = "1.0.0"

    def check_for_updates(self, show_notification=True):
        def check():
            try:
                version_url = f"{self.server_url}/version.json"
                response = requests.get(version_url, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    server_version = data.get("version")
                    apk_url = data.get("url")

                    if server_version and server_version != self.current_version:
                        Clock.schedule_once(
                            lambda dt: self.show_update_dialog(server_version, apk_url)
                        )
                    elif show_notification:
                        Clock.schedule_once(
                            lambda dt: self.show_message("Нет обновлений", "У вас последняя версия")
                        )
            except Exception as e:
                print(f"Ошибка проверки обновлений: {e}")

        thread = threading.Thread(target=check)
        thread.daemon = True
        thread.start()

    def show_update_dialog(self, new_version, apk_url):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f"Доступна новая версия {new_version}\n\nХотите обновить?"))

        btn_layout = BoxLayout(size_hint_y=0.3, spacing=10)
        update_btn = Button(text="Обновить")
        later_btn = Button(text="Позже")

        btn_layout.add_widget(update_btn)
        btn_layout.add_widget(later_btn)
        content.add_widget(btn_layout)

        popup = Popup(title="Обновление", content=content, size_hint=(0.8, 0.4))

        def update(instance):
            popup.dismiss()
            self.download_and_install(apk_url)

        def later(instance):
            popup.dismiss()

        update_btn.bind(on_press=update)
        later_btn.bind(on_press=later)

        popup.open()

    def download_and_install(self, apk_url):
        from kivy.uix.progressbar import ProgressBar

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        pb = ProgressBar(max=100)
        label = Label(text="Скачивание обновления...")
        content.add_widget(label)
        content.add_widget(pb)

        popup = Popup(title="Обновление", content=content, size_hint=(0.8, 0.4))

        def download():
            try:
                response = requests.get(apk_url, stream=True)
                apk_path = f"/sdcard/Download/almightyrandom_new.apk"

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(apk_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                Clock.schedule_once(lambda dt, p=progress: setattr(pb, 'value', p))

                Clock.schedule_once(lambda dt: self.install_apk(apk_path, popup))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_message("Ошибка", f"Не удалось скачать:\n{str(e)}"))
                popup.dismiss()

        popup.open()
        threading.Thread(target=download).start()

    def install_apk(self, apk_path, popup):
        popup.dismiss()

        if platform == 'android':
            try:
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')

                intent = Intent(Intent.ACTION_VIEW)
                intent.setDataAndType(Uri.fromFile(File(apk_path)), "application/vnd.android.package-archive")
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                PythonActivity.mActivity.startActivity(intent)
                self.show_message("Готово", "Запуск установщика...")
            except Exception as e:
                self.show_message("Ошибка", f"Не удалось запустить установку:\n{str(e)}")
        else:
            self.show_message("Установка", "На ПК установка не поддерживается")

    def show_message(self, title, message):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=message))

        btn = Button(text="OK", size_hint_y=0.3)
        content.add_widget(btn)

        popup = Popup(title=title, content=content, size_hint=(0.7, 0.3))
        btn.bind(on_press=popup.dismiss)
        popup.open()


class AlmightyRandomApp(App):
    """Главный класс приложения Almighty Random"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ✅ Флаг: приложение завершается. Используется экранами,
        # чтобы не возвращать громкость музыки при закрытии.
        self._is_stopping = False

    def build(self):
        print("🚀 [App] Запуск Almighty Random")

        if platform == 'android':
            Window.fullscreen = 'auto'
        else:
            Window.size = (400, 700)

        Window.clearcolor = (0.1, 0.1, 0.1, 1)

        self.screen_params = ScreenParams()

        print("🔧 [App] Инициализация менеджеров")
        self.lang = LanguageManager()
        self.sound_mgr = SoundManager()
        self.tokens = LuckyToken()
        self.update_mgr = UpdateManager(self)

        print(f"🎟️ [App] Lucky_Token готов. Баланс: {self.tokens.get_balance()}")

        if load_mute_state():
            self.sound_mgr.mute()
            print(f"🔇 [App] Звук ВЫКЛЮЧЕН")
        else:
            print(f"🔊 [App] Звук ВКЛЮЧЕН")

        try:
            sound_path = "assets/sounds/background.wav"
            if os.path.exists(sound_path):
                self.sound_mgr.initialize(sound_path)
                print(f"✅ [App] Звук загружен")
            else:
                print(f"❌ [App] Файл звука не найден")
        except Exception as e:
            print(f"❌ [App] Ошибка звука: {e}")

        self.sm = ScreenManager(transition=FadeTransition(duration=0.4))

        menu_class = get_screen_class('menu', 'menu_screen', 'MainMenuScreen')
        if menu_class:
            menu = menu_class(name='menu', screen_params=self.screen_params)
            self.sm.add_widget(menu)
            print("✅ [App] Создано меню")
        else:
            print("❌ [App] Ошибка: не удалось загрузить меню")
            error_screen = Screen(name='error')
            error_screen.add_widget(Label(text="Ошибка загрузки меню"))
            self.sm.add_widget(error_screen)

        def start_music(dt):
            if not self.sound_mgr.is_muted():
                self.sound_mgr.play()

        Clock.schedule_once(start_music, 0.5)

        Clock.schedule_once(lambda dt: self.update_mgr.check_for_updates(False), 5)

        print("✅ [App] Almighty Random запущено")
        return self.sm

    def switch_to_screen(self, screen_name, **kwargs):
        """Переключает на экран - ВСЕГДА загружает СВЕЖУЮ версию из файла"""
        # ✅ Если приложение завершается — не переключаем экраны
        if self._is_stopping:
            print(f"⚠️ [App] switch_to_screen('{screen_name}') пропущен — приложение завершается")
            return

        print(f"🔄 [App] Переключение на {screen_name}")

        screen_map = {
            'menu': ('menu_screen', 'MainMenuScreen'),
            'random_number': ('random_number_screen', 'RandomNumberScreen'),
            'random': ('random_number_screen', 'RandomNumberScreen'),
            'coin': ('coin_screen', 'CoinScreen'),
            'dice': ('dice_screen', 'DiceScreen'),
            'roulette': ('roulette_screen', 'RouletteScreen'),
            'rus_roulette': ('rus_roulette_screen', 'RusRouletteScreen'),
            'quiz': ('quiz_screen', 'QuizScreen'),
            'magic_ball': ('magic_ball_screen', 'MagicBallScreen'),
            'rsp': ('rsp_screen', 'RSPScreen'),
            'intermediate_roulette': ('intermediate_roulette', 'IntermediateRoulette'),
            'team_draw': ('draw.draw_main', 'DrawScreen'),
        }

        if screen_name not in screen_map:
            print(f"❌ Неизвестный экран: {screen_name}")
            return

        file_name, class_name = screen_map[screen_name]

        print(f"   📂 Загрузка свежей версии {file_name}.py...")
        screen_class = get_screen_class(screen_name, file_name, class_name)

        if screen_class is None:
            print(f"❌ Не удалось загрузить экран {screen_name}")
            return

        if self.sm.has_screen(screen_name):
            old_screen = self.sm.get_screen(screen_name)
            self.sm.remove_widget(old_screen)
            print(f"   🗑️ Удален старый экран {screen_name}")

        try:
            new_screen = screen_class(name=screen_name, screen_params=self.screen_params, **kwargs)
            self.sm.add_widget(new_screen)
            print(f"   ✨ Создан новый экран {screen_name}")
        except Exception as e:
            print(f"❌ Ошибка создания экрана {screen_name}: {e}")
            import traceback
            traceback.print_exc()
            return

        self.sm.current = screen_name
        print(f"✅ Переключено на {screen_name}")

    def go_to_menu(self):
        """Возврат в меню"""
        self.switch_to_screen('menu')

    def on_pause(self):
        print("📱 [App] on_pause - приложение свернуто")
        if hasattr(self, 'sound_mgr'):
            self.sound_mgr.pause()
        return True

    def on_resume(self):
        print("📱 [App] on_resume - приложение восстановлено")

        # ✅ Если приложение находится в процессе завершения — не запускаем звук
        if self._is_stopping:
            print("🔊 [App] on_resume: приложение завершается, звук не запускаем")
            return

        if hasattr(self, 'sound_mgr'):
            if not self.sound_mgr.is_muted():
                self.sound_mgr.play()

        if hasattr(self, 'update_mgr'):
            Clock.schedule_once(lambda dt: self.update_mgr.check_for_updates(False), 2)

    def on_stop(self):
        """✅ Вызывается при закрытии приложения.
        Жёстко останавливаем музыку, чтобы не было всплеска громкости."""
        print("🛑 [App] on_stop — приложение закрывается")

        self._is_stopping = True

        if hasattr(self, 'sound_mgr') and self.sound_mgr:
            try:
                self.sound_mgr.hard_stop()
            except Exception as e:
                print(f"⚠️ [App] Ошибка hard_stop: {e}")

        try:
            Clock.unschedule_all()
        except Exception:
            pass

        print("👋 [App] Ресурсы освобождены")

    def _(self, key):
        return self.lang._(key)


def switch_screen(screen_name, **kwargs):
    """Глобальная функция для переключения экранов"""
    app = App.get_running_app()
    if hasattr(app, 'switch_to_screen'):
        app.switch_to_screen(screen_name, **kwargs)
    else:
        app.sm.current = screen_name


if __name__ == '__main__':
    print("🎮 Запуск Almighty Random...")
    AlmightyRandomApp().run()
    print("👋 Приложение завершено")