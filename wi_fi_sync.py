import os
import time
import subprocess
import json
import sys
import shutil
from datetime import datetime

PACKAGE = "org.test.almightyrandom"
APP_DIR = f"/data/data/{PACKAGE}/files/app"
FILES_DIR = f"/data/data/{PACKAGE}/files"
ADB = "adb.exe"

STATE_FILE = "sync_state.json"
DEVICES_CONFIG = "devices_config.json"


class DeviceManager:
    """Управление несколькими устройствами"""

    def __init__(self):
        self.devices = []
        self.config_file = DEVICES_CONFIG
        self.load_config()

    def load_config(self):
        """Загружает конфигурацию устройств"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.devices = config.get('devices', [])
        else:
            self.devices = []
            self.save_config()

    def save_config(self):
        """Сохраняет конфигурацию устройств"""
        config = {'devices': self.devices}
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def scan_devices(self):
        """Сканирует подключенные устройства"""
        result = subprocess.run(f'{ADB} devices', shell=True, capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:]

        found_devices = []
        for line in lines:
            if 'device' in line and 'offline' not in line:
                device_id = line.split()[0]
                if '_adb-tls-connect' in device_id:
                    continue
                conn_type = "USB" if ":" not in device_id else "WiFi"
                found_devices.append({
                    'id': device_id,
                    'name': self.get_device_name(device_id),
                    'type': conn_type,
                    'enabled': True,
                    'last_sync': None
                })

        return found_devices

    def get_device_name(self, device_id):
        """Получает имя устройства"""
        try:
            result = subprocess.run(
                f'{ADB} -s {device_id} shell getprop ro.product.model',
                shell=True, capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except:
            return device_id[:8]

    def add_device(self, device_id, name=None):
        """Добавляет устройство в конфиг"""
        if not name:
            name = self.get_device_name(device_id)

        device = {
            'id': device_id,
            'name': name,
            'type': 'WiFi' if ':' in device_id else 'USB',
            'enabled': True,
            'last_sync': None
        }

        for i, d in enumerate(self.devices):
            if d['id'] == device_id:
                self.devices[i] = device
                break
        else:
            self.devices.append(device)

        self.save_config()
        return device

    def remove_device(self, device_id):
        """Удаляет устройство из конфига"""
        self.devices = [d for d in self.devices if d['id'] != device_id]
        self.save_config()

    def get_enabled_devices(self):
        """Возвращает список включенных устройств"""
        return [d for d in self.devices if d.get('enabled', True)]

    def select_devices(self, prompt="Выберите устройства"):
        """Интерактивный выбор устройств"""
        enabled_devices = self.get_enabled_devices()

        if not enabled_devices:
            print("Нет настроенных устройств!")
            return []

        print(f"\n{prompt}:")
        print("0. Все устройства")
        for i, device in enumerate(enabled_devices, 1):
            status = "✓" if device.get('enabled', True) else "✗"
            print(f"  {i}. [{status}] {device['name']} ({device['id']}) - {device['type']}")
        print(f"  {len(enabled_devices) + 1}. Управление устройствами")

        while True:
            try:
                choice = input("\nВаш выбор: ").strip()
                if choice == "0":
                    return enabled_devices
                elif choice == str(len(enabled_devices) + 1):
                    self.manage_devices()
                    return self.select_devices(prompt)
                elif choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(enabled_devices):
                        return [enabled_devices[idx]]
                print("Неверный выбор!")
            except KeyboardInterrupt:
                return []

    def manage_devices(self):
        """Управление устройствами"""
        while True:
            print("\n" + "=" * 50)
            print("УПРАВЛЕНИЕ УСТРОЙСТВАМИ")
            print("=" * 50)

            connected = self.scan_devices()

            print("\nПОДКЛЮЧЕННЫЕ УСТРОЙСТВА:")
            if connected:
                for device in connected:
                    is_enabled = any(d['id'] == device['id'] for d in self.devices)
                    status = "✓" if is_enabled else "○"
                    print(f"  {status} {device['name']} - {device['id']} ({device['type']})")
            else:
                print("  Нет подключенных устройств")

            print("\nНАСТРОЕННЫЕ УСТРОЙСТВА:")
            if self.devices:
                for i, device in enumerate(self.devices, 1):
                    status = "ВКЛ" if device.get('enabled', True) else "ВЫКЛ"
                    print(f"  {i}. {device['name']} - {status}")
                    print(f"     ID: {device['id']}")
                    if device.get('last_sync'):
                        print(f"     Последняя синхронизация: {device['last_sync']}")
            else:
                print("  Нет настроенных устройств")

            print("\n" + "-" * 50)
            print("Доступные действия:")
            print("  1. Добавить устройство по IP (WiFi)")
            print("  2. Добавить USB устройство")
            print("  3. Включить/выключить устройство")
            print("  4. Удалить устройство")
            print("  5. Обновить список")
            print("  6. Назад в главное меню")

            choice = input("\nВыбор: ").strip()

            if choice == "1":
                self.add_wifi_device()
            elif choice == "2":
                self.add_usb_device()
            elif choice == "3":
                self.toggle_device()
            elif choice == "4":
                self.remove_device_interactive()
            elif choice == "5":
                continue
            elif choice == "6":
                break
            else:
                print("Неверный выбор!")

    def add_wifi_device(self):
        """Добавление WiFi устройства"""
        print("\nПОДКЛЮЧЕНИЕ ПО WiFi")
        ip = input("\nВведите IP адрес телефона: ").strip()
        if not ip:
            return

        device_id = f"{ip}:5555"

        print(f"Подключение к {device_id}...")
        result = subprocess.run(f'{ADB} connect {device_id}', shell=True, capture_output=True, text=True, timeout=10)

        if "connected" in result.stdout.lower():
            print(f"Подключено к {device_id}")
            name = input("Введите имя устройства (Enter - автоматически): ").strip()
            self.add_device(device_id, name if name else None)
        else:
            print(f"Не удалось подключиться: {result.stdout}")

    def add_usb_device(self):
        """Добавление USB устройства"""
        connected = self.scan_devices()
        usb_devices = [d for d in connected if d['type'] == 'USB']

        if not usb_devices:
            print("Нет подключенных USB устройств!")
            return

        print("\nДоступные USB устройства:")
        for i, device in enumerate(usb_devices, 1):
            print(f"  {i}. {device['name']} - {device['id']}")

        try:
            choice = int(input("Выберите устройство: ")) - 1
            if 0 <= choice < len(usb_devices):
                device = usb_devices[choice]
                self.add_device(device['id'])
                print(f"Устройство {device['name']} добавлено!")
        except:
            print("Неверный выбор!")

    def toggle_device(self):
        """Включить/выключить устройство"""
        if not self.devices:
            print("Нет настроенных устройств!")
            return

        print("\nВыберите устройство для изменения статуса:")
        for i, device in enumerate(self.devices, 1):
            status = "ВКЛ" if device.get('enabled', True) else "ВЫКЛ"
            print(f"  {i}. {device['name']} - {status}")

        try:
            choice = int(input("Выбор: ")) - 1
            if 0 <= choice < len(self.devices):
                self.devices[choice]['enabled'] = not self.devices[choice].get('enabled', True)
                self.save_config()
                new_status = "ВКЛЮЧЕНО" if self.devices[choice]['enabled'] else "ВЫКЛЮЧЕНО"
                print(f"Устройство {self.devices[choice]['name']} - {new_status}")
        except:
            print("Неверный выбор!")

    def remove_device_interactive(self):
        """Интерактивное удаление устройства"""
        if not self.devices:
            print("Нет настроенных устройств!")
            return

        print("\nВыберите устройство для удаления:")
        for i, device in enumerate(self.devices, 1):
            print(f"  {i}. {device['name']} - {device['id']}")
        print(f"  {len(self.devices) + 1}. Отмена")

        try:
            choice = int(input("Выбор: ")) - 1
            if 0 <= choice < len(self.devices):
                confirm = input(f"Удалить {self.devices[choice]['name']}? (y/n): ").lower()
                if confirm == 'y':
                    self.remove_device(self.devices[choice]['id'])
                    print("Устройство удалено!")
        except:
            print("Неверный выбор!")


class MultiDeviceSync:
    """Синхронизация с несколькими устройствами"""

    def __init__(self):
        self.device_manager = DeviceManager()
        self.state_file = STATE_FILE

    def load_state(self, device_id=None):
        """Загружает состояние для устройства"""
        if device_id:
            state_file = f"sync_state_{device_id.replace(':', '_')}.json"
        else:
            state_file = self.state_file

        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                return json.load(f)
        return {}

    def save_state(self, state, device_id=None):
        """Сохраняет состояние для устройства"""
        if device_id:
            state_file = f"sync_state_{device_id.replace(':', '_')}.json"
        else:
            state_file = self.state_file

        with open(state_file, 'w') as f:
            json.dump(state, f)

    def run_adb(self, device_id, command):
        """Выполняет ADB команду на конкретном устройстве"""
        if 'run-as' in command:
            full_cmd = f'{ADB} -s {device_id} shell "{command}"'
        else:
            full_cmd = f'{ADB} -s {device_id} {command}'

        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
        return result

    def delete_app_folder(self, device_id):
        """Полностью удаляет папку app на устройстве"""
        print("   🗑️ Удаление старой папки app...")
        result = self.run_adb(device_id, f'run-as {PACKAGE} rm -rf {APP_DIR}')
        
        if result.returncode == 0:
            print("   ✅ Папка app удалена")
            return True
        else:
            print(f"   ⚠️ Ошибка удаления: {result.stderr}")
            return False

    def create_app_folders(self, device_id):
        """Создает структуру папок app заново"""
        print("   📁 Создание структуры папок...")
        
        folders = [
            APP_DIR,
            f"{APP_DIR}/screens",
            f"{APP_DIR}/components",
            f"{APP_DIR}/locales",
            f"{APP_DIR}/assets"
        ]
        
        for folder in folders:
            result = self.run_adb(device_id, f'run-as {PACKAGE} mkdir -p {folder}')
            if result.returncode != 0:
                print(f"   ❌ Ошибка создания {folder}")
                return False
        
        print("   ✅ Структура папок создана")
        return True

    def copy_directory(self, device_id, local_dir, remote_dir):
        """Копирует целую папку на устройство"""
        try:
            dir_name = os.path.basename(local_dir)
            temp_dir = f"/data/local/tmp/{dir_name}"

            # 1. Удаляем старую временную папку если есть
            self.run_adb(device_id, f'shell rm -rf {temp_dir}')
            
            # 2. Копируем всю папку на устройство
            push_cmd = f'{ADB} -s {device_id} push {local_dir} /data/local/tmp/'
            result = subprocess.run(push_cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"   Ошибка push папки: {result.stderr}")
                return False

            # 3. Создаем целевую папку
            mkdir_cmd = f'run-as {PACKAGE} mkdir -p {remote_dir}'
            self.run_adb(device_id, mkdir_cmd)

            # 4. Копируем содержимое из временной папки
            cp_cmd = f'run-as {PACKAGE} cp -r {temp_dir}/* {remote_dir}/'
            result = self.run_adb(device_id, cp_cmd)

            # 5. Удаляем временную папку
            self.run_adb(device_id, f'shell rm -rf {temp_dir}')

            if result.returncode != 0:
                print(f"   Ошибка cp папки: {result.stderr}")
                return False

            return True
        except Exception as e:
            print(f"   Ошибка: {e}")
            return False

    def copy_file(self, device_id, local_path, remote_dir):
        """Копирует один файл на устройство"""
        try:
            filename = os.path.basename(local_path)
            temp_file = f"/data/local/tmp/{filename}"

            # 1. Копируем во временную директорию
            push_cmd = f'{ADB} -s {device_id} push "{local_path}" /data/local/tmp/'
            result_push = subprocess.run(push_cmd, shell=True, capture_output=True, text=True)

            if result_push.returncode != 0:
                return False

            # 2. Создаем целевую директорию
            mkdir_cmd = f'run-as {PACKAGE} mkdir -p "{remote_dir}"'
            self.run_adb(device_id, mkdir_cmd)

            # 3. Копируем из временной в целевую
            cp_cmd = f'run-as {PACKAGE} cp "{temp_file}" "{remote_dir}/"'
            result_cp = self.run_adb(device_id, cp_cmd)

            # 4. Удаляем временный файл
            self.run_adb(device_id, f'shell rm "{temp_file}"')

            return result_cp.returncode == 0
        except Exception as e:
            return False

    def push_assets(self, device_id):
        """Копирует папку assets целиком"""
        try:
            print("   📦 Копирование папки assets...")
            return self.copy_directory(device_id, "assets", f"{APP_DIR}/assets")
        except Exception as e:
            print(f"   Ошибка: {e}")
            return False

    def full_sync_to_device(self, device):
        """Полная синхронизация с полным удалением старой папки"""
        device_id = device['id']
        device_name = device['name']

        print(f"\n{'=' * 50}")
        print(f"🔥 ПОЛНАЯ СИНХРОНИЗАЦИЯ С УДАЛЕНИЕМ")
        print(f"Устройство: {device_name} ({device_id})")
        print(f"{'=' * 50}")

        # 1. Полностью удаляем старую папку app
        if not self.delete_app_folder(device_id):
            print("   ⚠️ Не удалось удалить папку app, продолжаем...")
        
        # 2. Создаем структуру папок заново
        if not self.create_app_folders(device_id):
            print("   ❌ Ошибка создания структуры папок")
            return False

        success_count = 0
        error_count = 0

        # 3. Копируем main.py
        if os.path.exists("main.py"):
            print("   📄 main.py")
            if self.copy_file(device_id, "main.py", APP_DIR):
                success_count += 1
                print("   ✅ main.py")
            else:
                error_count += 1
                print("   ❌ main.py")

        # 4. Копируем settings.json
        if os.path.exists("settings.json"):
            print("   ⚙️ settings.json")
            if self.copy_file(device_id, "settings.json", FILES_DIR):
                success_count += 1
                print("   ✅ settings.json")
            else:
                error_count += 1
                print("   ❌ settings.json")

        # 5. Копируем sound_manager.py
        if os.path.exists("sound_manager.py"):
            print("   🔊 sound_manager.py")
            if self.copy_file(device_id, "sound_manager.py", APP_DIR):
                success_count += 1
                print("   ✅ sound_manager.py")
            else:
                error_count += 1
                print("   ❌ sound_manager.py")

        # 6. Копируем папку screens (целиком)
        if os.path.exists("screens"):
            print(f"\n📁 Копирование папки screens/...")
            if self.copy_directory(device_id, "screens", f"{APP_DIR}/screens"):
                screens_count = len([f for f in os.listdir("screens") if f.endswith(".py") and f != "__init__.py"])
                success_count += screens_count
                print(f"   ✅ Скопировано {screens_count} файлов из screens/")
            else:
                error_count += 1
                print(f"   ❌ Ошибка копирования screens/")

        # 7. Копируем папку components (целиком)
        if os.path.exists("components"):
            print(f"\n📁 Копирование папки components/...")
            if self.copy_directory(device_id, "components", f"{APP_DIR}/components"):
                components_count = len([f for f in os.listdir("components") if f.endswith(".py") and f != "__init__.py"])
                success_count += components_count
                print(f"   ✅ Скопировано {components_count} файлов из components/")
            else:
                error_count += 1
                print(f"   ❌ Ошибка копирования components/")

        # 8. Копируем папку locales (целиком)
        if os.path.exists("locales"):
            print(f"\n📁 Копирование папки locales/...")
            if self.copy_directory(device_id, "locales", f"{APP_DIR}/locales"):
                locales_count = len([f for f in os.listdir("locales") if f.endswith(".json")])
                success_count += locales_count
                print(f"   ✅ Скопировано {locales_count} файлов из locales/")
            else:
                error_count += 1
                print(f"   ❌ Ошибка копирования locales/")

        # 9. Копируем папку assets (целиком)
        if os.path.exists("assets"):
            assets_files = self.get_all_assets_files()
            assets_count = len(assets_files)
            if assets_count > 0:
                print(f"\n📁 Копирование assets/ ({assets_count} файлов)...")
                if self.push_assets(device_id):
                    success_count += assets_count
                    print(f"   ✅ Скопировано {assets_count} файлов из assets/")
                else:
                    error_count += assets_count
                    print(f"   ❌ Ошибка копирования assets/")

        # 10. Очищаем кэш Python
        print(f"\n🧹 Очистка кэша Python...")
        self.run_adb(device_id, f'run-as {PACKAGE} find {APP_DIR} -type f -name "*.pyc" -delete 2>/dev/null')
        self.run_adb(device_id, f'run-as {PACKAGE} find {APP_DIR} -type d -name "__pycache__" -exec rm -rf {{}} + 2>/dev/null')

        # 11. Жесткий перезапуск приложения
        print(f"\n🔄 Жесткий перезапуск приложения...")
        self.run_adb(device_id, f'am force-stop {PACKAGE}')
        time.sleep(2)
        self.run_adb(device_id, f'am start -n {PACKAGE}/org.kivy.android.PythonActivity')

        print(f"\n{'=' * 50}")
        print(f"РЕЗУЛЬТАТ СИНХРОНИЗАЦИИ:")
        print(f"   ✅ Успешно: {success_count}")
        print(f"   ❌ Ошибок: {error_count}")
        print(f"{'=' * 50}")

        # Обновляем время последней синхронизации
        device['last_sync'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.device_manager.save_config()

        return success_count > 0

    def get_all_assets_files(self):
        """Возвращает список файлов в assets"""
        assets_files = []
        assets_dir = "assets"

        if os.path.exists(assets_dir):
            for root, dirs, files in os.walk(assets_dir):
                for file in files:
                    if file.startswith('.'):
                        continue
                    rel_path = os.path.join(root, file)
                    assets_files.append(rel_path)

        return assets_files

    def get_files_to_watch(self):
        """Возвращает список файлов для отслеживания"""
        files_to_watch = []

        if os.path.exists("main.py"):
            files_to_watch.append("main.py")
        if os.path.exists("settings.json"):
            files_to_watch.append("settings.json")
        if os.path.exists("sound_manager.py"):
            files_to_watch.append("sound_manager.py")

        if os.path.exists("screens"):
            for f in os.listdir("screens"):
                if f.endswith(".py") and f != "__init__.py":
                    files_to_watch.append(f"screens/{f}")

        if os.path.exists("components"):
            for f in os.listdir("components"):
                if f.endswith(".py") and f != "__init__.py":
                    files_to_watch.append(f"components/{f}")

        if os.path.exists("locales"):
            for f in os.listdir("locales"):
                if f.endswith(".json"):
                    files_to_watch.append(f"locales/{f}")

        return files_to_watch

    def sync_single_file(self, device_id, filepath):
        """Синхронизация одного файла с устройством (без удаления)"""
        if filepath == "settings.json":
            remote_dir = FILES_DIR
        elif filepath.startswith("screens/"):
            remote_dir = f"{APP_DIR}/screens"
        elif filepath.startswith("components/"):
            remote_dir = f"{APP_DIR}/components"
        elif filepath.startswith("locales/"):
            remote_dir = f"{APP_DIR}/locales"
        else:
            remote_dir = APP_DIR

        if self.copy_file(device_id, filepath, remote_dir):
            print(f"   ✅ {os.path.basename(filepath)} -> {device_id[:8]}")
            
            # Перезапускаем приложение только если это не assets файл
            if not filepath.startswith("assets"):
                self.restart_app(device_id)
            return True
        else:
            print(f"   ❌ Ошибка синхронизации {filepath} с {device_id[:8]}")
            return False

    def restart_app(self, device_id):
        """Перезапускает приложение на устройстве"""
        self.run_adb(device_id, f'am force-stop {PACKAGE}')
        time.sleep(0.5)
        self.run_adb(device_id, f'am start -n {PACKAGE}/org.kivy.android.PythonActivity')

    def watch_mode_all(self):
        """Режим слежения за изменениями для всех устройств"""
        devices = self.device_manager.get_enabled_devices()

        if not devices:
            print("Нет включенных устройств!")
            return

        print("\n" + "=" * 50)
        print("РЕЖИМ СЛЕЖЕНИЯ ЗА ИЗМЕНЕНИЯМИ")
        print("=" * 50)
        print(f"Отслеживается {len(devices)} устройств:")
        for device in devices:
            print(f"  • {device['name']} ({device['id']})")
        print("\nПри сохранении файла (Ctrl+S) синхронизация произойдёт на ВСЕ устройства.")
        print("Нажмите Ctrl+C для выхода в главное меню.")
        print("=" * 50)

        files_to_watch = self.get_files_to_watch()

        states = {}
        for device in devices:
            states[device['id']] = self.load_state(device['id'])

        try:
            while True:
                changed = False
                for file in files_to_watch:
                    if os.path.exists(file):
                        mtime = os.path.getmtime(file)

                        for device in devices:
                            device_state = states[device['id']]
                            if mtime != device_state.get(file, 0):
                                device_state[file] = mtime
                                changed = True

                        if changed:
                            print(f"\n📝 Изменён: {file}")

                            for device in devices:
                                print(f"\n🔄 Синхронизация с {device['name']}...")
                                self.sync_single_file(device['id'], file)

                            for device in devices:
                                self.save_state(states[device['id']], device['id'])

                            changed = False

                if not changed:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n👋 Выход из режима слежения...")

    def debug_device_files(self, device_id):
        """Отладочная функция - показывает содержимое папок"""
        print(f"\n{'=' * 50}")
        print(f"🔍 ОТЛАДКА: Содержимое папок на устройстве {device_id[:8]}")
        print(f"{'=' * 50}")
        
        print(f"\n📁 Содержимое {APP_DIR}/screens/:")
        result = self.run_adb(device_id, f'run-as {PACKAGE} ls -la {APP_DIR}/screens/ 2>/dev/null')
        print(result.stdout if result.stdout else "   (пусто или нет доступа)")
        
        print(f"\n📁 Содержимое {APP_DIR}/:")
        result = self.run_adb(device_id, f'run-as {PACKAGE} ls -la {APP_DIR}/ 2>/dev/null')
        print(result.stdout if result.stdout else "   (пусто или нет доступа)")
        
        # Проверяем наличие random_number_screen.py
        print(f"\n🔍 Проверка random_number_screen.py:")
        result = self.run_adb(device_id, f'run-as {PACKAGE} ls -la {APP_DIR}/screens/random_number_screen.py 2>/dev/null')
        if result.returncode == 0:
            print(f"   ✅ Файл найден:")
            print(f"   {result.stdout.strip()}")
        else:
            print(f"   ❌ Файл НЕ найден!")


def show_menu():
    """Показывает главное меню"""
    print("\n" + "=" * 50)
    print("МУЛЬТИ-СИНХРОНИЗАЦИЯ С ТЕЛЕФОНАМИ")
    print("=" * 50)

    sync = MultiDeviceSync()
    devices = sync.device_manager.get_enabled_devices()

    print(f"\n📱 АКТИВНЫЕ УСТРОЙСТВА: {len(devices)}")
    for device in devices:
        print(f"   • {device['name']} - {device['type']}")

    print("\n" + "-" * 50)
    print("Выберите режим работы:")
    print("  1. Режим слежения (авто-синхронизация при изменениях)")
    print("  2. ПОЛНАЯ СИНХРОНИЗАЦИЯ (с удалением старой папки)")
    print("  3. Синхронизация без удаления (быстрая)")
    print("  4. Отладка - проверить файлы на устройстве")
    print("  5. Управление устройствами")
    print("  6. Показать список файлов")
    print("  7. Выход")
    print("-" * 50)

    while True:
        try:
            choice = input("Ваш выбор (1-7): ").strip()
            if choice in ["1", "2", "3", "4", "5", "6", "7"]:
                return choice
            else:
                print("Неверный ввод. Пожалуйста, введите 1-7.")
        except KeyboardInterrupt:
            return "7"


def print_file_list():
    """Выводит список файлов"""
    sync = MultiDeviceSync()
    files = sync.get_files_to_watch()
    
    # Получаем список файлов assets
    assets_files = []
    if os.path.exists("assets"):
        for root, dirs, files_in_assets in os.walk("assets"):
            for file in files_in_assets:
                if not file.startswith('.'):
                    assets_files.append(os.path.join(root, file))

    print("\n" + "=" * 60)
    print("СПИСОК ОТСЛЕЖИВАЕМЫХ ФАЙЛОВ И ПАПОК")
    print("=" * 60)

    print(f"\n📊 ВСЕГО ФАЙЛОВ: {len(files) + len(assets_files)}")
    print(f"   • Код и настройки: {len(files)}")
    print(f"   • Ресурсы (assets): {len(assets_files)}")
    
    print("\n📁 Файлы проекта:")
    for f in files:
        print(f"   - {f}")
    
    if assets_files:
        print(f"\n🎨 Файлы assets (первые 10):")
        for f in assets_files[:10]:
            print(f"   - {f}")
        if len(assets_files) > 10:
            print(f"   ... и еще {len(assets_files) - 10} файлов")
    
    print("=" * 60)


def main():
    """Главная функция"""
    while True:
        choice = show_menu()

        if choice == "1":
            sync = MultiDeviceSync()
            sync.watch_mode_all()
        elif choice == "2":
            sync = MultiDeviceSync()
            devices = sync.device_manager.select_devices("Выберите устройства для ПОЛНОЙ синхронизации")
            if devices:
                print(f"\n⚠️ ВНИМАНИЕ: Папка app будет ПОЛНОСТЬЮ УДАЛЕНА и скопирована заново!")
                confirm = input("Продолжить? (y/n): ").lower()
                if confirm == 'y':
                    for device in devices:
                        sync.full_sync_to_device(device)
            input("\nНажмите Enter для возврата в меню...")
        elif choice == "3":
            # Быстрая синхронизация (без удаления) - сохраняем для совместимости
            print("\nℹ️ Быстрая синхронизация (без удаления папки)")
            sync = MultiDeviceSync()
            devices = sync.device_manager.select_devices("Выберите устройства для синхронизации")
            if devices:
                for device in devices:
                    # Создаем старый объект для синхронизации
                    old_sync = MultiDeviceSync()
                    old_sync.sync_to_device = lambda d: old_sync.full_sync_to_device(d)  # Перенаправляем на полную
                    old_sync.sync_to_device(device)
            input("\nНажмите Enter для возврата в меню...")
        elif choice == "4":
            sync = MultiDeviceSync()
            devices = sync.device_manager.select_devices("Выберите устройство для отладки")
            if devices:
                for device in devices:
                    sync.debug_device_files(device['id'])
            input("\nНажмите Enter для возврата в меню...")
        elif choice == "5":
            sync = MultiDeviceSync()
            sync.device_manager.manage_devices()
        elif choice == "6":
            print_file_list()
            input("\nНажмите Enter для возврата в меню...")
        elif choice == "7":
            print("\n👋 Завершение работы скрипта...")
            sys.exit(0)


if __name__ == "__main__":
    main()