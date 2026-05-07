# database/people_db.py

import json
import os

people_db = {
    "C1": {
        "name": "Aishwarya",
        "age": 20,
        "email": "bokkiaishwarya@gmail.com",
        "mobile": "9392512067",
        "image" : "datasets/Custom/C1/4.jpg"
    },
    "C2": {
        "name": "Akanksha",
        "age": 20,
        "email": "akanksharanir@gmail.com",
        "mobile": "8639575597",
        "image" : "datasets/Custom/C2/4.jpg"
    },
    "C3": {
        "name": "Lohith",
        "age": 20,
        "email": "lohith@gmail.com",
        "mobile": "9876543210",
        "image" : "datasets/Custom/C3/2.jpg"    
    },
    "C4": {
        "name": "Praveen",
        "age": 20,
        "email": "praveen@gmail.com",
        "mobile": "8522816126",
        "image" : "datasets/Custom/C4/3.jpg"
    },
    "C5": {
        "name": "Pushpan",
        "age": 22,
        "email": "pushpan@gmail.com",
        "mobile": "7337528757",
        "image" : "datasets/Custom/C5/3.jpg"
    },
    "C6": {
        "name": "Raj Ratan",
        "age": 22,
        "email": "raj.ratan@gmail.com",
        "mobile": "9876543210",
        "image" : "datasets/Custom/C6/4.jpg"
    },
    "C7": {
        "name": "Sampath",
        "age": 19,
        "email": "malleboinasampath@gmail.com",
        "mobile": "6302694985",
        "image" : "datasets/Custom/C7/5.jpg"
    },
    "C8": {
        "name": "Swathi",
        "age": 20,
        "email": "bayyaswathi@gmail.com",
        "mobile": "6302182942",
        "image" : "datasets/Custom/C8/5.jpg"
    },
    "C9": {
        "name": "Varun",
        "age": 21,
        "email": "varun@gmail.com",
        "mobile": "9063356562",
        "image" : "datasets/Custom/C9/5.jpg"
    },
}

def save_people_db():
    """Save people_db to JSON file for persistence."""
    try:
        with open('database/people_db.json', 'w') as f:
            json.dump(people_db, f, indent=4)
        print("✅ People database saved to database/people_db.json")
    except Exception as e:
        print(f"❌ Failed to save people_db: {e}")

def load_people_db():
    """Load people_db from JSON if exists."""
    global people_db
    json_path = 'database/people_db.json'
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                loaded = json.load(f)
                people_db.update(loaded)  # Merge with existing
            print(f"✅ Loaded {len(loaded)} people from {json_path}")
        except Exception as e:
            print(f"❌ Failed to load people_db: {e}")

# Load on import
load_people_db()

def search_person(query):
    query = query.strip().lower()
    
    for pid, person in people_db.items():
        # ID matching
        if query == pid.lower().strip():
            return pid, person
        
        # Email matching
        if query == person["email"].lower().strip():
            return pid, person
        
        # Mobile matching (flexible)
        mobile_query = query.replace(" ", "").replace("-", "")
        person_mobile = str(person["mobile"]).replace(" ", "").replace("-", "")
        if mobile_query == person_mobile:
            return pid, person
        
        # Name matching (partial)
        if query in person["name"].lower():
            return pid, person
    
    return None, None

def get_person_by_id(person_id):
    return people_db.get(person_id)


def get_person_by_email(email):
    for pid, details in people_db.items():
        if details["email"] == email:
            return pid, details
    return None, None


def get_person_by_mobile(mobile):
    for pid, details in people_db.items():
        if details["mobile"] == mobile:
            return pid, details
    return None, None


def add_person(person_id, name, age, email, mobile):
    people_db[person_id] = {
        "name": name,
        "age": age,
        "email": email,
        "mobile": mobile,
    }

# If you want to statically add C10 in the default dataset, do it above directly in `people_db`.
# e.g.:
# people_db["C10"] = {
#     "name": "Sujatha",
#     "age": "44",
#     "email": "sujatthasuresh@gmail.com",
#     "mobile": "9618025106",
#     "image": "datasets/Custom/C10/1.jpg"
# }

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM_DATASET_PATH = os.path.join(BASE_DIR, "datasets", "Custom")

def find_person(value):

    pid = None
    details = None
    image_path = None

    # Search by ID
    if value in people_db:
        pid = value
        details = people_db[pid]
    else:
        for person_id, info in people_db.items():
            if info["email"] == value or info["mobile"] == value:
                pid = person_id
                details = info
                break

    if pid is None:
        return None, None, None

    # Fetch image
    person_folder = os.path.join(CUSTOM_DATASET_PATH, pid)

    if os.path.exists(person_folder):
        for f in os.listdir(person_folder):
            if f.lower().endswith((".jpg", ".png", ".jpeg")):
                image_path = os.path.join(person_folder, f)
                break

    return pid, details, image_path

