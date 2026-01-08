"""Wger workout manager integration.

Provides API client for wger workout tracking, exercise database,
nutrition logging, and body weight tracking.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import logging

import requests
import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".goals-mcp" / "wger-config.yml"
CACHE_PATH = Path.home() / ".goals-mcp" / "wger-cache"

# Equipment name to wger ID mapping
EQUIPMENT_IDS = {
    "Barbell": 1,
    "SZ-Bar": 2,
    "Dumbbell": 3,
    "Gym mat": 4,
    "Swiss Ball": 5,
    "Pull-up bar": 6,
    "none (bodyweight exercise)": 7,
    "Bench": 8,
    "Incline bench": 9,
    "Kettlebell": 10,
    "Resistance band": 11,
}

# Reverse mapping
EQUIPMENT_NAMES = {v: k for k, v in EQUIPMENT_IDS.items()}

# Category ID to name mapping
CATEGORY_IDS = {
    "Abs": 10,
    "Arms": 8,
    "Back": 12,
    "Calves": 14,
    "Cardio": 15,
    "Chest": 11,
    "Legs": 9,
    "Shoulders": 13,
}
CATEGORY_NAMES = {v: k for k, v in CATEGORY_IDS.items()}

# Muscle ID to muscle group mapping
MUSCLE_GROUPS = {
    1: "Biceps",       # Biceps brachii
    2: "Shoulders",    # Anterior deltoid
    4: "Chest",        # Pectoralis major
    5: "Triceps",      # Triceps brachii
    6: "Abs",          # Rectus abdominis
    7: "Calves",       # Gastrocnemius
    8: "Legs",         # Gluteus maximus
    10: "Legs",        # Quadriceps
    11: "Legs",        # Biceps femoris (hamstrings)
    12: "Back",        # Latissimus dorsi
    13: "Biceps",      # Brachialis
    14: "Abs",         # Obliques
    15: "Triceps",     # Secondary triceps
    16: "Back",        # Erector spinae (lower back)
}

MUSCLE_NAMES = {
    1: "Biceps",
    2: "Shoulders",
    4: "Chest",
    5: "Triceps",
    6: "Abs",
    7: "Calves",
    8: "Glutes",
    10: "Quads",
    11: "Hamstrings",
    12: "Lats",
    13: "Brachialis",
    14: "Obliques",
    15: "Triceps",
    16: "Lower Back",
}

# Recovery time in hours per muscle group
RECOVERY_HOURS = {
    "Chest": 48,
    "Back": 48,
    "Shoulders": 48,
    "Biceps": 36,
    "Triceps": 36,
    "Legs": 72,
    "Abs": 24,
    "Calves": 24,
}


class WgerClient:
    """Wger API client with JWT authentication."""

    def __init__(self, config: dict):
        self.host = config.get("host", "http://localhost").rstrip("/")
        self.username = config.get("username")
        self.password = config.get("password")
        self._access_token = None
        self._token_expires = None
        self._refresh_token = config.get("refresh_token")
        self._exercise_cache = {}

    def _get_token(self) -> str:
        """Get or refresh JWT access token."""
        now = datetime.now()

        # Return cached token if still valid (with 30s buffer)
        if (self._access_token and self._token_expires and
                now < self._token_expires - timedelta(seconds=30)):
            return self._access_token

        # Try refresh token first
        if self._refresh_token:
            try:
                resp = requests.post(
                    f"{self.host}/api/v2/token/refresh",
                    json={"refresh": self._refresh_token},
                    timeout=10
                )
                if resp.ok:
                    data = resp.json()
                    self._access_token = data["access"]
                    self._token_expires = now + timedelta(minutes=9)
                    return self._access_token
            except Exception as e:
                logger.debug(f"Token refresh failed: {e}")

        # Full login
        resp = requests.post(
            f"{self.host}/api/v2/token",
            json={"username": self.username, "password": self.password},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access"]
        self._refresh_token = data["refresh"]
        self._token_expires = now + timedelta(minutes=9)
        return self._access_token

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make authenticated API request."""
        token = self._get_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        url = f"{self.host}/api/v2/{endpoint.lstrip('/')}"
        timeout = kwargs.pop("timeout", 30)

        resp = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get(self, endpoint: str, **params) -> dict:
        """GET request."""
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: dict) -> dict:
        """POST request."""
        return self._request("POST", endpoint, json=data)

    # === Workout Session Methods ===

    def get_recent_sessions(self, days: int = 7) -> list[dict]:
        """Get workout sessions from last N days."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        resp = self.get("workoutsession/", date__gte=since, ordering="-date", limit=50)
        return resp.get("results", [])

    def get_session_logs(self, session_id: int) -> list[dict]:
        """Get exercise logs for a session."""
        resp = self.get("workoutlog/", session=session_id, limit=100)
        return resp.get("results", [])

    def create_session(self, date: str, notes: str = "") -> dict:
        """Get or create workout session for a date.

        Reuses existing session to avoid wger's MultipleObjectsReturned bug.
        """
        # Check for existing session on this date
        existing = self.get("workoutsession/", date=date, limit=10)
        sessions = existing.get("results", [])

        if sessions:
            # Reuse first existing session, optionally update notes
            session = sessions[0]
            if notes and not session.get("notes"):
                # Update notes if provided and session has none
                self._request("PATCH", f"workoutsession/{session['id']}/", json={"notes": notes})
            return session

        # Create new session
        return self.post("workoutsession/", {
            "date": date,
            "notes": notes,
            "impression": "2"  # neutral
        })

    def log_set(self, session_id: int, exercise_id: int,
                reps: int, weight: float, rir: int = None) -> dict:
        """Log an exercise set."""
        data = {
            "session": session_id,
            "exercise": exercise_id,
            "repetitions": reps,
            "weight": str(weight),
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        if rir is not None:
            data["rir"] = rir
        try:
            return self.post("workoutlog/", data)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                raise Exception("Wger server error: workout logging unavailable (server bug)")
            raise

    # === Exercise Methods ===

    def get_exercise(self, exercise_id: int) -> dict:
        """Get exercise by ID (cached)."""
        if exercise_id in self._exercise_cache:
            return self._exercise_cache[exercise_id]

        exercise = self.get(f"exercise/{exercise_id}/")
        self._exercise_cache[exercise_id] = exercise
        return exercise

    def get_exercise_info(self, exercise_id: int) -> dict:
        """Get full exercise info with translations."""
        return self.get(f"exerciseinfo/{exercise_id}/")

    def search_exercises(self, query: str = None, muscle: int = None,
                         equipment: int = None, category: int = None,
                         limit: int = 10) -> list[dict]:
        """Search exercises with optional filters."""
        # If query provided, use the search endpoint for better results
        if query and not (muscle or equipment or category):
            try:
                resp = self.get("exercise/search/", term=query, language=2)
                suggestions = resp.get("suggestions", [])

                # Get full exercise info for each result using base_id
                results = []
                for s in suggestions[:limit]:
                    data = s.get("data", {})
                    base_id = data.get("base_id")
                    if base_id:
                        try:
                            info = self.get_exercise_info(base_id)
                            results.append(info)
                        except Exception:
                            # If exerciseinfo fails, create minimal result from search data
                            results.append({
                                "id": base_id,
                                "translations": [{"language": 2, "name": data.get("name", "Unknown")}],
                                "category": {"name": data.get("category", "Unknown")},
                                "muscles": [],
                                "equipment": [],
                            })
                return results
            except Exception:
                pass  # Fall back to regular search

        # Regular search with filters
        params = {"limit": limit * 3, "language": 2}
        if query:
            # Client-side filter for combined searches
            params["limit"] = 200
        if muscle:
            params["muscles"] = muscle
        if equipment:
            params["equipment"] = equipment
        if category:
            params["category"] = category

        resp = self.get("exerciseinfo/", **params)
        results = resp.get("results", [])

        # Client-side filter by name if query with other filters
        if query:
            query_lower = query.lower()
            results = [
                e for e in results
                if any(
                    query_lower in t.get("name", "").lower()
                    for t in e.get("translations", [])
                )
            ]

        return results[:limit]

    def get_all_exercises(self) -> list[dict]:
        """Get all exercises (for caching)."""
        exercises = []
        offset = 0
        limit = 100

        while True:
            resp = self.get("exerciseinfo/", limit=limit, offset=offset)
            results = resp.get("results", [])
            exercises.extend(results)

            if not resp.get("next"):
                break
            offset += limit

        return exercises

    # === Weight Methods ===

    def log_weight_entry(self, weight: float, date: str = None) -> dict:
        """Log body weight. Updates existing entry if one exists for the date."""
        entry_date = date or datetime.now().strftime("%Y-%m-%d")

        # Check if entry exists for this date (API returns date with timezone)
        existing = self.get("weightentry/", ordering="-date", limit=50)
        existing_entry = None
        for entry in existing.get("results", []):
            # Compare just the date portion
            entry_date_str = entry.get("date", "")[:10]
            if entry_date_str == entry_date:
                existing_entry = entry
                break

        if existing_entry:
            # Update existing entry
            entry_id = existing_entry["id"]
            return self._request("PATCH", f"weightentry/{entry_id}/", json={
                "weight": str(weight),
                "date": entry_date
            })
        else:
            # Create new entry
            return self.post("weightentry/", {
                "weight": str(weight),
                "date": entry_date
            })

    def get_weight_history(self, days: int = 30) -> list[dict]:
        """Get weight entries."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        resp = self.get("weightentry/", date__gte=since, ordering="-date", limit=100)
        return resp.get("results", [])

    # === Nutrition Methods ===

    def search_ingredient(self, query: str, limit: int = 10) -> list[dict]:
        """Search ingredient database."""
        resp = self.get("ingredientinfo/", name=query, limit=limit)
        return resp.get("results", [])

    def get_ingredient(self, ingredient_id: int) -> dict:
        """Get ingredient details."""
        return self.get(f"ingredientinfo/{ingredient_id}/")

    def log_nutrition_entry(self, ingredient_id: int, amount: float,
                            datetime_str: str = None) -> dict:
        """Log nutrition diary entry."""
        return self.post("nutritiondiary/", {
            "ingredient": ingredient_id,
            "amount": amount,
            "datetime": datetime_str or datetime.now().isoformat()
        })

    def get_nutrition_diary(self, date: str = None) -> list[dict]:
        """Get nutrition diary for a date."""
        params = {"limit": 100}
        if date:
            params["datetime__date"] = date
        resp = self.get("nutritiondiary/", **params)
        return resp.get("results", [])


# === Module-Level Functions ===

def get_config() -> dict:
    """Load wger config from file."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}


def save_config(config: dict):
    """Save wger config to file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)


def is_authenticated() -> bool:
    """Check if wger is configured."""
    config = get_config()
    return bool(config.get("host") and config.get("username") and config.get("password"))


def get_client() -> Optional[WgerClient]:
    """Get wger client if authenticated."""
    if not is_authenticated():
        return None
    try:
        return WgerClient(get_config())
    except Exception as e:
        logger.error(f"Failed to create wger client: {e}")
        return None


def resolve_equipment_ids(equipment_set: str = None, equipment: list = None) -> list[int]:
    """Resolve equipment names to wger IDs."""
    config = get_config()

    if equipment:
        names = equipment
    elif equipment_set:
        names = config.get("equipment_sets", {}).get(equipment_set, [])
    else:
        default = config.get("default_equipment", "home")
        names = config.get("equipment_sets", {}).get(default, [])

    return [EQUIPMENT_IDS[n] for n in names if n in EQUIPMENT_IDS]


def resolve_equipment_names(equipment_set: str = None, equipment: list = None) -> list[str]:
    """Resolve equipment set to equipment names."""
    config = get_config()

    if equipment:
        return equipment
    elif equipment_set:
        return config.get("equipment_sets", {}).get(equipment_set, [])
    else:
        default = config.get("default_equipment", "home")
        return config.get("equipment_sets", {}).get(default, [])


# === High-Level Functions (called by tools) ===

def get_workout_context(equipment_set: str = None, equipment: list = None,
                        days_history: int = 7) -> dict:
    """Get all data needed for workout planning.

    Returns raw data for Claude to create intelligent workout recommendations.
    """
    client = get_client()
    if not client:
        return {"error": "Wger not configured. Create ~/.goals-mcp/wger-config.yml"}

    try:
        # Get recent workouts
        sessions = client.get_recent_sessions(days_history)

        # Calculate muscle fatigue
        fatigue = calculate_muscle_fatigue(client, sessions)

        # Get available exercises for equipment
        equipment_ids = resolve_equipment_ids(equipment_set, equipment)
        exercises = get_exercises_for_equipment(client, equipment_ids)

        # Get exercise history (last weights, trends)
        exercise_history = get_exercise_history(client, sessions)

        # Format workouts for output
        formatted_workouts = format_workouts(client, sessions)

        return {
            "recent_workouts": formatted_workouts,
            "muscle_fatigue": fatigue,
            "available_exercises": exercises,
            "exercise_history": exercise_history,
            "equipment_available": resolve_equipment_names(equipment_set, equipment),
        }

    except Exception as e:
        logger.error(f"get_workout_context error: {e}")
        return {"error": str(e)}


def calculate_muscle_fatigue(client: WgerClient, sessions: list) -> dict[str, float]:
    """Calculate fatigue per muscle group (0.0 = recovered, 1.0 = just worked)."""
    fatigue = {group: 0.0 for group in RECOVERY_HOURS}
    now = datetime.now()

    for session in sessions:
        try:
            session_date_str = session.get("date", "")
            if "T" in session_date_str:
                session_date = datetime.fromisoformat(session_date_str.replace("Z", "+00:00"))
            else:
                session_date = datetime.strptime(session_date_str, "%Y-%m-%d")

            hours_ago = (now - session_date.replace(tzinfo=None)).total_seconds() / 3600

            logs = client.get_session_logs(session["id"])
            for log in logs:
                exercise = client.get_exercise(log["exercise"])
                muscles = exercise.get("muscles", []) + exercise.get("muscles_secondary", [])

                for muscle_id in muscles:
                    group = MUSCLE_GROUPS.get(muscle_id)
                    if group and group in RECOVERY_HOURS:
                        recovery = RECOVERY_HOURS[group]
                        # Linear decay: 1.0 at 0 hours, 0.0 at recovery hours
                        remaining = max(0, 1 - (hours_ago / recovery))
                        fatigue[group] = max(fatigue[group], remaining)

        except Exception as e:
            logger.debug(f"Error processing session {session.get('id')}: {e}")

    return fatigue


def get_exercises_for_equipment(client: WgerClient, equipment_ids: list[int]) -> list[dict]:
    """Get exercises available with given equipment."""
    exercises = []
    seen_ids = set()

    # Always include bodyweight exercises
    all_equipment = set(equipment_ids) | {7}  # 7 = bodyweight

    for eq_id in all_equipment:
        try:
            results = client.search_exercises(equipment=eq_id, limit=50)
            for ex in results:
                if ex["id"] not in seen_ids:
                    seen_ids.add(ex["id"])
                    # Format exercise for output
                    exercises.append(format_exercise(ex))
        except Exception as e:
            logger.debug(f"Error fetching exercises for equipment {eq_id}: {e}")

    return exercises


def format_exercise(ex: dict) -> dict:
    """Format exercise info for tool output."""
    # Get English name from translations
    name = "Unknown"
    for trans in ex.get("translations", []):
        if trans.get("language") == 2:  # English
            name = trans.get("name", name)
            break
    if name == "Unknown" and ex.get("translations"):
        name = ex["translations"][0].get("name", "Unknown")

    # Get muscle names
    muscles = []
    for m in ex.get("muscles", []):
        if isinstance(m, dict):
            muscles.append(m.get("name_en") or m.get("name", "Unknown"))
        elif isinstance(m, int):
            muscles.append(MUSCLE_NAMES.get(m, f"Muscle {m}"))

    # Get equipment names
    equipment = []
    for e in ex.get("equipment", []):
        if isinstance(e, dict):
            equipment.append(e.get("name", "Unknown"))
        elif isinstance(e, int):
            equipment.append(EQUIPMENT_NAMES.get(e, f"Equipment {e}"))

    # Get category
    category = "Unknown"
    if isinstance(ex.get("category"), dict):
        category = ex["category"].get("name", "Unknown")
    elif isinstance(ex.get("category"), int):
        category = CATEGORY_NAMES.get(ex["category"], "Unknown")

    return {
        "id": ex["id"],
        "name": name,
        "category": category,
        "muscles": muscles,
        "equipment": equipment,
    }


def get_exercise_history(client: WgerClient, sessions: list) -> dict:
    """Get exercise performance history from recent sessions."""
    history = {}

    for session in sessions:
        try:
            logs = client.get_session_logs(session["id"])
            for log in logs:
                exercise = client.get_exercise(log["exercise"])

                # Get exercise name
                name = f"Exercise {log['exercise']}"
                info = client.get_exercise_info(log["exercise"])
                for trans in info.get("translations", []):
                    if trans.get("language") == 2:
                        name = trans.get("name", name)
                        break

                weight = float(log.get("weight", 0) or 0)
                reps = log.get("repetitions") or log.get("reps", 0)

                if name not in history:
                    history[name] = {
                        "last_weight": weight,
                        "last_reps": reps,
                        "max_weight": weight,
                        "sessions": 1,
                    }
                else:
                    h = history[name]
                    h["last_weight"] = weight
                    h["last_reps"] = reps
                    h["max_weight"] = max(h["max_weight"], weight)
                    h["sessions"] += 1

        except Exception as e:
            logger.debug(f"Error getting exercise history: {e}")

    # Add trend analysis
    for name, h in history.items():
        if h["sessions"] >= 2:
            h["trend"] = "stable"  # Would need more data for real trend

    return history


def format_workouts(client: WgerClient, sessions: list) -> list[dict]:
    """Format workout sessions for output."""
    workouts = []

    for session in sessions:
        try:
            logs = client.get_session_logs(session["id"])

            # Determine focus based on muscles worked
            muscle_counts = {}
            exercises = []

            for log in logs:
                exercise = client.get_exercise(log["exercise"])
                info = client.get_exercise_info(log["exercise"])

                # Get name
                name = f"Exercise {log['exercise']}"
                for trans in info.get("translations", []):
                    if trans.get("language") == 2:
                        name = trans.get("name", name)
                        break

                exercises.append(name)

                # Count muscle groups
                for m_id in exercise.get("muscles", []):
                    group = MUSCLE_GROUPS.get(m_id, "Other")
                    muscle_counts[group] = muscle_counts.get(group, 0) + 1

            # Determine focus from most worked muscle group
            focus = "General"
            if muscle_counts:
                focus = max(muscle_counts, key=muscle_counts.get)
                if focus in ("Chest", "Shoulders", "Triceps"):
                    focus = "Push"
                elif focus in ("Back", "Biceps"):
                    focus = "Pull"
                elif focus == "Legs":
                    focus = "Legs"

            workouts.append({
                "date": session.get("date", "")[:10],
                "focus": focus,
                "exercises": exercises,
                "notes": session.get("notes", ""),
            })

        except Exception as e:
            logger.debug(f"Error formatting workout: {e}")

    return workouts


def search_exercise(query: str = None, muscle: str = None, equipment: str = None,
                    category: str = None, limit: int = 10) -> dict:
    """Search exercises by name, muscle, equipment, or category."""
    client = get_client()
    if not client:
        return {"error": "Wger not configured"}

    try:
        # Resolve muscle/equipment/category to IDs
        muscle_id = None
        if muscle:
            for m_id, m_name in MUSCLE_NAMES.items():
                if muscle.lower() in m_name.lower():
                    muscle_id = m_id
                    break

        equipment_id = None
        if equipment:
            equipment_id = EQUIPMENT_IDS.get(equipment)
            if not equipment_id:
                for name, eq_id in EQUIPMENT_IDS.items():
                    if equipment.lower() in name.lower():
                        equipment_id = eq_id
                        break

        category_id = None
        if category:
            category_id = CATEGORY_IDS.get(category)
            if not category_id:
                for name, cat_id in CATEGORY_IDS.items():
                    if category.lower() in name.lower():
                        category_id = cat_id
                        break

        results = client.search_exercises(
            query=query,
            muscle=muscle_id,
            equipment=equipment_id,
            category=category_id,
            limit=limit
        )

        exercises = [format_exercise(ex) for ex in results]
        return {"exercises": exercises, "count": len(exercises)}

    except Exception as e:
        return {"error": str(e)}


def log_workout(exercises: list, duration: int = None, notes: str = "",
                date: str = None) -> dict:
    """Log a completed workout session."""
    client = get_client()
    if not client:
        return {"error": "Wger not configured"}

    try:
        workout_date = date or datetime.now().strftime("%Y-%m-%d")

        # Create session
        session = client.create_session(workout_date, notes)
        session_id = session["id"]

        logged_exercises = []
        total_sets = 0

        for ex in exercises:
            # Find exercise by name
            name = ex.get("name", "")
            sets = ex.get("sets", 1)
            reps = ex.get("reps", 0)
            weight = ex.get("weight", 0)

            # Search for exercise
            search_results = client.search_exercises(query=name, limit=5)
            if not search_results:
                logged_exercises.append({
                    "name": name,
                    "status": "not_found"
                })
                continue

            exercise_id = search_results[0]["id"]

            # Log each set
            for _ in range(sets):
                client.log_set(session_id, exercise_id, reps, weight)
                total_sets += 1

            logged_exercises.append({
                "name": name,
                "exercise_id": exercise_id,
                "sets": sets,
                "reps": reps,
                "weight": weight,
                "status": "logged"
            })

        return {
            "success": True,
            "session_id": session_id,
            "date": workout_date,
            "exercises": logged_exercises,
            "total_sets": total_sets,
            "duration": duration,
            "message": f"Logged {len(logged_exercises)} exercises ({total_sets} sets)"
        }

    except Exception as e:
        return {"error": str(e)}


def log_weight(weight: float, unit: str = "kg", date: str = None) -> dict:
    """Log body weight and return trends."""
    client = get_client()
    if not client:
        return {"error": "Wger not configured"}

    try:
        # Convert lbs to kg if needed
        weight_kg = weight
        if unit.lower() == "lbs":
            weight_kg = weight * 0.453592

        entry_date = date or datetime.now().strftime("%Y-%m-%d")
        client.log_weight_entry(weight_kg, entry_date)

        # Get history for trends
        history = client.get_weight_history(days=30)

        weights = [float(h["weight"]) for h in history]

        avg_7d = None
        avg_30d = None
        change = None

        if weights:
            avg_30d = sum(weights) / len(weights)
            if len(weights) >= 7:
                avg_7d = sum(weights[:7]) / 7
            if len(weights) >= 2:
                change = weights[0] - weights[1]

        return {
            "success": True,
            "weight": weight_kg,
            "unit": "kg",
            "date": entry_date,
            "avg_7d": round(avg_7d, 1) if avg_7d else None,
            "avg_30d": round(avg_30d, 1) if avg_30d else None,
            "change": round(change, 1) if change else None,
            "message": f"Logged {weight_kg:.1f} kg"
        }

    except Exception as e:
        return {"error": str(e)}


def get_workout_history(days: int = 7) -> dict:
    """Get detailed workout history."""
    client = get_client()
    if not client:
        return {"error": "Wger not configured"}

    try:
        sessions = client.get_recent_sessions(days)
        workouts = format_workouts(client, sessions)
        fatigue = calculate_muscle_fatigue(client, sessions)

        return {
            "workouts": workouts,
            "count": len(workouts),
            "muscle_fatigue": fatigue,
            "days": days
        }

    except Exception as e:
        return {"error": str(e)}


def get_fitness_summary() -> dict:
    """Get combined fitness dashboard."""
    client = get_client()
    if not client:
        return {"error": "Wger not configured"}

    try:
        # Weight trend
        weight_history = client.get_weight_history(days=30)
        weights = [float(h["weight"]) for h in weight_history]

        weight_summary = None
        if weights:
            weight_summary = {
                "current": weights[0] if weights else None,
                "avg_7d": round(sum(weights[:7]) / len(weights[:7]), 1) if len(weights) >= 7 else None,
                "avg_30d": round(sum(weights) / len(weights), 1),
                "change_7d": round(weights[0] - weights[6], 1) if len(weights) >= 7 else None,
            }

        # Workout stats
        sessions_7d = client.get_recent_sessions(days=7)
        sessions_30d = client.get_recent_sessions(days=30)

        workout_summary = {
            "workouts_7d": len(sessions_7d),
            "workouts_30d": len(sessions_30d),
        }

        # Muscle balance (last 7 days)
        fatigue = calculate_muscle_fatigue(client, sessions_7d)

        return {
            "weight": weight_summary,
            "workouts": workout_summary,
            "muscle_balance": fatigue,
        }

    except Exception as e:
        return {"error": str(e)}


def log_meal(description: str, calories: int = None, protein: float = None,
             carbs: float = None, fat: float = None, meal_type: str = None,
             date: str = None) -> dict:
    """Log a meal to nutrition diary."""
    client = get_client()
    if not client:
        return {"error": "Wger not configured"}

    try:
        # If macros provided directly, use them
        if calories is not None:
            return {
                "success": True,
                "description": description,
                "calories": calories,
                "protein": protein,
                "carbs": carbs,
                "fat": fat,
                "meal_type": meal_type,
                "source": "manual",
                "message": f"Logged {description}: {calories} cal"
            }

        # Search ingredient database
        results = client.search_ingredient(description, limit=5)

        if not results:
            return {
                "success": False,
                "message": f"No ingredients found for '{description}'. Provide calories manually."
            }

        # Use first result
        ingredient = results[0]

        # Get nutrition info
        energy = ingredient.get("energy", 0)
        protein_g = ingredient.get("protein", 0)
        carbs_g = ingredient.get("carbohydrates", 0)
        fat_g = ingredient.get("fat", 0)

        # Log to diary (100g default)
        datetime_str = None
        if date:
            datetime_str = f"{date}T12:00:00"

        client.log_nutrition_entry(ingredient["id"], 100, datetime_str)

        return {
            "success": True,
            "description": description,
            "ingredient_matched": ingredient.get("name", description),
            "amount": "100g",
            "calories": energy,
            "protein": protein_g,
            "carbs": carbs_g,
            "fat": fat_g,
            "meal_type": meal_type,
            "source": "wger",
            "message": f"Logged {description}: {energy} cal, {protein_g}g protein"
        }

    except Exception as e:
        return {"error": str(e)}


def get_nutrition_summary(date: str = None, days: int = 1) -> dict:
    """Get nutrition summary for a date or period."""
    client = get_client()
    if not client:
        return {"error": "Wger not configured"}

    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        entries = client.get_nutrition_diary(target_date)

        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0

        for entry in entries:
            ingredient = client.get_ingredient(entry["ingredient"])
            amount = entry.get("amount", 100) / 100  # Convert to per 100g multiplier

            total_calories += (ingredient.get("energy", 0) or 0) * amount
            total_protein += (ingredient.get("protein", 0) or 0) * amount
            total_carbs += (ingredient.get("carbohydrates", 0) or 0) * amount
            total_fat += (ingredient.get("fat", 0) or 0) * amount

        return {
            "date": target_date,
            "entries": len(entries),
            "calories": round(total_calories),
            "protein": round(total_protein, 1),
            "carbs": round(total_carbs, 1),
            "fat": round(total_fat, 1),
        }

    except Exception as e:
        return {"error": str(e)}
