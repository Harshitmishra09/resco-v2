# ReSCo: Result Scraper and Compiler

**ReSCo** is a powerful Python web application designed to batch-download, compile, and visualize student results from the J.C. Bose University of Science and Technology, YMCA, Faridabad portal. It features a beautiful, responsive dashboard, automated CAPTCHA solving, and deep academic analytics.

---

## 🌟 Key Features

### 🚀 Core Engine
- **Batch Processing:** Fetch results for multiple roll numbers and semesters concurrently using a multithreaded backend.
- **Automated CAPTCHA Solving:** Uses Pytesseract OCR to automatically bypass image CAPTCHAs.
- **Smart Scraping:** 
  - **Skip Logic:** Checks the SQLite database before scraping to skip already downloaded results, saving compute power.
  - **Auto-Retry:** Automatically requeues and retries failed scrape attempts within a batch to handle network or CAPTCHA errors.

### 📊 Advanced Interactive Analytics
- **Comprehensive Dashboard:** View batch statistics like highest CGPA, average SGPA, and a detailed student leaderboard.
- **Interactive Filtering:** Click on any semester in the "Semester Overview" graph to dynamically filter the Grade Distribution, Subject Difficulty, and Top 10 Performers charts for that specific semester.
- **Subject Difficulty Analysis:** Visualizes the fail rate and pass count for every subject to identify curriculum bottlenecks.
- **Performance Trends:** Search for a specific student to see their SGPA/CGPA trajectory over time.

### 📁 Output & Export
- **Organised Storage:** Saves full-page screenshots (`.png`) of result cards grouped by roll number.
- **Data Export:** Download the entire compiled dataset as a clean Excel spreadsheet (`.xlsx`) or download all generated screenshots as a single `.zip` file.

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask, SQLite3
- **Scraping:** Requests, BeautifulSoup4, Selenium (Headless Chrome)
- **OCR/Image Processing:** Pytesseract, Pillow (PIL)
- **Frontend:** HTML5, Vanilla CSS (Glassmorphism design), Vanilla JS, Chart.js

---

## ⚙️ Setup and Usage

### Prerequisites

- **Python 3.x**
- **Google Tesseract OCR** installed and accessible in your system's PATH.
  - Windows Installer: [Tesseract v5.5.0](https://github.com/Harshitmishra09/resco/blob/main/tesseract-ocr-w64-setup-5.5.0.20241111.exe)
  - Wiki: [Tesseract GitHub Wiki](https://github.com/UB-Mannheim/tesseract/wiki)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/Harshitmishra09/resco.git
cd resco
```

2. **Set up virtual environment:**
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the Application:**
```bash
python app.py
```
*The web dashboard will be available at `http://localhost:5000`.*
