/* Connexion et inscription : on garde le jeton, puis on revient à la page demandée. */
(() => {
  const next = () => {
    const target = new URLSearchParams(location.search).get("suite") || "/";
    return target.startsWith("/") && !target.startsWith("//") ? target : "/";
  };
  if (Nova.store.get()) location.replace(next());

  function bind(form, path, fields) {
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const button = form.querySelector('[type="submit"]');
      const body = Object.fromEntries(fields.map((f) => [f, form.elements[f].value]));
      Nova.busy(button, true);
      try {
        const data = await Nova.api(path, { method: "POST", body, auth: false });
        Nova.store.set(data.token);
        location.href = next();
      } catch (error) {
        Nova.showErrors(form, error);
        Nova.busy(button, false);
      }
    });
  }

  bind(document.getElementById("login-form"), "/api/auth/login", ["email", "password"]);
  bind(document.getElementById("register-form"), "/api/auth/register", ["name", "email", "service", "password"]);

  document.addEventListener("click", (e) => {
    const demo = e.target.closest("[data-demo]");
    if (!demo) return;
    const form = document.getElementById("login-form");
    form.elements.email.value = demo.dataset.demo;
    form.elements.password.value = "novaservices";
    form.requestSubmit();
  });
})();
