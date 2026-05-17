from flask import Flask, request, jsonify, render_template
import threading
import scraper_engine
import db
import os
import pandas as pd
import io
import shutil
import zipfile
from flask import send_file

app = Flask(__name__)

# Ensure DB is initialized
db.init_db()

@app.route('/')
def index():
    db.cleanup_old_data()
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_job():
    data = request.json
    roll_numbers_str = data.get('roll_numbers', '')
    semesters = data.get('semesters', ['1'])
    
    # Process roll numbers: split by comma, newline, or space
    import re
    roll_numbers = [r.strip() for r in re.split(r'[,\n ]+', roll_numbers_str) if r.strip()]
    
    if not roll_numbers:
        return jsonify({"error": "No roll numbers provided"}), 400
        
    if scraper_engine.job_status['is_running']:
        return jsonify({"error": "Job already running"}), 400
    
    # Start in background
    threading.Thread(target=scraper_engine.run_batch, args=(roll_numbers, semesters)).start()
    return jsonify({"message": "Job started successfully!", "total": len(roll_numbers) * len(semesters)})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(scraper_engine.job_status)

@app.route('/api/students', methods=['GET'])
def get_all_students():
    return jsonify(db.get_all_students())

@app.route('/api/analysis/student/<roll_number>', methods=['GET'])
def get_student_analysis(roll_number):
    return jsonify(db.get_student_performance(roll_number))

@app.route('/api/analysis/semester/<semester>', methods=['GET'])
def get_semester_analysis(semester):
    return jsonify(db.get_semester_analysis(semester))

@app.route('/api/analysis/semester/overall', methods=['GET'])
def get_semester_overall_analysis():
    return jsonify(db.get_semester_overall_analysis())

@app.route('/api/analysis/subjects', methods=['GET'])
def get_batch_subject_analysis():
    semester = request.args.get('semester')
    return jsonify(db.get_batch_subject_analysis(semester))

@app.route('/api/analysis/grades', methods=['GET'])
def get_grade_distribution():
    semester = request.args.get('semester')
    return jsonify(db.get_grade_distribution(semester))

@app.route('/api/analysis/toppers', methods=['GET'])
def get_toppers():
    semester = request.args.get('semester')
    return jsonify(db.get_toppers(semester))

@app.route('/api/download/excel', methods=['GET'])
def download_excel():
    students = db.get_all_students()
    if not students:
        return jsonify({"error": "No data available"}), 404
        
    df = pd.DataFrame(students)
    # Reorder columns for better readability
    cols = ['roll_number', 'name', 'semesters', 'max_sgpa', 'max_cgpa']
    df = df[cols]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Results Summary')
    
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='resco_results_summary.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/api/download/zip', methods=['GET'])
def download_zip():
    results_dir = 'results'
    if not os.path.exists(results_dir) or not os.listdir(results_dir):
        return jsonify({"error": "No folders found"}), 404
        
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(results_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Create arcname relative to the results directory
                arcname = os.path.relpath(file_path, results_dir)
                zf.write(file_path, arcname)
    
    memory_file.seek(0)
    return send_file(memory_file, as_attachment=True, download_name='resco_all_results.zip', mimetype='application/zip')

@app.route('/api/clear', methods=['POST'])
def clear_data():
    db.clear_all_data()
    return jsonify({"message": "All data wiped successfully!"})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port, use_reloader=False)
