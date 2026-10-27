with open('backend/app/rules/rule_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_block = '''        version_id = getattr(profile, "version_id", "prof-custom")
        profile_name = getattr(profile, "profile_name", "Custom Strategy")
        raw_rules = getattr(profile, "rules", [])'''

new_block = '''        if isinstance(profile, list):
            raw_rules = profile
            version_id = "prof-custom"
            profile_name = "Custom Strategy"
        else:
            version_id = getattr(profile, "version_id", "prof-custom")
            profile_name = getattr(profile, "profile_name", "Custom Strategy")
            raw_rules = getattr(profile, "rules", []) or []'''

if old_block in text:
    text = text.replace(old_block, new_block, 1)
    with open('backend/app/rules/rule_engine.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("SUCCESS: rule_engine.py updated to support list profiles")
else:
    print("WARNING: old_block not found in rule_engine.py")

