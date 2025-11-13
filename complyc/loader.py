import yaml

def load_rules(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    style = data.get("style", {})
    rules = data.get("rules", [])
    return style, rules
