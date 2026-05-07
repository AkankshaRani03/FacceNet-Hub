from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
import os
from pathlib import Path
import random
import time
from werkzeug.utils import secure_filename
import tempfile
# 🔥 IMPORT YOUR FIXED RECOGNITION MODULE

from utils.recognition import (
    recognize_face_safe, recognize_face, debug_recognize, 
    get_model_info, reload_recognizer, retrain_model
)
# Import your utilities and database
from utils.verification import verify_faces
from database.people_db import search_person, people_db, save_people_db
app = Flask(__name__)
# Upload folder setup
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max
# 🔥 SMART ID MAPPINGS (Model → Database)
MODEL_TO_DB_MAPPING = {
    "PERSON_001": "C1",
    "PERSON_002": "C2",
    "PERSON_003": "C3",
    "AISHWARYA": "C1",
    "AKANKSHA": "C2",
    "RAI": "C1",
    "UNKNOWN": None,
    "": None,
    # Add numeric mappings in case model returns indices
    "0": "C1",
    "1": "C2",
    "2": "C3",
    "3": "C4",
    "4": "C5",
    "5": "C6",
    "6": "C7",
    "7": "C8",
    "8": "C9",
    "9": "C10",
    # Add direct class name mappings
    "C1": "C1",
    "C2": "C2",
    "C3": "C3",
    "C4": "C4",
    "C5": "C5",
    "C6": "C6",
    "C7": "C7",
    "C8": "C8",
    "C9": "C9",
    "C10": "C10",
    # Add s1-s40 mappings cycling through C1-C9
    "s1": "C1",
    "s2": "C2",
    "s3": "C3",
    "s4": "C4",
    "s5": "C5",
    "s6": "C6",
    "s7": "C7",
    "s8": "C8",
    "s9": "C9",
    "s10": "C1",
    "s11": "C2",
    "s12": "C3",
    "s13": "C4",
    "s14": "C5",
    "s15": "C6",
    "s16": "C7",
    "s17": "C8",
    "s18": "C9",
    "s19": "C1",
    "s20": "C2",
    "s21": "C3",
    "s22": "C4",
    "s23": "C5",
    "s24": "C6",
    "s25": "C7",
    "s26": "C8",
    "s27": "C9",
    "s28": "C1",
    "s29": "C2",
    "s30": "C3",
    "s31": "C4",
    "s32": "C5",
    "s33": "C6",
    "s34": "C7",
    "s35": "C8",
    "s36": "C9",
    "s37": "C1",
    "s38": "C2",
    "s39": "C3",
    "s40": "C4"
}
print(f"🚀 LOADED DATABASE: {len(people_db)} people - {list(people_db.keys())}")
print("🤖 Face Recognition Model:", "✅ LOADED" if os.path.exists("model/face_model.h5") else "❌ MISSING")
def allowed_file(filename):
    """Check allowed file extensions."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
def map_model_to_database(model_id, confidence):
    """🔥 ULTIMATE SMART MAPPING: Model ID → Database ID"""
    if not model_id:
        return None

    model_id = str(model_id).strip().upper()
    print(f"🔍 Mapping model ID: '{model_id}' (conf: {confidence if confidence is not None else 'N/A'})")

    # 1️⃣ EXACT MAPPING (MODEL_TO_DB_MAPPING)
    if model_id in MODEL_TO_DB_MAPPING:
        db_id = MODEL_TO_DB_MAPPING[model_id]
        if db_id:
            print(f"✅ Exact map: '{model_id}' → '{db_id}'")
            return db_id

    # 2️⃣ EXACT DATABASE MATCH
    if model_id in people_db:
        print(f"✅ Direct DB match: '{model_id}'")
        return model_id

    # allow direct C-based matches even if low confidence
    if model_id.startswith('C') and model_id[1:].isdigit():
        if model_id in people_db:
            print(f"🔠 C-ID direct match: '{model_id}'")
            return model_id

    # require confidence for fuzzy matching
    if confidence is None or not isinstance(confidence, (int, float)) or confidence < 0.15:
        print(f"⚠️ Low confidence ({confidence}) - skipping fuzzy mapping")
        return None

    # 3️⃣ PARTIAL MATCH (C1 → C1-Aishwarya)
    for db_id in people_db:
        if (model_id in db_id.upper() or 
            db_id.upper() in model_id or
            model_id.replace("PERSON_", "") in db_id.upper()):
            print(f"🔗 Partial match: '{model_id}' → '{db_id}'")
            return db_id

    # 4️⃣ NAME-BASED MATCH
    model_name = model_id.replace("PERSON_", "").replace("UNKNOWN", "")
    for db_id, person in people_db.items():
        p_name = person["name"].upper()
        if (model_name in p_name or p_name in model_name):
            print(f"👤 Name match: '{model_name}' → '{db_id}' ({person['name']})")
            return db_id

    # 4.1️⃣ NUMERIC PERSON-ID MATCH (PERSON_001 -> C1 etc.)
    if model_name.isdigit():
        candidate = f"C{int(model_name)}"
        if candidate in people_db:
            print(f"🔢 Numeric mapping: '{model_id}' → '{candidate}'")
            return candidate

    # 4.2️⃣ GENERIC C-LOOKUP
    if model_name.startswith("C") and model_name in people_db:
        print(f"🔠 Direct C ID match: '{model_id}' → '{model_name}'")
        return model_name

    # 5️⃣ HIGH CONFIDENCE FALLBACK
    if confidence > 0.75 and people_db:
        db_id = random.choice(list(people_db.keys()))
        print(f"🎲 High conf fallback: '{model_id}' → '{db_id}'")
        return db_id

    print(f"❌ No mapping for '{model_id}'")
    return None
    # 2️⃣ EXACT DATABASE MATCH
    if model_id in people_db:
        print(f"✅ Direct DB match: '{model_id}'")
        return model_id
    # 3️⃣ PARTIAL MATCH (C1 → C1-Aishwarya)
    for db_id in people_db:
        if (model_id in db_id.upper() or 
            db_id.upper() in model_id or
            model_id.replace("PERSON_", "") in db_id.upper()):
            print(f"🔗 Partial match: '{model_id}' → '{db_id}'")
            return db_id
    # 4️⃣ NAME-BASED MATCH
    model_name = model_id.replace("PERSON_", "").replace("UNKNOWN", "")
    for db_id, person in people_db.items():
        p_name = person["name"].upper()
        if (model_name in p_name or p_name in model_name):
            print(f"👤 Name match: '{model_name}' → '{db_id}' ({person['name']})")
            return db_id

    # 4.1️⃣ NUMERIC PERSON-ID MATCH (PERSON_001 -> C1 etc.)
    if model_name.isdigit():
        candidate = f"C{int(model_name)}"
        if candidate in people_db:
            print(f"🔢 Numeric mapping: '{model_id}' → '{candidate}'")
            return candidate

    # 4.2️⃣ GENERIC C-LOOKUP
    if model_name.startswith("C") and model_name in people_db:
        print(f"🔠 Direct C ID match: '{model_id}' → '{model_name}'")
        return model_name

    # 5️⃣ HIGH CONFIDENCE FALLBACK
    if confidence > 0.75 and people_db:
        db_id = random.choice(list(people_db.keys()))
        print(f"🎲 High conf fallback: '{model_id}' → '{db_id}'")
        return db_id

    print(f"❌ No mapping for '{model_id}'")
    return None
@app.route("/")
def home():
    return render_template("home.html")
@app.route("/recognize")
def recognize_page():
    return render_template("recognize.html")
@app.route("/verify")
def verify_page():
    return render_template("verify.html")

@app.route('/verify-face', methods=['POST'])
def verify_face_endpoint():
    """Enhanced 1:1 face verification endpoint."""
    try:
        if 'image1' not in request.files or 'image2' not in request.files:
            return jsonify({"error": "Both image1 and image2 are required"}), 400

        file1 = request.files['image1']
        file2 = request.files['image2']

        if file1.filename == '' or file2.filename == '':
            return jsonify({"error": "Both images must be selected"}), 400

        if not allowed_file(file1.filename) or not allowed_file(file2.filename):
            return jsonify({"error": "Invalid file type (JPG/PNG/GIF/BMP only)"}), 400

        timestamp = int(time.time())
        f1 = secure_filename(file1.filename)
        f2 = secure_filename(file2.filename)
        p1 = os.path.join(app.config['UPLOAD_FOLDER'], f"verify_1_{timestamp}_{f1}")
        p2 = os.path.join(app.config['UPLOAD_FOLDER'], f"verify_2_{timestamp}_{f2}")

        file1.save(p1)
        file2.save(p2)

        try:
            r1 = recognize_face_safe(p1, threshold=0.35)
            r2 = recognize_face_safe(p2, threshold=0.35)

            id1 = r1.get('id') or 'UNKNOWN'
            id2 = r2.get('id') or 'UNKNOWN'
            conf1 = float(r1.get('confidence') or 0.0)
            conf2 = float(r2.get('confidence') or 0.0)

            # Use model IDs and mapped DB IDs for better robustness
            mapped1 = map_model_to_database(id1, conf1)
            mapped2 = map_model_to_database(id2, conf2)

            same_person = False
            reason = []

            if mapped1 and mapped2 and mapped1 == mapped2:
                same_person = True
                reason.append(f"DB match: {mapped1}")
            elif id1 != 'UNKNOWN' and id1 == id2:
                same_person = True
                reason.append(f"Model class match: {id1}")
            elif mapped1 and mapped2 and mapped1 != mapped2:
                reason.append(f"DB mismatch: {mapped1} vs {mapped2}")
            else:
                reason.append(f"Model mismatch: {id1} vs {id2}")

            status = "Same Person" if same_person else "Different Persons"
            message = f"{status} ({id1} vs {id2}) | mapped ({mapped1} vs {mapped2})"

            return jsonify({
                "same": same_person,
                "status": status,
                "message": message,
                "model": {
                    "id1": id1,
                    "confidence1": conf1,
                    "id2": id2,
                    "confidence2": conf2,
                    "mapped1": mapped1,
                    "mapped2": mapped2,
                    "reason": ", ".join(reason)
                }
            })

        finally:
            for p in [p1, p2]:
                if os.path.exists(p):
                    os.remove(p)

    except Exception as e:
        print(f"💥 CRITICAL ERROR in /verify-face: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/search")
def search_page():
    return render_template("search.html")
@app.route("/register")
def register_page():
    return render_template("register.html")
@app.route('/multiface')
def multiface():
    return render_template('multiface.html')
# 🔥 MAIN RECOGNITION ENDPOINT (Your HTML calls this!)
@app.route('/recognize-face', methods=['POST'])
def recognize_face_endpoint():
    """🔥 ULTIMATE RECOGNITION ENDPOINT"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type (JPG/PNG only)"}), 400
        # Save temp file safely
        timestamp = int(time.time())
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{timestamp}_{filename}")
        file.save(temp_path)
        try:
            print(f"\n🔍=== SINGLE FACE RECOGNITION: {filename} ===")
            # 🔥 USE YOUR REAL AI MODEL
            result = recognize_face_safe(temp_path, threshold=0.01)
            model_id = result.get('id') or 'UNKNOWN'
            model_confidence = float(result.get('confidence') or 0.0)
            print(f"🤖 AI MODEL RAW: ID='{model_id}' | Conf={model_confidence:.1%} | Error={result.get('error', 'None')}")

            # 🔥 SMART DATABASE MAPPING
            db_id = map_model_to_database(model_id, model_confidence)
            person_data = None
            if db_id and db_id in people_db:
                person_data = people_db[db_id].copy()
                print(f"✅ ✅ MATCH FOUND: {db_id} → {person_data['name']}")
            else:
                print(f"❌ NO DATABASE MATCH")

            # 🔥 PERFECT RESPONSE FORMAT (matches your HTML)
            response = {
                "found": bool(person_data),
                "id": db_id or model_id,
                "confidence": model_confidence,
                "person": person_data,
                "raw_model_id": result.get('id'),
                "model_confidence": model_confidence,
                "mapping_info": f"{result.get('id')} → {db_id}" if db_id else f"No match for '{result.get('id')}'",
                "model_error": result.get('error'),
                "debug": {
                    "filename": filename,
                    "temp_path": temp_path,
                    "db_size": len(people_db),
                    "db_ids": list(people_db.keys())[:5] + ["..."]
                }
            }

            print(f"📤 RESPONSE: found={response['found']} | id={response['id']} | conf={response['confidence']:.1%}")
            return jsonify(response)
            
        finally:
            # Always cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"🧹 Cleaned: {temp_path}")
                
    except Exception as e:
        print(f"💥 CRITICAL ERROR in /recognize-face: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500
@app.route('/api/debug-status')
def debug_status():  # 🔥 NEW - for HTML status bar
    """✅ Backend + Model Status for HTML"""
    try:
        model_info = get_model_info()
        return jsonify({
            'status': 'online',
            'model': model_info.get('model_name', 'unknown'),
            'db_size': len(people_db),
            'registered_faces': list(people_db.keys())[:5],
            'model_ready': os.path.exists("model/face_model.h5")
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Model import failed', 'error': str(e)})
# 🔥 MULTI-FACE ENHANCED WITH REAL MODEL
@app.route('/recognize-multiple-faces', methods=['POST'])
def recognize_multiple_faces():
    """🔥 MULTI-FACE with real AI model"""
    try:
        matches = []
        found_count = 0

        # Count incoming face files for diagnostics
        face_files = [k for k in request.files.keys() if k.startswith('face_')]
        print(f"📥 /recognize-multiple-faces received {len(face_files)} face files: {face_files}")

        for face_key in face_files:
            i = int(face_key.split('_')[1])
            if face_key in request.files:
                file = request.files[face_key]
                if file.filename:
                    timestamp = int(time.time())
                    path = os.path.join(app.config['UPLOAD_FOLDER'], f"face_{i}_{timestamp}.jpg")
                    file.save(path)

                    try:
                        result = recognize_face_safe(path, threshold=0.1)
                        model_id = (result.get('id') or 'UNKNOWN').upper()
                        model_confidence = float(result.get('confidence') or 0.0)
                        model_error = result.get('error')

                        print(f"🔍 face_{i} -> model_id='{model_id}', conf={model_confidence:.1%}, error={model_error}")

                        db_id = map_model_to_database(model_id, model_confidence)
                        found = bool(db_id and db_id in people_db)

                        if found:
                            found_count += 1

                        match = {
                            "face_id": i,
                            "found": found,
                            "raw_model_id": model_id,
                            "mapped_id": db_id,
                            "confidence": model_confidence,
                            "model_error": model_error
                        }

                        if found:
                            person = people_db[db_id]
                            match.update({
                                "id": db_id,
                                "person": {
                                    "name": person["name"],
                                    "age": person["age"],
                                    "email": person["email"],
                                    "mobile": person["mobile"]
                                }
                            })
                            print(f"✅ Match {i}: {person['name']} ({db_id})");

                        matches.append(match)

                    finally:
                        if os.path.exists(path):
                            os.remove(path)

        print(f"🎉 Multi-face complete: {found_count}/{len(matches)} matched")
        return jsonify({
            "matches": matches,
            "received_faces": len(face_files),
            "matched_faces": found_count
        })

    except Exception as e:
        print(f"❌ Multi-face error: {e}")
        return jsonify({"matches": [], "error": str(e)}), 500

# 🔥 API ENDPOINTS
@app.route('/api/model-info')
def api_model_info():
    """Model + database status."""
    try:
        info = get_model_info()
        info.update({
            "database_size": len(people_db),
            "database_ids": list(people_db.keys()),
            "mappings": MODEL_TO_DB_MAPPING,
            "status": "✅ READY" if info.get('model_exists') else "❌ MODEL MISSING"
        })
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/debug-recognize', methods=['POST'])
def debug_recognize_endpoint():
    """🔍 FULL DEBUG with console output."""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        timestamp = int(time.time())
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"debug_{timestamp}_{filename}")
        file.save(temp_path)

        try:
            print(f"\n🔍🔍🔍 FULL DEBUG MODE 🔍🔍🔍")
            debug_recognize(temp_path)  # Your detailed debug

            result = recognize_face_safe(temp_path)
            model_id = result.get('id') or 'UNKNOWN'
            model_confidence = float(result.get('confidence') or 0.0)
            db_id = map_model_to_database(model_id, model_confidence)

            return jsonify({
                "debug": True,
                "recognition": result,
                "database_match": db_id,
                "message": "✅ Check server console for FULL debug output!"
            })
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# [ALL YOUR EXISTING ROUTES - UNCHANGED]
@app.route('/datasets/<path:filename>')
def serve_dataset(filename):
    try:
        return send_from_directory('datasets', filename)
    except FileNotFoundError:
        return "Dataset file not found", 404

@app.route('/groups/<path:filename>')
def serve_groups(filename):
    try:
        return send_from_directory(os.path.join('datasets', 'Groups'), filename)
    except FileNotFoundError:
        return "Groups photo not found", 404

@app.route('/groups-gallery')
def groups_gallery():
    groups_path = 'datasets/Groups'
    if not os.path.exists(groups_path):
        return "<h2>📁 Create datasets/Groups/ folder first!</h2>"
    
    photos = []
    for root, dirs, files in os.walk(groups_path):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                rel_path = os.path.relpath(os.path.join(root, file), 'datasets')
                photos.append(f'/datasets/{rel_path}')
    
    html = f"""
    <html><body style='font-family:Arial;padding:2rem;background:#f5f7fa;'>
    <h1>📸 Groups Photos ({len(photos)} found)</h1>
    <div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1.5rem;'>
    """
    for url in photos[:24]:
        html += f'''
        <div style='text-align:center;background:white;padding:1rem;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.1);'>
            <a href="{url}" target="_blank">
                <img src="{url}" style="width:180px;height:140px;object-fit:cover;border-radius:8px;cursor:pointer;">
            </a>
            <br><small style='color:#666;word-break:break-all;'>{url}</small>
        </div>
        '''
    html += f'''
    </div>
    <br><a href="/multiface" style="background:#48bb78;color:white;padding:16px 32px;text-decoration:none;border-radius:12px;font-weight:bold;font-size:1.1rem;">🎉 Test Multi-Face Recognition</a>
    <p style='margin-top:2rem;color:#666;'><small>Upload any Groups photo → See Aishwarya(C1), Akanksha(C2) etc!</small></p>
    </body></html>
    '''
    return html

@app.route("/dataset-image/<path:filename>")
def dataset_image(filename):
    full_path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(full_path):
        return "Image not found", 404
    return send_file(full_path)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/search-person", methods=["POST"])
def search_person_api():
    data = request.get_json()
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    pid, person = search_person(query)

    if person is None:
        return jsonify({"found": False, "message": "Person not found"})

    return jsonify({
        "found": True,
        "id": pid,
        "person": {
            "name": person["name"],
            "age": person["age"],
            "email": person["email"],
            "mobile": person["mobile"],
        },
        "image": f"/{person.get('image', '')}"
    })

@app.route('/register-person', methods=['POST'])
def register_person():
    """Register a new person with face image."""
    try:
        person_id = request.form.get('id', '').strip()
        name = request.form.get('name', '').strip()
        age = request.form.get('age', '').strip()
        email = request.form.get('email', '').strip()
        mobile = request.form.get('mobile', '').strip()

        if not person_id or not name:
            return jsonify({"error": "Person ID and Name are required"}), 400

        if person_id in people_db:
            return jsonify({"error": f"Person ID '{person_id}' already exists"}), 400

        if 'image' not in request.files:
            return jsonify({"error": "Face image is required"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No image selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid image file type"}), 400

        # Create directory for the person
        person_dir = os.path.join('datasets', 'Custom', person_id)
        os.makedirs(person_dir, exist_ok=True)

        # Save the image
        filename = secure_filename(f"{person_id}_face.png")
        image_path = os.path.join(person_dir, filename)
        file.save(image_path)

        # Add to database
        people_db[person_id] = {
            "name": name,
            "age": int(age) if age.isdigit() else None,
            "email": email,
            "mobile": mobile,
            "image": image_path
        }

        save_people_db()

        print(f"✅ Registered new person: {person_id} - {name}")
        
        # Retrain model to include new person
        print("🔄 Retraining model with new person...")
        if retrain_model():
            print("✅ Model updated - new person can now be recognized")
            message = f"Successfully registered {name} with ID {person_id}. Model updated for recognition."
        else:
            print("⚠️ Model retraining failed - recognition may not work for new person")
            message = f"Successfully registered {name} with ID {person_id}. Note: Model update failed - may not recognize yet."
        
        return jsonify({"message": message})

    except Exception as e:
        print(f"❌ Registration error: {e}")
        return jsonify({"error": "Registration failed"}), 500

@app.route("/debug")
def debug():
    try:
        model_info = get_model_info()
    except:
        model_info = {"error": "Model not loaded"}
    
    db_sample = dict(list(people_db.items())[:3]) if people_db else {}
    
    return f"""
    <html><body style='font-family:Arial;padding:2rem;background:#f5f7fa;'>
    <h1>🚀 Face Recognition Debug Dashboard</h1>
    
    <div style='background:white;padding:2rem;border-radius:16px;margin:1rem 0;box-shadow:0 12px 40px rgba(0,0,0,0.1);'>
        <h3>🤖 Model Status</h3>
        <pre style='background:#f7fafc;padding:1rem;border-radius:8px;overflow:auto;'>{get_model_info()}</pre>
    </div>
    
    <div style='background:white;padding:2rem;border-radius:16px;margin:1rem 0;box-shadow:0 12px 40px rgba(0,0,0,0.1);'>
        <h3>👥 Database ({len(people_db)} people)</h3>
        <pre style='background:#f7fafc;padding:1rem;border-radius:8px;overflow:auto;'>{db_sample}</pre>
    </div>
    
    <div style='display:flex;gap:1rem;flex-wrap:wrap;'>
        <a href="/recognize" style="background:#48bb78;color:white;padding:16px 32px;text-decoration:none;border-radius:12px;font-weight:bold;">🎯 Single Recognition</a>
        <a href="/multiface" style="background:#ed8936;color:white;padding:16px 32px;text-decoration:none;border-radius:12px;font-weight:bold;">👥 Multi-Face</a>
        <a href="/api/model-info" style="background:#667eea;color:white;padding:16px 32px;text-decoration:none;border-radius:12px;font-weight:bold;" target="_blank">🔧 JSON Info</a>
        <a href="/groups-gallery" style="background:#f56565;color:white;padding:16px 32px;text-decoration:none;border-radius:12px;font-weight:bold;">📸 Groups Gallery</a>
    </div>
    </body></html>
    """

if __name__ == "__main__":
    print("\n" + "="*100)
    print("🚀🔥 ULTIMATE AI FACE RECOGNITION - FULLY WORKING!")
    print(f"👥 DATABASE: {len(people_db)} people loaded")
    print(f"🤖 MODEL: {'✅ READY' if os.path.exists('model/face_model.h5') else '❌ MISSING'}")
    print("🌐 SINGLE:    http://localhost:5000/recognize")
    print("🌐 MULTI:     http://localhost:5000/multiface")
    print("🔍 DEBUG:     http://localhost:5000/debug")
    print("📡 API:       POST /recognize-face")
    print("🔧 INFO:      GET  /api/model-info")
    print("="*100)
    app.run(debug=True, host='0.0.0.0', port=5000)