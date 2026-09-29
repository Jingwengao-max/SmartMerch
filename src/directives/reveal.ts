import type { Directive } from 'vue'

/**
 * v-reveal —— 元素进入视口时淡入上移。
 * 用法：v-reveal 或 v-reveal="80"（80 = 过渡延迟毫秒，用于交错出现）。
 */
const reveal: Directive<HTMLElement, number | undefined> = {
  mounted(el, binding) {
    el.classList.add('reveal')
    if (typeof binding.value === 'number') {
      el.style.transitionDelay = `${binding.value}ms`
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            el.classList.add('is-visible')
            io.unobserve(el)
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
    )
    io.observe(el)
  },
}

export default reveal
