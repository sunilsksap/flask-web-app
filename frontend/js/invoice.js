const state = {
  records: [],
  current: null,
  dirty: false,
  pinConfigured: false,
  selectedId: null,
};

const COMPANY_NAME = "AstroVolt Global LLP";
const COMPANY_TAGLINE = "Aerospace & Defence | Healthcare Sterilization | Industrial Automation";
const DEFAULT_COMPANY_ADDRESS = "#7/31, 2nd Main Road, Domlur Layout, Bengaluru-560071.";
const COMPANY_EMAIL = "support@astrovoltglobal.com";
const COMPANY_WEBSITE = "www.astrovoltglobal.com";
const COMPANY_PAN = "ACNFA6723D";
const COMPANY_TAN = "BLRA60131B";
const FIXED_TERMS = [
  { title: "Validity", body: "This invoice is valid for 60 days from the date of issue." },
  { title: "Delivery", body: "Delivery schedule shall be as per Purchase Order (PO)." },
  { title: "Payment Terms", body: "Payment shall be as per mutually agreed Purchase Order conditions." },
  { title: "Taxes", body: "GST, if applicable, shall be charged extra as per prevailing government regulations." },
  { title: "Warranty", body: "Warranty shall be as per the terms agreed in the Purchase Order." },
  { title: "Confidentiality", body: "The information contained in this invoice shall be confidential and shall not be disclosed to any third party without written consent." },
];
const FIXED_TERMS_TEXT = FIXED_TERMS
  .map((term) => `${term.title}: ${term.body}`)
  .join("\n");

const fieldIds = [
  "companyMobile",
  "companyGstin",
  "customerName",
  "customerContact",
  "customerAddress",
  "customerMobile",
  "customerGstin",
  "quoteDate",
  "validUntil",
  "bankAccountName",
  "bankName",
  "bankAccountNumber",
  "bankIfsc",
  "signatoryName",
  "signatoryDesignation",
];

const elements = {
  databasePath: document.getElementById("databasePath"),
  importQuoteSelect: document.getElementById("importQuoteSelect"),
  importQuoteBtn: document.getElementById("importQuoteBtn"),
  quoteList: document.getElementById("quoteList"),
  recordCount: document.getElementById("recordCount"),
  currentDisplayNumber: document.getElementById("currentDisplayNumber"),
  displayNumberChip: document.getElementById("displayNumberChip"),
  statusBadge: document.getElementById("statusBadge"),
  lockBadge: document.getElementById("lockBadge"),
  saveNotice: document.getElementById("saveNotice"),
  securityNotice: document.getElementById("securityNotice"),
  itemsTableBody: document.getElementById("itemsTableBody"),
  amountWords: document.getElementById("amountWords"),
  subTotal: document.getElementById("subTotal"),
  cgst: document.getElementById("cgst"),
  sgst: document.getElementById("sgst"),
  grandTotal: document.getElementById("grandTotal"),
  searchInput: document.getElementById("searchInput"),
  newQuoteBtn: document.getElementById("newQuoteBtn"),
  saveDraftBtn: document.getElementById("saveDraftBtn"),
  finalizeBtn: document.getElementById("finalizeBtn"),
  reviseBtn: document.getElementById("reviseBtn"),
  printBtn: document.getElementById("printBtn"),
  pinBtn: document.getElementById("pinBtn"),
  addItemBtn: document.getElementById("addItemBtn"),
  dbRecordView: document.getElementById("dbRecordView"),
  termsList: document.getElementById("termsList"),
  signatoryNamePrint: document.getElementById("signatoryNamePrint"),
  signatoryDesignationPrint: document.getElementById("signatoryDesignationPrint"),
  logoutBtn: document.getElementById("logoutBtn"),
};

function field(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function toNumber(value) {
  const parsed = Number(String(value ?? "").replace(/,/g, "").trim());
  return Number.isFinite(parsed) ? parsed : 0;
}

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

function markDirty(message = "Changes not saved") {
  state.dirty = true;
  elements.saveNotice.textContent = message;
}

function markSaved(message) {
  state.dirty = false;
  elements.saveNotice.textContent = message;
}

function confirmIfDirty() {
  if (!state.dirty) {
    return true;
  }
  return window.confirm("You have unsaved changes. Continue anyway?");
}

function defaultQuote() {
  const today = new Date();
  const local = new Date(today.getTime() - today.getTimezoneOffset() * 60000);
  const quoteDate = local.toISOString().slice(0, 10);
  const validUntilDate = new Date(local);
  validUntilDate.setDate(validUntilDate.getDate() + 60);
  const validUntil = new Date(validUntilDate.getTime() - validUntilDate.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 10);

  return {
    id: null,
    base_quote_number: "",
    display_number: "AVG-INV-0000-000",
    revision_number: 0,
    status: "DRAFT",
    company_name: COMPANY_NAME,
    tagline: COMPANY_TAGLINE,
    company_address: DEFAULT_COMPANY_ADDRESS,
    company_mobile: "+91 00000 00000",
    company_email: COMPANY_EMAIL,
    company_website: COMPANY_WEBSITE,
    company_gstin: "Add GST number",
    company_pan: COMPANY_PAN,
    company_tan: COMPANY_TAN,
    customer_name: "",
    customer_contact: "",
    customer_address: "",
    customer_mobile: "",
    customer_gstin: "",
    quote_date: quoteDate,
    valid_until: validUntil,
    reference: "Engineering systems supply, service, and customer-specific technical support",
    payment_terms: "Payment shall be as per mutually agreed Purchase Order conditions.",
    notes: FIXED_TERMS_TEXT,
    bank_account_name: "AstroVolt Global LLP",
    bank_name: "Add bank name here",
    bank_account_number: "000000000000",
    bank_ifsc: "ABCD0000000",
    bank_upi: "",
    signatory_name: "Authorised Person",
    signatory_designation: "Partner / Manager",
    items: [
      {
        description: "Aerospace and defence reliability engineering, review and technical advisory support",
        sac: "Add SAC",
        qty: 1,
        rate: 18000,
        tax: 18,
      },
      {
        description: "ETO sterilizer validation and documentation support",
        sac: "Add SAC",
        qty: 1,
        rate: 6500,
        tax: 18,
      },
      {
        description: "PLC, SCADA and HMI configuration / commissioning support",
        sac: "Add SAC",
        qty: 1,
        rate: 12000,
        tax: 18,
      },
      {
        description: "Autoclave preventive maintenance, inspection and service support",
        sac: "Add SAC",
        qty: 1,
        rate: 4500,
        tax: 18,
      },
      {
        description: "Custom requirement / special item / materials used as per customer demand",
        sac: "Add SAC",
        qty: 1,
        rate: 0,
        tax: 18,
      },
    ],
  };
}

function itemAmount(item) {
  return toNumber(item.qty) * toNumber(item.rate);
}

function itemTaxAmount(item) {
  return itemAmount(item) * toNumber(item.tax) / 100;
}

function itemTotalWithTax(item) {
  return itemAmount(item) + itemTaxAmount(item);
}

function totalsFromItems(items) {
  let subtotal = 0;
  let taxTotal = 0;
  items.forEach((item) => {
    const amount = itemAmount(item);
    subtotal += amount;
    taxTotal += itemTaxAmount(item);
  });
  const cgst = taxTotal / 2;
  const sgst = taxTotal / 2;
  const grandTotal = subtotal + taxTotal;
  return {
    subtotal,
    cgst,
    sgst,
    grandTotal,
  };
}

function numberToWords(value) {
  const whole = Math.floor(value);
  const paise = Math.round((value - whole) * 100);
  const ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];
  const tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];

  function underThousand(number) {
    const hundred = Math.floor(number / 100);
    const rest = number % 100;
    const parts = [];
    if (hundred) {
      parts.push(`${ones[hundred]} Hundred`);
    }
    if (rest) {
      if (rest < 20) {
        parts.push(ones[rest]);
      } else {
        parts.push(`${tens[Math.floor(rest / 10)]} ${ones[rest % 10]}`.trim());
      }
    }
    return parts.join(" ").trim();
  }

  function integerWords(number) {
    if (number === 0) {
      return "Zero";
    }
    const crore = Math.floor(number / 10000000);
    const lakh = Math.floor((number % 10000000) / 100000);
    const thousand = Math.floor((number % 100000) / 1000);
    const rest = number % 1000;
    const pieces = [];
    if (crore) {
      pieces.push(`${underThousand(crore)} Crore`);
    }
    if (lakh) {
      pieces.push(`${underThousand(lakh)} Lakh`);
    }
    if (thousand) {
      pieces.push(`${underThousand(thousand)} Thousand`);
    }
    if (rest) {
      pieces.push(underThousand(rest));
    }
    return pieces.join(" ").trim();
  }

  if (paise) {
    return `${integerWords(whole)} and ${integerWords(paise)} Paise Only`;
  }
  return `${integerWords(whole)} Only`;
}

function renderItems(items) {
  elements.itemsTableBody.innerHTML = items
    .map((item, index) => {
      const amount = itemTotalWithTax(item);
      return `
        <tr data-index="${index}">
          <td class="item-index">${index + 1}</td>
          <td><textarea class="item-input item-textarea" data-key="description">${escapeHtml(item.description)}</textarea></td>
          <td><input class="item-input" data-key="sac" type="text" value="${escapeHtml(item.sac)}"></td>
          <td><input class="item-input item-number" data-key="qty" type="text" inputmode="decimal" value="${escapeHtml(item.qty)}"></td>
          <td><input class="item-input item-number" data-key="rate" type="text" inputmode="decimal" value="${escapeHtml(item.rate)}"></td>
          <td><input class="item-input item-number" data-key="tax" type="text" inputmode="decimal" value="${escapeHtml(item.tax)}"></td>
          <td class="item-amount">${formatMoney(amount)}</td>
          <td><button class="remove-btn" type="button">-</button></td>
        </tr>
      `;
    })
    .join("");
  syncTextareaHeights(elements.itemsTableBody);
}

function minimumTextareaHeight(textarea) {
  if (textarea.classList.contains("notes-field")) {
    return 220;
  }
  if (textarea.classList.contains("item-textarea")) {
    return 72;
  }
  return 92;
}

function autoResizeTextarea(textarea) {
  if (!textarea) {
    return;
  }
  const minHeight = Number(textarea.dataset.minHeight || minimumTextareaHeight(textarea));
  textarea.style.height = "auto";
  textarea.style.height = `${Math.max(textarea.scrollHeight, minHeight)}px`;
}

function syncTextareaHeights(root = document) {
  root.querySelectorAll("textarea").forEach((textarea) => {
    if (!textarea.dataset.minHeight) {
      textarea.dataset.minHeight = String(minimumTextareaHeight(textarea));
    }
    autoResizeTextarea(textarea);
  });
}

function renderFixedTerms() {
  elements.termsList.innerHTML = FIXED_TERMS.map(
    (term) => `
      <div class="term-row">
        <div class="term-title">${escapeHtml(term.title)}</div>
        <div class="term-body">${escapeHtml(term.body)}</div>
      </div>
    `
  ).join("");
}

function syncPrintFields() {
  if (elements.signatoryNamePrint) {
    elements.signatoryNamePrint.textContent = field("signatoryName").value.trim() || "Authorised Person";
  }
  if (elements.signatoryDesignationPrint) {
    elements.signatoryDesignationPrint.textContent = field("signatoryDesignation").value.trim() || "Partner / Manager";
  }
}

async function exportPdf() {
  if (!state.current) {
    return;
  }

  const popup = window.open("about:blank", "_blank");
  try {
    if (!state.current.id || state.dirty) {
      await saveDraft();
    }
    const quoteId = state.current?.id || state.selectedId;
    if (!quoteId) {
      throw new Error("Save the invoice before generating the PDF.");
    }
    const exportUrl = `/api/invoices/${quoteId}/export-pdf?ts=${Date.now()}`;
    if (popup) {
      popup.location = exportUrl;
    } else {
      window.open(exportUrl, "_blank");
    }
  markSaved(`${state.current.display_number || "Invoice"} PDF generated.`);
  } catch (error) {
    if (popup && !popup.closed) {
      popup.close();
    }
    throw error;
  }
}

function readItems() {
  return Array.from(elements.itemsTableBody.querySelectorAll("tr")).map((row) => ({
    description: row.querySelector('[data-key="description"]').value.trim(),
    sac: row.querySelector('[data-key="sac"]').value.trim(),
    qty: toNumber(row.querySelector('[data-key="qty"]').value),
    rate: toNumber(row.querySelector('[data-key="rate"]').value),
    tax: toNumber(row.querySelector('[data-key="tax"]').value),
  }));
}

function currentFormData() {
  const quotation = {
    ...(state.current || defaultQuote()),
    items: readItems(),
  };

  quotation.company_name = COMPANY_NAME;
  quotation.tagline = COMPANY_TAGLINE;
  quotation.company_address = DEFAULT_COMPANY_ADDRESS;
  quotation.company_mobile = field("companyMobile").value.trim();
  quotation.company_email = COMPANY_EMAIL;
  quotation.company_website = COMPANY_WEBSITE;
  quotation.company_gstin = field("companyGstin").value.trim();
  quotation.company_pan = COMPANY_PAN;
  quotation.company_tan = COMPANY_TAN;
  quotation.customer_name = field("customerName").value.trim();
  quotation.customer_contact = field("customerContact").value.trim();
  quotation.customer_address = field("customerAddress").value.trim();
  quotation.customer_mobile = field("customerMobile").value.trim();
  quotation.customer_gstin = field("customerGstin").value.trim();
  quotation.quote_date = field("quoteDate").value;
  quotation.valid_until = field("validUntil").value;
  quotation.reference = "";
  quotation.payment_terms = "";
  quotation.notes = FIXED_TERMS_TEXT;
  quotation.bank_account_name = field("bankAccountName").value.trim();
  quotation.bank_name = field("bankName").value.trim();
  quotation.bank_account_number = field("bankAccountNumber").value.trim();
  quotation.bank_ifsc = field("bankIfsc").value.trim();
  quotation.bank_upi = "";
  quotation.signatory_name = field("signatoryName").value.trim();
  quotation.signatory_designation = field("signatoryDesignation").value.trim();
  return quotation;
}

function applyQuote(quotation) {
  state.current = typeof structuredClone === "function"
    ? structuredClone(quotation)
    : JSON.parse(JSON.stringify(quotation));
  document.getElementById("companyNameStatic").textContent = COMPANY_NAME;
  document.getElementById("taglineStatic").textContent = COMPANY_TAGLINE;
  document.getElementById("companyAddressStatic").textContent = DEFAULT_COMPANY_ADDRESS;
  document.getElementById("companyEmailStatic").textContent = COMPANY_EMAIL;
  document.getElementById("companyWebsiteStatic").textContent = COMPANY_WEBSITE;
  document.getElementById("companyPanStatic").textContent = COMPANY_PAN;
  document.getElementById("companyTanStatic").textContent = COMPANY_TAN;
  field("companyMobile").value = quotation.company_mobile || "";
  field("companyGstin").value = quotation.company_gstin || "";
  field("customerName").value = quotation.customer_name || "";
  field("customerContact").value = quotation.customer_contact || "";
  field("customerAddress").value = quotation.customer_address || "";
  field("customerMobile").value = quotation.customer_mobile || "";
  field("customerGstin").value = quotation.customer_gstin || "";
  field("quoteDate").value = quotation.quote_date || "";
  field("validUntil").value = quotation.valid_until || "";
  field("bankAccountName").value = quotation.bank_account_name || "";
  field("bankName").value = quotation.bank_name || "";
  field("bankAccountNumber").value = quotation.bank_account_number || "";
  field("bankIfsc").value = quotation.bank_ifsc || "";
  field("signatoryName").value = quotation.signatory_name || "";
  field("signatoryDesignation").value = quotation.signatory_designation || "";

  renderItems(quotation.items || []);
  renderFixedTerms();
  syncPrintFields();
  syncTextareaHeights();
  refreshHeader();
  recalculateTotals();
  renderDbRecordView();
  updateActionState();
}

function refreshHeader() {
  const current = currentFormData();
  const displayNumber = current.display_number || current.base_quote_number || "AVG-0000-000";
  elements.currentDisplayNumber.textContent = displayNumber;
  elements.displayNumberChip.textContent = displayNumber;
  const isFinal = current.status === "FINAL" || current.is_locked;
  elements.statusBadge.textContent = isFinal ? "Final" : "Draft";
  elements.statusBadge.className = `status-badge ${isFinal ? "final" : "draft"}`;
  elements.lockBadge.textContent = isFinal ? "Locked" : "Editable";
  syncPrintFields();
}

function recalculateTotals() {
  const items = readItems();
  const totals = totalsFromItems(items);
  elements.subTotal.textContent = formatMoney(totals.subtotal);
  elements.cgst.textContent = formatMoney(totals.cgst);
  elements.sgst.textContent = formatMoney(totals.sgst);
  elements.grandTotal.textContent = formatMoney(totals.grandTotal);
  elements.amountWords.textContent = numberToWords(totals.grandTotal);

  Array.from(elements.itemsTableBody.querySelectorAll("tr")).forEach((row, index) => {
    row.querySelector(".item-index").textContent = String(index + 1);
    row.querySelector(".item-amount").textContent = formatMoney(itemTotalWithTax(items[index]));
  });
  renderDbRecordView();
}

function setFormLocked(locked) {
  fieldIds.forEach((id) => {
    field(id).disabled = locked;
  });
  elements.itemsTableBody.querySelectorAll(".item-input, .remove-btn").forEach((node) => {
    node.disabled = locked;
  });
  elements.addItemBtn.disabled = locked;
  elements.saveDraftBtn.disabled = locked;
  elements.finalizeBtn.disabled = locked || !state.current || !state.current.id;
  elements.reviseBtn.disabled = !locked;
}

function updateActionState() {
  const current = state.current || defaultQuote();
  const locked = current.status === "FINAL" || current.is_locked;
  setFormLocked(locked);
}

function renderList() {
  const searchText = elements.searchInput.value.trim().toLowerCase();
  const records = state.records.filter((record) => {
    if (!searchText) {
      return true;
    }
    const haystack = `${record.display_number} ${record.customer_name}`.toLowerCase();
    return haystack.includes(searchText);
  });

  elements.recordCount.textContent = String(records.length);
  if (!records.length) {
    elements.quoteList.innerHTML = '<div class="empty-state">No invoices match the current search.</div>';
    return;
  }

  elements.quoteList.innerHTML = records
    .map((record) => {
      const active = record.id === state.selectedId ? "active" : "";
      const statusClass = record.status === "FINAL" ? "final" : "draft";
      return `
        <div class="quote-card ${active}" data-id="${record.id}">
          <div class="quote-card-top">
            <div class="quote-number">${escapeHtml(record.display_number)}</div>
            <span class="status-badge ${statusClass}">${escapeHtml(record.status)}</span>
          </div>
          <div class="quote-customer">${escapeHtml(record.customer_name || "No customer yet")}</div>
          <div class="quote-card-bottom">
            <div class="quote-meta">${escapeHtml(record.quote_date || "")}</div>
            <div class="quote-meta">${formatMoney(record.grand_total || 0)}</div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderDbRecordView() {
  const current = currentFormData();
  const itemsHtml = (current.items || [])
    .map(
      (item, index) => `
        <div class="db-pair">
          <div class="db-key">Item ${index + 1}</div>
          <div class="db-value">${escapeHtml(item.description || "")}
HSN/SAC: ${escapeHtml(item.sac || "")}
Qty: ${escapeHtml(item.qty)}
Rate: ${escapeHtml(item.rate)}
Tax %: ${escapeHtml(item.tax)}
Taxable Value: ${escapeHtml(formatMoney(itemAmount(item)))}
Line Total: ${escapeHtml(formatMoney(itemTotalWithTax(item)))}</div>
        </div>
      `
    )
    .join("");

  elements.dbRecordView.innerHTML = `
    <div class="db-block">
      <h3>Header</h3>
      <div class="db-pair"><div class="db-key">Invoice Number</div><div class="db-value">${escapeHtml(current.display_number || current.base_quote_number || "")}</div></div>
      <div class="db-pair"><div class="db-key">Status</div><div class="db-value">${escapeHtml(current.status || "DRAFT")}</div></div>
      <div class="db-pair"><div class="db-key">Company</div><div class="db-value">${escapeHtml(current.company_name || "")}
${escapeHtml(current.tagline || "")}
${escapeHtml(current.company_address || "")}
Mobile: ${escapeHtml(current.company_mobile || "")}
Email: ${escapeHtml(current.company_email || "")}
Website: ${escapeHtml(current.company_website || "")}
GSTIN: ${escapeHtml(current.company_gstin || "")}
PAN: ${escapeHtml(current.company_pan || "")}
TAN: ${escapeHtml(current.company_tan || "")}</div></div>
    </div>
    <div class="db-block">
      <h3>Customer</h3>
      <div class="db-pair"><div class="db-key">Name</div><div class="db-value">${escapeHtml(current.customer_name || "")}</div></div>
      <div class="db-pair"><div class="db-key">Contact</div><div class="db-value">${escapeHtml(current.customer_contact || "")}</div></div>
      <div class="db-pair"><div class="db-key">Address</div><div class="db-value">${escapeHtml(current.customer_address || "")}</div></div>
      <div class="db-pair"><div class="db-key">Mobile / GSTIN</div><div class="db-value">${escapeHtml(current.customer_mobile || "")}
${escapeHtml(current.customer_gstin || "")}</div></div>
    </div>
    <div class="db-block">
      <h3>Terms</h3>
      <div class="db-pair"><div class="db-key">Invoice Date</div><div class="db-value">${escapeHtml(current.quote_date || "")}</div></div>
      <div class="db-pair"><div class="db-key">Due Date</div><div class="db-value">${escapeHtml(current.valid_until || "")}</div></div>
      <div class="db-pair"><div class="db-key">Notes</div><div class="db-value">${escapeHtml(current.notes || "")}</div></div>
    </div>
    <div class="db-block">
      <h3>Items</h3>
      ${itemsHtml || '<div class="db-value">No items</div>'}
    </div>
    <div class="db-block">
      <h3>Totals</h3>
      <div class="db-pair"><div class="db-key">Taxable Value</div><div class="db-value">${escapeHtml(elements.subTotal.textContent || "0.00")}</div></div>
      <div class="db-pair"><div class="db-key">CGST</div><div class="db-value">${escapeHtml(elements.cgst.textContent || "0.00")}</div></div>
      <div class="db-pair"><div class="db-key">SGST</div><div class="db-value">${escapeHtml(elements.sgst.textContent || "0.00")}</div></div>
      <div class="db-pair"><div class="db-key">Total Payable</div><div class="db-value">${escapeHtml(elements.grandTotal.textContent || "0.00")}</div></div>
      <div class="db-pair"><div class="db-key">Invoice Value in Words</div><div class="db-value">${escapeHtml(elements.amountWords.textContent || "")}</div></div>
    </div>
  `;
}

function renderImportQuotes(quotations = []) {
  if (!elements.importQuoteSelect) {
    return;
  }
  if (!quotations.length) {
    elements.importQuoteSelect.innerHTML = '<option value="">No quotations found</option>';
    elements.importQuoteSelect.disabled = true;
    if (elements.importQuoteBtn) {
      elements.importQuoteBtn.disabled = true;
    }
    return;
  }
  elements.importQuoteSelect.disabled = false;
  if (elements.importQuoteBtn) {
    elements.importQuoteBtn.disabled = false;
  }
  elements.importQuoteSelect.innerHTML = quotations
    .map(
      (quote) =>
        `<option value="${quote.id}">${escapeHtml(quote.display_number)} - ${escapeHtml(quote.customer_name || "No customer")}</option>`
    )
    .join("");
}

async function loadBootstrap() {
  const data = await api("/api/invoices/bootstrap");
  state.records = data.records || [];
  state.pinConfigured = Boolean(data.pin_configured);
  elements.databasePath.textContent = data.database_path || "quotations.db";
  elements.securityNotice.textContent = state.pinConfigured ? "Admin PIN configured" : "PIN not set yet";
  renderList();
  renderImportQuotes(data.quotations || []);
}

async function createNewQuote() {
  if (!confirmIfDirty()) {
    return;
  }
  const data = await api("/api/invoices/template");
  state.pinConfigured = Boolean(data.pin_configured);
  state.selectedId = null;
  const fresh = {
    ...data.invoice,
    customer_name: "",
    customer_contact: "",
    customer_address: "",
    customer_mobile: "",
    customer_gstin: "",
    items: [],
  };
  applyQuote(fresh);
  markSaved("New draft loaded. Save to create it in the database.");
  renderList();
}

async function importFromQuotation() {
  if (!elements.importQuoteSelect || !elements.importQuoteSelect.value) {
    return;
  }
  if (!confirmIfDirty()) {
    return;
  }
  const quoteId = Number(elements.importQuoteSelect.value);
  const [template, quoteData] = await Promise.all([
    api("/api/invoices/template"),
    api(`/api/quotations/${quoteId}`),
  ]);
  const quotation = quoteData.quotation || {};
  const invoice = {
    ...template.invoice,
    customer_name: quotation.customer_name || "",
    customer_contact: quotation.customer_contact || "",
    customer_address: quotation.customer_address || "",
    customer_mobile: quotation.customer_mobile || "",
    customer_gstin: quotation.customer_gstin || "",
    items: Array.isArray(quotation.items) ? quotation.items : [],
  };
  state.pinConfigured = Boolean(template.pin_configured);
  state.selectedId = null;
  applyQuote(invoice);
  markSaved(`Imported ${quotation.display_number || "quotation"} into a new invoice draft.`);
  renderList();
}

async function loadRecord(id) {
  if (!confirmIfDirty()) {
    renderList();
    return;
  }
  const data = await api(`/api/invoices/${id}`);
  state.selectedId = id;
  applyQuote(data.invoice);
  markSaved(`${data.display_number || data.invoice.display_number} loaded from database.`);
  renderList();
}

async function saveDraft() {
  const invoice = currentFormData();
  const data = await api("/api/invoices/save-draft", {
    method: "POST",
    body: JSON.stringify({ invoice }),
  });
  state.records = data.records || state.records;
  state.selectedId = data.record.id;
  applyQuote(data.record.invoice);
  markSaved(`${data.record.display_number} saved to database.`);
  renderList();
}

async function ensurePin() {
  if (state.pinConfigured) {
    return true;
  }
  const newPin = window.prompt("Create an admin PIN for final locking and revisions (minimum 4 characters).");
  if (!newPin) {
    return false;
  }
  await api("/api/security/pin", {
    method: "POST",
    body: JSON.stringify({ new_pin: newPin }),
  });
  state.pinConfigured = true;
  elements.securityNotice.textContent = "Admin PIN configured";
  return true;
}

async function promptAndFinalize() {
  if (!state.current) {
    return;
  }
  if (!state.current.id) {
    await saveDraft();
  }
  if (!(await ensurePin())) {
    return;
  }
  const pin = window.prompt("Enter the admin PIN to finalize and permanently lock this invoice.");
  if (!pin) {
    return;
  }
  const data = await api(`/api/invoices/${state.current.id}/finalize`, {
    method: "POST",
    body: JSON.stringify({ pin }),
  });
  state.records = data.records || state.records;
  state.selectedId = data.record.id;
  applyQuote(data.record.invoice);
  markSaved(`${data.record.display_number} finalised and locked.`);
  renderList();
}

async function createRevision() {
  if (!state.current || !state.current.id) {
    return;
  }
  if (!(await ensurePin())) {
    return;
  }
  const pin = window.prompt("Enter the admin PIN to create a new revision draft.");
  if (!pin) {
    return;
  }
  const data = await api(`/api/invoices/${state.current.id}/revise`, {
    method: "POST",
    body: JSON.stringify({ pin }),
  });
  state.records = data.records || state.records;
  state.selectedId = data.record.id;
  applyQuote(data.record.invoice);
  markSaved(`${data.record.display_number} revision draft created.`);
  renderList();
}

async function changePin() {
  const currentPin = state.pinConfigured ? window.prompt("Enter current admin PIN.") : "";
  if (state.pinConfigured && !currentPin) {
    return;
  }
  const newPin = window.prompt("Enter the new admin PIN (minimum 4 characters).");
  if (!newPin) {
    return;
  }
  await api("/api/security/pin", {
    method: "POST",
    body: JSON.stringify({
      current_pin: currentPin || "",
      new_pin: newPin,
    }),
  });
  state.pinConfigured = true;
  elements.securityNotice.textContent = "Admin PIN configured";
  markSaved("Admin PIN saved.");
}

function attachEvents() {
  elements.newQuoteBtn.addEventListener("click", () => {
    createNewQuote().catch(showError);
  });
  elements.saveDraftBtn.addEventListener("click", () => {
    saveDraft().catch(showError);
  });
  elements.finalizeBtn.addEventListener("click", () => {
    promptAndFinalize().catch(showError);
  });
  elements.reviseBtn.addEventListener("click", () => {
    createRevision().catch(showError);
  });
  elements.printBtn.addEventListener("click", () => {
    exportPdf().catch(showError);
  });
  elements.pinBtn.addEventListener("click", () => {
    changePin().catch(showError);
  });
  if (elements.importQuoteBtn) {
    elements.importQuoteBtn.addEventListener("click", () => {
      importFromQuotation().catch(showError);
    });
  }
  elements.addItemBtn.addEventListener("click", () => {
    const current = currentFormData();
    current.items.push({
      description: "",
      sac: "",
      qty: 1,
      rate: 0,
      tax: 18,
    });
    applyQuote(current);
    markDirty();
  });

  elements.quoteList.addEventListener("click", (event) => {
    const card = event.target.closest(".quote-card");
    if (!card) {
      return;
    }
    loadRecord(Number(card.dataset.id)).catch(showError);
  });

  elements.searchInput.addEventListener("input", () => {
    renderList();
  });

  document.addEventListener("input", (event) => {
    if (event.target.classList.contains("field") || event.target.classList.contains("item-input")) {
      if (event.target.tagName === "TEXTAREA") {
        autoResizeTextarea(event.target);
      }
      if (event.target.id === "quoteDate") {
        const quoteDate = field("quoteDate").value;
        if (!field("validUntil").value || field("validUntil").value < quoteDate) {
          const base = new Date(`${quoteDate}T00:00:00`);
          base.setDate(base.getDate() + 60);
          field("validUntil").value = base.toISOString().slice(0, 10);
        }
      }
      refreshHeader();
      recalculateTotals();
      markDirty();
    }
  });

  elements.itemsTableBody.addEventListener("click", (event) => {
    if (!event.target.classList.contains("remove-btn")) {
      return;
    }
    const row = event.target.closest("tr");
    if (row) {
      row.remove();
      recalculateTotals();
      markDirty();
    }
  });

  window.addEventListener("beforeunload", (event) => {
    if (!state.dirty) {
      return;
    }
    event.preventDefault();
    event.returnValue = "";
  });

  window.addEventListener("beforeprint", () => {
    syncPrintFields();
  });

  if (elements.logoutBtn) {
    elements.logoutBtn.addEventListener("click", () => {
      logout().catch(showError);
    });
  }
}

function showError(error) {
  window.alert(error.message || String(error));
}

async function logout() {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } finally {
    window.location.href = "/login";
  }
}

async function init() {
  attachEvents();
  await loadBootstrap();
  if (state.records.length) {
    await loadRecord(state.records[0].id);
  } else {
    await createNewQuote();
  }
}

init().catch(showError);

