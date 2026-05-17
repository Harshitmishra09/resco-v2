import sqlite3
import os
import shutil

DB_PATH = "results.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            roll_number TEXT,
            name TEXT,
            semester TEXT,
            sgpa REAL,
            cgpa REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(roll_number, semester)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            roll_number TEXT,
            semester TEXT,
            subject_name TEXT,
            marks REAL,
            grade TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(roll_number, semester, subject_name)
        )
    ''')
    
    conn.commit()
    conn.close()

def cleanup_old_data():
    """Deletes data older than 2 hours and their associated files."""
    conn = get_db()
    c = conn.cursor()
    
    # Get roll numbers to delete
    c.execute("SELECT DISTINCT roll_number FROM students WHERE created_at < datetime('now', '-2 hours')")
    rolls_to_delete = [row['roll_number'] for row in c.fetchall()]
    
    for roll in rolls_to_delete:
        folder_path = os.path.join("results", roll)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)

    c.execute("DELETE FROM students WHERE created_at < datetime('now', '-2 hours')")
    c.execute("DELETE FROM subjects WHERE created_at < datetime('now', '-2 hours')")
    conn.commit()
    conn.close()

def clear_all_data():
    """Immediately deletes ALL data and files."""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM students")
    c.execute("DELETE FROM subjects")
    
    results_dir = "results"
    if os.path.exists(results_dir):
        for item in os.listdir(results_dir):
            item_path = os.path.join(results_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
                
    conn.commit()
    conn.close()

def save_result(roll_number, name, semester, sgpa, cgpa, subjects=None):
    if subjects is None:
        subjects = []
    conn = get_db()
    c = conn.cursor()
    try:
        # sgpa/cgpa might be "N/A" or empty, convert to float if possible
        try:
            sgpa_val = float(sgpa)
        except:
            sgpa_val = None
        try:
            cgpa_val = float(cgpa)
        except:
            cgpa_val = None

        c.execute('''
            INSERT OR REPLACE INTO students (roll_number, name, semester, sgpa, cgpa)
            VALUES (?, ?, ?, ?, ?)
        ''', (roll_number, name, semester, sgpa_val, cgpa_val))
        
        for subject in subjects:
            c.execute('''
                INSERT OR REPLACE INTO subjects (roll_number, semester, subject_name, marks, grade)
                VALUES (?, ?, ?, ?, ?)
            ''', (roll_number, semester, subject['name'], None, subject['grade']))

        conn.commit()
    except Exception as e:
        print(f"DB Save Error: {e}")
    finally:
        conn.close()

def has_result(roll_number, semester):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM students WHERE roll_number = ? AND semester = ?', (str(roll_number), str(semester)))
    row = c.fetchone()
    conn.close()
    return row is not None

def get_all_students():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT roll_number, name, 
               GROUP_CONCAT(semester) as semesters, 
               MAX(sgpa) as max_sgpa, 
               MAX(cgpa) as max_cgpa
        FROM students
        GROUP BY roll_number, name
    ''')
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def get_student_performance(roll_number):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT semester, sgpa, cgpa FROM students WHERE roll_number = ? ORDER BY semester ASC', (roll_number,))
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def get_semester_analysis(semester):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT roll_number, name, sgpa FROM students WHERE semester = ? ORDER BY sgpa DESC', (semester,))
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def get_semester_overall_analysis():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT semester, AVG(sgpa) as avg_sgpa
        FROM students
        WHERE sgpa IS NOT NULL
        GROUP BY semester
        ORDER BY CAST(semester AS INTEGER) ASC
    ''')
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def get_batch_subject_analysis(semester=None):
    conn = get_db()
    c = conn.cursor()
    
    query = '''
        SELECT subject_name, 
               COUNT(*) as total_students,
               SUM(CASE WHEN grade IN ('F', 'Absent', 'Fail', 'Ab', 'RE') THEN 1 ELSE 0 END) as failed,
               SUM(CASE WHEN grade NOT IN ('F', 'Absent', 'Fail', 'Ab', 'RE') THEN 1 ELSE 0 END) as passed,
               CAST(SUM(CASE WHEN grade IN ('F', 'Absent', 'Fail', 'Ab', 'RE') THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as fail_rate
        FROM subjects
    '''
    params = []
    if semester:
        query += " WHERE semester = ?"
        params.append(str(semester))
        
    query += '''
        GROUP BY subject_name
        ORDER BY fail_rate DESC, total_students DESC
    '''
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def get_grade_distribution(semester=None):
    conn = get_db()
    c = conn.cursor()
    
    query = "SELECT grade, COUNT(*) as count FROM subjects WHERE grade IS NOT NULL AND grade != ''"
    params = []
    if semester:
        query += " AND semester = ?"
        params.append(str(semester))
        
    query += '''
        GROUP BY grade
        ORDER BY 
            CASE grade
                WHEN 'O' THEN 1
                WHEN 'A+' THEN 2
                WHEN 'A' THEN 3
                WHEN 'B+' THEN 4
                WHEN 'B' THEN 5
                WHEN 'C' THEN 6
                WHEN 'P' THEN 7
                WHEN 'F' THEN 8
                ELSE 9
            END
    '''
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def get_toppers(semester=None):
    conn = get_db()
    c = conn.cursor()
    
    query = '''
        SELECT roll_number, name, MAX(sgpa) as max_sgpa, MAX(cgpa) as max_cgpa
        FROM students
        WHERE sgpa IS NOT NULL
    '''
    params = []
    if semester:
        query += " AND semester = ?"
        params.append(str(semester))
        
    query += '''
        GROUP BY roll_number, name
    '''
    if semester:
        query += " ORDER BY max_sgpa DESC "
    else:
        query += " ORDER BY max_cgpa DESC, max_sgpa DESC "
        
    query += " LIMIT 10"
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

if __name__ == "__main__":
    init_db()
