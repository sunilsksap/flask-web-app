AstroVoltCore
==========================

Files
- backend\AstroVoltCore_server.py : local Python server + API
- frontend\html\login.html : login screen
- frontend\html\home.html : module dashboard
- frontend\html\index.html : quotation manager
- frontend\html\employees.html : employee manager
- frontend\html\attendance.html : attendance manager
- frontend\html\salary.html : salary manager
- frontend\css\app.css : styling
- frontend\js\ : JavaScript modules
- assets\logo.png : company logo
- database\quotations.db : SQLite database file for quotations + login
- database\hr.db : SQLite database file for employees, attendance, salary, holidays
- exports\generated_pdfs\ : saved PDF files
- scripts\start-AstroVoltCore_server.bat : easy launcher

How to run
1. Double-click scripts\start-AstroVoltCore_server.bat
2. Your browser will open http://127.0.0.1:8765
3. Create the admin username/password on first launch
4. The database file quotations.db will be used from the database folder

How it works
- New quotations start as DRAFT
- Save Draft writes them into database\quotations.db
- Finalize & Lock marks them FINAL and prevents later editing
- If changes are needed later, use Create Revision
- Revisions create a new draft like AVG-2026-001-R1 while the older FINAL quotation stays unchanged
- Save PDF creates files in exports\generated_pdfs\
- Employee Manager stores staff master data with employee codes like AVG00001
- Attendance Manager captures daily attendance with overtime hours
- Salary Manager generates monthly salary runs based on attendance and deductions

Technology
- Frontend: HTML + CSS + JavaScript
- Backend: Python
- Database: SQLite
- Server: Python ThreadingHTTPServer
- PDF export: local Google Chrome headless engine

Security
- Set the admin username/password on first launch (stored as a salted hash in SQLite)
- Set an admin PIN from the app before finalising quotations
- The app stores only salted hashes, not plain secrets
- Final quotations are protected by both app logic and SQLite triggers

Important note
- The SQLite file is local and not encrypted
- For stronger protection, keep this folder on a user account only you can access, or store it on a BitLocker-protected drive
