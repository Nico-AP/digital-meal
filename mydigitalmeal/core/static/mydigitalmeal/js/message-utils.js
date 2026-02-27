function removeAfter(element, seconds, fadeDuration = 300) {
  setTimeout(() => {
    element.style.transition = `opacity ${fadeDuration}ms ease`
    element.style.opacity = '0'
    setTimeout(() => element.remove(), fadeDuration)
  }, seconds * 1000)
}

document.addEventListener('DOMContentLoaded', () => {
  const msg = document.querySelector('.mdm-alert')
  if (msg) removeAfter(msg, 3)
})
