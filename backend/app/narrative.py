import json
import os
import random
from datetime import datetime, timezone

def load_templates():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'narrative_templates.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def evaluate_condition(cond, stats, streak):
    if cond == "always_true":
        return True
    
    current_streak = streak.get("current_streak", 0)
    avg_per_day = stats.get("avg_per_day", 0)
    
    if cond == "streak_over_30":
        return current_streak >= 30
    if cond == "high_avg_per_day":
        return avg_per_day >= 30
    if cond == "streak_0":
        return current_streak == 0
    if cond == "streak_1_2":
        return 1 <= current_streak <= 2
    if cond == "streak_3_5":
        return 3 <= current_streak <= 5
    if cond == "streak_6_10":
        return 6 <= current_streak <= 10
    if cond == "streak_11_plus":
        return current_streak >= 11
        
    return False

def safe_interpolate(text, vars_dict):
    for k, v in vars_dict.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text

def generate_narrative(stats, streak, seed=None):
    templates = load_templates()
    
    if not seed:
        seed = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
    rng = random.Random(seed)
    
    vars_dict = {
        "days_active": stats.get("days_active", 0),
        "avg_per_day": stats.get("avg_per_day", 0),
        "top_source": stats.get("top_source", "").replace("_", " "),
        "current_streak": streak.get("current_streak", 0),
        "total_listens": stats.get("total_listens", 0)
    }
    
    result = {}
    
    for key, items in templates.items():
        # Separate into specific matches and fallbacks (always_true)
        specific_matches = []
        fallbacks = []
        
        for item in items:
            cond = item.get("condition", "always_true")
            if evaluate_condition(cond, stats, streak):
                if cond == "always_true":
                    fallbacks.append(item["text"])
                else:
                    specific_matches.append(item["text"])
        
        # Prefer specific matches over fallbacks
        pool = specific_matches if specific_matches else fallbacks
        
        if pool:
            chosen = rng.choice(pool)
            result[key] = safe_interpolate(chosen, vars_dict)
        else:
            result[key] = ""
            
    return result
