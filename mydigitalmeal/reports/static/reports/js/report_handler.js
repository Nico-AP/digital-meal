/**
 * report_handler.js
 *
 * Drives the report slideshow. Manages slide state (intro → visible → outro),
 * user input (keyboard / swipe), and SVG animation resets.
 *
 * Slides are expected to have the following structure:
 *   <div class="report-slide" data-slide="0"
 *        data-autoplay="3000"         (optional) auto-advance from visible after Xms
 *        data-intro-hide-delay="1000" (optional) fade out intro after Xms once visible
 *        data-content-hide-delay="500"(optional) fade out content Xms after outro starts
 *   >
 *     <div class="slide-intro"  data-duration="2000">...</div>
 *     <div class="slide-content">...</div>
 *     <div class="slide-outro"  data-duration="1000">...</div>
 *   </div>
 *
 * The slide template/component is located at mydigitalmeal/reports/templates/cotton/report_slide.html.
 * This component uses django-cotton.
 */


document.addEventListener('htmx:afterSettle', () => {
  requestAnimationFrame(() => {
    const container = document.getElementById('report-container');
    if (container && !container._slideshow) {
      container._slideshow = new SlideShow(container);
    }
  });
});

class SlideShow {
  constructor(container) {
    this.container = container;
    this.slides = [...container.querySelectorAll('.report-slide')];
    this.current = 0;
    this.state = 'idle'; // idle | intro | visible | outro
    this.generation = 0; // incremented on every navigation to invalidate stale callbacks
    this.isLastSlide = false;

    if (this.slides.length === 0) return;

    this.bindInput();
    this.goToSlide(0);
  }

  // ── Navigation ─────────────────────────────────────────────────

  goToSlide(index) {
    if (index < 0) return;
    if (index >= this.slides.length) {
      this.onFinished();
      return;
    }

    this.generation++;

    // Clean up previous slide
    this.slides.forEach(s => {
      s.classList.remove('is-active');
      delete s.dataset.state;
      const content = s.querySelector('.slide-content');
      if (content) content.style.opacity = '';
      const intro = s.querySelector('.slide-intro');
      if (intro) intro.style.opacity = '';
    });

    this.slides[index].classList.add('is-active');
    this.current = index;
    this.isLastSlide = index === this.slides.length - 1;

    this.setState('intro');
  }

  goBack() {
    if (this.current === 0) return;
    this.goToSlide(this.current - 1);
  }

  restart() {
    this.goToSlide(0);
  }

  // ── State machine ──────────────────────────────────────────────

  setState(state) {
    const slide = this.slides[this.current];
    const gen = this.generation;
    this.state = state;
    slide.dataset.state = state;

    if (state === 'intro') {
      const el = slide.querySelector('.slide-intro');
      el.classList.remove('is-playing');
      resetSvgAnimation(el)

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          // Double rAF ensures browser has processed the clone

          if (this.generation !== gen) return;
          el.classList.add('is-playing');

          const duration = el.dataset.duration;
          if (duration) {
            setTimeout(() => {
              if (this.generation !== gen) return;
              if (this.state === 'intro') this.setState('visible');
            }, parseInt(duration));
          } else {
            const onEnd = (e) => {
              if (e.target !== el.querySelector('svg')) return;
              el.removeEventListener('animationend', onEnd);
              if (this.generation !== gen) return;
              if (this.state === 'intro') this.setState('visible');
            };
            el.addEventListener('animationend', onEnd);
          }
        });
      });
    }

    if (state === 'visible') {
      resetSvgAnimation(slide.querySelector('.slide-content'));

      const introHideDelay = slide.dataset.introHideDelay;
      if (introHideDelay) {
        setTimeout(() => {
          if (this.generation !== gen) return;
          slide.querySelector('.slide-intro').style.opacity = '0';
        }, parseInt(introHideDelay));
      }

      const autoplay = slide.dataset.autoplay;
      if (autoplay) {
        setTimeout(() => {
          if (this.generation !== gen) return;
          if (this.state === 'visible') this.setState('outro');
        }, parseInt(autoplay));
      }
    }

    if (state === 'outro') {
      const el = slide.querySelector('.slide-outro');
      el.classList.remove('is-playing');
      resetSvgAnimation(el);

      const contentHideDelay = slide.dataset.contentHideDelay;
      if (contentHideDelay) {
        setTimeout(() => {
          if (this.generation !== gen) return;
          slide.querySelector('.slide-content').style.opacity = '0';
        }, parseInt(contentHideDelay));
      }

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          // Double rAF ensures browser has processed the clone

          if (this.generation !== gen) return;
          el.classList.add('is-playing');

          const duration = el.dataset.duration;
          if (duration) {
            setTimeout(() => {
              if (this.generation !== gen) return;
              if (this.state === 'outro') {
                this.goToSlide(this.current + 1);
              }
            }, parseInt(duration));
          } else {
            const onEnd = (e) => {
              if (e.target !== el.querySelector('svg')) return;
              el.removeEventListener('animationend', onEnd);
              if (this.generation !== gen) return; // stale, abort
              if (this.state === 'outro') this.goToSlide(this.current + 1);
            };
            el.addEventListener('animationend', onEnd);
          }
        });
      });
    }
  }

  // ── User input ─────────────────────────────────────────────────

  advance() {
    if (this.isLastSlide) return;

    if (this.state === 'intro') {
      // Skip intro
      const el = this.slides[this.current].querySelector('.slide-intro');
      el.classList.remove('is-playing');
      this.setState('visible');
      return;
    }
    if (this.state === 'visible') {
      this.setState('outro');
    }
    // 'outro' is unskippable — let it finish
  }

  bindInput() {
    // Keyboard
    this._onKeyDown = (e) => {
      if (['ArrowDown', ' '].includes(e.key)) {
        e.preventDefault();
        this.advance();
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.goBack();
      }
    };
    document.addEventListener('keydown', this._onKeyDown);

    // Swipe up
    let touchStartY = null;
    this.container.addEventListener('touchstart', (e) => {
      touchStartY = e.touches[0].clientY;
    }, {passive: true});

    this.container.addEventListener('touchend', (e) => {
      if (touchStartY === null) return;
      const delta = touchStartY - e.changedTouches[0].clientY;
      if (delta > 50) this.advance();
      if (delta < -50) this.goBack();
      touchStartY = null;
    }, {passive: true});
  }

  // ── End of slideshow ───────────────────────────────────────────

  onFinished() {
    this.state = 'idle';
    document.removeEventListener('keydown', this._onKeyDown);
  }
}

// Clone svg to reset its animation state
function resetSvgAnimation(el) {
  if (!el) return;
  el.querySelectorAll('svg').forEach(svg => {
    const uid = Math.random().toString(36).slice(2, 8);
    let html = svg.outerHTML;
    const idMatches = html.matchAll(/\bid="([^"]+)"/g);
    const ids = [...idMatches].map(m => m[1]);

    // Replace every occurrence of each ID (in attributes AND in style block)
    ids.forEach(id => {
      html = html.split(id).join(id + '_' + uid);
    });

    // Inject the modified SVG
    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    svg.replaceWith(wrapper.firstElementChild);
  });
}
