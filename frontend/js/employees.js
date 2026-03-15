const state = {
  employees: [],
  selectedId: null,
  nextCode: "AVG00001",
};

const elements = {
  employeeList: document.getElementById("employeeList"),
  employeeCount: document.getElementById("employeeCount"),
  employeeSearch: document.getElementById("employeeSearch"),
  formTitle: document.getElementById("formTitle"),
  employeeCode: document.getElementById("employeeCode"),
  employeeId: document.getElementById("employeeId"),
  fullName: document.getElementById("fullName"),
  dob: document.getElementById("dob"),
  gender: document.getElementsByName("gender"),
  phone: document.getElementById("phone"),
  email: document.getElementById("email"),
  address: document.getElementById("address"),
  doj: document.getElementById("doj"),
  department: document.getElementById("department"),
  designation: document.getElementById("designation"),
  employmentType: document.getElementsByName("employmentType"),
  status: document.getElementById("status"),
  baseSalary: document.getElementById("baseSalary"),
  allowances: document.getElementById("allowances"),
  pfPercent: document.getElementById("pfPercent"),
  pfFixed: document.getElementById("pfFixed"),
  esiPercent: document.getElementById("esiPercent"),
  overtimeRate: document.getElementById("overtimeRate"),
  bankName: document.getElementById("bankName"),
  bankAccount: document.getElementById("bankAccount"),
  bankIfsc: document.getElementById("bankIfsc"),
  emergencyName: document.getElementById("emergencyName"),
  emergencyPhone: document.getElementById("emergencyPhone"),
  leaveBalance: document.getElementById("leaveBalance"),
  newEmployeeBtn: document.getElementById("newEmployeeBtn"),
  saveEmployeeBtn: document.getElementById("saveEmployeeBtn"),
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

function getRadioValue(nodeList) {
  const selected = Array.from(nodeList).find((node) => node.checked);
  return selected ? selected.value : "";
}

function setRadioValue(nodeList, value) {
  Array.from(nodeList).forEach((node) => {
    node.checked = node.value === value;
  });
}

function resetForm() {
  state.selectedId = null;
  elements.employeeId.value = "";
  elements.formTitle.textContent = "New Employee";
  elements.employeeCode.textContent = state.nextCode;
  elements.fullName.value = "";
  elements.dob.value = "";
  setRadioValue(elements.gender, "Male");
  elements.phone.value = "";
  elements.email.value = "";
  elements.address.value = "";
  elements.doj.value = "";
  elements.department.value = "";
  elements.designation.value = "";
  setRadioValue(elements.employmentType, "Permanent");
  elements.status.value = "ACTIVE";
  elements.baseSalary.value = "";
  elements.allowances.value = "";
  elements.pfPercent.value = "";
  elements.pfFixed.value = "1800";
  elements.esiPercent.value = "";
  elements.overtimeRate.value = "";
  elements.bankName.value = "";
  elements.bankAccount.value = "";
  elements.bankIfsc.value = "";
  elements.emergencyName.value = "";
  elements.emergencyPhone.value = "";
  elements.leaveBalance.value = "";
  document.querySelectorAll(".weekoff-block input[type='checkbox']").forEach((box) => {
    box.checked = false;
  });
}

function fillForm(employee) {
  state.selectedId = employee.id;
  elements.employeeId.value = employee.id;
  elements.formTitle.textContent = "Edit Employee";
  elements.employeeCode.textContent = employee.employee_code;
  elements.fullName.value = employee.full_name || "";
  elements.dob.value = employee.dob || "";
  setRadioValue(elements.gender, employee.gender || "");
  elements.phone.value = employee.phone || "";
  elements.email.value = employee.email || "";
  elements.address.value = employee.address || "";
  elements.doj.value = employee.doj || "";
  elements.department.value = employee.department || "";
  elements.designation.value = employee.designation || "";
  setRadioValue(elements.employmentType, employee.employment_type || "");
  elements.status.value = employee.status || "ACTIVE";
  elements.baseSalary.value = employee.base_salary || "";
  elements.allowances.value = employee.allowances || "";
  elements.pfPercent.value = employee.pf_percent || "";
  elements.pfFixed.value = employee.pf_fixed ?? "1800";
  elements.esiPercent.value = employee.esi_percent || "";
  elements.overtimeRate.value = employee.overtime_rate || "";
  setRadioValue(document.getElementsByName("pfMode"), employee.pf_mode || "PERCENT");
  elements.bankName.value = employee.bank_name || "";
  elements.bankAccount.value = employee.bank_account || "";
  elements.bankIfsc.value = employee.bank_ifsc || "";
  elements.emergencyName.value = employee.emergency_contact_name || "";
  elements.emergencyPhone.value = employee.emergency_contact_phone || "";
  elements.leaveBalance.value = employee.leave_balance ?? "";
  document.querySelectorAll(".weekoff-block input[type='checkbox']").forEach((box) => {
    box.checked = Array.isArray(employee.week_off) && employee.week_off.includes(box.value);
  });
}

function renderList() {
  const searchText = elements.employeeSearch.value.trim().toLowerCase();
  const filtered = state.employees.filter((employee) => {
    if (!searchText) {
      return true;
    }
    const haystack = `${employee.employee_code} ${employee.full_name}`.toLowerCase();
    return haystack.includes(searchText);
  });

  elements.employeeCount.textContent = String(filtered.length);
  if (!filtered.length) {
    elements.employeeList.innerHTML = '<div class="empty-state">No employees found.</div>';
    return;
  }

  elements.employeeList.innerHTML = filtered
    .map(
      (employee) => `
        <div class="list-card ${employee.id === state.selectedId ? "active" : ""}" data-id="${employee.id}">
          <div class="list-card-top">
            <strong>${employee.full_name}</strong>
            <span class="pill ${employee.status === "ACTIVE" ? "pill-success" : "pill-muted"}">${employee.status}</span>
          </div>
          <div class="list-card-meta">${employee.employee_code} • ${employee.department || "No department"}</div>
        </div>
      `
    )
    .join("");
}

function selectedWeekOff() {
  return Array.from(document.querySelectorAll(".weekoff-block input[type='checkbox']"))
    .filter((box) => box.checked)
    .map((box) => box.value);
}

async function loadEmployees() {
  const data = await api("/api/employees");
  state.employees = data.records || [];
  state.nextCode = data.next_employee_code || "AVG00001";
  if (!state.selectedId) {
    elements.employeeCode.textContent = state.nextCode;
  }
  renderList();
}

async function saveEmployee() {
  const payload = {
    id: elements.employeeId.value || null,
    employee_code: elements.employeeCode.textContent,
    full_name: elements.fullName.value.trim(),
    dob: elements.dob.value,
    gender: getRadioValue(elements.gender),
    phone: elements.phone.value.trim(),
    email: elements.email.value.trim(),
    address: elements.address.value.trim(),
    doj: elements.doj.value,
    department: elements.department.value.trim(),
    designation: elements.designation.value.trim(),
    employment_type: getRadioValue(elements.employmentType),
    status: elements.status.value,
    base_salary: toNumber(elements.baseSalary.value),
    allowances: toNumber(elements.allowances.value),
    pf_percent: toNumber(elements.pfPercent.value),
    pf_fixed: toNumber(elements.pfFixed.value),
    pf_mode: getRadioValue(document.getElementsByName("pfMode")) || "PERCENT",
    esi_percent: toNumber(elements.esiPercent.value),
    overtime_rate: toNumber(elements.overtimeRate.value),
    bank_name: elements.bankName.value.trim(),
    bank_account: elements.bankAccount.value.trim(),
    bank_ifsc: elements.bankIfsc.value.trim(),
    emergency_contact_name: elements.emergencyName.value.trim(),
    emergency_contact_phone: elements.emergencyPhone.value.trim(),
    leave_balance: toNumber(elements.leaveBalance.value),
    week_off: selectedWeekOff(),
  };

  const data = await api("/api/employees", {
    method: "POST",
    body: JSON.stringify({ employee: payload }),
  });
  state.employees = data.records || state.employees;
  const saved = data.employee;
  state.selectedId = saved.id;
  fillForm(saved);
  renderList();
  await loadEmployees();
}

elements.employeeList.addEventListener("click", (event) => {
  const card = event.target.closest(".list-card");
  if (!card) {
    return;
  }
  const employee = state.employees.find((item) => item.id === Number(card.dataset.id));
  if (employee) {
    fillForm(employee);
    renderList();
  }
});

elements.employeeSearch.addEventListener("input", () => {
  renderList();
});

elements.newEmployeeBtn.addEventListener("click", () => {
  loadEmployees()
    .then(() => {
      resetForm();
      renderList();
    })
    .catch(showError);
});

elements.saveEmployeeBtn.addEventListener("click", () => {
  saveEmployee().catch(showError);
});

elements.logoutBtn.addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

loadEmployees()
  .then(() => resetForm())
  .catch(showError);
