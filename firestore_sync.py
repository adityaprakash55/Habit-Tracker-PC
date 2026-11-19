import os
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal

import config

logger = logging.getLogger("VoltHabitSync")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def calculate_streak(completed_dates: List[str], today_str: Optional[str] = None) -> int:
    """
    Calculate the current consecutive-day streak.
    - If today is completed: streak = 1 + consecutive preceding days.
    - If today is not completed: if yesterday was completed, streak = consecutive days up to yesterday.
    - If neither today nor yesterday is completed: streak = 0.
    """
    if not completed_dates:
        return 0

    if not today_str:
        today_str = datetime.now().strftime("%Y-%m-%d")

    date_set = set(completed_dates)
    today = datetime.strptime(today_str, "%Y-%m-%d").date()

    if today_str in date_set:
        streak = 1
        curr = today - timedelta(days=1)
        while curr.strftime("%Y-%m-%d") in date_set:
            streak += 1
            curr -= timedelta(days=1)
        return streak
    else:
        yesterday = today - timedelta(days=1)
        if yesterday.strftime("%Y-%m-%d") in date_set:
            streak = 0
            curr = yesterday
            while curr.strftime("%Y-%m-%d") in date_set:
                streak += 1
                curr -= timedelta(days=1)
            return streak
        else:
            return 0


class FirestoreSyncService(QObject):
    # Signals emitted to UI thread
    habits_updated = pyqtSignal(list)
    goals_updated = pyqtSignal(list)
    groups_updated = pyqtSignal(list)
    sync_status = pyqtSignal(str, str)  # (status_message, state: "ok", "syncing", "warning", "error")
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = None
        self.habits_watch = None
        self.goals_watch = None
        self.is_demo_mode = False
        self.habits_cache: List[Dict[str, Any]] = []
        self.goals_cache: List[Dict[str, Any]] = []
        self.groups_cache: List[Dict[str, Any]] = []

        # Local storage paths for offline caching
        self.goals_file = config.BASE_DIR / "volthabit_goals.json"
        self.groups_file = config.BASE_DIR / "volthabit_groups.json"
        self.habits_file = config.BASE_DIR / "volthabit_habits.json"

        self._load_local_data()

    def _load_local_data(self):
        """Load persistent local cache for goals, groups, and habits."""
        if self.goals_file.exists():
            try:
                with open(self.goals_file, "r", encoding="utf-8") as f:
                    self.goals_cache = json.load(f)
            except Exception:
                self._init_default_goals()
        else:
            self._init_default_goals()

        if self.groups_file.exists():
            try:
                with open(self.groups_file, "r", encoding="utf-8") as f:
                    self.groups_cache = json.load(f)
            except Exception:
                self._init_default_groups()
        else:
            self._init_default_groups()

        if self.habits_file.exists():
            try:
                with open(self.habits_file, "r", encoding="utf-8") as f:
                    self.habits_cache = json.load(f)
            except Exception:
                self.habits_cache = []

    def _save_local_goals(self):
        try:
            with open(self.goals_file, "w", encoding="utf-8") as f:
                json.dump(self.goals_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save goals locally: {e}")

    def _save_local_groups(self):
        try:
            with open(self.groups_file, "w", encoding="utf-8") as f:
                json.dump(self.groups_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save groups locally: {e}")

    def _save_local_habits(self):
        try:
            with open(self.habits_file, "w", encoding="utf-8") as f:
                json.dump(self.habits_cache, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save habits locally: {e}")

    def _init_default_goals(self):
        self.goals_cache = [
            {
                "id": "goal-1",
                "title": "Achieve 50 Consistent Workout Days",
                "category": "Fitness",
                "currentValue": 12,
                "targetValue": 50,
                "unit": "workouts",
                "deadline": "2026-12-31",
                "linkedHabitTitle": "upperchest",
                "completed": False,
            },
            {
                "id": "goal-2",
                "title": "Read 24 Non-Fiction Books",
                "category": "Learning",
                "currentValue": 14,
                "targetValue": 24,
                "unit": "books",
                "deadline": "2026-12-31",
                "linkedHabitTitle": "",
                "completed": False,
            },
        ]
        self._save_local_goals()

    def _init_default_groups(self):
        self.groups_cache = [
            {"id": "grp-1", "name": "exercise", "icon": "💪", "color": "#10B981"},
            {"id": "grp-2", "name": "morning routine", "icon": "🌅", "color": "#F59E0B"},
            {"id": "grp-3", "name": "deep work", "icon": "⚡", "color": "#39FF14"},
            {"id": "grp-4", "name": "night routine", "icon": "🌙", "color": "#8B5CF6"},
        ]
        self._save_local_groups()

    def start(self):
        """Initialize Firestore connection with real-time listeners for habits and goals."""
        self.sync_status.emit("Connecting...", "syncing")
        user_id = config.USER_ID.strip()
        service_account_path = config.SERVICE_ACCOUNT_KEY.strip()

        # Emit initial cached data immediately
        if self.habits_cache:
            self.habits_updated.emit(self.habits_cache)
        self.goals_updated.emit(self.goals_cache)
        self.groups_updated.emit(self.groups_cache)

        if not user_id or user_id in ("your_firebase_user_id_here", "demo_user"):
            logger.info("No user ID configured. Starting in Local / Demo Mode.")
            self._start_demo_mode("Demo Mode (Set .env for live sync)")
            return

        try:
            from google.cloud import firestore
            from google.oauth2 import service_account

            credentials = None
            if service_account_path:
                full_path = (config.BASE_DIR / service_account_path).resolve()
                if full_path.exists():
                    credentials = service_account.Credentials.from_service_account_file(str(full_path))
                elif os.path.exists(service_account_path):
                    credentials = service_account.Credentials.from_service_account_file(service_account_path)
                elif service_account_path.startswith("{"):
                    key_info = json.loads(service_account_path)
                    credentials = service_account.Credentials.from_service_account_info(key_info)

            logger.info(f"Connecting to Firestore Project: {config.PROJECT_ID}, DB: {config.DATABASE_ID}")
            if credentials:
                self.db = firestore.Client(
                    project=config.PROJECT_ID,
                    database=config.DATABASE_ID,
                    credentials=credentials,
                )
            else:
                self.db = firestore.Client(
                    project=config.PROJECT_ID,
                    database=config.DATABASE_ID,
                )

            # Start real-time snapshot listeners
            self._start_habits_listener(user_id)
            self._start_goals_listener(user_id)
            self.sync_status.emit("Live Synced", "ok")

        except Exception as e:
            logger.error(f"Firestore initialization error: {e}", exc_info=True)
            self._start_demo_mode(f"Local Storage ({type(e).__name__})")
            self.error_occurred.emit(str(e))

    def _start_habits_listener(self, user_id: str):
        """Sets up the real-time snapshot listener on the habits collection."""
        try:
            col_ref = self.db.collection("users").document(user_id).collection("habits")

            def on_snapshot(col_snapshot, changes, read_time):
                habits = []
                for doc in col_snapshot:
                    data = doc.to_dict() or {}
                    data["id"] = doc.id
                    if "completedDates" not in data or not isinstance(data["completedDates"], list):
                        data["completedDates"] = []
                    if "streak" not in data or not isinstance(data["streak"], int):
                        data["streak"] = calculate_streak(data["completedDates"])

                    # Support mobile app's 'groupName' attribute or fallback to 'group' or title tags
                    group = data.get("groupName") or data.get("group")
                    title = data.get("title", "")

                    if not group:
                        if title.startswith("[") and "]" in title:
                            parts = title.split("]", 1)
                            group = parts[0][1:].strip()
                            data["cleanTitle"] = parts[1].strip()
                        else:
                            group = "General"
                            data["cleanTitle"] = title
                    else:
                        data["cleanTitle"] = title

                    data["group"] = group
                    data["groupName"] = group
                    habits.append(data)

                    # Auto-register group if new
                    self._register_discovered_group(group)

                habits.sort(key=lambda h: h.get("title", "").lower())
                self.habits_cache = habits
                self._save_local_habits()
                self.habits_updated.emit(habits)
                self.sync_status.emit("Live Synced", "ok")

            self.habits_watch = col_ref.on_snapshot(on_snapshot)
            logger.info("Real-time Firestore habits listener active.")
        except Exception as e:
            logger.error(f"Failed to start habits listener: {e}", exc_info=True)

    def _start_goals_listener(self, user_id: str):
        """Sets up the real-time snapshot listener on the goals collection."""
        try:
            goals_ref = self.db.collection("users").document(user_id).collection("goals")

            def on_goals_snapshot(col_snapshot, changes, read_time):
                goals = []
                for doc in col_snapshot:
                    data = doc.to_dict() or {}
                    data["id"] = doc.id
                    goals.append(data)

                if goals:
                    self.goals_cache = goals
                    self._save_local_goals()
                    self.goals_updated.emit(goals)

            self.goals_watch = goals_ref.on_snapshot(on_goals_snapshot)
            logger.info("Real-time Firestore goals listener active.")
        except Exception as e:
            logger.debug(f"Goals listener not active (using local persistence): {e}")

    def _register_discovered_group(self, group_name: str):
        if not group_name or group_name == "General":
            return
        existing_names = [g["name"].lower() for g in self.groups_cache]
        if group_name.lower() not in existing_names:
            self.groups_cache.append({
                "id": f"grp-{uuid.uuid4().hex[:6]}",
                "name": group_name,
                "icon": "⚡",
                "color": "#39FF14",
            })
            self._save_local_groups()
            self.groups_updated.emit(self.groups_cache)

    def _start_demo_mode(self, message: str = "Demo Mode"):
        self.is_demo_mode = True
        self.habits_updated.emit(self.habits_cache)
        self.goals_updated.emit(self.goals_cache)
        self.groups_updated.emit(self.groups_cache)
        self.sync_status.emit(message, "warning")

    # --- HABIT OPERATIONS ---
    def toggle_habit_today(self, habit_id: str, is_completed: bool):
        """Toggle today's completion for a habit, recalculate streak, and sync."""
        today_str = datetime.now().strftime("%Y-%m-%d")

        target_habit = None
        for h in self.habits_cache:
            if h.get("id") == habit_id:
                target_habit = h
                break

        if not target_habit:
            return

        dates = list(target_habit.get("completedDates", []))
        if is_completed:
            if today_str not in dates:
                dates.append(today_str)
        else:
            if today_str in dates:
                dates.remove(today_str)

        dates.sort()
        new_streak = calculate_streak(dates, today_str)

        # Optimistic UI update
        target_habit["completedDates"] = dates
        target_habit["streak"] = new_streak
        self._save_local_habits()
        self.habits_updated.emit(self.habits_cache)

        if is_completed:
            self._check_goal_progress_on_habit_completed(target_habit.get("title", ""))

        if self.is_demo_mode or not self.db:
            self.sync_status.emit("Saved Locally", "ok")
            return

        try:
            self.sync_status.emit("Syncing...", "syncing")
            user_id = config.USER_ID.strip()
            doc_ref = self.db.collection("users").document(user_id).collection("habits").document(habit_id)

            doc_ref.update({
                "completedDates": dates,
                "streak": new_streak,
            })
            self.sync_status.emit("Live Synced", "ok")
            logger.info(f"Updated habit {habit_id} on Firestore: streak={new_streak}")
        except Exception as e:
            logger.error(f"Failed to update habit {habit_id} in Firestore: {e}", exc_info=True)
            self.sync_status.emit("Sync Failed", "error")
            self.error_occurred.emit(f"Update failed: {e}")

    def add_habit(self, title: str, frequency: str = "daily", group: str = "General") -> bool:
        """Add a new habit to Firestore and local cache."""
        title = title.strip()
        if not title:
            return False

        clean_title = title
        if title.startswith("[") and "]" in title:
            clean_title = title.split("]", 1)[1].strip()

        habit_data = {
            "title": clean_title,
            "groupName": group,
            "group": group,
            "frequency": frequency if frequency in ("daily", "weekly", "custom") else "daily",
            "completedDates": [],
            "streak": 0,
            "scheduledDays": [0, 1, 2, 3, 4, 5, 6],
            "cleanTitle": clean_title,
        }

        if self.is_demo_mode or not self.db:
            new_id = f"habit-{uuid.uuid4().hex[:8]}"
            habit_data["id"] = new_id
            self.habits_cache.append(habit_data)
            self._save_local_habits()
            self._register_discovered_group(group)
            self.habits_updated.emit(self.habits_cache)
            self.sync_status.emit("Habit Created (Local)", "ok")
            return True

        try:
            from google.cloud import firestore
            self.sync_status.emit("Creating habit...", "syncing")
            user_id = config.USER_ID.strip()
            col_ref = self.db.collection("users").document(user_id).collection("habits")

            payload = {
                "title": clean_title,
                "groupName": group,
                "frequency": frequency,
                "completedDates": [],
                "streak": 0,
                "scheduledDays": [0, 1, 2, 3, 4, 5, 6],
                "createdAt": firestore.SERVER_TIMESTAMP,
            }
            new_ref = col_ref.document()
            new_ref.set(payload)

            habit_data["id"] = new_ref.id
            self.habits_cache.append(habit_data)
            self._save_local_habits()
            self._register_discovered_group(group)
            self.habits_updated.emit(self.habits_cache)
            self.sync_status.emit("Live Synced", "ok")
            return True
        except Exception as e:
            logger.error(f"Failed to create habit in Firestore: {e}", exc_info=True)
            self.error_occurred.emit(f"Failed to create habit: {e}")
            return False

    def edit_habit(self, habit_id: str, new_title: str, new_frequency: str = "daily", group: str = "General") -> bool:
        """Edit an existing habit."""
        clean_title = new_title.strip()

        target = next((h for h in self.habits_cache if h["id"] == habit_id), None)
        if target:
            target["title"] = clean_title
            target["frequency"] = new_frequency
            target["group"] = group
            target["groupName"] = group
            target["cleanTitle"] = clean_title
            self._save_local_habits()
            self._register_discovered_group(group)
            self.habits_updated.emit(self.habits_cache)

        if self.is_demo_mode or not self.db:
            return True

        try:
            user_id = config.USER_ID.strip()
            doc_ref = self.db.collection("users").document(user_id).collection("habits").document(habit_id)
            doc_ref.update({
                "title": clean_title,
                "groupName": group,
                "frequency": new_frequency,
            })
            self.sync_status.emit("Live Synced", "ok")
            return True
        except Exception as e:
            logger.error(f"Failed to edit habit in Firestore: {e}", exc_info=True)
            self.error_occurred.emit(f"Failed to edit habit: {e}")
            return False

    def delete_habit(self, habit_id: str) -> bool:
        """Delete a habit from Firestore and local cache."""
        self.habits_cache = [h for h in self.habits_cache if h["id"] != habit_id]
        self._save_local_habits()
        self.habits_updated.emit(self.habits_cache)

        if self.is_demo_mode or not self.db:
            self.sync_status.emit("Habit Deleted", "ok")
            return True

        try:
            user_id = config.USER_ID.strip()
            doc_ref = self.db.collection("users").document(user_id).collection("habits").document(habit_id)
            doc_ref.delete()
            self.sync_status.emit("Live Synced", "ok")
            return True
        except Exception as e:
            logger.error(f"Failed to delete habit in Firestore: {e}", exc_info=True)
            self.error_occurred.emit(f"Failed to delete: {e}")
            return False

    def batch_complete_group(self, group_name: str):
        """Complete all habits in a given group for today."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        for habit in self.habits_cache:
            if habit.get("group") == group_name or habit.get("groupName") == group_name:
                if today_str not in habit.get("completedDates", []):
                    self.toggle_habit_today(habit["id"], True)

    # --- GOAL OPERATIONS ---
    def add_goal(self, goal_data: Dict[str, Any]) -> str:
        """Add a long-term goal."""
        goal_id = f"goal-{uuid.uuid4().hex[:8]}"
        goal_data["id"] = goal_id
        if "completed" not in goal_data:
            goal_data["completed"] = False
        if "createdAt" not in goal_data:
            goal_data["createdAt"] = datetime.now().isoformat()

        self.goals_cache.append(goal_data)
        self._save_local_goals()
        self.goals_updated.emit(self.goals_cache)

        if not self.is_demo_mode and self.db:
            try:
                user_id = config.USER_ID.strip()
                self.db.collection("users").document(user_id).collection("goals").document(goal_id).set(goal_data)
            except Exception as e:
                logger.debug(f"Firestore goals sync error: {e}")

        return goal_id

    def update_goal_progress(self, goal_id: str, delta: float = 1.0):
        """Increment/decrement current progress on a goal."""
        for g in self.goals_cache:
            if g["id"] == goal_id:
                g["currentValue"] = max(0, round(float(g.get("currentValue", 0)) + delta, 2))
                g["completed"] = g["currentValue"] >= float(g.get("targetValue", 1))
                break
        self._save_local_goals()
        self.goals_updated.emit(self.goals_cache)

        if not self.is_demo_mode and self.db:
            try:
                user_id = config.USER_ID.strip()
                g = next((x for x in self.goals_cache if x["id"] == goal_id), None)
                if g:
                    self.db.collection("users").document(user_id).collection("goals").document(goal_id).set(g)
            except Exception:
                pass

    def delete_goal(self, goal_id: str):
        """Delete a long-term goal."""
        self.goals_cache = [g for g in self.goals_cache if g["id"] != goal_id]
        self._save_local_goals()
        self.goals_updated.emit(self.goals_cache)

        if not self.is_demo_mode and self.db:
            try:
                user_id = config.USER_ID.strip()
                self.db.collection("users").document(user_id).collection("goals").document(goal_id).delete()
            except Exception:
                pass

    def _check_goal_progress_on_habit_completed(self, habit_title: str):
        """Automatically advance linked goals when a habit is completed."""
        clean = habit_title.split("]", 1)[1].strip() if "]" in habit_title else habit_title
        for g in self.goals_cache:
            linked = g.get("linkedHabitTitle", "")
            if linked and (linked.lower() in clean.lower() or clean.lower() in linked.lower()):
                self.update_goal_progress(g["id"], delta=1.0)
                break

    # --- GROUP OPERATIONS ---
    def add_group(self, name: str, icon: str = "📁", color: str = "#39FF14"):
        group_id = f"grp-{uuid.uuid4().hex[:6]}"
        self.groups_cache.append({
            "id": group_id,
            "name": name.strip(),
            "icon": icon,
            "color": color,
        })
        self._save_local_groups()
        self.groups_updated.emit(self.groups_cache)

    def delete_group(self, group_id: str):
        self.groups_cache = [g for g in self.groups_cache if g["id"] != group_id]
        self._save_local_groups()
        self.groups_updated.emit(self.groups_cache)

    def refresh(self):
        """Trigger re-sync."""
        if self.is_demo_mode:
            self.habits_updated.emit(self.habits_cache)
            self.goals_updated.emit(self.goals_cache)
            self.groups_updated.emit(self.groups_cache)
            self.sync_status.emit("Refreshed", "ok")
        else:
            self.start()
