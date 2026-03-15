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

const setupNotice = document.getElementById("setupNotice");
const loginForm = document.getElementById("loginForm");
const setupForm = document.getElementById("setupForm");
const loginUsername = document.getElementById("loginUsername");
const loginPassword = document.getElementById("loginPassword");
const setupUsername = document.getElementById("setupUsername");
const setupPassword = document.getElementById("setupPassword");

function showError(error) {
  window.alert(error.message || String(error));
}

async function bootstrap() {
  const data = await api("/api/auth/bootstrap");
  if (!data.configured) {
    setupNotice.classList.remove("hidden");
    setupForm.classList.remove("hidden");
  }
}

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({
      username: loginUsername.value.trim(),
      password: loginPassword.value,
    }),
  })
    .then(() => {
      window.location.href = "/home";
    })
    .catch(showError);
});

setupForm.addEventListener("submit", (event) => {
  event.preventDefault();
  api("/api/auth/setup", {
    method: "POST",
    body: JSON.stringify({
      username: setupUsername.value.trim(),
      password: setupPassword.value,
    }),
  })
    .then(() => {
      setupNotice.classList.add("hidden");
      setupForm.classList.add("hidden");
      window.alert("Admin user created. Please sign in.");
    })
    .catch(showError);
});

bootstrap().catch(showError);
