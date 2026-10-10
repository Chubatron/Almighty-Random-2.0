# lucky_token.py
# Глобальный менеджер игровой валюты Lucky_Token.
# Сделан по образцу SoundManager — синглтон, JSON-персист, Kivy-события.
#
# Пока файл НЕ подключён к экранам. Логика начисления будет
# активирована после того, как UI-виджет TokenWidget встанет в меню и игры.

import os
import json
from datetime import date

from kivy.utils import platform
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty


# ==================== ПУТЬ ХРАНЕНИЯ ====================

def _get_storage_dir():
    """Возвращает корректную директорию для хранения данных.

    На Android — filesDir приложения (доступен без разрешений).
    На ПК — текущая рабочая директория.
    """
    if platform == 'android':
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            files_dir = context.getFilesDir().getAbsolutePath()
            return files_dir
        except Exception as e:
            print(f"⚠️ [LuckyToken] Не удалось получить filesDir: {e}")
            return '.'
    return '.'


# ==================== МЕНЕДЖЕР ====================

class LuckyToken(EventDispatcher):
    """Синглтон-менеджер игровой валюты Lucky_Token.

    Возможности:
      • Хранит баланс в lucky_token.json (в filesDir на Android).
      • Автосохраняется при каждом изменении.
      • Шлёт событие on_balance_changed при изменении баланса.
      • Держит достижения и дату последнего ежедневного бонуса.
      • Начисляет токены за игры, рекламу, достижения.
    """

    # --- Регистрация события для Kivy ---
    __events__ = ('on_balance_changed',)

    _instance = None

    # --- Kivy properties (можно биндиться прямо в .py и в .kv) ---
    balance = NumericProperty(0)
    total_earned = NumericProperty(0)
    total_spent = NumericProperty(0)

    # --- Настройки наград (менять тут, не в играх) ---
    STARTING_BALANCE = 100     # выдаётся новому игроку
    REWARD_PER_GAME = 5        # за завершённый раунд любой игры
    REWARD_FOR_AD = 25         # за просмотр рекламы до конца
    REWARD_DAILY_BONUS = 50    # ежедневный вход
    REWARD_ACHIEVEMENT_DEFAULT = 20  # за достижение, если не указано иное

    # ==================== СИНГЛТОН ====================

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Инициализируем один раз
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        self._storage_path = os.path.join(_get_storage_dir(), 'lucky_token.json')
        self._achievements = {}         # dict: id -> True
        self._daily_claimed = None      # строка 'YYYY-MM-DD' или None

        self._load()

        print(f"🎟️ [LuckyToken] Готово. Баланс: {self.balance}, "
              f"всего заработано: {self.total_earned}, "
              f"всего потрачено: {self.total_spent}")
        print(f"🎟️ [LuckyToken] Файл: {self._storage_path}")

    # ==================== ПЕРСИСТ ====================

    def _load(self):
        """Загружает состояние из JSON. Если файла нет — создаёт с бонусом новичка."""
        if not os.path.exists(self._storage_path):
            self.balance = self.STARTING_BALANCE
            self.total_earned = self.STARTING_BALANCE
            self.total_spent = 0
            self._achievements = {}
            self._daily_claimed = None
            self._save()
            print(f"🎟️ [LuckyToken] Создан новый файл, стартовый баланс {self.STARTING_BALANCE}")
            return

        try:
            with open(self._storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.balance = int(data.get('balance', self.STARTING_BALANCE))
            self.total_earned = int(data.get('total_earned', 0))
            self.total_spent = int(data.get('total_spent', 0))
            self._achievements = data.get('achievements', {}) or {}
            self._daily_claimed = data.get('daily_claimed', None)

            print(f"🎟️ [LuckyToken] Загружено из файла")

        except Exception as e:
            print(f"⚠️ [LuckyToken] Ошибка загрузки ({e}). Ставлю стартовый баланс.")
            self.balance = self.STARTING_BALANCE
            self.total_earned = self.STARTING_BALANCE
            self.total_spent = 0
            self._achievements = {}
            self._daily_claimed = None

    def _save(self):
        """Сохраняет состояние в JSON."""
        try:
            data = {
                'balance': int(self.balance),
                'total_earned': int(self.total_earned),
                'total_spent': int(self.total_spent),
                'achievements': self._achievements,
                'daily_claimed': self._daily_claimed,
            }
            with open(self._storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [LuckyToken] Ошибка сохранения: {e}")

    # ==================== ОСНОВНОЕ API ====================

    def get_balance(self):
        """Текущий баланс (int)."""
        return int(self.balance)

    def add(self, amount, reason=""):
        """Начислить токены. amount > 0."""
        amount = int(amount)
        if amount <= 0:
            return
        self.balance += amount
        self.total_earned += amount
        self._save()
        print(f"🎟️ [LuckyToken] +{amount} ({reason or 'без причины'}). Баланс: {self.balance}")
        self.dispatch('on_balance_changed', self.balance)

    def spend(self, amount, reason=""):
        """Списать токены. Возвращает True, если хватило баланса."""
        amount = int(amount)
        if amount <= 0:
            return False
        if self.balance < amount:
            print(f"🎟️ [LuckyToken] Недостаточно: нужно {amount}, есть {self.balance}")
            return False
        self.balance -= amount
        self.total_spent += amount
        self._save()
        print(f"🎟️ [LuckyToken] -{amount} ({reason or 'без причины'}). Баланс: {self.balance}")
        self.dispatch('on_balance_changed', self.balance)
        return True

    def can_afford(self, amount):
        """Хватает ли токенов."""
        return self.balance >= int(amount)

    # ==================== ХУКИ ДЛЯ ИГР ====================

    def reward_game_completed(self, game_name="game"):
        """Вызывается при завершении раунда любой из 8 игр."""
        self.add(self.REWARD_PER_GAME, reason=f"game:{game_name}")

    def reward_ad_watched(self):
        """Вызывается после успешного просмотра рекламы."""
        self.add(self.REWARD_FOR_AD, reason="ad")

    def reward_achievement(self, achievement_id, reward=None):
        """Награда за достижение. Повторно не начисляется.
        Возвращает True, если начислено впервые, иначе False."""
        if self._achievements.get(achievement_id):
            return False
        amount = self.REWARD_ACHIEVEMENT_DEFAULT if reward is None else int(reward)
        self._achievements[achievement_id] = True
        self.add(amount, reason=f"achievement:{achievement_id}")
        return True

    def has_achievement(self, achievement_id):
        """Получено ли достижение."""
        return bool(self._achievements.get(achievement_id))

    def get_achievements(self):
        """Список id всех полученных достижений."""
        return list(self._achievements.keys())

    # ==================== ЕЖЕДНЕВНЫЙ БОНУС ====================

    def can_claim_daily(self):
        """Можно ли получить ежедневный бонус сегодня."""
        today = date.today().isoformat()
        return self._daily_claimed != today

    def claim_daily_bonus(self):
        """Начислить ежедневный бонус, если сегодня ещё не брали.
        Возвращает True, если начислено."""
        if not self.can_claim_daily():
            return False
        self._daily_claimed = date.today().isoformat()
        self.add(self.REWARD_DAILY_BONUS, reason="daily_bonus")
        return True

    # ==================== СОБЫТИЕ ====================

    def on_balance_changed(self, *args):
        """Переопредели или слушай через bind(on_balance_changed=...)."""
        pass