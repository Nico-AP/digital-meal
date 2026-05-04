/**
 * report_animations.js
 *
 * Custom animation helpers for the report slideshow.
 * These animations are triggered alongside the SVGator animations
 * and are controlled by the SlideShow state machine in report_handler.js.
 */

/**
 * Waits for a DOM element with the given ID to exist, then calls the callback.
 * If the element already exists, the callback is called immediately.
 * Otherwise, a MutationObserver watches the DOM until the element appears.
 *
 * @param {string} id - The ID of the element to wait for.
 * @param {function} callback - Function to call once the element is found, receives the element as argument.
 */
function waitForElement(id, callback) {
  const el = document.getElementById(id);
  if (el) {
    callback(el);
    return;
  }

  const observer = new MutationObserver(() => {
    const el = document.getElementById(id);
    if (el) {
      observer.disconnect();
      callback(el);
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
}


// ── Slide 08: Top Video ───────────────────────────────────────────

waitForElement("slide-8-content-caption", (el) => {
  const reportSlide = el.closest(".report-slide");
  const introSlide = reportSlide.querySelector(".slide-intro");
  const observer = new MutationObserver(() => {
    if (introSlide.classList.contains("is-playing")) {
      el.classList.add('wipe-down');
    }
  });

  observer.observe(introSlide, { attributeFilter: ["class"] });
});

waitForElement("slide-8-top-video-img", (el) => {
  const reportSlide = el.closest(".report-slide");
  const introSlide = reportSlide.querySelector(".slide-intro");
  const observer = new MutationObserver(() => {
    if (introSlide.classList.contains("is-playing")) {
      el.classList.add('zoom-in');
    }
  });

  observer.observe(introSlide, { attributeFilter: ["class"] });
});


// ── Slide 11: Usage Image Part 1 ───────────────────────────────────────────

waitForElement("slide-11-intro-img", (el) => {
  el.style.maxHeight = "0px";
  el.style.overflow = "hidden";
  el.style.transition = `max-height 2.2s cubic-bezier(0.39, 0.1, 0.46, 0.98)`;

  const introSlide = el.closest(".slide-intro");
  const observer = new MutationObserver(() => {
    if (introSlide.classList.contains("is-playing")) {
      setTimeout(() => {
        el.offsetHeight; // force reflow
        el.style.maxHeight = "1000px";
        observer.disconnect(); // only trigger once
      }, 500);
    }
  });

  observer.observe(introSlide, { attributeFilter: ["class"] });
});

waitForElement("slide-11-outro-caption", (el) => {
  el.style.maxHeight = "1000px";
  el.style.overflow = "hidden";
  el.style.transition = `max-height 2s cubic-bezier(0.15, 0, 0.4, 1)`;

  const outroSlide = el.closest(".slide-outro");

  const observer = new MutationObserver(() => {
    if (outroSlide.classList.contains("is-playing")) {
      el.offsetHeight; // force reflow
      el.style.maxHeight = "0px";
      observer.disconnect(); // only trigger once
    }
  });

  observer.observe(outroSlide, { attributeFilter: ["class"] });
});

// ── Slide 12: Usage Image Part 2 ───────────────────────────────────────────

waitForElement("slide-12-intro-caption", (el) => {
  el.style.maxHeight = "0px";
  el.style.overflow = "hidden";
  el.style.transition = `max-height 2s cubic-bezier(0.15, 0, 0.4, 1)`;

  const introSlide = el.closest(".slide-intro");
  const observer = new MutationObserver(() => {
    if (introSlide.classList.contains("is-playing")) {
      setTimeout(() => {
        el.offsetHeight; // force reflow
        el.style.maxHeight = "1000px";
        observer.disconnect(); // only trigger once
      }, 500);
    }
  });

  observer.observe(introSlide, { attributeFilter: ["class"] });
});

waitForElement("slide-12-outro-img", (el) => {
  el.style.maxHeight = "1000px";
  el.style.overflow = "hidden";
  el.style.transition = `max-height 1s cubic-bezier(0.15, 0, 0.4, 1)`;

  const introSlide = el.closest(".slide-outro");
  const observer = new MutationObserver(() => {
    if (introSlide.classList.contains("is-playing")) {
      setTimeout(() => {
        el.offsetHeight; // force reflow
        el.style.maxHeight = "0";
        observer.disconnect(); // only trigger once
      }, 100);
    }
  });

  observer.observe(introSlide, { attributeFilter: ["class"] });
});

waitForElement("slide-12-outro-caption", (el) => {
  el.style.maxHeight = "1000px";
  el.style.overflow = "hidden";
  el.style.transition = `max-height 1s cubic-bezier(0.15, 0, 0.4, 1)`;

  const introSlide = el.closest(".slide-outro");
  const observer = new MutationObserver(() => {
    if (introSlide.classList.contains("is-playing")) {
      setTimeout(() => {
        el.offsetHeight; // force reflow
        el.style.maxHeight = "0";
        observer.disconnect(); // only trigger once
      }, 100);
    }
  });

  observer.observe(introSlide, { attributeFilter: ["class"] });
});

waitForElement("slide-12-content-caption", (el) => {
  el.style.opacity = "0.0001";
  el.style.overflow = "hidden";
  el.style.transition = `opacity 1s cubic-bezier(0.15, 0, 0.4, 1)`;

  const reportSlide = el.closest(".report-slide");
  const introSlide = reportSlide.querySelector(".slide-intro");
  const observer = new MutationObserver(() => {
    if (introSlide.classList.contains("is-playing")) {
      let duration = introSlide.dataset.duration;
      if (duration) {
        duration = parseInt(duration);
      } else {
        duration = 0;
      }

      setTimeout(() => {
        el.offsetHeight; // force reflow
        el.style.opacity = "1";
        observer.disconnect(); // only trigger once
      }, duration + 1000);
    }
  });

  observer.observe(introSlide, { attributeFilter: ["class"] });
});


// ── Slide 13: Session Length ───────────────────────────────────────────

waitForElement("slide-13-content-caption", (el) => {
  const reportSlide = el.closest(".report-slide");
  const introSlide = reportSlide.querySelector(".slide-intro");
  const observer = new MutationObserver(() => {
    if (introSlide.classList.contains("is-playing")) {
      el.classList.add('wipe-in');
      observer.disconnect(); // only trigger once
    }
  });

  observer.observe(introSlide, { attributeFilter: ["class"] });
});

waitForElement("slide-13-outro-caption", (el) => {
  const outroSlide = el.closest(".slide-outro");
  const observer = new MutationObserver(() => {
    if (outroSlide.classList.contains("is-playing")) {
      el.classList.add('wipe-out');
      observer.disconnect(); // only trigger once
    }
  });

  observer.observe(outroSlide, { attributeFilter: ["class"] });
});
