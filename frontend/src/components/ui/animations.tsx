import { useEffect, useRef, useState } from 'react'
import { cn } from '../../lib/utils'

interface FadeContentProps {
  children: React.ReactNode
  delay?: number
  duration?: number
  direction?: 'up' | 'down' | 'left' | 'right' | 'none'
  className?: string
  threshold?: number
  once?: boolean
}

export function FadeContent({
  children,
  delay = 0,
  duration = 0.5,
  direction = 'up',
  className = '',
  threshold = 0.1,
  once = true,
}: FadeContentProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
          if (once) observer.disconnect()
        } else if (!once) {
          setIsVisible(false)
        }
      },
      { threshold }
    )

    observer.observe(element)
    return () => observer.disconnect()
  }, [threshold, once])

  const getTransform = () => {
    if (!isVisible) {
      switch (direction) {
        case 'up': return 'translateY(20px)'
        case 'down': return 'translateY(-20px)'
        case 'left': return 'translateX(20px)'
        case 'right': return 'translateX(-20px)'
        default: return 'none'
      }
    }
    return 'none'
  }

  return (
    <div
      ref={ref}
      className={cn(className)}
      style={{
        opacity: isVisible ? 1 : 0,
        transform: getTransform(),
        transition: `opacity ${duration}s ease-out ${delay}s, transform ${duration}s ease-out ${delay}s`,
      }}
    >
      {children}
    </div>
  )
}

interface StaggeredFadeInProps {
  children: React.ReactNode[]
  staggerDelay?: number
  duration?: number
  direction?: 'up' | 'down' | 'left' | 'right' | 'none'
  className?: string
  itemClassName?: string
}

export function StaggeredFadeIn({
  children,
  staggerDelay = 0.1,
  duration = 0.5,
  direction = 'up',
  className = '',
  itemClassName = '',
}: StaggeredFadeInProps) {
  return (
    <div className={cn(className)}>
      {children.map((child, index) => (
        <FadeContent
          key={index}
          delay={index * staggerDelay}
          duration={duration}
          direction={direction}
          className={itemClassName}
        >
          {child}
        </FadeContent>
      ))}
    </div>
  )
}

interface AnimatedNumberProps {
  value: number
  duration?: number
  className?: string
  formatFn?: (n: number) => string
}

export function AnimatedNumber({
  value,
  duration = 1000,
  className = '',
  formatFn = (n) => n.toString(),
}: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(0)
  const startTime = useRef<number | null>(null)
  const startValue = useRef(0)

  useEffect(() => {
    startValue.current = displayValue
    startTime.current = null

    const animate = (timestamp: number) => {
      if (!startTime.current) startTime.current = timestamp
      const progress = Math.min((timestamp - startTime.current) / duration, 1)

      // Easing function
      const easeOutQuart = 1 - Math.pow(1 - progress, 4)
      const currentValue = startValue.current + (value - startValue.current) * easeOutQuart

      setDisplayValue(Math.round(currentValue))

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)
  }, [value, duration])

  return (
    <span className={cn(className)}>
      {formatFn(displayValue)}
    </span>
  )
}

interface SlideInProps {
  children: React.ReactNode
  direction?: 'left' | 'right' | 'up' | 'down'
  delay?: number
  duration?: number
  className?: string
}

export function SlideIn({
  children,
  direction = 'right',
  delay = 0,
  duration = 0.3,
  className = '',
}: SlideInProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay * 1000)
    return () => clearTimeout(timer)
  }, [delay])

  const getTransform = () => {
    if (!isVisible) {
      switch (direction) {
        case 'left': return 'translateX(100%)'
        case 'right': return 'translateX(-100%)'
        case 'up': return 'translateY(100%)'
        case 'down': return 'translateY(-100%)'
      }
    }
    return 'none'
  }

  return (
    <div
      className={cn(className)}
      style={{
        transform: getTransform(),
        opacity: isVisible ? 1 : 0,
        transition: `transform ${duration}s ease-out, opacity ${duration}s ease-out`,
      }}
    >
      {children}
    </div>
  )
}