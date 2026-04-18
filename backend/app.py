from pathlib import Path
import shutil
import uuid
import subprocess
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULTS_DIR = BASE_DIR / "results"

UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)


@app.route("/results/<path:filename>")
def serve_results(filename):
    return send_from_directory(RESULTS_DIR, filename)


@app.route("/api/denoise", methods=["POST"])
def denoise():
    if "image" not in request.files:
        return "No image uploaded", 400

    image_file = request.files["image"]
    sigma = request.form.get("sigma", "50")

    run_id = str(uuid.uuid4())[:8]
    input_path = UPLOAD_DIR / f"{run_id}_{image_file.filename}"
    output_dir = RESULTS_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    image_file.save(input_path)

    cmd = [
        "python",
        str(BASE_DIR / "swk_svd_repro.py"),
        "--image",
        str(input_path),
        "--sigma",
        str(sigma),
    ]

    env = None

    try:
        subprocess.run(cmd, check=True, cwd=BASE_DIR, env=env)

        # Move generated files from default outputs/ into this run folder
        default_out = BASE_DIR / "outputs"
        files_to_move = [
            "clean.png",
            "noisy.png",
            "denoised.png",
            "ksvd_only_denoised.png",
            "ksvd_only_dictionary.png",
            "dictionary_A.png",
            "dictionary_H.png",
            "dictionary_V.png",
            "dictionary_D.png",
            "metrics.txt",
        ]

        for name in files_to_move:
            src = default_out / name
            if src.exists():
                shutil.copy(src, output_dir / name)

        metrics_text = ""
        metrics_path = output_dir / "metrics.txt"
        if metrics_path.exists():
            metrics_text = metrics_path.read_text(encoding="utf-8")

        def url(name):
            return f"http://localhost:5000/results/{run_id}/{name}"

        noisy_psnr = None
        denoised_psnr = None
        ksvd_only_psnr = None

        for line in metrics_text.splitlines():
            if ":" in line:
                parts = line.split(":", 1)
                key = parts[0].strip()
                value_part = parts[1].strip()
                if "dB" in value_part:
                    value = float(value_part.split()[0])
                    if key == "Noisy PSNR":
                        noisy_psnr = value
                    elif key == "Denoised PSNR":
                        denoised_psnr = value
                    elif key == "K-SVD Only PSNR":
                        ksvd_only_psnr = value

        return jsonify({
            "noisy_psnr": noisy_psnr,
            "denoised_psnr": denoised_psnr,
            "ksvd_only_psnr": ksvd_only_psnr,
            "clean_image": url("clean.png"),
            "noisy_image": url("noisy.png"),
            "denoised_image": url("denoised.png"),
            "ksvd_only_image": url("ksvd_only_denoised.png"),
            "ksvd_only_dictionary": url("ksvd_only_dictionary.png"),
            "dictionaries": {
                "A": url("dictionary_A.png"),
                "H": url("dictionary_H.png"),
                "V": url("dictionary_V.png"),
                "D": url("dictionary_D.png"),
            },
            "metrics_text": metrics_text
        })

    except subprocess.CalledProcessError as e:
        return f"Python script failed: {e}", 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)