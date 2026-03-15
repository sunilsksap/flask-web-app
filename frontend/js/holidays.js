const elements = {
  holidayDate: document.getElementById("holidayDate"),
  holidayTitle: document.getElementById("holidayTitle"),
  saveHolidayBtn: document.getElementById("saveHolidayBtn"),
  holidayList: document.getElementById("holidayList"),
  holidayCount: document.getElementById("holidayCount"),
  holidaySearch: document.getElementById("holidaySearch"),
  logoutBtn: document.getElementById("logoutBtn"),
};

let holidayRecords = [];
let editingId = null;

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

function renderHolidays(records) {
  const searchText = elements.holidaySearch.value.trim().toLowerCase();
  const filtered = records.filter((holiday) => {
    if (!searchText) return true;
    const haystack = `${holiday.holiday_date} ${holiday.title}`.toLowerCase();
    return haystack.includes(searchText);
  });
  elements.holidayCount.textContent = String(filtered.length);
  if (!filtered.length) {
    elements.holidayList.innerHTML = '<div class="empty-state">No holidays added.</div>';
    return;
  }
  elements.holidayList.innerHTML = filtered
    .map(
      (holiday) => `
        <div class="list-card" data-id="${holiday.id}">
          <div class="list-card-top">
            <strong>${holiday.holiday_date}</strong>
            <span class="pill">Holiday</span>
          </div>
          <div class="list-card-meta">${holiday.title}</div>
          <div class="row-actions">
            <button class="mini-btn ghost" data-action="edit" type="button">Edit</button>
            <button class="mini-btn danger" data-action="delete" type="button">Delete</button>
          </div>
        </div>
      `
    )
    .join("");
}

async function loadHolidays() {
  const data = await api("/api/holidays");
  holidayRecords = data.records || [];
  renderHolidays(holidayRecords);
}

async function saveHoliday() {
  const payload = {
    holiday_date: elements.holidayDate.value,
    title: elements.holidayTitle.value.trim(),
  };
  await api("/api/holidays", {
    method: "POST",
    body: JSON.stringify({ holiday: payload }),
  });
  elements.holidayTitle.value = "";
  editingId = null;
  await loadHolidays();
}

async function deleteHoliday(id) {
  await api("/api/holidays/delete", {
    method: "POST",
    body: JSON.stringify({ holiday_id: id }),
  });
  await loadHolidays();
}

elements.saveHolidayBtn.addEventListener("click", () => {
  saveHoliday().catch((error) => {
    window.alert(error.message || String(error));
  });
});

elements.holidaySearch.addEventListener("input", () => {
  renderHolidays(holidayRecords);
});

elements.holidayList.addEventListener("click", (event) => {
  const action = event.target.dataset.action;
  const card = event.target.closest(".list-card");
  if (!action || !card) return;
  const holiday = holidayRecords.find((item) => item.id === Number(card.dataset.id));
  if (!holiday) return;

  if (action === "edit") {
    editingId = holiday.id;
    elements.holidayDate.value = holiday.holiday_date;
    elements.holidayTitle.value = holiday.title;
    return;
  }
  if (action === "delete") {
    if (window.confirm(`Delete holiday ${holiday.title}?`)) {
      deleteHoliday(holiday.id).catch((error) => {
        window.alert(error.message || String(error));
      });
    }
  }
});

elements.logoutBtn.addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
});

loadHolidays().catch((error) => {
  window.alert(error.message || String(error));
});
