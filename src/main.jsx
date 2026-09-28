import { StrictMode, useCallback, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import { ArrowIcon, LockIcon, SparkIcon } from './components/Icons'
import { MOCK_PHOTOS, SAMPLE_SELFIE } from './data/mockPhotos'
import { CollectionView, ProcessingView, ResultsView, SelfieView, Viewer } from './views/FlowViews'
import { ImageWithFallback } from './components/ImageWithFallback'
import { API_BASE_URL } from './api/client'
import { createCollection, importGoogleDriveFolder, matchCollection, processCollectionFaces, processCollectionSelfie, uploadCollectionPhotos, uploadCollectionSelfie } from './api/collections'

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
  const [collectionId, setCollectionId] = useState(null)
  const [selfie, setSelfie] = useState(null)
  const [viewerIndex, setViewerIndex] = useState(null)
  const [collectionUpload, setCollectionUpload] = useState({ loading: false, error: '' })
  const [selfieUpload, setSelfieUpload] = useState({ loading: false, error: '' })
  const [isDemoSession, setIsDemoSession] = useState(true)
  const [realMatches, setRealMatches] = useState([])
  const [matchError, setMatchError] = useState('')
  const [driveImport, setDriveImport] = useState({ loading: false, error: '', summary: null })

  const start = () => setScreen('collection')
  const releaseCollectionAssets = (items) => items.forEach((file) => { if (file.url?.startsWith('blob:')) URL.revokeObjectURL(file.url); if (file.preview?.startsWith('blob:')) URL.revokeObjectURL(file.preview) })
  const releaseSelfieAsset = (item) => { if (item?.url?.startsWith('blob:')) URL.revokeObjectURL(item.url) }
  const reset = () => { releaseCollectionAssets(collection); releaseSelfieAsset(selfie); setScreen('landing'); setCollection([]); setCollectionId(null); setSelfie(null); setViewerIndex(null); setIsDemoSession(true); setRealMatches([]); setMatchError(''); setDriveImport({ loading: false, error: '', summary: null }); setCollectionUpload({ loading: false, error: '' }); setSelfieUpload({ loading: false, error: '' }) }
  const appendCollection = (incoming) => setCollection((current) => [...current, ...incoming.filter((file) => !current.some((existing) => existing.name === file.name && existing.size === file.size))])
  const removeCollectionFile = (id) => setCollection((current) => {
    const file = current.find((item) => item.id === id)
    if (file?.url?.startsWith('blob:')) URL.revokeObjectURL(file.url)
    if (file?.preview?.startsWith('blob:')) URL.revokeObjectURL(file.preview)
    return current.filter((item) => item.id !== id)
  })
  const clearCollection = () => { releaseCollectionAssets(collection); setCollection([]); setCollectionId(null); setDriveImport({ loading: false, error: '', summary: null }); setCollectionUpload({ loading: false, error: '' }) }
  const startOver = () => { clearCollection(); releaseSelfieAsset(selfie); setSelfie(null); setRealMatches([]); setMatchError(''); setSelfieUpload({ loading: false, error: '' }); setScreen('collection') }
  const useSampleCollection = () => { releaseCollectionAssets(collection); setCollectionId(null); setIsDemoSession(true); setDriveImport({ loading: false, error: '', summary: null }); setCollectionUpload({ loading: false, error: '' }); setCollection(MOCK_PHOTOS.slice(0, 5).map((photo, index) => ({ id: `sample-${photo.id}`, name: `event-frame-${index + 1}.jpg`, size: 1800000 + index * 170000, url: photo.src, preview: photo.src, isSample: true }))) }
  const useSampleSelfie = () => { releaseSelfieAsset(selfie); setSelfieUpload({ loading: false, error: '' }); setSelfie({ ...SAMPLE_SELFIE, id: 'sample-selfie' }) }
  const setSelfieAndReleasePrevious = (nextSelfie) => { releaseSelfieAsset(selfie); setSelfieUpload({ loading: false, error: '' }); setSelfie(nextSelfie) }
  const continueWithCollection = async () => {
    const files = collection.map((item) => item.file).filter(Boolean)
    if (!files.length) { setScreen('selfie'); return }
    setCollectionUpload({ loading: true, error: '' })
    try {
      const created = collectionId ? { collection_id: collectionId } : await createCollection()
      const response = await uploadCollectionPhotos(created.collection_id, files)
      setCollectionId(created.collection_id)
      setIsDemoSession(false)
      setCollectionUpload({ loading: false, error: response.failed_files?.length ? `${response.failed_files.length} photo${response.failed_files.length === 1 ? '' : 's'} couldn’t be added. The rest are ready.` : '' })
      if (response.photos.length) setScreen('selfie')
    } catch (error) {
      setCollectionUpload({ loading: false, error: error.message || 'Some photos couldn’t be added. Please try again.' })
    }
  }
  const importDriveFolder = async (folderUrl) => {
    setDriveImport({ loading: true, error: '', summary: null })
    try {
      const created = collectionId ? { collection_id: collectionId } : await createCollection()
      const response = await importGoogleDriveFolder(created.collection_id, folderUrl)
      setCollectionId(created.collection_id)
      setIsDemoSession(false)
      setDriveImport({ loading: false, error: response.failed_count ? `${response.imported_count} photos imported. ${response.failed_count} couldn’t be added.` : '', summary: response })
      if (response.imported_count > 0 || response.duplicate_count > 0) setScreen('selfie')
    } catch (error) {
      setDriveImport({ loading: false, error: error.message || 'We couldn’t import this Drive folder.', summary: null })
    }
  }
  const continueWithSelfie = async () => {
    if (!selfie?.file || !collectionId) { setScreen('processing'); return }
    setSelfieUpload({ loading: true, error: '' })
    try {
      await uploadCollectionSelfie(collectionId, selfie.file)
      await processCollectionSelfie(collectionId)
      await processCollectionFaces(collectionId)
      setSelfieUpload({ loading: false, error: '' })
      setScreen('processing')
    } catch (error) {
      setSelfieUpload({ loading: false, error: error.message || 'Your selfie couldn’t be added. Please try another photo.' })
    }
  }
  const finishProcessing = useCallback(async () => {
    if (isDemoSession || !collectionId) { setScreen('results'); return }
    try {
      const response = await matchCollection(collectionId)
      setRealMatches(response.matches.map((match) => ({ ...match, id: match.photo_id, src: `${API_BASE_URL}${match.image_url}`, alt: match.original_filename, label: `${match.match_type === 'strong' ? 'Strong' : 'Possible'} match · ${match.similarity_score.toFixed(2)}`, shape: match.height > match.width ? 'tall' : match.width > match.height ? 'wide' : 'square' })))
      setMatchError('')
    } catch (error) {
      setRealMatches([])
      setMatchError(error.message || 'We couldn’t compare your selfie with this collection.')
    }
    setScreen('results')
  }, [collectionId, isDemoSession])

  const viewerItems = isDemoSession ? MOCK_PHOTOS : realMatches

  if (screen === 'landing') return <LandingView onStart={start} />
  if (screen === 'collection') return <CollectionView files={collection} onFiles={appendCollection} onRemove={removeCollectionFile} onClear={clearCollection} onContinue={continueWithCollection} onSample={useSampleCollection} onDriveImport={importDriveFolder} onBack={reset} onHome={reset} isUploading={collectionUpload.loading} errorMessage={collectionUpload.error} driveImporting={driveImport.loading} driveError={driveImport.error} />
  if (screen === 'selfie') return <SelfieView selfie={selfie} onSelfie={setSelfieAndReleasePrevious} onContinue={continueWithSelfie} onBack={() => setScreen('collection')} onHome={reset} onSample={useSampleSelfie} isUploading={selfieUpload.loading} errorMessage={selfieUpload.error} collectionNotice={driveImport.error || collectionUpload.error} />
  if (screen === 'processing') return <ProcessingView onComplete={finishProcessing} onBack={() => setScreen('collection')} onHome={() => setScreen('collection')} collectionId={collectionId} realProcessing={!isDemoSession} onProcessingError={(message) => { setCollectionUpload({ loading: false, error: message }); setScreen('collection') }} />
  if (screen === 'results') return <>
    <ResultsView isDemo={isDemoSession} matches={realMatches} errorMessage={matchError} onOpen={(photo) => setViewerIndex(viewerItems.findIndex((item) => item.id === photo.id))} onStartOver={startOver} onHome={reset} collectionCount={`${((driveImport.summary?.imported_count || 0) + (driveImport.summary?.duplicate_count || 0)) || collection.length || 5} photos`} />
    {viewerIndex !== null && viewerItems[viewerIndex] && <Viewer photo={viewerItems[viewerIndex]} onClose={() => setViewerIndex(null)} onPrevious={() => setViewerIndex((index) => (index - 1 + viewerItems.length) % viewerItems.length)} onNext={() => setViewerIndex((index) => (index + 1) % viewerItems.length)} />}
  </>
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)
