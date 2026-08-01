document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("input[type=range]").forEach((input) => {
    const output = document.querySelector(`[data-output-for="${input.id}"]`);
    const update = () => {
      if (output) {
        if (input.id === "discovery") output.value = input.value < 25 ? "Precise" : input.value < 65 ? "Balanced" : "Adventurous";
        else output.value = input.value;
      }
      if (input.id === "track-count") {
        const minutes = Number(input.value) * 3.5;
        const duration = document.querySelector("[data-duration]");
        if (duration) duration.textContent = `${Math.floor(minutes / 60)} hr ${Math.round(minutes % 60)} min`;
      }
    };
    input.addEventListener("input", update); update();
  });
  const start = document.querySelector("#start-mood");
  const end = document.querySelector("#end-mood");
  if (start && end) {
    const descriptions = {peaceful:"still and spacious",cozy:"warm and easy",dreamy:"soft and floating",reflective:"quiet and inward",moody:"shadowy and textured",focused:"clear and steady",romantic:"warm and open",joyful:"bright and buoyant",confident:"bold and assured",energized:"bright and high-energy",cathartic:"intense and releasing",euphoric:"all-out and celebratory"};
    const updateJourney = () => {
      document.querySelector("[data-start-label]").textContent = start.options[start.selectedIndex].text;
      document.querySelector("[data-end-label]").textContent = end.options[end.selectedIndex].text;
      document.querySelector("[data-journey-copy]").textContent = `A journey from ${descriptions[start.value]} to ${descriptions[end.value]}.`;
      end.setCustomValidity(start.value === end.value ? "Choose a different destination mood." : "");
    };
    start.addEventListener("change", updateJourney); end.addEventListener("change", updateJourney); updateJourney();
  }
  window.setTimeout(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()), 6000);
});
