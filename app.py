print("🔥 THIS app.py FILE IS RUNNING 🔥")

from flask import Flask, request, jsonify, send_from_directory , render_template
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask import url_for
import requests
from datetime import datetime
import json
import base64
import google.generativeai as genai
from models import db, History
import traceback
from sqlalchemy import text




load_dotenv()

app = Flask(__name__)

# CORS(app)  # allow frontend JS calls
CORS(app, resources={r"/api/*": {"origins": "*"}})




# ---------------- CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GENERATED_DIR = os.path.join(BASE_DIR, "generated")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

NANOBANANA_KEY = os.environ.get("NANOBANANA_KEY")

# Configure Gemini API
genai.configure(api_key=NANOBANANA_KEY)

os.makedirs(GENERATED_DIR, exist_ok=True)

print(f"[INFO] Flask app started")
print(f"[INFO] Generated dir: {GENERATED_DIR}")
print(f"[INFO] API Key exists: {bool(NANOBANANA_KEY)}")

# ---------------- ROOT ----------------
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "success": True,
        "message": "Server is running"
    })

#============================================================================
# ---------------- DATABASE CONFIG ----------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///imageai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    print(f"Current Database Path: {app.config['SQLALCHEMY_DATABASE_URI']}")
    count = db.session.execute(text("SELECT count(*) FROM history")).scalar()
    print(f"--- SUCCESS: Total records found in ROOT database: {count} ---")
# DATABASE CONFIGURATION
# =============================================================================



# ---------------- SERVE GENERATED ----------------
@app.route("/generated/<filename>")
def serve_generated_image(filename):
    response = send_from_directory(GENERATED_DIR, filename, as_attachment=False)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return send_from_directory(GENERATED_DIR, filename)

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory("uploads", filename)

SYSTEM_PROMPTS = {
    "prompt-to-image": (
        "Act as a professional digital artist. Create a high-quality, detailed image "
        "in {style} style based on the following user description: {prompt}. "
        "Ensure the lighting and textures match the {style} aesthetic perfectly."
    ),
    "image-to-style": (
        "Maintain the original composition, objects, and structure of the uploaded image. "
        "Redraw the entire scene strictly in {style} style. Adjust colors, shading, "
        "and artistic strokes to reflect {style} while keeping the subject recognizable."
    ),
    "specs-try-on": (
        "Photorealistic facial modification. Take the glasses from the 'specs' image "
        "and place them naturally on the face in the 'face' image. Ensure the perspective, "
        "shadows on the skin, and bridge fit are anatomically correct. Prompt: {prompt}"
    ),
    "haircut-preview": (
        "Professional AI hair stylist. Replace the hair in the user's photo with the "
        "haircut style provided in the sample image. Seamlessly blend the hairline "
        "and ensure the hair volume matches the head shape naturally. Prompt: {prompt}"
    ),
    # ✅ NEW: Insta Story Template Prompt
    "insta-story": (
        "Create a professional, high-end Instagram Story template strictly in a "
        "9:16 vertical aspect ratio. Design the layout using {style} aesthetics. "
        "Artistically incorporate the following overlay text: '{prompt}'. "
        "Ensure the composition is mobile-optimized with premium typography."
    )
}
# ---------------- IMAGE GENERATION ----------------
def generate_nano_banana_image(prompt, style):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={NANOBANANA_KEY}"
        headers = {'Content-Type': 'application/json'}

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{prompt} {style}"}
                    ]
                }
            ]
        }

        response = requests.post(url, headers=headers, json=payload)
        print("Gemini status:", response.status_code)
        print("Gemini response:", response.text)

        if response.status_code != 200:
            return None

        data = response.json()

        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])

        for part in parts:
            if "inline_data" in part:
                image_data = part["inline_data"]["data"]

                os.makedirs("generated", exist_ok=True)
                file_path = "generated/generated_image.png"

                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(image_data))

                return "http://127.0.0.1:5000/generated/generated_image.png"

        print("❌ No image returned by Gemini")
        return None

    except Exception as e:
        print("🔥 Backend crash:", str(e))
        return None


# ---------------- PROMPT TO IMAGE ----------------



@app.route("/api/prompt-to-image", methods=["POST"])
def prompt_to_image():
    try:
        # 1. RECEIVE
        data = request.json
        user_prompt = data.get("prompt", "").strip()
        user_style = data.get("imgstyle", "clean")
        user_aspect = data.get("aspect", "1:1")

        if not user_prompt:
            return jsonify({"success": False, "error": "Prompt is required"}), 400

        # 2. ENHANCE (The Format Logic)
        # Injects user data into the "Professional" recipe
        final_prompt = SYSTEM_PROMPTS["prompt-to-image"].format(
            style=user_style, 
            prompt=user_prompt
        )
        # Add aspect ratio instruction to the prompt
        final_prompt += f" Final Aspect Ratio: {user_aspect}."

        # 3. GENERATE (AI Call)
        # Replace this with your actual Gemini function later
        generated_url = "http://127.0.0.1:5000/generated/test.jpg" 

        # 4. RECORD (Save to History Table)
        new_entry = History(
            tool_name="prompt-to-image",
            input_text=f"[Aspect Ratio: {user_aspect}] |  Prompt: {user_prompt}",
            output_text=final_prompt,
            output_image=generated_url
        )
        db.session.add(new_entry)
        db.session.commit()

        print(f"DEBUG: Saved to DB. ID is: {new_entry.id}")
        print(f"DEBUG: DB Path is: {app.config['SQLALCHEMY_DATABASE_URI']}")

        

        # 5. RESPOND
        return jsonify({
            "success": True,
            "image_url": generated_url
            
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    
#----------------------Prompt to image history--------------------------------------
@app.route("/api/get-history", methods=["GET"])
def get_history():
    target_tool = request.args.get("tool")
    if not target_tool:
        return jsonify({"success": False, "error": "tool required"}), 400

    records = (
        History.query
        .filter(History.tool_name == target_tool)
        .order_by(History.created_at.desc())
        .limit(6)
        .all()
    )

    return jsonify({
        "success": True,
        "history": [{
            "id": r.id,
            "input": r.input_text,         # Keeps old tools working
            "image": r.output_image,       # Keeps old tools working
            "raw_input_img": r.input_image, # New: for Specs/Hair logic
            "date": r.created_at.strftime("%Y-%m-%d %H:%M")
        } for r in records]
    })

        
#-------------------------------delete history--------------------------------------------------------------
# 3. DELETE RECORD
@app.route("/api/delete-history/<int:record_id>", methods=["DELETE"])
def delete_history(record_id):
    try:
        record = History.query.get(record_id)
        if record:
            db.session.delete(record)
            db.session.commit()
            return jsonify({"success": True}), 200 # Explicit status code
        return jsonify({"success": False, "error": "Record not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500



# ---------------- PLACEHOLDER APIs ----------------

# def allowed_file(filename):
    # return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
#---------------------------------------------------------------------------- x --------------------------------------------------- x ---------------------------------
# ---------------- IMAGE TO STYLE ----------------
@app.route("/api/image-style", methods=["POST"])
def api_image_style():
    try:
        # 1. Mandatory File Check
        if "image" not in request.files:
            return jsonify({"success": False, "error": "Image is required"}), 400

        image = request.files["image"]
        if image.filename == "":
            return jsonify({"success": False, "error": "No image selected"}), 400

        # 2. Extract Data (Text is optional)
        style = request.form.get("style", "Cinematic")
        instruction = request.form.get("instruction", "").strip()
        aspect = request.form.get("aspect", "1:1")

        # Save the uploaded file safely
        filename = secure_filename(image.filename)
        image.save(os.path.join(UPLOAD_FOLDER, filename))

        # 3. Logic Fix: Return the test.jpg result
        generated_url = "http://127.0.0.1:5000/generated/test.jpg"

        # 4. Record to Database History
        new_entry = History(
            tool_name="image-to-style",
            input_text=f"[Aspect ratio : {aspect}] | Style: {style}  | Prompt : (File: {filename})",
            output_text=instruction if instruction else f"Stylized as {style}",
            output_image=generated_url
        )
        db.session.add(new_entry)
        db.session.commit()

        return jsonify({
            "success": True,
            "output_url": generated_url
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


#----------------------Specs Try On--------------------------------------------------------------------

@app.route("/api/specs-tryon", methods=["POST"])
def specs_tryon():
    try:
        # 1. Validation
        if "face" not in request.files or "specs" not in request.files:
            return jsonify({"success": False, "error": "Missing files"}), 400

        face = request.files["face"]
        specs = request.files["specs"]
        user_instruction = request.form.get("prompt", "")

        # 2. Setup Paths
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        f_fn = f"face_{ts}_{secure_filename(face.filename)}"
        s_fn = f"specs_{ts}_{secure_filename(specs.filename)}"
        
        # Ensure directories exist
        os.makedirs("uploads", exist_ok=True)
        os.makedirs("generated", exist_ok=True)

        face.save(os.path.join("uploads", f_fn))
        specs.save(os.path.join("uploads", s_fn))

        # 3. SYSTEM PROMPT FORMATTING
        # This combines your preset instructions with the user's text
        final_prompt = SYSTEM_PROMPTS["specs-try-on"].format(
            prompt=user_instruction if user_instruction else "natural fit"
        )

        # 3. Pack JSON
        input_history_data = json.dumps({
            "face": f"uploads/{f_fn}",
            "specs": f"uploads/{s_fn}"
        })

        

        # 4. Result Path
        output_url = "http://127.0.0.1:5000/generated/test.jpg"

        # 5. Database Insertion 
        # NOTE: I am using 'input_image' and 'output_image'. 
        # If your table uses 'image', change 'output_image' to 'image' below.
        # 5. Database Insertion 
        new_entry = History(
            tool_name='specs-tryon',
            # USE final_prompt HERE so you save the full AI instructions
            input_text=user_instruction if user_instruction else "natural fit", 
            input_image=input_history_data, 
            output_image=output_url,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_entry)
        db.session.commit()

        return jsonify({"success": True, "output_url": output_url})

    except Exception as e:
        print("--- SERVER CRASH LOG ---")
        traceback.print_exc() # Check your VS Code / CMD terminal for this output!
        db.session.rollback()
        return jsonify({"success": False, "error": "Database or Server Error"}), 500
    

#------------------------------------------Haircut Previeew-----------------------------------------
# =========================================================
# HAIRCUT PREVIEW (DUMMY AI)
# =========================================================
@app.route("/api/haircut-preview", methods=["POST"])
def haircut_preview():
    try:
        # 1. Validation - matching HTML names 'you' and 'sample'
        if "you" not in request.files or "sample" not in request.files:
            return jsonify({"success": False, "error": "Missing files"}), 400

        user_photo = request.files["you"]
        hair_sample = request.files["sample"]
        # prompt = request.form.get("prompt", "")

        user_instruction_prompt = request.form.get("prompt", "").strip()

        # 2. Setup Paths
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        u_fn = f"user_{ts}_{secure_filename(user_photo.filename)}"
        h_fn = f"hair_{ts}_{secure_filename(hair_sample.filename)}"
        
        os.makedirs("uploads", exist_ok=True)
        os.makedirs("generated", exist_ok=True)

        user_photo.save(os.path.join("uploads", u_fn))
        hair_sample.save(os.path.join("uploads", h_fn))

        # ✅ 3. SYSTEM PROMPT MODIFICATION
        # This injects the user's request into the professional hair stylist template
        final_prompt = SYSTEM_PROMPTS["haircut-preview"].format(
        prompt=user_instruction_prompt if user_instruction_prompt  else "seamless blend with natural lighting"
        )

        # 3. Pack JSON for history
        input_history_data = json.dumps({
            "face": f"uploads/{u_fn}",
            "sample": f"uploads/{h_fn}"
        })

        # 4. Result Path (Mocking the AI output)
        output_url = "http://127.0.0.1:5000/generated/test.jpg"

        # 5. Database Insertion
        # ✅ 6. Database Insertion (Modified to use final_prompt)
        new_entry = History(
            tool_name='haircut-preview',
            input_text=user_instruction_prompt if user_instruction_prompt  else "seamless blend with natural lighting", # Store the full engineered prompt here
            input_image=input_history_data,
            output_image=output_url,
            created_at=datetime.utcnow()
        )

        
        db.session.add(new_entry)
        db.session.commit()

        return jsonify({"success": True, "output_url": output_url})

    except Exception as e:
        print("--- HAIRCUT ERROR ---")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    
#--------------------------------------------Insta-story-template--------------------------------
GENERATED_FOLDER = os.path.join(os.getcwd(), "generated")

@app.route("/api/insta-story", methods=["POST", "OPTIONS"])
def api_insta_story():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    try:
        # 1. Safely get the data from your JS fetch
        data = request.get_json() or {}
        user_text = data.get("overlay_text", "New Story")

        # 2. Get prompt template safely
        template = SYSTEM_PROMPTS.get("insta-story", "Instagram Story: [TEXT]")

        # 3. USE REPLACE INSTEAD OF FORMAT (This prevents 500 crashes)
        # This replaces the placeholder [TEXT] or {prompt} manually
        if "{prompt}" in template:
            final_prompt = template.replace("{prompt}", user_text)
        else:
            final_prompt = f"{template} {user_text}"

        output_url = "http://127.0.0.1:5000/generated/test.jpg"

        # 4. Database logic (wrapped so it never crashes the main response)
        try:
            new_entry = History(
                tool_name='insta-story',
                input_text=f"Prompt : {user_text}",
                input_image="Text Input",
                output_image=output_url,
                created_at=datetime.utcnow()
            )
            db.session.add(new_entry)
            db.session.commit()
        except Exception as db_e:
            db.session.rollback()
            print(f"DB Error: {db_e}")

        # 5. Send back exactly what JS is waiting for
        return jsonify({
            "success": True,
            "output_url": output_url
        })

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
#-------------------------------------Social media post generator------------------------------------------
TEST_IMAGE = "test.jpg"  # Backend placeholder image

@app.route("/api/social/generate", methods=["POST", "OPTIONS"])
def generate_social_post():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200
    
    try:
        # FIX: Define platform and prompt from the request
        if request.is_json:
            data = request.get_json()
            prompt = data.get("prompt", "").strip()
            platform = data.get("platform", "Instagram") # Added this line
        else:
            prompt = request.form.get("prompt", "").strip()
            platform = request.form.get("platform", "Instagram") # Added this line

        # Now platform is defined, so template.format won't crash
        template = SYSTEM_PROMPTS.get("social-post", "A {platform} post: {prompt}")
        final_prompt = template.format(platform=platform, prompt=prompt if prompt else "Aesthetic visual")

        output_url = "http://127.0.0.1:5000/generated/test.jpg"

        # Database save logic
        try:
            new_entry = History(
                tool_name='social/generate', 
                input_text=f"Platform: {platform} | Prompt: {prompt if prompt else 'Aesthetic visual'}",
                input_image="Text Input",
                output_image=output_url,
                created_at=datetime.utcnow()
            )
            db.session.add(new_entry)
            db.session.commit()
        except Exception as db_e:
            db.session.rollback()
            print(f"DB Error: {db_e}")

        return jsonify({
            "success": True,
            "image_url": output_url,
            "caption": "Your AI generated caption here...",
            "hashtags": "#AI #Generated",
            "tips": "Post this at 10 AM."
        })
    except Exception as e:
        # This catch-all will now catch errors properly without crashing the server
        return jsonify({"success": False, "error": str(e)}), 500
#--------------------------------------Story Animation-----------------------------------------
# Tool-specific generated folders
TOOL_FOLDERS = {
    "story_image": os.path.join(BASE_DIR, "generated_story_image"),
    "post_generator": os.path.join(BASE_DIR, "generated_post")
}

# Ensure folders exist
for folder in TOOL_FOLDERS.values():
    os.makedirs(folder, exist_ok=True)


# ----------- Story Image Generator API -----------
# ---------- STORY IMAGE API ----------
@app.route("/api/story-image", methods=["POST"])
def story_image_api():

    scenes = []
    for i in range(1, 5):
        scenes.append({
            "scene": i,
            "image_url": f"/api/story-image/file/test.jpg"
        })

    return jsonify({
        "status": "success",
        "scenes": scenes
    })

@app.route("/generated/<filename>")
def serve_generated(filename):
    return send_from_directory(GENERATED_FOLDER, filename)


# ---------- SERVE GENERATED IMAGE ----------
# @app.route("/api/story-image/file/<filename>")
# def serve_story_image(filename):
    # return send_from_directory(GENERATED_DIR, filename)


# ========== PROMPT ENHANCER ==========
@app.route("/api/enhance-prompt", methods=["POST"])
def enhance_prompt():
    """Enhance a simple prompt into a detailed, image-generation-ready prompt"""
    try:
        data = request.json
        simple_prompt = data.get("prompt", "").strip()
        
        if not simple_prompt:
            return jsonify({"success": False, "error": "Prompt cannot be empty"}), 400
        
        # Use Gemini to enhance the prompt
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        enhancement_instruction = f"""You are an expert prompt engineer for AI image generation models.
        
Take this simple prompt and enhance it into a detailed, vivid, and comprehensive prompt suitable for high-quality image generation.

Add details about:
- Visual style and aesthetic
- Lighting and atmosphere
- Color palette
- Composition and framing
- Quality indicators (masterpiece, highly detailed, professional, etc.)
- Any relevant artistic styles or references

Simple prompt: {simple_prompt}

Respond with ONLY the enhanced prompt, nothing else. Make it detailed but concise (1-2 sentences max)."""
        
        response = model.generate_content(enhancement_instruction)
        enhanced_prompt = response.text.strip()

        # ✅ SAVE TO HISTORY TABLE
        history = History(
            tool_name="prompt-enhancer",
            input_text=simple_prompt,
            input_image=None,
            output_text=enhanced_prompt,
            output_image=None
        )

        db.session.add(history)
        db.session.commit()

        
        return jsonify({
            "success": True,
            "original_prompt": simple_prompt,
            "enhanced_prompt": enhanced_prompt
        }), 200
        
    except Exception as e:
        print(f"[ERROR] enhance_prompt: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
# ========== PROMPT ENHANCER HISTORY ==========
@app.route("/api/prompt-enhancer/history", methods=["GET"])
def prompt_enhancer_history():
    history_items = (
        History.query
        .filter(History.tool_name == "prompt-enhancer")
        .order_by(History.created_at.desc())
        .limit(8)
        .all()
    )

    return jsonify({
        "success": True,
        "history": [
            {
                "id": h.id,
                "input": h.input_text,
                "output": h.output_text,
                "time": h.created_at.strftime("%d %b %Y · %I:%M %p")
            }
            for h in history_items
        ]
    })



# ---------------- RUN ----------------
print("ROUTES REGISTERED:")
for rule in app.url_map.iter_rules():
    print(rule)


if __name__ == "__main__":
  
    app.run(debug=True)


