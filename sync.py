import os
import time
import subprocess
import json
import sys
import threading
from datetime import datetime

PACKAGE = "org.almighty.almightyrandom"
APP_DIR = f"/data/data/{PACKAGE}/files/app"
ADB = "adb.exe"

# Файл для сохранения состояния
STATE_FILE = "sync_state.json"
# Файл для сохранения выбранного устройства
DEVICE_STATE_FILE = "device_state.json"


def get_adb_devices():
    """Получает список подключенных устройств"""
    result = subprocess.run(f"{ADB} devices", shell=True, capture_output=True, text=True, encoding='utf-8',
                            errors='ignore')
    lines = result.stdout.strip().split('\n')[1:]

    devices = []
    for line in lines:
        if line.strip() and 'device' in line:
            device_id = line.split()[0]
            devices.append(device_id)
    return devices


def load_selected_device():
    """Загружает сохранённое устройство"""
    if os.path.exists(DEVICE_STATE_FILE):
        with open(DEVICE_STATE_FILE, 'r') as f:
            data = json.load(f)
            return data.get('device')
    return None


def save_selected_device(device):
    """Сохраняет выбранное устройство"""
    with open(DEVICE_STATE_FILE, 'w') as f:
        json.dump({'device': device}, f)


def select_device():
    """Меню выбора устройства"""
    print("=" * 50)
    print("🔍 Поиск подключенных устройств...")
    print("=" * 50)

    devices = get_adb_devices()

    if not devices:
        print("❌ Не найдено ни одного подключенного устройства!")
        return None

    print(f"\n✅ Найдено устройств: {len(devices)}\n")

    for i, device in enumerate(devices, 1):
        try:
            result = subprocess.run(f"{ADB} -s {device} shell getprop ro.product.model",
                                    shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            model = result.stdout.strip()
            print(f"  {i}. {device} - {model}")
        except:
            print(f"  {i}. {device}")

    print("\n" + "=" * 50)
    print(" 0. Выход")
    print("=" * 50)

    while True:
        try:
            choice = input("\n👉 Выберите устройство: ")
            choice = int(choice)

            if choice == 0:
                return None
            elif 1 <= choice <= len(devices):
                selected = devices[choice - 1]
                print(f"\n✅ Выбрано устройство: {selected}")
                save_selected_device(selected)
                return selected
            else:
                print(f"❌ Неверный выбор")
        except ValueError:
            print("❌ Введите число!")
        except KeyboardInterrupt:
            return None


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def format_size(size):
    """Форматирует размер файла"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def get_assets_file_list(local_dir="assets"):
    """Рекурсивно получает список всех файлов в папке assets"""
    files = []
    if not os.path.exists(local_dir):
        return files

    for root, dirs, filenames in os.walk(local_dir):
        for filename in filenames:
            if filename.endswith(('.pyc', '.pyo', '.DS_Store')):
                continue
            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, local_dir)
            files.append({
                "full_path": full_path,
                "relative_path": relative_path.replace("\\", "/"),
                "name": filename,
                "size": os.path.getsize(full_path)
            })
    return files


def list_assets_files_with_numbers(local_dir="assets"):
    """Показывает все файлы в assets с номерами для выбора"""
    files = get_assets_file_list(local_dir)

    if not files:
        print("❌ В папке assets нет файлов")
        return {}

    print("\n" + "=" * 70)
    print("📁 ФАЙЛЫ В ПАПКЕ assets (будут скопированы с СОХРАНЕНИЕМ структуры папок):")
    print("=" * 70)

    files_by_folder = {}
    for file in files:
        folder = os.path.dirname(file["relative_path"])
        if not folder:
            folder = "(корень)"
        if folder not in files_by_folder:
            files_by_folder[folder] = []
        files_by_folder[folder].append(file)

    file_number = 1
    file_map = {}

    for folder in sorted(files_by_folder.keys()):
        print(f"\n📂 {folder}/")
        for file in files_by_folder[folder]:
            size_str = format_size(file["size"])
            print(f"   {file_number:3}. {file['name']} ({size_str}) -> {file['relative_path']}")
            file_map[file_number] = file
            file_number += 1

    print(f"\n📊 Всего файлов: {len(files)}")
    print("💡 При копировании будет сохранена ВСЯ структура папок")
    return file_map


def copy_single_file_to_assets(device):
    """Копирует один выбранный файл в папку assets на устройстве с сохранением структуры"""
    print("\n" + "=" * 50)
    print("📋 КОПИРОВАНИЕ ФАЙЛА В assets")
    print("=" * 50)

    file_map = list_assets_files_with_numbers("assets")

    if not file_map:
        print("❌ Нет файлов для копирования!")
        return

    while True:
        try:
            choice = input(f"\n👉 Выберите номер файла (1-{len(file_map)}) или 0 для выхода: ")
            choice = int(choice)

            if choice == 0:
                return
            elif 1 <= choice <= len(file_map):
                selected_file = file_map[choice]
                break
            else:
                print(f"❌ Введите число от 1 до {len(file_map)}")
        except ValueError:
            print("❌ Введите число!")

    print(f"\n📄 Выбран файл: {selected_file['relative_path']}")
    print(f"📏 Размер: {format_size(selected_file['size'])}")
    print(f"📁 Локальный путь: {selected_file['full_path']}")

    confirm = input("\n🔄 Скопировать файл на устройство? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Отменено")
        return

    print("\n🚀 Копирую файл...")

    target_file = f"{APP_DIR}/assets/{selected_file['relative_path']}"
    target_dir = os.path.dirname(target_file)

    print(f"   📂 Целевая папка: {target_dir}")
    print(f"   📄 Целевой файл: {target_file}")

    subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} mkdir -p {target_dir}"', shell=True)

    result_push = subprocess.run(f"{ADB} -s {device} push \"{selected_file['full_path']}\" /data/local/tmp/temp_file",
                                 shell=True, capture_output=True)
    if result_push.returncode != 0:
        print(f"❌ Ошибка при копировании на устройство: {result_push.stderr}")
        return

    result_cp = subprocess.run(
        f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/temp_file {target_file}"', shell=True,
        capture_output=True)
    if result_cp.returncode != 0:
        print(f"❌ Ошибка при копировании в assets: {result_cp.stderr}")
        return

    subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {target_file}"', shell=True)

    print(f"✅ Файл скопирован: {selected_file['relative_path']}")

    check_result = subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} ls -la {target_file}"',
                                  shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if check_result.stdout.strip():
        print(f"   ✅ Файл найден на устройстве!")
        parts = check_result.stdout.strip().split()
        if len(parts) >= 5:
            print(f"   📏 Размер на устройстве: {parts[4]} байт")
    else:
        print(f"   ❌ Файл НЕ НАЙДЕН на устройстве!")

    restart = input("\n🔄 Перезапустить приложение? (y/n): ")
    if restart.lower() == 'y':
        print("🔄 Перезапускаем приложение...")
        subprocess.run(f"{ADB} -s {device} shell am force-stop {PACKAGE}", shell=True)
        time.sleep(1)
        subprocess.run(f"{ADB} -s {device} shell am start -n {PACKAGE}/org.kivy.android.PythonActivity", shell=True)
        print("✅ Приложение запущено")


def copy_multiple_files_to_assets(device):
    """Копирует несколько выбранных файлов в папку assets с сохранением структуры"""
    print("\n" + "=" * 50)
    print("📋 КОПИРОВАНИЕ НЕСКОЛЬКИХ ФАЙЛОВ В assets")
    print("=" * 50)

    file_map = list_assets_files_with_numbers("assets")

    if not file_map:
        return

    print("\n💡 Введите номера файлов через запятую (например: 1,3,5)")
    print("   Или укажите диапазон (например: 1-5)")
    print("   Или 'a' для выбора всех файлов")
    print("   Или '0' для выхода")

    while True:
        choice = input("\n👉 Выберите файлы: ").strip().lower()

        if choice == '0':
            return

        selected_numbers = set()

        if choice == 'a':
            selected_numbers = set(file_map.keys())
            print(f"✅ Выбраны все {len(selected_numbers)} файлов")
            break

        parts = choice.replace(' ', '').split(',')
        for part in parts:
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    for num in range(start, end + 1):
                        if 1 <= num <= len(file_map):
                            selected_numbers.add(num)
                except:
                    print(f"⚠️ Неверный диапазон: {part}")
            else:
                try:
                    num = int(part)
                    if 1 <= num <= len(file_map):
                        selected_numbers.add(num)
                    else:
                        print(f"⚠️ Число {num} вне диапазона (1-{len(file_map)})")
                except:
                    print(f"⚠️ Неверный ввод: {part}")

        if selected_numbers:
            print(f"✅ Выбрано файлов: {len(selected_numbers)}")
            break
        else:
            print("❌ Не выбрано ни одного файла! Попробуйте снова.")

    print("\n📋 Выбранные файлы:")
    for num in sorted(selected_numbers):
        print(f"   {num}. {file_map[num]['relative_path']} ({format_size(file_map[num]['size'])})")

    confirm = input(f"\n🔄 Скопировать {len(selected_numbers)} файл(ов) на устройство? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Отменено")
        return

    print("\n🚀 Начинаю копирование...\n")

    success_count = 0
    failed_count = 0

    for num in sorted(selected_numbers):
        file_info = file_map[num]
        target_file = f"{APP_DIR}/assets/{file_info['relative_path']}"
        target_dir = os.path.dirname(target_file)

        print(f"📄 {file_info['relative_path']}")

        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} mkdir -p {target_dir}"', shell=True)

        result_push = subprocess.run(f"{ADB} -s {device} push \"{file_info['full_path']}\" /data/local/tmp/temp_file",
                                     shell=True, capture_output=True)
        if result_push.returncode != 0:
            print(f"   ❌ Ошибка push: {result_push.stderr}")
            failed_count += 1
            continue

        result_cp = subprocess.run(
            f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/temp_file {target_file}"', shell=True,
            capture_output=True)
        if result_cp.returncode != 0:
            print(f"   ❌ Ошибка cp: {result_cp.stderr}")
            failed_count += 1
            continue

        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {target_file}"', shell=True)

        print(f"   ✅ Скопирован")
        success_count += 1

    print(f"\n✅ Успешно скопировано: {success_count}/{len(selected_numbers)} файлов")
    if failed_count > 0:
        print(f"❌ Ошибок: {failed_count}")

    restart = input("\n🔄 Перезапустить приложение? (y/n): ")
    if restart.lower() == 'y':
        print("Перезапускаем...")
        subprocess.run(f"{ADB} -s {device} shell am force-stop {PACKAGE}", shell=True)
        time.sleep(1)
        subprocess.run(f"{ADB} -s {device} shell am start -n {PACKAGE}/org.kivy.android.PythonActivity", shell=True)
        print("✅ Приложение запущено")


def sync_file(filepath, device):
    """Синхронизирует файл на выбранном устройстве"""
    filename = os.path.basename(filepath)
    print(f"🔄 {filepath}")

    subprocess.run(f"{ADB} -s {device} push {filepath} /data/local/tmp/", shell=True, capture_output=True)

    if filepath.startswith("screens/"):
        relative_path = filepath[8:]
        target_file = f"{APP_DIR}/screens/{relative_path}"
        target_dir = os.path.dirname(target_file)

        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} mkdir -p {target_dir}"', shell=True)

        subprocess.run(f"{ADB} -s {device} push {filepath} /data/local/tmp/temp_file", shell=True, capture_output=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/temp_file {target_file}"',
                       shell=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {target_file}"', shell=True)

    elif filepath.startswith("components/"):
        relative_path = filepath[11:]
        target_file = f"{APP_DIR}/components/{relative_path}"
        target_dir = os.path.dirname(target_file)

        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} mkdir -p {target_dir}"', shell=True)
        subprocess.run(f"{ADB} -s {device} push {filepath} /data/local/tmp/temp_file", shell=True, capture_output=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/temp_file {target_file}"',
                       shell=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {target_file}"', shell=True)

    elif filepath.startswith("locales/"):
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/{filename} {APP_DIR}/locales/"',
                       shell=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {APP_DIR}/locales/{filename}"', shell=True)

    elif filepath.startswith("assets/"):
        relative_path = filepath[7:]
        target_file = f"{APP_DIR}/assets/{relative_path}"
        target_dir = os.path.dirname(target_file)

        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} mkdir -p {target_dir}"', shell=True)

        subprocess.run(f"{ADB} -s {device} push {filepath} /data/local/tmp/temp_file", shell=True, capture_output=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/temp_file {target_file}"',
                       shell=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {target_file}"', shell=True)

    elif filepath == "main.py" or filepath == "sound_manager.py":
        # ✅ main.py и sound_manager.py лежат в корне проекта — кладём их в корень APP_DIR
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/{filename} {APP_DIR}/"',
                       shell=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {APP_DIR}/{filename}"', shell=True)

    print(f"   ✅ {filename}")


def sync_directory(local_dir, remote_dir, device):
    """Синхронизирует целую директорию (добавляет/обновляет файлы, не удаляя существующие)"""
    if not os.path.exists(local_dir):
        print(f"⚠️ Папка {local_dir} не существует")
        return

    print(f"📁 Синхронизация {local_dir}/")

    subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} mkdir -p {remote_dir}"', shell=True)

    for root, dirs, files in os.walk(local_dir):
        for file in files:
            if file.endswith(('.pyc', '.pyo', '.DS_Store')):
                continue

            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_dir)
            remote_path = f"{remote_dir}/{relative_path}".replace("\\", "/")
            remote_file_dir = os.path.dirname(remote_path)

            subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} mkdir -p {remote_file_dir}"', shell=True)

            subprocess.run(f"{ADB} -s {device} push {local_path} /data/local/tmp/temp_file", shell=True, capture_output=True)
            subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/temp_file {remote_path}"',
                           shell=True)
            subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {remote_path}"', shell=True)

            print(f"   ✅ {relative_path}")


def sync_selected_folders(device):
    """Выборочная синхронизация папок (БЕЗ УДАЛЕНИЯ существующих файлов)"""
    print("\n" + "=" * 50)
    print("📁 ВЫБОРОЧНАЯ СИНХРОНИЗАЦИЯ ПАПОК")
    print("=" * 50)

    folders = {
        "1": {"name": "screens", "local": "screens", "remote": f"{APP_DIR}/screens"},
        "2": {"name": "components", "local": "components", "remote": f"{APP_DIR}/components"},
        "3": {"name": "locales", "local": "locales", "remote": f"{APP_DIR}/locales"},
        "4": {"name": "assets", "local": "assets", "remote": f"{APP_DIR}/assets"},
        "5": {"name": "main.py", "local": "main.py", "remote": f"{APP_DIR}/main.py", "is_file": True},
        "6": {"name": "sound_manager.py", "local": "sound_manager.py", "remote": f"{APP_DIR}/sound_manager.py", "is_file": True},
    }

    available = []
    for key, folder in folders.items():
        if folder.get("is_file"):
            if os.path.exists(folder["local"]):
                available.append(key)
                print(f" {key}. {folder['name']} (файл)")
            else:
                print(f" {key}. {folder['name']} (файл) [НЕ СУЩЕСТВУЕТ]")
        else:
            if os.path.exists(folder["local"]):
                available.append(key)
                print(f" {key}. {folder['name']}/")
            else:
                print(f" {key}. {folder['name']}/ [НЕ СУЩЕСТВУЕТ]")

    print(f"\n a. Выбрать все")
    print(f" 0. Назад")
    print("=" * 50)

    while True:
        choice = input("\n👉 Выберите папки (через запятую, например: 1,2,4): ").strip().lower()

        if choice == '0':
            return
        elif choice == 'a':
            selected_keys = available
            print(f"\n✅ Выбраны все папки: {', '.join([folders[k]['name'] for k in selected_keys])}")
            break
        else:
            try:
                selected_keys = []
                parts = choice.replace(' ', '').split(',')
                for part in parts:
                    if part in available:
                        selected_keys.append(part)
                    elif part in folders and part not in available:
                        print(f"⚠️ Папка {folders[part]['name']} не существует локально")
                    elif part not in folders:
                        print(f"❌ Неверный выбор: {part}")

                if selected_keys:
                    print(f"\n✅ Выбраны: {', '.join([folders[k]['name'] for k in selected_keys])}")
                    break
                else:
                    print("❌ Не выбрано ни одной папки!")
            except:
                print("❌ Неверный формат!")

    confirm = input("\n🔄 Синхронизировать выбранные папки? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Отменено")
        return

    print("\n🚀 Начинаю синхронизацию...\n")

    if selected_keys != ['4']:
        print("⏹️ Останавливаем приложение...")
        subprocess.run(f"{ADB} -s {device} shell am force-stop {PACKAGE}", shell=True)
        time.sleep(1)

    for key in selected_keys:
        folder = folders[key]
        if folder.get("is_file"):
            print(f"\n📄 {folder['name']}")
            local_path = folder["local"]
            if os.path.exists(local_path):
                subprocess.run(f"{ADB} -s {device} push {local_path} /data/local/tmp/", shell=True, capture_output=True)
                subprocess.run(
                    f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/{os.path.basename(local_path)} {folder["remote"]}"',
                    shell=True)
                subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {folder["remote"]}"', shell=True)
                print(f"   ✅ {folder['name']}")
            else:
                print(f"   ❌ Файл не найден!")
        else:
            print(f"\n📁 {folder['name']}/")
            if os.path.exists(folder["local"]):
                sync_directory(folder["local"], folder["remote"], device)
            else:
                print(f"   ⚠️ Папка {folder['local']} не существует локально")

    print("\n🧹 Очищаем Python кэш...")
    subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} find {APP_DIR} -name *.pyc -delete"', shell=True)

    print("\n" + "=" * 50)
    print("✅ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА")
    print("=" * 50)

    if selected_keys != ['4']:
        print("\n🔄 Перезапускаем приложение...")
        time.sleep(1)
        subprocess.run(f"{ADB} -s {device} shell am start -n {PACKAGE}/org.kivy.android.PythonActivity", shell=True)

    show_logs = input("\n📋 Показать логи приложения? (y/n): ")
    if show_logs.lower() == 'y':
        show_app_logs(device)


def check_assets(device):
    """Проверяет наличие файлов assets на устройстве"""
    print("\n" + "=" * 50)
    print("🔍 ПРОВЕРКА ФАЙЛОВ ASSETS")
    print("=" * 50)

    result = subprocess.run(
        f'{ADB} -s {device} shell "run-as {PACKAGE} find {APP_DIR}/assets -type d 2>/dev/null"',
        shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')

    print("\n📁 Структура папок assets:")
    for line in result.stdout.strip().split('\n'):
        if line:
            print(f"   {line}")

    result = subprocess.run(
        f'{ADB} -s {device} shell "run-as {PACKAGE} find {APP_DIR}/assets -name *.png 2>/dev/null"',
        shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')

    print("\n🖼️ Найденные PNG файлы:")
    for line in result.stdout.strip().split('\n'):
        if line:
            size_result = subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} ls -la {line} 2>/dev/null"',
                                         shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            print(f"   {line}")
            if size_result.stdout:
                print(f"      {size_result.stdout.strip()}")

    test_paths = [
        f"{APP_DIR}/assets/images/buttons/neon_button.png"
    ]

    print("\n🔍 Проверка наличия neon_button.png:")
    for path in test_paths:
        result = subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} ls -la {path} 2>/dev/null"',
                                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.stdout.strip():
            print(f"   ✅ НАЙДЕН: {path}")
            print(f"      {result.stdout.strip()}")
        else:
            print(f"   ❌ НЕ НАЙДЕН: {path}")


def interactive_log_viewer(device):
    """Интерактивный просмотр логов с возможностью запуска/остановки"""
    print("\n" + "=" * 60)
    print("📋 ИНТЕРАКТИВНЫЙ ПРОСМОТР ЛОГОВ")
    print("=" * 60)
    print("Инструкция:")
    print("  1. Нажмите ENTER для начала записи логов")
    print("  2. Откройте приложение и выполните нужные действия")
    print("  3. Нажмите ENTER снова для остановки записи")
    print("  4. Получите вывод логов в терминал")
    print("=" * 60)

    input("\n👉 Нажмите ENTER для начала записи логов...")

    print("\n🔄 Очищаем старые логи...")
    subprocess.run(f"{ADB} -s {device} logcat -c", shell=True)

    print("🚀 Запускаем приложение...")
    subprocess.run(f"{ADB} -s {device} shell am start -n {PACKAGE}/org.kivy.android.PythonActivity", shell=True)

    print("\n" + "=" * 60)
    print("⏳ ИДЕТ ЗАПИСЬ ЛОГОВ...")
    print("📱 Выполните нужные действия в приложении")
    print("=" * 60)

    log_data = []
    stop_logging = False

    def collect_logs():
        """Собирает логи в фоновом потоке"""
        nonlocal stop_logging
        process = subprocess.Popen(
            f'{ADB} -s {device} logcat -v time',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            bufsize=1
        )

        while not stop_logging:
            try:
                line = process.stdout.readline()
                if line:
                    if PACKAGE in line or 'python' in line.lower() or 'kivy' in line.lower():
                        log_data.append(line)
                        print(f"   {line.strip()}")
            except:
                break

        process.terminate()

    log_thread = threading.Thread(target=collect_logs, daemon=True)
    log_thread.start()

    input("\n👉 Нажмите ENTER для остановки записи логов...")

    print("\n⏹️ Останавливаем запись логов...")
    stop_logging = True
    time.sleep(0.5)

    print("\n" + "=" * 60)
    print("📋 СОБРАННЫЕ ЛОГИ:")
    print("=" * 60)

    if log_data:
        keyboard_logs = []
        other_logs = []
        error_logs = []

        for line in log_data:
            if 'KEYBOARD' in line:
                keyboard_logs.append(line)
            elif 'ERROR' in line.upper() or 'FATAL' in line.upper() or 'EXCEPTION' in line.upper():
                error_logs.append(line)
            else:
                other_logs.append(line)

        if keyboard_logs:
            print(f"\n⌨️ ЛОГИ КЛАВИАТУРЫ ({len(keyboard_logs)} записей):")
            print("-" * 60)
            for line in keyboard_logs[-50:]:
                if '✅' in line or 'успешно' in line:
                    print(f"\033[92m{line.strip()}\033[0m")
                elif '⚠️' in line or 'ошибк' in line.lower():
                    print(f"\033[93m{line.strip()}\033[0m")
                elif '❌' in line:
                    print(f"\033[91m{line.strip()}\033[0m")
                else:
                    print(f"   {line.strip()}")

        if error_logs:
            print(f"\n❌ ОШИБКИ ({len(error_logs)} записей):")
            print("-" * 60)
            for line in error_logs[-20:]:
                print(f"\033[91m{line.strip()}\033[0m")

        if other_logs:
            print(f"\n📝 ДРУГИЕ ЛОГИ ({len(other_logs)} записей):")
            print("-" * 60)
            for line in other_logs[-20:]:
                print(f"   {line.strip()}")

        log_file = f"app_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("ЛОГИ ПРИЛОЖЕНИЯ AlmightyRandom\n")
            f.write(f"Время записи: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            f.write("⌨️ ЛОГИ КЛАВИАТУРЫ:\n")
            f.write("-" * 60 + "\n")
            for line in keyboard_logs:
                f.write(line)

            f.write("\n\n❌ ОШИБКИ:\n")
            f.write("-" * 60 + "\n")
            for line in error_logs:
                f.write(line)

            f.write("\n\n📝 ДРУГИЕ ЛОГИ:\n")
            f.write("-" * 60 + "\n")
            for line in other_logs:
                f.write(line)

        print(f"\n📁 Логи сохранены в файл: {log_file}")

        result = subprocess.run(f"{ADB} -s {device} shell pidof {PACKAGE}",
                                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')

        print("\n" + "=" * 60)
        print("СТАТУС ПРИЛОЖЕНИЯ:")
        if result.stdout.strip():
            pid = result.stdout.strip()
            print(f"✅ ПРИЛОЖЕНИЕ ЗАПУЩЕНО (PID: {pid})")
        else:
            print(f"❌ ПРИЛОЖЕНИЕ НЕ ЗАПУЩЕНО ИЛИ УПАЛО")

        show_all = input("\n📋 Показать все собранные логи? (y/n): ")
        if show_all.lower() == 'y':
            print("\n" + "=" * 60)
            print("ВСЕ ЛОГИ:")
            print("=" * 60)
            for line in log_data:
                print(line.strip())

    else:
        print("❌ Логи не были собраны!")

    print("\n" + "=" * 60)
    print("✅ ПРОСМОТР ЛОГОВ ЗАВЕРШЕН")
    print("=" * 60)


def full_update(device):
    """Полное обновление проекта (с очисткой)"""
    print("\n" + "=" * 50)
    print("🔄 ПОЛНОЕ ОБНОВЛЕНИЕ (С ОЧИСТКОЙ)")
    print("=" * 50)
    print("⚠️ ВНИМАНИЕ: Это удалит ВСЕ файлы приложения, включая assets!")
    print("   После этого приложение может перестать работать,")
    print("   если у вас нет полной копии всех необходимых файлов.")
    print("=" * 50)

    confirm = input("\nВы уверены, что хотите продолжить? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Отменено")
        return False

    print("\n🚀 Начинаю обновление...\n")

    print("⏹️ Останавливаем приложение...")
    subprocess.run(f"{ADB} -s {device} shell am force-stop {PACKAGE}", shell=True)
    time.sleep(1)

    print("🗑️ Очищаем старые файлы...")
    folders = ["screens", "components", "locales", "assets"]
    for folder in folders:
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} rm -rf {APP_DIR}/{folder}"', shell=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} mkdir -p {APP_DIR}/{folder}"', shell=True)
        print(f"   ✅ {folder}")

    if os.path.exists("main.py"):
        print("\n📄 main.py")
        subprocess.run(f"{ADB} -s {device} push main.py /data/local/tmp/", shell=True, capture_output=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/main.py {APP_DIR}/"', shell=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {APP_DIR}/main.py"', shell=True)

    if os.path.exists("sound_manager.py"):
        print("\n📄 sound_manager.py")
        subprocess.run(f"{ADB} -s {device} push sound_manager.py /data/local/tmp/", shell=True, capture_output=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} cp /data/local/tmp/sound_manager.py {APP_DIR}/"', shell=True)
        subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} chmod 644 {APP_DIR}/sound_manager.py"', shell=True)

    if os.path.exists("screens"):
        sync_directory("screens", f"{APP_DIR}/screens", device)

    if os.path.exists("components"):
        sync_directory("components", f"{APP_DIR}/components", device)

    if os.path.exists("locales"):
        sync_directory("locales", f"{APP_DIR}/locales", device)

    if os.path.exists("assets"):
        sync_directory("assets", f"{APP_DIR}/assets", device)

    print("\n🧹 Очищаем кэш...")
    subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} rm -rf {APP_DIR}/__pycache__"', shell=True)
    subprocess.run(f'{ADB} -s {device} shell "run-as {PACKAGE} find {APP_DIR} -name *.pyc -delete"', shell=True)

    check_assets(device)
    show_app_logs(device)

    print("\n" + "=" * 50)
    print("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО")
    print("=" * 50)

    return True


def get_all_files():
    """Собирает все файлы для отслеживания (рекурсивно обходит все папки)"""
    files = []

    if os.path.exists("main.py"):
        files.append("main.py")

    # ✅ Добавляем sound_manager.py в отслеживание
    if os.path.exists("sound_manager.py"):
        files.append("sound_manager.py")

    if os.path.exists("screens"):
        for root, dirs, filenames in os.walk("screens"):
            for filename in filenames:
                if filename.endswith(".py"):
                    full_path = os.path.join(root, filename)
                    relative_path = full_path.replace("\\", "/")
                    files.append(relative_path)

    if os.path.exists("components"):
        for root, dirs, filenames in os.walk("components"):
            for filename in filenames:
                if filename.endswith(".py"):
                    full_path = os.path.join(root, filename)
                    relative_path = full_path.replace("\\", "/")
                    files.append(relative_path)

    if os.path.exists("locales"):
        for root, dirs, filenames in os.walk("locales"):
            for filename in filenames:
                if filename.endswith(".json"):
                    full_path = os.path.join(root, filename)
                    relative_path = full_path.replace("\\", "/")
                    files.append(relative_path)

    if os.path.exists("assets"):
        for root, dirs, filenames in os.walk("assets"):
            for filename in filenames:
                if not filename.endswith(('.pyc', '.pyo', '.DS_Store')):
                    full_path = os.path.join(root, filename)
                    relative_path = full_path.replace("\\", "/")
                    files.append(relative_path)

    return files


def show_app_logs(device):
    """Показывает логи только вашего приложения (старая версия)"""
    print("\n" + "=" * 60)
    print("📋 ЛОГИ ПРИЛОЖЕНИЯ AlmightyRandom")
    print("=" * 60)

    print("🧹 Очищаем старые логи...")
    subprocess.run(f"{ADB} -s {device} logcat -c", shell=True)

    print("🚀 Запускаем приложение...")
    subprocess.run(f"{ADB} -s {device} shell am start -n {PACKAGE}/org.kivy.android.PythonActivity", shell=True)

    print("⏳ Ждём 5 секунд...")
    time.sleep(5)

    print("\n" + "=" * 60)
    print("ЛОГИ ПРИЛОЖЕНИЯ:")
    print("=" * 60)

    result = subprocess.run(
        f'{ADB} -s {device} logcat -d | findstr /i "{PACKAGE} python Kivy Traceback FATAL AndroidRuntime"',
        shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')

    if result.stdout:
        lines = result.stdout.strip().split('\n')
        lines = lines[-100:]
        error_found = False
        for line in lines:
            if 'FATAL' in line or 'Exception' in line or 'Traceback' in line or 'Error' in line:
                print(f"\033[91m{line}\033[0m")
                error_found = True
            elif 'Warning' in line or 'WARNING' in line:
                print(f"\033[93m{line}\033[0m")
            else:
                print(line)

        if not error_found:
            print("\n✅ Нет критических ошибок в логах")
    else:
        print("❌ Нет логов. Возможно, приложение не запустилось или упало сразу")

    print("\n" + "=" * 60)
    print("СТАТУС ПРИЛОЖЕНИЯ:")
    print("=" * 60)

    result = subprocess.run(f"{ADB} -s {device} shell pidof {PACKAGE}",
                            shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')

    if result.stdout.strip():
        pid = result.stdout.strip()
        print(f"✅ ПРИЛОЖЕНИЕ ЗАПУЩЕНО (PID: {pid})")
    else:
        print(f"❌ ПРИЛОЖЕНИЕ НЕ ЗАПУЩЕНО ИЛИ УПАЛО")

        print("\n" + "=" * 60)
        print("ПОСЛЕДНИЕ ОШИБКИ ИЗ ЛОГОВ:")
        print("=" * 60)
        result = subprocess.run(f"{ADB} -s {device} logcat -d | findstr /i 'FATAL AndroidRuntime java.lang'",
                                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.stdout:
            print(result.stdout[-2000:])

    log_file = f"app_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("ЛОГИ ПРИЛОЖЕНИЯ AlmightyRandom\n")
        f.write("=" * 60 + "\n\n")
        if result.stdout:
            f.write(result.stdout)
    print(f"\n📁 Логи сохранены в файл: {log_file}")


def main_menu(device):
    """Главное меню"""
    print("\n" + "=" * 50)
    print(f"📱 УСТРОЙСТВО: {device}")
    print("=" * 50)
    print(" 1. Обычный режим (отслеживание изменений)")
    print(" 2. Полное обновление (ОПАСНО - удаляет всё!)")
    print(" 3. Выборочная синхронизация папок (БЕЗОПАСНО - только обновление)")
    print(" 4. Копировать файл(ы) в assets (БЕЗОПАСНО - только добавление)")
    print(" 5. Проверить assets")
    print(" 6. Посмотреть логи приложения (быстрый просмотр)")
    print(" 7. ИНТЕРАКТИВНЫЙ ПРОСМОТР ЛОГОВ (запись + остановка)")
    print(" 8. Сменить устройство")
    print(" 0. Выход")
    print("=" * 50)

    while True:
        try:
            choice = input("\n👉 Выберите режим: ")
            choice = int(choice)

            if choice == 0:
                return False
            elif choice == 1:
                return "normal"
            elif choice == 2:
                full_update(device)
                return "restart"
            elif choice == 3:
                sync_selected_folders(device)
                return "restart"
            elif choice == 4:
                print("\n" + "=" * 50)
                print(" 1. Скопировать один файл")
                print(" 2. Скопировать несколько файлов")
                print(" 0. Назад")
                print("=" * 50)

                sub_choice = input("\n👉 Выберите действие: ")
                if sub_choice == '1':
                    copy_single_file_to_assets(device)
                elif sub_choice == '2':
                    copy_multiple_files_to_assets(device)
            elif choice == 5:
                check_assets(device)
            elif choice == 6:
                show_app_logs(device)
            elif choice == 7:
                interactive_log_viewer(device)
            elif choice == 8:
                return "change_device"
            else:
                print("❌ Неверный выбор")
        except ValueError:
            print("❌ Введите число")
        except KeyboardInterrupt:
            return False


# ==================== ГЛАВНАЯ ПРОГРАММА ====================

print("=" * 50)
print("🚀 СИНХРОНИЗАЦИЯ ПРОЕКТА")
print("=" * 50)

try:
    subprocess.run(f"{ADB} version", shell=True, capture_output=True, check=True)
except:
    print("❌ ADB не найден!")
    input("Нажмите Enter для выхода...")
    exit(1)

while True:
    selected_device = load_selected_device()

    if selected_device:
        devices = get_adb_devices()
        if selected_device not in devices:
            print(f"⚠️ Устройство {selected_device} не найдено")
            selected_device = None

    if not selected_device:
        selected_device = select_device()
        if not selected_device:
            exit(0)

    mode = main_menu(selected_device)

    if mode == "normal":
        break
    elif mode == "change_device":
        if os.path.exists(DEVICE_STATE_FILE):
            os.remove(DEVICE_STATE_FILE)
        continue
    elif mode == "restart":
        continue
    else:
        exit(0)

print(f"\n📱 Работа с устройством: {selected_device}")
print("=" * 50)
print("👀 ОТСЛЕЖИВАНИЕ ИЗМЕНЕНИЙ")
print("=" * 50)
print("Сохраняйте файлы (Ctrl+S) для синхронизации")
print("Нажмите Ctrl+C для выхода")
print("=" * 50)

state = load_state()
files_to_watch = get_all_files()

print(f"\nОтслеживается {len(files_to_watch)} файлов")

for file in files_to_watch:
    if file not in state:
        state[file] = 0

save_state(state)

try:
    while True:
        changed = False
        for file in files_to_watch:
            if os.path.exists(file):
                mtime = os.path.getmtime(file)
                if mtime != state.get(file, 0):
                    state[file] = mtime
                    changed = True
                    print(f"\n📝 {file}")
                    sync_file(file, selected_device)
                    save_state(state)

        if not changed:
            time.sleep(1)
except KeyboardInterrupt:
    print("\n\n👋 Завершение...")
    save_state(state)