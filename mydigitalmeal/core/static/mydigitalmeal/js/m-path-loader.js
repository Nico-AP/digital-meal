const path = document.getElementById('mStrokePath');
const len = path.getTotalLength();

// Inject the keyframe animation dynamically using the real path length
const style = document.createElement('style');
style.textContent = `
    @keyframes drawLoop {
      0%   { stroke-dashoffset: ${len};   opacity: 1; }
      60%  { stroke-dashoffset: 0;        opacity: 1; }
      75%  { stroke-dashoffset: 0;        opacity: 1; }
      100% { stroke-dashoffset: ${-len};  opacity: 0.2; }
    }

    .draw-path {
      stroke-dasharray: ${len};
      stroke-dashoffset: ${len};
      animation: drawLoop 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }
  `;
document.head.appendChild(style);
