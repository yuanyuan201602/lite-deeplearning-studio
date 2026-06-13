"use strict";

/* Global tutorial drawer — open/close, scrim, Esc, body scroll lock, TOC jump. */

(function () {
  const openButton = document.getElementById("tutorial-open");
  const drawer = document.getElementById("tutorial-drawer");
  const scrim = document.getElementById("tutorial-scrim");
  const closeButton = document.getElementById("tutorial-close");
  if (!openButton || !drawer || !scrim || !closeButton) return;

  const body = drawer.querySelector(".tutorial-body");

  function openDrawer() {
    drawer.hidden = false;
    scrim.hidden = false;
    // Next frame so the transition runs from the hidden start state.
    requestAnimationFrame(() => {
      drawer.classList.add("is-open");
      scrim.classList.add("is-open");
    });
    document.body.classList.add("tutorial-locked");
    closeButton.focus();
  }

  function closeDrawer() {
    drawer.classList.remove("is-open");
    scrim.classList.remove("is-open");
    document.body.classList.remove("tutorial-locked");
    const onEnd = () => {
      drawer.hidden = true;
      scrim.hidden = true;
      drawer.removeEventListener("transitionend", onEnd);
    };
    drawer.addEventListener("transitionend", onEnd);
    openButton.focus();
  }

  openButton.addEventListener("click", openDrawer);
  closeButton.addEventListener("click", closeDrawer);
  scrim.addEventListener("click", closeDrawer);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !drawer.hidden) closeDrawer();
  });

  // TOC links scroll within the drawer body, not the whole page.
  drawer.querySelectorAll(".tutorial-toc a").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const target = drawer.querySelector(link.getAttribute("href"));
      if (target && body) {
        body.scrollTo({ top: target.offsetTop - body.offsetTop - 8, behavior: "smooth" });
      }
    });
  });
})();
