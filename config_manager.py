import json
import os

class ConfigManager:
    def __init__(self, file_path="rules_config.json"):
        self.file_path = file_path
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.default_img_dir = os.path.join(self.base_dir, "img")
        
        if not os.path.exists(self.default_img_dir):
            os.makedirs(self.default_img_dir)
            
        self.default_rules = self._generate_empty_rules()

    def _generate_empty_rules(self):
        rules = []
        for i in range(1, 257):
            rule_item = {
                "id": i,
                "location": f"地點 {i}",
                "source_dir": "",
                "source_filename": "",
                "output_dir": self.default_img_dir,
                "restore_dir": "",
                "target_x": 800,
                "target_y": 600,
                "count_broken": 0,
                "count_no_update": 0,
                "count_missing": 0,
                "last_hash": "",
                "enabled": False,
                "status": "停止"
            }
            rules.append(rule_item)
        return rules

    def load_config(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self.default_rules
        return self.default_rules

    def save_config(self, data):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def update_rule(self, rule_id, new_data):
        all_rules = self.load_config()
        if 1 <= rule_id <= 256:
            all_rules[rule_id - 1].update(new_data)
            self.save_config(all_rules)