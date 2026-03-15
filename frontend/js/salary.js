const elements = {
  employeeSelect: document.getElementById("employeeSelect"),
  monthPicker: document.getElementById("monthPicker"),
  otherDeductions: document.getElementById("otherDeductions"),
  advance: document.getElementById("advance"),
  generateBtn: document.getElementById("generateBtn"),
  salaryPreview: document.getElementById("salaryPreview"),
  filterMonth: document.getElementById("filterMonth"),
  sortBy: document.getElementById("sortBy"),
  salaryList: document.getElementById("salaryList"),
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

function monthValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

async function loadEmployees() {
  const data = await api("/api/employees");
  const employees = data.records || [];
  elements.employeeSelect.innerHTML = employees
    .map((emp) => `<option value="${emp.id}">${emp.employee_code} - ${emp.full_name}</option>`)
    .join("");
}

function renderPreview(salary) {
  elements.salaryPreview.classList.remove("hidden");
  const slipId = elements.salaryPreview.dataset.runId || "";
  elements.salaryPreview.innerHTML = `
    <div class="panel-head"><h3>Salary Slip Preview</h3></div>
    <div class="salary-slip-frame">
      ${slipId ? `<iframe src="/salary-slip/${slipId}" title="Salary Slip"></iframe>` : ""}
    </div>
    <div class="form-actions">
      <button id="printSlipBtn" class="action-btn ghost" type="button" ${slipId ? "" : "disabled"}>Save Salary Slip PDF</button>
    </div>
  `;
}

function renderSalaryList(records) {
  if (!records.length) {
    elements.salaryList.innerHTML = '<div class="empty-state">No salary runs found.</div>';
    return;
  }
  elements.salaryList.innerHTML = records
    .map(
      (record) => `
        <div class="list-card">
          <div class="list-card-top">
            <strong>${record.employee_name}</strong>
            <span class="pill">${record.employee_code}</span>
          </div>
          <div class="list-card-meta">Month: ${record.month}</div>
          <div class="list-card-meta">Net Pay: ${formatMoney(record.net_pay)}</div>
        </div>
      `
    )
    .join("");
}

async function loadSalaryList() {
  const month = elements.filterMonth.value;
  const sortBy = elements.sortBy.value || "name";
  const url = month
    ? `/api/salary?month=${month}&sort=${sortBy}`
    : `/api/salary?sort=${sortBy}`;
  const data = await api(url);
  renderSalaryList(data.records || []);
}

async function generateSalary() {
  const payload = {
    employee_id: Number(elements.employeeSelect.value),
    month: elements.monthPicker.value,
    other_deductions: toNumber(elements.otherDeductions.value),
    advance: toNumber(elements.advance.value),
  };
  const data = await api("/api/salary/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  elements.salaryPreview.dataset.runId = data.salary_run_id || "";
  renderPreview(data.salary);
  const printBtn = document.getElementById("printSlipBtn");
  if (printBtn) {
    printBtn.addEventListener("click", async () => {
      const runId = elements.salaryPreview.dataset.runId;
      if (runId) {
        try {
          const response = await fetch(`/api/salary/${runId}/export-pdf`);
          if (!response.ok) {
            const text = await response.text();
            const data = text ? JSON.parse(text) : {};
            throw new Error(data.error || data.message || "Download failed");
          }
          const blob = await response.blob();
          const header = response.headers.get("Content-Disposition") || "";
          const match = header.match(/filename=\"([^\"]+)\"/i);
          const filename = match ? match[1] : `salary-slip-${runId}.pdf`;
          const link = document.createElement("a");
          link.href = URL.createObjectURL(blob);
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          URL.revokeObjectURL(link.href);
          link.remove();
        } catch (error) {
          showError(error);
        }
      }
    });
  }
  await loadSalaryList();
}

elements.generateBtn.addEventListener("click", () => {
  generateSalary().catch(showError);
});

elements.filterMonth.addEventListener("change", () => {
  loadSalaryList().catch(showError);
});

elements.sortBy.addEventListener("change", () => {
  loadSalaryList().catch(showError);
});

elements.logoutBtn.addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

elements.monthPicker.value = monthValue();
elements.filterMonth.value = monthValue();

loadEmployees()
  .then(loadSalaryList)
  .catch(showError);
