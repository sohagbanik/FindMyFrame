import { useState } from 'react'

const FALLBACK = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"%3E%3Crect width="800" height="600" fill="%232e302c"/%3E%3Ccircle cx="400" cy="250" r="80" fill="%23d55632" opacity=".8"/%3E%3Cpath d="M180 600c50-160 390-160 440 0" fill="%23f1eee8" opacity=".9"/%3E%3C/svg%3E'

export function ImageWithFallback({ src, alt, className, ...props }) {
  const [source, setSource] = useState(src)

  return <img className={className} src={source} alt={alt} onError={() => setSource(FALLBACK)} {...props} />
}
