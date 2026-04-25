import os
import sys
import requests
import threading
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.utils import platform
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout

# --- ЖИВАЯ СИНХРОНИЗАЦИЯ ЧЕРЕЗ ADB PUSH ---
if platform == 'android':
    # Папка для синхронизации (внутренняя папка приложения)
    sync_path = "/data/data/org.yourdomain.almightyrandom/files/sync"
    
    # Создаем папку если её нет
    if not os.path.exists(sync_path):
        os.makedirs(sync_path)
    
    # Добавляем в путь поиска модулей
    if sync_path not in sys.path:
        sys.path.insert(0, sync_path)
    
    # Меняем рабочую директорию
    os.chdir(sync_path)
    print(f"DEBUG: ЖИВАЯ СИНХРОНИЗАЦИЯ - {sync_path}")
# -----------------------------------------

# Импорты ваших модулей
from language_manager import LanguageManager
from sound_manager import SoundManager

from screens.menu_screen import MainMenuScreen
from screens.coin_screen import CoinScreen
from screens.dice_screen import DiceScreen
from screens.roulette_screen import RouletteScreen
from screens.rus_roulette_screen import RusRouletteScreen
from screens.quiz_screen import QuizScreen
from screens.random_screen import RandomScreen
from screens.random_number import RandomNumberScreen
from screens.magic_ball_screen import MagicBallScreen
from screens.intermediate_roulette import IntermediateRoulette
from screens.intermediate_random import IntermediateRandom
from screens.rsp_screen import RSPScreen


class UpdateManager:
    """Класс для обновления APK через Wi-Fi"""
    
    def __init__(self, app):
        self.app = app
        # ЗАМЕНИТЕ НА IP ВАШЕГО КОМПЬЮТЕРА
        self.server_url = "http://192.168.0.50:8000"
        self.current_version = "1.0.0"
        
    def check_for_updates(self, show_notification=True):
        """Проверка наличия новой версии APK на сервере"""
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
                else:
                    print("Сервер обновлений не отвечает")
                    
            except Exception as e:
                print(f"Ошибка проверки обновлений: {e}")
                
        thread = threading.Thread(target=check)
        thread.daemon = True
        thread.start()
    
    def show_update_dialog(self, new_version, apk_url):
        """Диалог предложения обновления"""
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
        """Скачивание и установка нового APK"""
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
                                Clock.schedule_once(
                                    lambda dt, p=progress: setattr(pb, 'value', p)
                                )
                
                Clock.schedule_once(
                    lambda dt: self.install_apk(apk_path, popup)
                )
                
            except Exception as e:
                Clock.schedule_once(
                    lambda dt: self.show_message("Ошибка", f"Не удалось скачать:\n{str(e)}")
                )
                popup.dismiss()
        
        popup.open()
        threading.Thread(target=download).start()
    
    def install_apk(self, apk_path, popup):
        """Запуск установщика APK"""
        popup.dismiss()
        
        if platform == 'android':
            try:
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                
                intent = Intent(Intent.ACTION_VIEW)
                intent.setDataAndType(
                    Uri.fromFile(File(apk_path)),
                    "application/vnd.android.package-archive"
                )
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                PythonActivity.mActivity.startActivity(intent)
                self.show_message("Готово", "Запуск установщика...")
                
            except Exception as e:
                self.show_message("Ошибка", f"Не удалось запустить установку:\n{str(e)}")
        else:
            self.show_message("Установка", "На ПК установка не поддерживается")
    
    def show_message(self, title, message):
        """Простое сообщение"""
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=message))
        
        btn = Button(text="OK", size_hint_y=0.3)
        content.add_widget(btn)
        
        popup = Popup(title=title, content=content, size_hint=(0.7, 0.3))
        btn.bind(on_press=popup.dismiss)
        popup.open()


class SportsGameApp(App):
    def build(self):
        # Настройка окна
        if platform == 'android':
            Window.fullscreen = 'auto'
        else:
            Window.size = (400, 700)

        Window.clearcolor = (0.1, 0.1, 0.1, 1)

        # Инициализация менеджеров
        self.lang = LanguageManager()
        self.sound_mgr = SoundManager()
        self.update_mgr = UpdateManager(self)
        
        # Звук
        self.sound_mgr.initialize("assets/sounds/background.wav")

        # Экраны
        self.sm = ScreenManager(transition=FadeTransition(duration=0.3))

        screens = [
            MainMenuScreen(name='menu'),
            MagicBallScreen(name='magic_ball'),
            CoinScreen(name='coin'),
            DiceScreen(name='dice'),
            RouletteScreen(name='roulette'),
            RusRouletteScreen(name='rus_roulette'),
            RandomScreen(name='random'),
            QuizScreen(name='quiz'),
            RandomNumberScreen(name='random_number'),
            RSPScreen(name='rsp'),
            IntermediateRoulette(name='intermediate_roulette'),
            IntermediateRandom(name='intermediate_random')
        ]

        for screen in screens:
            self.sm.add_widget(screen)

        # Запуск музыки
        Clock.schedule_once(lambda dt: self.sound_mgr.play(), 0.5)
        
        # Проверка обновлений через 5 секунд после запуска
        Clock.schedule_once(lambda dt: self.update_mgr.check_for_updates(False), 5)

        return self.sm

    def on_pause(self):
        if hasattr(self, 'sound_mgr'):
            self.sound_mgr.pause()
        return True

    def on_resume(self):
        if hasattr(self, 'sound_mgr'):
            self.sound_mgr.play()
        # Проверка обновлений при возврате в приложение
        if hasattr(self, 'update_mgr'):
            Clock.schedule_once(lambda dt: self.update_mgr.check_for_updates(False), 2)

    def _(self, key):
        return self.lang._(key)


if __name__ == '__main__':
    SportsGameApp().run()
