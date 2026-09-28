import { StrictMode, useCallback, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import { ArrowIcon, LockIcon, SparkIcon } from './components/Icons'
import { MOCK_PHOTOS, SAMPLE_SELFIE } from './data/mockPhotos'
import { CollectionView, ProcessingView, ResultsView, SelfieView, Viewer } from './views/FlowViews'
import { ImageWithFallback } from './components/ImageWithFallback'
import { API_BASE_URL } from './api/client'
import { createCollection, getCollectionStatus, importGoogleDriveFolder, matchCollection, processCollectionFaces, processCollectionSelfie, uploadCollectionPhotos, uploadCollectionSelfie } from './api/collections'

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
        <p className="hero-dek">Thousands of event photos.<br />One clear reference photo. We&apos;ll find yours.</p>
        <div className="hero-actions"><button className="primary-button" type="button" onClick={onStart}>Find my photos <ArrowIcon /></button><span className="hero-note">No account needed</span></div>
        <div className="mini-proof" aria-label="FindMyFrame product promise"><span className="mini-avatars"><span style={{ backgroundImage: `url(${landingImages.friends})` }} /><span style={{ backgroundImage: `url(${landingImages.dance})` }} /><span style={{ backgroundImage: `url(${landingImages.concert})` }} /></span><span><strong>Made for being there.</strong><br />Not for scrolling forever.</span></div>
      </div>
      <div className="hero-art" aria-label="A collage of event photographs">
        <div className="art-caption art-caption-top"><span>FRAME 001</span><span>YOUR NIGHT, REMEMBERED</span></div>
        <div className="image-frame image-frame-main"><ImageWithFallback src={landingImages.crowd} alt="A crowd with hands raised at a live event" /><span className="image-stamp">01 / 04</span></div>
        <div className="image-frame image-frame-small"><ImageWithFallback src={landingImages.dance} alt="Friends dancing together at an outdoor event" /></div>
        <div className="art-card"><SparkIcon /><span>One reference photo<br /><strong>every moment</strong></span></div>
        <div className="art-caption art-caption-bottom"><span>THE AFTERGLOW</span><span>↓ SCROLL TO BEGIN</span></div>
      </div>
    </section>

    <section id="how-it-works" className="story-section" aria-labelledby="story-title">
      <div className="section-intro"><p className="eyebrow"><span className="eyebrow-dot" /> three small steps</p><h2 id="story-title">You were there.<br /><em>Now find the proof.</em></h2></div>
      <div className="steps-grid">
        <article className="step-card step-card-dark"><span className="step-number">01</span><div className="step-art folder-art"><span /><span /><span /></div><h3>Bring the collection</h3><p>Add local photos or paste a Google Drive folder link. We&apos;ll take it from here.</p></article>
        <article className="step-card"><span className="step-number">02</span><div className="step-art selfie-art"><div className="selfie-sun" /><div className="selfie-head" /><div className="selfie-body" /></div><h3>Show us you</h3><p>One clear reference photo is enough to start looking through the crowd.</p></article>
        <article className="step-card step-card-image"><span className="step-number">03</span><div className="step-art result-art"><ImageWithFallback src={landingImages.friends} alt="Friends smiling together" /><span className="result-ring" /></div><h3>Keep your moments</h3><p>Open, save, and share the photographs where you were part of it.</p></article>
      </div>
    </section>

    <section id="privacy" className="privacy-strip" aria-label="Privacy promise"><div className="privacy-icon"><LockIcon /></div><div><strong>Private by design.</strong> Your reference photo is used to find your photos in this event — not to build a profile of you.</div><span className="privacy-side-note">FACE DATA / EVENT-SCOPED</span></section>
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
  const [driveImport, setDriveImport] = useState({ loading: false, status: 'not_started', error: '', summary: null, discovered: 0, processed: 0, imported: 0, duplicates: 0, failed: 0, currentFile: '', currentBytes: 0, currentSize: null })

  const emptyDriveImport = () => ({ loading: false, status: 'not_started', error: '', summary: null, discovered: 0, processed: 0, imported: 0, duplicates: 0, failed: 0, currentFile: '', currentBytes: 0, currentSize: null })

  const start = () => setScreen('collection')
  const releaseCollectionAssets = (items) => items.forEach((file) => { if (file.url?.startsWith('blob:')) URL.revokeObjectURL(file.url); if (file.preview?.startsWith('blob:')) URL.revokeObjectURL(file.preview) })
  const releaseSelfieAsset = (item) => { if (item?.url?.startsWith('blob:')) URL.revokeObjectURL(item.url) }
  const reset = () => { releaseCollectionAssets(collection); releaseSelfieAsset(selfie); setScreen('landing'); setCollection([]); setCollectionId(null); setSelfie(null); setViewerIndex(null); setIsDemoSession(true); setRealMatches([]); setMatchError(''); setDriveImport(emptyDriveImport()); setCollectionUpload({ loading: false, error: '' }); setSelfieUpload({ loading: false, error: '' }) }
  const appendCollection = (incoming) => setCollection((current) => [...current, ...incoming.filter((file) => !current.some((existing) => existing.name === file.name && existing.size === file.size))])
  const removeCollectionFile = (id) => setCollection((current) => {
    const file = current.find((item) => item.id === id)
    if (file?.url?.startsWith('blob:')) URL.revokeObjectURL(file.url)
    if (file?.preview?.startsWith('blob:')) URL.revokeObjectURL(file.preview)
    return current.filter((item) => item.id !== id)
  })
  const clearCollection = () => { releaseCollectionAssets(collection); setCollection([]); setCollectionId(null); setDriveImport(emptyDriveImport()); setCollectionUpload({ loading: false, error: '' }) }
  const startOver = () => { clearCollection(); releaseSelfieAsset(selfie); setSelfie(null); setRealMatches([]); setMatchError(''); setSelfieUpload({ loading: false, error: '' }); setScreen('collection') }
  const useSampleCollection = () => { releaseCollectionAssets(collection); setCollectionId(null); setIsDemoSession(true); setDriveImport(emptyDriveImport()); setCollectionUpload({ loading: false, error: '' }); setCollection(MOCK_PHOTOS.slice(0, 5).map((photo, index) => ({ id: `sample-${photo.id}`, name: `event-frame-${index + 1}.jpg`, size: 1800000 + index * 170000, url: photo.src, preview: photo.src, isSample: true }))) }
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
    setDriveImport({ ...emptyDriveImport(), loading: true, status: 'starting' })
    try {
      const created = collectionId ? { collection_id: collectionId } : await createCollection()
      const response = await importGoogleDriveFolder(created.collection_id, folderUrl)
      setCollectionId(created.collection_id)
      setIsDemoSession(false)
      const importStatus = response.status || 'discovering'
      setDriveImport({ loading: importStatus === 'processing' || importStatus === 'discovering', status: importStatus, error: '', summary: response, discovered: response.discovered_count || 0, processed: response.processed_count || 0, imported: response.imported_count || 0, duplicates: response.duplicate_count || 0, failed: response.failed_count || 0, currentFile: '', currentBytes: 0, currentSize: null })
      setScreen('selfie')
    } catch (error) {
      setDriveImport({ ...emptyDriveImport(), error: error.message || 'We couldn’t start this Drive import.' })
    }
  }

  useEffect(() => {
    if (!collectionId || !['discovering', 'processing'].includes(driveImport.status)) return undefined
    let cancelled = false
    let timer
    const poll = async () => {
      try {
        const status = await getCollectionStatus(collectionId)
        if (cancelled) return
        const importStatus = status.drive_import_status || 'processing'
        const complete = importStatus === 'complete' || importStatus === 'complete_with_errors'
        const failed = importStatus === 'failed'
        setDriveImport((current) => ({
          ...current,
          loading: !complete && !failed,
          status: importStatus,
          discovered: status.drive_discovered_count || 0,
          processed: status.drive_processed_count || 0,
          imported: status.drive_imported_count || 0,
          duplicates: status.drive_duplicate_count || 0,
          failed: status.drive_failed_count || 0,
          currentFile: status.drive_current_file || '',
          currentBytes: status.drive_current_bytes || 0,
          currentSize: status.drive_current_size || null,
          error: complete ? (status.drive_import_error || '') : failed ? (status.drive_import_error || 'The Drive import could not be completed.') : current.error,
          summary: { ...(current.summary || {}), imported_count: status.drive_imported_count || 0, duplicate_count: status.drive_duplicate_count || 0, failed_count: status.drive_failed_count || 0, status: importStatus },
        }))
        if (!complete && !failed) timer = window.setTimeout(poll, 700)
      } catch (error) {
        if (!cancelled) setDriveImport((current) => ({ ...current, loading: false, status: 'failed', error: error.message || 'We couldn’t read the Drive import status.' }))
      }
    }
    poll()
    return () => { cancelled = true; window.clearTimeout(timer) }
  }, [collectionId, driveImport.status])

  const waitForDriveImport = async (id) => {
    let status = await getCollectionStatus(id)
    while (['discovering', 'processing'].includes(status.drive_import_status)) {
      await new Promise((resolve) => window.setTimeout(resolve, 800))
      status = await getCollectionStatus(id)
    }
    if (status.drive_import_status === 'failed') throw new Error(status.drive_import_error || 'The Drive import could not be completed.')
    if (!status.photo_count) throw new Error('No photographs could be imported from this Drive folder.')
    return status
  }
  const continueWithSelfie = async () => {
    if (!selfie?.file || !collectionId) { setScreen('processing'); return }
    setSelfieUpload({ loading: true, error: '' })
    try {
      await uploadCollectionSelfie(collectionId, selfie.file)
      await processCollectionSelfie(collectionId)
      if (['discovering', 'processing'].includes(driveImport.status)) await waitForDriveImport(collectionId)
      await processCollectionFaces(collectionId)
      setSelfieUpload({ loading: false, error: '' })
      setScreen('processing')
    } catch (error) {
      setSelfieUpload({ loading: false, error: error.message || 'Your reference photo couldn’t be added. Please try another photo.' })
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
      setMatchError(error.message || 'We couldn’t compare your reference photo with this collection.')
    }
    setScreen('results')
  }, [collectionId, isDemoSession])

  const viewerItems = isDemoSession ? MOCK_PHOTOS : realMatches

  if (screen === 'landing') return <LandingView onStart={start} />
  if (screen === 'collection') return <CollectionView files={collection} onFiles={appendCollection} onRemove={removeCollectionFile} onClear={clearCollection} onContinue={continueWithCollection} onSample={useSampleCollection} onDriveImport={importDriveFolder} onBack={reset} onHome={reset} isUploading={collectionUpload.loading} errorMessage={collectionUpload.error} driveProgress={driveImport} driveImporting={driveImport.loading} driveError={driveImport.error} />
  if (screen === 'selfie') return <SelfieView selfie={selfie} onSelfie={setSelfieAndReleasePrevious} onContinue={continueWithSelfie} onBack={() => setScreen('collection')} onHome={reset} onSample={useSampleSelfie} isUploading={selfieUpload.loading} errorMessage={selfieUpload.error} collectionNotice={collectionUpload.error} driveProgress={driveImport} />
  if (screen === 'processing') return <ProcessingView photoCount={driveImport.imported + driveImport.duplicates || collection.length || 1} onComplete={finishProcessing} onBack={() => setScreen('collection')} onHome={() => setScreen('collection')} collectionId={collectionId} realProcessing={!isDemoSession} onProcessingError={(message) => { setCollectionUpload({ loading: false, error: message }); setScreen('collection') }} />
  if (screen === 'results') return <>
    <ResultsView isDemo={isDemoSession} matches={realMatches} errorMessage={matchError} onOpen={(photo) => setViewerIndex(viewerItems.findIndex((item) => item.id === photo.id))} onStartOver={startOver} onHome={reset} collectionCount={`${((driveImport.summary?.imported_count || 0) + (driveImport.summary?.duplicate_count || 0)) || collection.length || 5} photos`} />
    {viewerIndex !== null && viewerItems[viewerIndex] && <Viewer photo={viewerItems[viewerIndex]} onClose={() => setViewerIndex(null)} onPrevious={() => setViewerIndex((index) => (index - 1 + viewerItems.length) % viewerItems.length)} onNext={() => setViewerIndex((index) => (index + 1) % viewerItems.length)} />}
  </>
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)
