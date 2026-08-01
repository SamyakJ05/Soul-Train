document.addEventListener("DOMContentLoaded", () => {
  const builder = document.querySelector("[data-builder]");
  if (builder) {
    const setMode = (mode) => {
      builder.querySelectorAll("[data-mode-button]").forEach((button) => {
        const active = button.dataset.modeButton === mode;
        button.setAttribute("aria-selected", String(active));
        button.tabIndex = active ? 0 : -1;
      });
      builder.querySelectorAll("[data-mode-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.modePanel !== mode;
      });
      history.replaceState({}, "", `?mode=${mode}`);
    };
    builder.querySelectorAll("[data-mode-button]").forEach((button) => {
      button.addEventListener("click", () => setMode(button.dataset.modeButton));
    });
    setMode(builder.dataset.activeMode === "library" ? "library" : "mood");
  }
  document.querySelectorAll("input[type=range]").forEach((input) => {
    const output = document.querySelector(`[data-output-for="${input.id}"]`);
    const update = () => { if (output) output.value = input.id === "discovery" ? `${input.value}%` : input.value; };
    input.addEventListener("input", update); update();
  });
  window.setTimeout(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()), 6000);
});
