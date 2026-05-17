import requests
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract
import io
import re
import os
import time
import tempfile
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from concurrent.futures import ThreadPoolExecutor, as_completed
import db

# Support both local Windows dev and Linux Docker container
TESSERACT_CMD = os.environ.get('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH', None)  # None = use ChromeDriverManager
IS_CONTAINER = os.environ.get('CHROMEDRIVER_PATH') is not None

BASE_URL = "https://jcboseustymca.co.in/Forms/Student/ResultStudents.aspx"
RESULT_URL = "https://jcboseustymca.co.in/Forms/Student/PrintReportCardNew.aspx"
CAPTCHA_URL = "https://jcboseustymca.co.in/Handler/GenerateCaptchaImage.ashx"
OUTPUT_DIR = "results"
MAX_WORKERS = 4

job_status = {
    "is_running": False,
    "total": 0,
    "completed": 0,
    "results": [],
    "message": ""
}

def clean_captcha(text):
    text = text.strip().upper()
    text = re.sub(r'[^A-Z0-9]', '', text)
    text = text.replace("0", "O").replace("1", "I").replace("5", "S").replace("8", "B")
    return text

def solve_captcha(img_bytes):
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("L")
        img = img.point(lambda x: 0 if x < 140 else 255)
        text = pytesseract.image_to_string(
            img, config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )
        return clean_captcha(text)
    except Exception as e:
        return ""

def get_chrome_driver():
    """Create a Chrome WebDriver, supporting both local dev and Docker container."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1200,800")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--log-level=3")
    # Required flags when running inside Docker/container
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")

    if IS_CONTAINER:
        # Use system chromium installed in the Docker image
        options.binary_location = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
        service = ChromeService(executable_path=CHROMEDRIVER_PATH)
    else:
        # Local dev — use ChromeDriverManager to auto-download
        from webdriver_manager.chrome import ChromeDriverManager
        if os.name != 'nt':  # non-Windows local
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
        service = ChromeService(ChromeDriverManager().install())

    return webdriver.Chrome(service=service, options=options)

def save_html_as_image(html_content, output_path):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as fp:
            fp.write(html_content)
            temp_path = "file://" + os.path.abspath(fp.name).replace('\\', '/')

        driver = get_chrome_driver()
        driver.get(temp_path)
        time.sleep(2)

        driver.execute_script("document.body.style.zoom='70%'")
        time.sleep(2)

        js_get_height = "return Math.max( document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight );"
        total_height = driver.execute_script(js_get_height)

        driver.set_window_size(1200, total_height + 50)
        time.sleep(2)

        driver.save_screenshot(output_path)
        driver.quit()
        os.unlink(fp.name)
        return True
    except Exception as e:
        print(f"Screenshot error: {e}")
        return False

def parse_result_details(soup):
    try:
        name_span = soup.find('span', {'id': 'lblname'})
        if not name_span or not name_span.text.strip():
            return None

        name = name_span.text.strip()
        sgpa_span = soup.find('span', {'id': 'lblResult'})
        sgpa = sgpa_span.text.strip() if sgpa_span else "N/A"
        cgpa_span = soup.find('span', {'id': 'lblCgpaResult'})
        cgpa = cgpa_span.text.strip() if cgpa_span and cgpa_span.text.strip() else "N/A"
        
        subjects = []
        for table in soup.find_all('table'):
            first_row = table.find('tr')
            if first_row and 'Course Code with Course Title' in first_row.text:
                for tr in table.find_all('tr', recursive=False)[1:]:
                    tds = tr.find_all('td', recursive=False)
                    if len(tds) >= 6:
                        course_info = tds[1].text.strip().split('\n')
                        course_code = course_info[0].strip()
                        course_name = course_info[-1].strip()
                        grade = tds[-1].text.strip()
                        subjects.append({"code": course_code, "name": course_name, "grade": grade})
                break
                
        return {"name": name, "sgpa": sgpa, "cgpa": cgpa, "subjects": subjects}

    except AttributeError:
        return None

def fetch_result(session, roll_number, semester):
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            response = session.get(BASE_URL, timeout=15)
            soup = BeautifulSoup(response.text, "html.parser")

            viewstate = soup.find("input", {"id": "__VIEWSTATE"})["value"]
            viewstategen = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})["value"]
            eventvalidation = soup.find("input", {"id": "__EVENTVALIDATION"})["value"]
            captcha_img_bytes = session.get(CAPTCHA_URL, timeout=15).content
            captcha_text = solve_captcha(captcha_img_bytes)

            if len(captcha_text) < 5: continue

            payload = {
                "__VIEWSTATE": viewstate, "__VIEWSTATEGENERATOR": viewstategen,
                "__EVENTVALIDATION": eventvalidation, "txtRollNo": roll_number,
                "ddlSem": str(semester).zfill(2), "txtCaptcha": captcha_text,
                "btnResult": "View Result",
            }

            session.post(BASE_URL, data=payload, timeout=20)
            report_page = session.get(RESULT_URL, timeout=20)
            soup_result = BeautifulSoup(report_page.text, "html.parser")
            
            parsed_data = parse_result_details(soup_result)

            if parsed_data:
                return {"status": "success", "html": report_page.text, "details": parsed_data}
            else:
                time.sleep(2)
        except Exception as e:
            time.sleep(3)
            
    return {"status": "failed", "html": "", "details": {"name": "N/A", "sgpa": "N/A", "cgpa": "N/A"}}

def process_roll_number(roll_number, semester):
    try:
        time.sleep(random.uniform(0.5, 2.0))
        with requests.Session() as session:
            result = fetch_result(session, roll_number, semester)
        
        result['roll_number'] = roll_number

        if result['status'] == 'success':
            roll_dir = os.path.join(OUTPUT_DIR, roll_number)
            os.makedirs(roll_dir, exist_ok=True)
            image_path = os.path.join(roll_dir, f"result_sem_{semester}.png")
            save_html_as_image(result["html"], image_path)
            
            # Save to DB
            db.save_result(roll_number, result['details']['name'], str(semester), result['details']['sgpa'], result['details']['cgpa'], result['details'].get('subjects', []))

        return result
    except Exception as e:
        print(f"Error processing {roll_number}: {e}")
        return {"status": "failed", "roll_number": roll_number, "details": {"name": "N/A", "sgpa": "N/A", "cgpa": "N/A"}}

def run_batch(roll_numbers, semesters):
    global job_status
    job_status["is_running"] = True
    job_status["total"] = len(roll_numbers) * len(semesters)
    job_status["completed"] = 0
    job_status["results"] = []
    job_status["message"] = "Processing..."
    
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        db.init_db()

        failed_tasks = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures_map = {}
            for roll in roll_numbers:
                for sem in semesters:
                    if db.has_result(roll, sem):
                        job_status["completed"] += 1
                        job_status["results"].append({"status": "skipped", "roll_number": roll, "semester": sem})
                    else:
                        future = executor.submit(process_roll_number, roll, sem)
                        futures_map[future] = (roll, sem)
                    
            for future in as_completed(futures_map):
                try:
                    res = future.result()
                    if res:
                        job_status["results"].append(res)
                        if res['status'] == 'failed':
                            failed_tasks.append(futures_map[future])
                except Exception as e:
                    failed_tasks.append(futures_map[future])
                finally:
                    job_status["completed"] += 1
                    
        # Retry logic for failed tasks
        if failed_tasks:
            job_status["message"] = "Retrying failed tasks..."
            job_status["completed"] -= len(failed_tasks)
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures_retry = []
                for roll, sem in failed_tasks:
                    futures_retry.append(executor.submit(process_roll_number, roll, sem))
                
                for future in as_completed(futures_retry):
                    try:
                        res = future.result()
                        if res and res['status'] == 'success':
                            job_status["results"].append(res)
                    except Exception as e:
                        pass
                    finally:
                        job_status["completed"] += 1
                        
    finally:
        job_status["is_running"] = False
        job_status["message"] = "Completed"
