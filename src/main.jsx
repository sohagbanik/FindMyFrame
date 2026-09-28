import { StrictMode, useCallback, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import { ArrowIcon, LockIcon, SparkIcon } from './components/Icons'
import { MOCK_PHOTOS, SAMPLE_SELFIE } from './data/mockPhotos'
import { CollectionView, ProcessingView, ResultsView, SelfieView, Viewer } from './views/FlowViews'
import { ImageWithFallback } from './components/ImageWithFallback'

const landingImages = {
  crowd: 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=1200&q=85',
  dance: 'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?auto=format&fit=crop&w=900&q=85',
  friends: 'https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&w=900&q=85',
  concert: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=900&q=85',
}

function Wordmark() {
  return <span className="wordmark"><span className="wordmark-mark" aria-hidden="true"><i /><i /><i /><i /></span>findmyframe</span>
}

function LandingView({ onStart }) {
  const scrollToStory = () => document.querySelector('#how-it-works')?.scrollIntoView({ behavior: 'smooth' })

  return <main className="site-shell">
    <nav className="topbar" aria-label="Main navigation">
      <a className="wordmark" href="#top" aria-label="FindMyFrame home"><Wordmark /></a>
      <div className="topbar-links"><button className="text-button" type="button" onClick={scrollToStory}>How it works</button><a className="quiet-link" href="#privacy">Privacy</a></div>
      <button className="nav-cta" type="button" onClick={onStart}>Find my photos <ArrowIcon /></button>
    </nav>

    <section id="top" className="hero" aria-labelledby="hero-title">
      <div className="hero-copy">
        <p className="eyebrow"><span className="eyebrow-dot" /> for the moments you missed</p>
        <h1 id="hero-title">Find yourself<br /><em>in the crowd.</em></h1>
        <p className="hero-dek">Thousands of event photos.<br />One selfie. We&apos;ll find yours.</p>
        <div className="hero-actions"><button className="primary-button" type="button" onClick={onStart}>Find my photos <ArrowIcon /></button><span className="hero-note">No account needed</span></div>
        <div className="mini-proof" aria-label="FindMyFrame product promise"><span className="mini-avatars"><span style={{ backgroundImage: `url(${landingImages.friends})` }} /><span style={{ backgroundImage: `url(${landingImages.dance})` }} /><span style={{ backgroundImage: `url(${landingImages.concert})` }} /></span><span><strong>Made for being there.</strong><br />Not for scrolling forever.</span></div>
      </div>
      <div className="hero-art" aria-label="A collage of event photographs">
        <div className="art-caption art-caption-top"><span>FRAME 001</span><span>YOUR NIGHT, REMEMBERED</span></div>
        <div className="image-frame image-frame-main"><ImageWithFallback src={landingImages.crowd} alt="A crowd with hands raised at a live event" /><span className="image-stamp">01 / 04</span></div>
        <div className="image-frame image-frame-small"><ImageWithFallback src={landingImages.dance} alt="Friends dancing together at an outdoor event" /></div>
        <div className="art-card"><SparkIcon /><span>One selfie<br /><strong>every moment</strong></span></div>
        <div className="art-caption art-caption-bottom"><span>THE AFTERGLOW</span><span>↓ SCROLL TO BEGIN</span></div>
      </div>
    </section>

    <section id="how-it-works" className="story-section" aria-labelledby="story-title">
      <div className="section-intro"><p className="eyebrow"><span className="eyebrow-dot" /> three small steps</p><h2 id="story-title">You were there.<br /><em>Now find the proof.</em></h2></div>
      <div className="steps-grid">
        <article className="step-card step-card-dark"><span className="step-number">01</span><div className="step-art folder-art"><span /><span /><span /></div><h3>Bring the collection</h3><p>Upload an event folder or a ZIP. We&apos;ll take it from here.</p></article>
        <article className="step-card"><span className="step-number">02</span><div className="step-art selfie-art"><div className="selfie-sun" /><div className="selfie-head" /><div className="selfie-body" /></div><h3>Show us you</h3><p>One clear selfie is enough to start looking through the crowd.</p></article>
        <article className="step-card step-card-image"><span className="step-number">03</span><div className="step-art result-art"><ImageWithFallback src={landingImages.friends} alt="Friends smiling together" /><span className="result-ring" /></div><h3>Keep your moments</h3><p>Open, save, and share the photographs where you were part of it.</p></article>
      </div>
    </section>

    <section id="privacy" className="privacy-strip" aria-label="Privacy promise"><div className="privacy-icon"><LockIcon /></div><div><strong>Private by design.</strong> Your selfie is used to find your photos in this event — not to build a profile of you.</div><span className="privacy-side-note">FACE DATA / EVENT-SCOPED</span></section>
    <footer className="footer"><a className="wordmark" href="#top"><Wordmark /></a><span>For the moments worth finding.</span><span>© 2026</span></footer>
  </main>
}

function App() {
  const [screen, setScreen] = useState('landing')
  const [collection, setCollection] = useState([])
  const [selfie, setSelfie] = useState(null)
  const [viewerIndex, setViewerIndex] = useState(null)

  const start = () => setScreen('collection')
  const reset = () => { setScreen('landing'); setCollection([]); setSelfie(null); setViewerIndex(null) }
  const appendCollection = (incoming) => setCollection((current) => [...current, ...incoming.filter((file) => !current.some((existing) => existing.name === file.name && existing.size === file.size))])
  const removeCollectionFile = (id) => setCollection((current) => {
    const file = current.find((item) => item.id === id)
    if (file?.url?.startsWith('blob:')) URL.revokeObjectURL(file.url)
    if (file?.preview?.startsWith('blob:')) URL.revokeObjectURL(file.preview)
    return current.filter((item) => item.id !== id)
  })
  const clearCollection = () => { collection.forEach((file) => { if (file.url?.startsWith('blob:')) URL.revokeObjectURL(file.url); if (file.preview?.startsWith('blob:')) URL.revokeObjectURL(file.preview) }); setCollection([]) }
  const useSampleCollection = () => setCollection(MOCK_PHOTOS.slice(0, 5).map((photo, index) => ({ id: `sample-${photo.id}`, name: `event-frame-${index + 1}.jpg`, size: 1800000 + index * 170000, url: photo.src, preview: photo.src, isSample: true })))
  const useSampleSelfie = () => setSelfie({ ...SAMPLE_SELFIE, id: 'sample-selfie' })
  const finishProcessing = useCallback(() => setScreen('results'), [])

  if (screen === 'landing') return <LandingView onStart={start} />
  if (screen === 'collection') return <CollectionView files={collection} onFiles={appendCollection} onRemove={removeCollectionFile} onClear={clearCollection} onContinue={() => setScreen('selfie')} onSample={useSampleCollection} onBack={reset} onHome={reset} />
  if (screen === 'selfie') return <SelfieView selfie={selfie} onSelfie={setSelfie} onContinue={() => setScreen('processing')} onBack={() => setScreen('collection')} onHome={reset} onSample={useSampleSelfie} />
  if (screen === 'processing') return <ProcessingView onComplete={finishProcessing} onBack={() => setScreen('collection')} onHome={() => setScreen('collection')} />
  if (screen === 'results') return <>
    <ResultsView onOpen={(photo) => setViewerIndex(MOCK_PHOTOS.findIndex((item) => item.id === photo.id))} onStartOver={() => setScreen('collection')} onHome={reset} collectionCount={`${collection.length || 5} photos`} />
    {viewerIndex !== null && <Viewer photo={MOCK_PHOTOS[viewerIndex]} onClose={() => setViewerIndex(null)} onPrevious={() => setViewerIndex((index) => (index - 1 + MOCK_PHOTOS.length) % MOCK_PHOTOS.length)} onNext={() => setViewerIndex((index) => (index + 1) % MOCK_PHOTOS.length)} />}
  </>
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)
