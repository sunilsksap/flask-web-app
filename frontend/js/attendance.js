const elements = {
  employeeSelect: document.getElementById("employeeSelect"),
  workDate: document.getElementById("workDate"),
  status: document.getElementById("status"),
  overtimeHours: document.getElementById("overtimeHours"),
  note: document.getElementById("note"),
  saveAttendanceBtn: document.getElementById("saveAttendanceBtn"),
  monthPicker: document.getElementById("monthPicker"),
  summaryCards: document.getElementById("summaryCards"),
  attendanceList: document.getElementById("attendanceList"),
  logoutBtn: document.getElementById("logoutBtn"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.error || data.message || "Request failed");
  }
  return data;
}

function toNumber(value) {
  const parsed = Number(String(value ?? "").replace(/,/g, "").trim());
  return Number.isFinite(parsed) ? parsed : 0;
}

function showError(error) {
  window.alert(error.message || String(error));
}

function todayValue() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function monthValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

async function loadEmployees() {
  const data = await api("/api/employees");
  const employees = data.records || [];
  elements.employeeSelect.innerHTML = employees
    .map((emp) => `<option value="${emp.id}">${emp.employee_code} - ${emp.full_name}</option>`)
    .join("");
}

function renderSummary(summary) {
  elements.summaryCards.innerHTML = `
    <div class="summary-card">
      <div class="summary-label">Present Days</div>
      <div class="summary-value">${summary.present_days}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Absent Days</div>
      <div class="summary-value">${summary.absent_days}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Half Days</div>
      <div class="summary-value">${summary.half_days}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Leave Days</div>
      <div class="summary-value">${summary.leave_days}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Holiday Days</div>
      <div class="summary-value">${summary.holiday_days}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Week Off</div>
      <div class="summary-value">${summary.week_off_days}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">LWP Days</div>
      <div class="summary-value">${summary.lwp_days}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Leave Balance</div>
      <div class="summary-value" id="leaveBalanceCard">0</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Leave Used</div>
      <div class="summary-value" id="leaveUsedCard">0</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Leave Remaining</div>
      <div class="summary-value" id="leaveRemainCard">0</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Overtime Hours</div>
      <div class="summary-value">${summary.overtime_hours}</div>
    </div>
  `;
}

function renderEntries(entries) {
  if (!entries.length) {
    elements.attendanceList.innerHTML = '<div class="empty-state">No attendance entries yet.</div>';
    return;
  }
  elements.attendanceList.innerHTML = entries
    .map(
      (entry) => `
        <div class="list-card">
          <div class="list-card-top">
            <strong>${entry.work_date}</strong>
            <span class="pill">${entry.status.replace("_", " ")}</span>
          </div>
          <div class="list-card-meta">Overtime: ${entry.overtime_hours} hrs</div>
          <div class="list-card-meta">${entry.note || ""}</div>
        </div>
      `
    )
    .join("");
}


async function loadAttendance() {
  const employeeId = elements.employeeSelect.value;
  const month = elements.monthPicker.value;
  if (!employeeId || !month) {
    return;
  }
  const data = await api(`/api/attendance?employee_id=${employeeId}&month=${month}`);
  renderSummary(data.summary);
  const balanceNode = document.getElementById("leaveBalanceCard");
  const usedNode = document.getElementById("leaveUsedCard");
  const remainNode = document.getElementById("leaveRemainCard");
  if (balanceNode) balanceNode.textContent = data.leave_balance ?? 0;
  if (usedNode) usedNode.textContent = data.leave_used ?? 0;
  if (remainNode) remainNode.textContent = data.leave_remaining ?? 0;
  renderEntries(data.entries || []);
}

async function saveAttendance() {
  const payload = {
    employee_id: Number(elements.employeeSelect.value),
    work_date: elements.workDate.value,
    status: elements.status.value,
    overtime_hours: toNumber(elements.overtimeHours.value),
    note: elements.note.value.trim(),
  };
  await api("/api/attendance", {
    method: "POST",
    body: JSON.stringify({ attendance: payload }),
  });
  await loadAttendance();
}


elements.saveAttendanceBtn.addEventListener("click", () => {
  saveAttendance().catch(showError);
});

elements.employeeSelect.addEventListener("change", () => {
  loadAttendance().catch(showError);
});

elements.monthPicker.addEventListener("change", () => {
  loadAttendance().catch(showError);
});


elements.logoutBtn.addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

elements.workDate.value = todayValue();
elements.monthPicker.value = monthValue();

loadEmployees()
  .then(() => loadAttendance())
  .catch(showError);
