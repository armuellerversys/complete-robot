import os
from ovos_workshop.skills.ovos import OVOSSkill
from ovos_workshop.skill_launcher import load_skill_module

def check_structure():
    base_path = "/skills/skill-test"
    locale_path = os.path.join(base_path, "locale", "en-us")
    
    print(f"--- 🔍 Checking Skill Path: {base_path} ---")
    
    if not os.path.exists(locale_path):
        print(f"❌ ERROR: Locale path not found at {locale_path}")
        # List what actually exists
        print(f"Found in skill folder: {os.listdir(base_path)}")
        return

    print(f"✅ Locale path found. Files: {os.listdir(locale_path)}")
    
    # Check intent file content
    intent_file = os.path.join(locale_path, "vehicle.intent")
    if os.path.exists(intent_file):
        with open(intent_file, 'r') as f:
            print(f"📄 Intent content:\n{f.read()}")
    else:
        print("❌ ERROR: vehicle.intent missing!")

if __name__ == "__main__":
    check_structure()