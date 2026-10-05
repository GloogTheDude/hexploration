const AUTH_ERROR = "AUTHENTICATION_EXPIRED";

let currentUser = null;
let resolveReady;
export const authReady = new Promise(resolve => { resolveReady = resolve; });

function overlay() {
  let root = document.querySelector("#auth-gate");
  if (root) return root;
  root = document.createElement("section");
  root.id = "auth-gate";
  root.innerHTML = `<div class="auth-card" role="dialog" aria-labelledby="auth-title">
    <div class="auth-eyebrow">HEXPLORATION</div>
    <h1 id="auth-title">Connexion</h1>
    <p id="auth-intro" class="auth-muted">Connecte-toi pour accéder à ton espace de jeu.</p>
    <form id="auth-login-form">
      <label>Nom d’utilisateur ou email<input id="auth-identity" name="username_or_email" autocomplete="username" required></label>
      <label>Mot de passe<input id="auth-password" name="password" type="password" autocomplete="current-password" required></label>
      <button type="submit">Se connecter</button>
      <p id="auth-message" class="auth-error" role="alert"></p>
      <button id="auth-show-register" class="auth-link" type="button">Créer un compte</button>
    </form>
    <form id="auth-register-form" hidden>
      <label>Nom d’utilisateur<input id="auth-register-username" name="username" autocomplete="username" minlength="2" maxlength="80" required></label>
      <label>Email<input id="auth-register-email" name="email" type="email" autocomplete="email" required></label>
      <label>Mot de passe<input id="auth-register-password" name="password" type="password" autocomplete="new-password" minlength="8" maxlength="256" required></label>
      <button type="submit">Créer mon compte</button>
      <p id="auth-register-message" class="auth-error" role="alert"></p>
      <button id="auth-show-login" class="auth-link" type="button">J’ai déjà un compte</button>
    </form>
  </div>`;
  document.body.append(root);
  const loginForm = root.querySelector("#auth-login-form");
  const registerForm = root.querySelector("#auth-register-form");
  const title = root.querySelector("#auth-title");
  const intro = root.querySelector("#auth-intro");
  const showLogin = (message = "") => {
    title.textContent = "Connexion";
    intro.textContent = "Connecte-toi pour accéder à ton espace de jeu.";
    loginForm.hidden = false;
    registerForm.hidden = true;
    root.querySelector("#auth-message").textContent = message;
  };
  const showRegister = () => {
    title.textContent = "Créer un compte";
    intro.textContent = "Crée ton compte pour commencer à jouer.";
    loginForm.hidden = true;
    registerForm.hidden = false;
    root.querySelector("#auth-register-message").textContent = "";
  };
  root.querySelector("#auth-show-register").addEventListener("click", showRegister);
  root.querySelector("#auth-show-login").addEventListener("click", () => showLogin());
  loginForm.addEventListener("submit", async event => {
    event.preventDefault();
    const message = root.querySelector("#auth-message");
    const button = loginForm.querySelector("button[type=submit]");
    button.disabled = true;
    message.textContent = "Connexion…";
    try {
      const values = Object.fromEntries(new FormData(loginForm));
      await loginWithCredentials(values.username_or_email, values.password);
      loginForm.reset();
      root.classList.remove("visible");
    } catch (_) {
      message.textContent = "Identifiants invalides.";
    } finally {
      button.disabled = false;
    }
  });
  registerForm.addEventListener("submit", async event => {
    event.preventDefault();
    const message = root.querySelector("#auth-register-message");
    const button = registerForm.querySelector("button[type=submit]");
    const values = Object.fromEntries(new FormData(registerForm));
    button.disabled = true;
    message.textContent = "Création du compte…";
    try {
      const response = await fetch("/api/users", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username: values.username, email: values.email, password: values.password}),
      });
      if (!response.ok) {
        let detail = "Impossible de créer le compte.";
        if (response.status === 409) detail = "Ce nom d’utilisateur ou cet email est déjà utilisé.";
        else if (response.status === 422) detail = "Vérifie les informations saisies.";
        throw new Error(detail);
      }
      const password = values.password;
      registerForm.reset();
      try {
        await loginWithCredentials(values.username, password);
        root.classList.remove("visible");
      } catch (_) {
        showLogin("Compte créé. Connecte-toi pour continuer.");
      }
    } catch (error) {
      message.textContent = error.message || "Impossible de créer le compte.";
    } finally {
      button.disabled = false;
    }
  });
  return root;
}

function showLogin(message = "") {
  const root = overlay();
  root.classList.add("visible");
  root.querySelector("#auth-message").textContent = message;
}

async function establishSession() {
  const response = await fetch("/auth/me", {cache: "no-store"});
  if (!response.ok) throw new Error("Session invalide");
  currentUser = await response.json();
  document.body.dataset.authenticated = "true";
  let bar = document.querySelector("#auth-session-bar");
  if (!bar) { bar = document.createElement("div"); bar.id = "auth-session-bar"; document.body.append(bar); }
  bar.innerHTML = `<span>${String(currentUser.username || currentUser.email)}</span><button type="button">Se déconnecter</button>`;
  bar.querySelector("button").addEventListener("click", logout);
  resolveReady(currentUser);
  window.dispatchEvent(new CustomEvent("hex-authenticated", {detail: currentUser}));
  return currentUser;
}

async function loginWithCredentials(usernameOrEmail, password) {
  const response = await fetch("/auth/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username_or_email: usernameOrEmail, password}),
  });
  if (!response.ok) throw new Error("Invalid credentials");
  return establishSession();
}

function expireSession() {
  if (!currentUser) return;
  currentUser = null;
  delete document.body.dataset.authenticated;
  showLogin("Ta session a expiré. Connecte-toi à nouveau.");
  window.dispatchEvent(new Event("hex-auth-expired"));
}

export function getCurrentUser() { return currentUser; }

export async function authFetch(input, options = {}) {
  const response = await fetch(input, options);
  if (response.status === 401) {
    expireSession();
    const error = new Error(AUTH_ERROR);
    error.code = AUTH_ERROR;
    throw error;
  }
  return response;
}

export async function logout() {
  try { await fetch("/auth/logout", {method: "POST"}); } finally {
    currentUser = null;
    delete document.body.dataset.authenticated;
    document.querySelector("#auth-session-bar")?.remove();
    showLogin();
    window.dispatchEvent(new Event("hex-logout"));
  }
}

async function bootstrap() {
  overlay();
  try {
    await establishSession();
    overlay().classList.remove("visible");
  } catch (error) {
    if (error?.message === "Session invalide") showLogin();
    else showLogin("Impossible de vérifier la session. Réessaie.");
  }
}

bootstrap();
