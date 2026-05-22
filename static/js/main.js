document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation Tabs ---
    const navLinks = document.querySelectorAll('.nav-links a');
    const tabContents = document.querySelectorAll('.tab-content');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('data-tab');
            
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            tabContents.forEach(content => {
                content.classList.remove('active');
                if(content.id === targetId) {
                    content.classList.add('active');
                }
            });

            if (targetId === 'dashboard') {
                fetchDashboardData();
            }
        });
    });

    // --- Chart Configurations ---
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Inter', sans-serif";

    let studentChartInstance = null;
    let semesterChartInstance = null;

    // --- Scraper Form Submission ---
    const scraperForm = document.getElementById('scraper-form');
    let pollingInterval = null;

    scraperForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const rollNumbers = document.getElementById('roll-numbers').value;
        const semesterCheckboxes = document.querySelectorAll('input[name="semester"]:checked');
        const semesters = Array.from(semesterCheckboxes).map(cb => cb.value);

        if (semesters.length === 0) {
            alert("Please select at least one semester.");
            return;
        }

        const btn = document.getElementById('btn-start');
        const originalText = btn.textContent;
        btn.textContent = "Processing...";
        btn.disabled = true;

        try {
            const res = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ roll_numbers: rollNumbers, semesters })
            });

            const data = await res.json();
            if (res.ok) {
                document.getElementById('progress-container').style.display = 'block';
                document.getElementById('job-total').textContent = data.total;
                startPolling();
            } else if (data.error === "Job already running") {
                document.getElementById('progress-container').style.display = 'block';
                startPolling();
            } else {
                alert("Error: " + data.error);
            }
        } catch (error) {
            console.error("Error starting job", error);
            alert("Error starting job: " + error.message);
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    });

    function startPolling() {
        if (pollingInterval) clearInterval(pollingInterval);
        pollingInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                const status = await res.json();

                document.getElementById('job-status-text').textContent = status.message;
                document.getElementById('job-completed').textContent = status.completed;
                document.getElementById('job-total').textContent = status.total;

                const percent = status.total > 0 ? (status.completed / status.total) * 100 : 0;
                document.getElementById('job-progress-fill').style.width = `${percent}%`;

                if (!status.is_running && status.total > 0) {
                    clearInterval(pollingInterval);
                    document.getElementById('job-status-text').textContent = "Completed Successfully!";
                    setTimeout(() => fetchDashboardData(), 1000);
                }
            } catch (err) {
                console.error("Polling error", err);
            }
        }, 2000);
    }

    // --- Dashboard Data ---
    async function fetchDashboardData() {
        try {
            const res = await fetch('/api/students');
            const students = await res.json();
            
            // Populate Table
            const tbody = document.getElementById('results-body');
            tbody.innerHTML = '';
            
            let maxCgpa = 0;
            let sem1SgpaSum = 0;
            let sem1Count = 0;

            students.forEach(student => {
                const tr = document.createElement('tr');
                // The new endpoint returns 'semesters' as a comma separated string
                const semText = student.semesters ? student.semesters.split(',').sort().join(', ') : 'N/A';
                
                tr.innerHTML = `
                    <td><strong>${student.roll_number}</strong></td>
                    <td>${student.name}</td>
                    <td>Sem ${semText}</td>
                    <td style="color: var(--accent); font-weight: 600;">${student.max_sgpa || student.sgpa || 'N/A'}</td>
                    <td>${student.max_cgpa || student.cgpa || 'N/A'}</td>
                `;
                tbody.appendChild(tr);

                if (student.max_cgpa && student.max_cgpa > maxCgpa) maxCgpa = student.max_cgpa;
                if (student.semesters && student.semesters.includes('1') && student.max_sgpa) {
                    sem1SgpaSum += student.max_sgpa;
                    sem1Count++;
                }
            });

            // Update Stats
            document.getElementById('stat-total').textContent = new Set(students.map(s => s.roll_number)).size;
            document.getElementById('stat-highest').textContent = maxCgpa.toFixed(2);
            document.getElementById('stat-avg').textContent = sem1Count > 0 ? (sem1SgpaSum / sem1Count).toFixed(2) : '0.0';

        } catch (error) {
            console.error("Error fetching students", error);
        }
    }

    // --- Analytics ---
    const btnAnalyze = document.getElementById('btn-analyze');
    btnAnalyze.addEventListener('click', async () => {
        const roll = document.getElementById('search-roll').value.trim();
        if(!roll) return;

        try {
            const res = await fetch(`/api/analysis/student/${roll}`);
            const data = await res.json();

            if (data.length === 0) {
                alert("No data found for this roll number.");
                return;
            }

            renderStudentChart(data);
            fetchStudentReappears(roll);
        } catch(error) {
            console.error("Analytics error", error);
        }
    });

    async function fetchStudentReappears(roll) {
        try {
            const res = await fetch(`/api/analysis/student/${roll}/reappears`);
            const data = await res.json();
            
            const reappearCard = document.getElementById('reappear-card');
            const tbody = document.getElementById('reappear-body');
            tbody.innerHTML = '';
            
            if (data.length === 0) {
                reappearCard.style.display = 'none';
            } else {
                reappearCard.style.display = 'block';
                data.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>Sem ${item.semester}</td>
                        <td>${item.subject_name}</td>
                        <td style="color: #ef4444; font-weight: 600;">${item.grade}</td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        } catch (error) {
            console.error("Error fetching reappear details", error);
        }
    }

    function renderStudentChart(data) {
        const ctx = document.getElementById('studentChart').getContext('2d');
        const labels = data.map(d => `Sem ${d.semester}`);
        const sgpaData = data.map(d => d.sgpa);
        const cgpaData = data.map(d => d.cgpa);

        if (studentChartInstance) {
            studentChartInstance.destroy();
        }

        studentChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'SGPA',
                        data: sgpaData,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'CGPA',
                        data: cgpaData,
                        borderColor: '#10b981',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' }
                },
                scales: {
                    y: { beginAtZero: false, min: 0, max: 10 }
                }
            }
        });
    }

    let batchSubjectChartInstance = null;
    let gradeChartInstance = null;

    async function fetchSemesterOverview() {
        try {
            const semRes = await fetch('/api/analysis/semester/overall');
            const semData = await semRes.json();
            
            if (semData.length > 0) {
                const ctxSem = document.getElementById('semesterChart').getContext('2d');
                if (semesterChartInstance) semesterChartInstance.destroy();
                
                semesterChartInstance = new Chart(ctxSem, {
                    type: 'bar',
                    data: {
                        labels: semData.map(d => `Sem ${d.semester}`),
                        datasets: [{
                            label: 'Average SGPA',
                            data: semData.map(d => d.avg_sgpa),
                            backgroundColor: 'rgba(16, 185, 129, 0.2)',
                            borderColor: '#10b981',
                            borderWidth: 2,
                            borderRadius: 4
                        }]
                    },
                    options: { 
                        responsive: true, 
                        scales: { y: { beginAtZero: true, max: 10 } },
                        onClick: (e, elements) => {
                            if (elements.length > 0) {
                                const index = elements[0].index;
                                const semText = semesterChartInstance.data.labels[index];
                                const semNum = semText.replace('Sem ', '');
                                document.getElementById('current-filter-text').textContent = `Showing: Sem ${semNum}`;
                                document.getElementById('btn-clear-filter').style.display = 'block';
                                updateBatchAnalytics(semNum);
                            }
                        }
                    }
                });
            }
        } catch(e) {
            console.error("Error fetching semester overview", e);
        }
    }

    async function updateBatchAnalytics(semester = null) {
        try {
            let queryStr = semester ? `?semester=${semester}` : '';

            // Fetch Grade Distribution
            const gradeRes = await fetch(`/api/analysis/grades${queryStr}`);
            const gradeData = await gradeRes.json();
            const ctxGrade = document.getElementById('gradeChart').getContext('2d');
            if (gradeChartInstance) gradeChartInstance.destroy();
            if (gradeData.length > 0) {
                gradeChartInstance = new Chart(ctxGrade, {
                    type: 'doughnut',
                    data: {
                        labels: gradeData.map(d => d.grade),
                        datasets: [{
                            data: gradeData.map(d => d.count),
                            backgroundColor: [
                                '#10b981', '#34d399', '#6ee7b7', '#a7f3d0',
                                '#fbbf24', '#f59e0b', '#ef4444', '#b91c1c'
                            ]
                        }]
                    },
                    options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
                });
            }

            // Fetch Toppers
            const topperRes = await fetch(`/api/analysis/toppers${queryStr}`);
            const topperData = await topperRes.json();
            const topperBody = document.getElementById('toppers-body');
            topperBody.innerHTML = '';
            topperData.forEach((t, i) => {
                const tr = document.createElement('tr');
                const score = semester ? t.max_sgpa : (t.max_cgpa || 'N/A');
                tr.innerHTML = `
                    <td><span class="rank-badge">${i+1}</span></td>
                    <td>${t.roll_number}</td>
                    <td>${t.name}</td>
                    <td style="color: var(--accent); font-weight: 600;">${score}</td>
                `;
                topperBody.appendChild(tr);
            });

            // Fetch Batch Subject Analysis (Difficulty)
            const subjRes = await fetch(`/api/analysis/subjects${queryStr}`);
            const subjData = await subjRes.json();
            const ctxSubj = document.getElementById('subjectChart').getContext('2d');
            if (batchSubjectChartInstance) batchSubjectChartInstance.destroy();
            
            if (subjData.length > 0) {
                batchSubjectChartInstance = new Chart(ctxSubj, {
                    type: 'bar',
                    data: {
                        labels: subjData.map(d => d.subject_name.length > 30 ? d.subject_name.substring(0, 30) + '...' : d.subject_name),
                        datasets: [
                            {
                                label: 'Fail Rate %',
                                data: subjData.map(d => d.fail_rate.toFixed(1)),
                                backgroundColor: 'rgba(239, 68, 68, 0.4)',
                                borderColor: '#ef4444',
                                borderWidth: 2
                            },
                            {
                                label: 'Students Passed',
                                data: subjData.map(d => d.passed),
                                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                borderColor: 'rgba(16, 185, 129, 0.4)',
                                borderWidth: 1,
                                type: 'line',
                                yAxisID: 'y1'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        scales: { 
                            y: { title: { display: true, text: 'Fail Rate (%)' }, beginAtZero: true, max: 100 },
                            y1: { title: { display: true, text: 'Total Passed' }, position: 'right', beginAtZero: true, grid: { drawOnChartArea: false } }
                        }
                    }
                });
            }
        } catch(e) {
            console.error("Error updating batch analytics", e);
        }
    }

    document.getElementById('btn-clear-filter').addEventListener('click', () => {
        document.getElementById('current-filter-text').textContent = 'Showing: All Semesters';
        document.getElementById('btn-clear-filter').style.display = 'none';
        updateBatchAnalytics(null);
    });

    // Initialize Dashboard
    fetchDashboardData();
    fetchSemesterOverview();
    updateBatchAnalytics();
    
    // Check if a job is already running
    fetch('/api/status').then(res => res.json()).then(status => {
        if (status.is_running) {
            document.getElementById('progress-container').style.display = 'block';
            startPolling();
        }
    }).catch(console.error);

    // Wipe Data
    const btnClear = document.getElementById('btn-clear');
    if (btnClear) {
        btnClear.addEventListener('click', async () => {
            if (!confirm("Are you sure you want to permanently delete ALL scraped data and result folders? This cannot be undone.")) {
                return;
            }
            
            try {
                const res = await fetch('/api/clear', { method: 'POST' });
                if (res.ok) {
                    alert("All data wiped successfully!");
                    window.location.reload();
                }
            } catch (err) {
                console.error("Error wiping data", err);
            }
        });
    }
});
