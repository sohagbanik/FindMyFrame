import { useEffect, useRef, useState } from 'react'
import { MOCK_PHOTOS } from '../data/mockPhotos'
import { ArrowIcon, BackIcon, CloseIcon, DownloadIcon, LockIcon, PlusIcon, ShareIcon } from '../components/Icons'
import { ImageWithFallback } from '../components/ImageWithFallback'
import { getCollectionStatus } from '../api/collections'

const steps = ['Collection', 'Reference photo', 'Your moments']

function formatBytes(bytes) {
  if (!bytes) return '0 KB'
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function DriveImportProgress({ progress }) {
  if (!progress || progress.status === 'not_started') return null
  const complete = progress.status === 'complete' || progress.status === 'complete_with_errors'
  const failed = progress.status === 'failed'
  const discovered = progress.discovered || 0
  const processed = progress.processed || 0
  const percent = complete ? 100 : discovered ? Math.min(99, Math.round((processed / discovered) * 100)) : progress.status === 'starting' ? 2 : 4
  const label = failed ? 'Drive import stopped' : complete ? 'Drive import complete' : progress.status === 'starting' ? 'Starting Drive import…' : progress.status === 'discovering' ? 'Finding Drive photos…' : 'Importing Drive photos…'
  return <div className="drive-progress" role="status" aria-live="polite">
    <div className="drive-progress-heading"><strong>{label}</strong><span>{percent}%</span></div>
    <div className="drive-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={percent} aria-label="Google Drive import progress"><span style={{ width: `${percent}%` }} /></div>
    <div className="drive-progress-count"><span>{processed.toLocaleString()} of {discovered.toLocaleString()} files processed</span><span>{progress.imported || 0} imported · {progress.duplicates || 0} already added · {progress.failed || 0} skipped</span></div>
    {progress.currentFile && !complete && <p className="drive-progress-current">{progress.currentFile}{progress.currentSize ? ` · ${formatBytes(progress.currentBytes || 0)} / ${formatBytes(progress.currentSize)}` : ''}</p>}
    {progress.error && <p className="drive-progress-error">{progress.error}</p>}
  </div>
}

function Wordmark() {
  return <span className="wordmark"><span className="wordmark-mark" aria-hidden="true"><i /><i /><i /><i /></span>findmyframe</span>
}

function FlowHeader({ onBack, onHome }) {
  return <header className="flow-header">
    <button className="flow-wordmark-button" type="button" onClick={onHome} aria-label="Return to FindMyFrame home"><Wordmark /></button>
    <div className="flow-header-note"><span className="flow-status-dot" /> no account needed</div>
    <button className="flow-close-button" type="button" onClick={onBack} aria-label="Go back"><CloseIcon /></button>
  </header>
}

function FlowProgress({ current }) {
  return <div className="flow-progress" aria-label={`Step ${current + 1} of ${steps.length}`}>
    {steps.map((step, index) => <div className={`progress-step ${index === current ? 'is-current' : ''} ${index < current ? 'is-done' : ''}`} key={step}>
      <span>{String(index + 1).padStart(2, '0')}</span>{step}
    </div>)}
  </div>
}

function FlowFrame({ current, eyebrow, title, copy, onBack, onHome, children, aside }) {
  return <main className="flow-shell">
    <FlowHeader onBack={onBack} onHome={onHome} />
    <FlowProgress current={current} />
    <section className="flow-content" aria-labelledby="flow-title">
      <div className="flow-intro">
        <p className="eyebrow"><span className="eyebrow-dot" /> {eyebrow}</p>
        <h1 id="flow-title">{title}</h1>
        <p className="flow-copy">{copy}</p>
      </div>
      <div className="flow-layout">
        <div className="flow-main-column">{children}</div>
        {aside && <aside className="flow-aside">{aside}</aside>}
      </div>
    </section>
  </main>
}

function PrivacyNote() {
  return <p className="inline-privacy"><span><LockIcon /></span><span><strong>Private by design.</strong> Your reference photo stays scoped to this search.</span></p>
}

export function CollectionView({ files, onFiles, onRemove, onClear, onContinue, onSample, onBack, onHome, isUploading = false, errorMessage = '', onDriveImport, driveImporting = false, driveError = '', driveProgress = null }) {
  const [dragging, setDragging] = useState(false)
  const [driveUrl, setDriveUrl] = useState('')
  const inputRef = useRef(null)

  const acceptFiles = (incoming) => {
    const normalized = incoming.filter((file) => file.type.startsWith('image/')).map((file) => ({
      id: `${file.name}-${file.lastModified}-${Math.random()}`,
      name: file.name,
      size: file.size,
      file,
      url: URL.createObjectURL(file),
      preview: URL.createObjectURL(file),
    }))
    if (normalized.length) onFiles(normalized)
  }

  return <FlowFrame current={0} eyebrow="step one / the collection" title={<>Bring the<br /><em>whole night.</em></>} copy="Choose the event photographs you want to search. We’ll keep the rest of the process simple." onBack={onBack} onHome={onHome} aside={<>
    <div className="aside-number">01 <span>/ 03</span></div>
    <p>Start with the folder you already have. A few photographs or a whole event both work here.</p>
    <div className="aside-line" />
    <p className="aside-small">For Drive links, the folder must be accessible to anyone with the link. Private-folder OAuth is coming later.</p>
  </>}>
    <div className={`upload-zone ${dragging ? 'is-dragging' : ''} ${files.length ? 'has-files' : ''}`} aria-busy={isUploading} onDragEnter={(event) => { event.preventDefault(); setDragging(true) }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFiles(Array.from(event.dataTransfer.files)) }}>
      <input ref={inputRef} id="collection-upload" className="visually-hidden" type="file" accept="image/*" multiple onChange={(event) => acceptFiles(Array.from(event.target.files))} />
      <label className="upload-zone-action" htmlFor="collection-upload">
        <span className="upload-plus"><PlusIcon /></span>
        <strong>{files.length ? 'Add more photographs' : 'Drop local photographs here'}</strong>
        <span>or <u>choose from this device</u></span>
      </label>
      <span className="upload-format">Local JPG, PNG or WEBP · multiple files welcome</span>
    </div>

    {files.length > 0 && <div className="collection-summary">
      <div className="collection-summary-top"><div><strong>{files.length} photograph{files.length === 1 ? '' : 's'}</strong><span>{formatBytes(files.reduce((total, file) => total + file.size, 0))} total</span></div><button className="text-action" type="button" onClick={onClear}>Clear collection</button></div>
      <div className="collection-previews">
        {files.map((file) => <div className="collection-preview" key={file.id}><ImageWithFallback src={file.preview} alt="" /><button type="button" aria-label={`Remove ${file.name}`} onClick={() => onRemove(file.id)}><CloseIcon /></button></div>)}
      </div>
    </div>}

    {errorMessage && <p className="upload-error" role="alert">{errorMessage}</p>}
    <div className="flow-actions">
      <button className="primary-button" type="button" disabled={!files.length || isUploading} onClick={onContinue}>{isUploading ? 'Adding photographs…' : 'Continue to reference photo'} {!isUploading && <ArrowIcon />}</button>
      {!files.length && <button className="ghost-action" type="button" onClick={onSample}>Try the small demo collection <ArrowIcon /></button>}
    </div>
    <div className="drive-source">
      <div className="drive-source-heading"><span>Or use Google Drive</span><small>Accessible folder link</small></div>
      <label className="drive-input-label" htmlFor="drive-folder-url">Paste your event folder link</label>
      <div className="drive-input-row"><input id="drive-folder-url" type="url" value={driveUrl} onChange={(event) => setDriveUrl(event.target.value)} placeholder="https://drive.google.com/drive/folders/..." autoComplete="off" /><button className="drive-import-button" type="button" disabled={!driveUrl.trim() || driveImporting} onClick={() => onDriveImport?.(driveUrl.trim())}>{driveImporting ? 'Importing…' : 'Import photos'} <ArrowIcon /></button></div>
      <p className="drive-note">Make sure the folder is shared as <strong>Anyone with the link</strong>. We only read supported image files.</p>
      <DriveImportProgress progress={driveProgress} />
      {driveError && (!driveProgress || driveProgress.status === 'not_started') && <p className="upload-error" role="alert">{driveError}</p>}
    </div>
  </FlowFrame>
}

export function SelfieView({ selfie, onSelfie, onContinue, onBack, onHome, onSample, isUploading = false, errorMessage = '', collectionNotice = '', driveProgress = null }) {
  const [dragging, setDragging] = useState(false)
  const chooseSelfie = (file) => {
    if (!file || !file.type.startsWith('image/')) return
    onSelfie({ id: `${file.name}-${file.lastModified}`, name: file.name, size: file.size, file, url: URL.createObjectURL(file) })
  }

  return <FlowFrame current={1} eyebrow="step two / the reference" title={<>Find<br /><em>yourself.</em></>} copy="Upload a clear reference photo of yourself. We’ll use it to find the moments you’re in." onBack={onBack} onHome={onHome} aside={<>
    <div className="aside-number">02 <span>/ 03</span></div>
    <p>A clear, front-facing reference photo works best. No name, email, or account needed.</p>
    <div className="aside-line" />
    <p className="aside-small">We don’t need to build a permanent profile of you to find one event.</p>
  </>}>
    <div className={`selfie-upload ${dragging ? 'is-dragging' : ''} ${selfie ? 'has-selfie' : ''}`} onDragEnter={(event) => { event.preventDefault(); setDragging(true) }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); chooseSelfie(event.dataTransfer.files[0]) }}>
      <input id="selfie-upload" className="visually-hidden" type="file" accept="image/*" onChange={(event) => chooseSelfie(event.target.files[0])} />
      {selfie ? <div className="selfie-preview-wrap"><ImageWithFallback src={selfie.url} alt="Your reference photo" /><div className="selfie-preview-overlay"><span>Ready to look</span><label htmlFor="selfie-upload">Replace photo</label></div></div> : <label className="selfie-upload-action" htmlFor="selfie-upload"><span className="selfie-frame-icon"><span /></span><strong>Drop your reference photo here</strong><span>or <u>choose a photo</u> from this device</span></label>}
    </div>
    {errorMessage && <p className="upload-error" role="alert">{errorMessage}</p>}
    <div className="flow-actions">
      <button className="primary-button" type="button" disabled={!selfie || isUploading} onClick={onContinue}>{isUploading ? 'Preparing your search…' : 'Find my moments'} {!isUploading && <ArrowIcon />}</button>
      {!selfie && <button className="ghost-action" type="button" onClick={onSample}>Use a sample reference photo <ArrowIcon /></button>}
    </div>
    <DriveImportProgress progress={driveProgress} />
    {collectionNotice && <p className="import-summary" role="status">{collectionNotice}</p>}
    <PrivacyNote />
  </FlowFrame>
}

const processingCopy = ['Looking through the crowd.', 'Finding familiar faces.', 'Almost there.', 'Bringing your moments together.']

export function ProcessingView({ onComplete, photoCount = 4283, onBack, onHome, collectionId, realProcessing = false, onProcessingError }) {
  const [progress, setProgress] = useState(0)
  const [copyIndex, setCopyIndex] = useState(0)

  useEffect(() => {
    if (realProcessing && collectionId) {
      let cancelled = false
      const started = performance.now()
      let pollTimer
      const poll = async () => {
        try {
          const status = await getCollectionStatus(collectionId)
          if (cancelled) return
          if (status.face_processing_status === 'complete' || status.face_processing_status === 'complete_with_errors') {
            setProgress(100)
            onComplete()
            return
          }
          if (status.face_processing_status === 'failed') {
            onProcessingError?.('We couldn’t finish looking through this collection. You can try the search again.')
            return
          }
          const processed = (status.photos_processed || 0) + (status.photos_processing_failed || 0)
          const measuredProgress = status.photo_count ? Math.min(99, (processed / status.photo_count) * 100) : 0
          const elapsedProgress = Math.min(93, ((performance.now() - started) / 9000) * 93)
          setProgress((current) => Math.max(current, measuredProgress || elapsedProgress))
          pollTimer = window.setTimeout(poll, 800)
        } catch (error) {
          if (!cancelled) onProcessingError?.(error.message || 'We couldn’t read the processing status.')
        }
      }
      poll()
      return () => { cancelled = true; window.clearTimeout(pollTimer) }
    }
    const start = performance.now()
    let frame
    const tick = (now) => {
      const next = Math.min(100, ((now - start) / 5200) * 100)
      setProgress(next)
      setCopyIndex(Math.min(processingCopy.length - 1, Math.floor(next / 26)))
      if (next < 100) frame = requestAnimationFrame(tick)
      else onComplete()
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [collectionId, onComplete, onProcessingError, realProcessing])

  const scanned = Math.round((progress / 100) * photoCount)
  return <main className="processing-shell">
    <FlowHeader onBack={onBack} onHome={onHome} />
    <div className="processing-center">
      <p className="eyebrow"><span className="eyebrow-dot" /> your search is underway</p>
      <div className="processing-orbit" aria-hidden="true"><span className="orbit-ring orbit-ring-one" /><span className="orbit-ring orbit-ring-two" /><span className="orbit-core" /></div>
      <h1>Looking through<br /><em>the crowd.</em></h1>
      <p className="processing-status" aria-live="polite">{processingCopy[copyIndex]}</p>
      <div className="processing-meter"><span style={{ width: `${progress}%` }} /></div>
      <div className="processing-count"><strong>{scanned.toLocaleString()}</strong><span>of {photoCount.toLocaleString()} photographs</span><span>{Math.round(progress)}%</span></div>
      <p className="processing-note"><LockIcon /> The reference photo is only used for this event search.</p>
    </div>
  </main>
}

function PhotoCard({ photo, selected, onSelect, onOpen, index }) {
  return <article className={`photo-card photo-card-${photo.shape} photo-card-index-${index}`}>
    <button className="photo-open" type="button" onClick={() => onOpen(photo)} aria-label={`Open ${photo.label} photograph`}>
      <ImageWithFallback src={photo.src} alt={photo.alt} />
      <span className="photo-hover-label">{photo.label} <ArrowIcon /></span>
    </button>
    <button className={`photo-select ${selected ? 'is-selected' : ''}`} type="button" aria-label={`${selected ? 'Deselect' : 'Select'} ${photo.label}`} aria-pressed={selected} onClick={() => onSelect(photo.id)}><span /></button>
  </article>
}

export function ResultsView({ onOpen, onStartOver, collectionCount, onHome, isDemo = true, matches = [], errorMessage = '' }) {
  const [selected, setSelected] = useState([])
  const [notice, setNotice] = useState('')
  const hasMatches = isDemo || matches.length > 0
  const possibleMatches = matches.filter((match) => match.match_type === 'possible').length

  const toggleSelected = (id) => setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
  const share = async () => {
    try {
      if (navigator.share) await navigator.share({ title: 'My FindMyFrame moments', text: 'I found my moments from the event.' })
      else if (navigator.clipboard) await navigator.clipboard.writeText(window.location.href)
      setNotice(navigator.share ? 'Share sheet ready.' : 'Link copied to clipboard.')
    } catch { setNotice('Your gallery is ready to share.') }
    window.setTimeout(() => setNotice(''), 2600)
  }

  return <main className="results-shell">
    <FlowHeader onBack={onStartOver} onHome={onHome} />
    <section className="results-head" aria-labelledby="results-title">
      <div><p className="eyebrow"><span className="eyebrow-dot" /> {isDemo ? `search complete · ${collectionCount || 'your'} collection` : 'real search · similarity ranked'}</p><h1 id="results-title">{isDemo || hasMatches ? <>Your <em>moments.</em></> : <>Nothing <em>confident.</em></>}</h1><p className="results-subtitle"><strong>{isDemo ? '37 photos found' : `${matches.length} photo${matches.length === 1 ? '' : 's'} found`}</strong><span>{isDemo ? 'We kept the best matches first.' : errorMessage || (matches.length ? 'Ranked by actual face similarity.' : 'Try a clearer selfie or another collection.')}</span></p></div>
      <div className="results-actions"><button className="outline-action" type="button" onClick={share}><ShareIcon /> Share</button><button className="outline-action" type="button" disabled={!selected.length} onClick={() => setNotice(`${selected.length} selected ${selected.length === 1 ? 'photo is' : 'photos are'} ready to download.`)}><DownloadIcon /> Download {selected.length ? `(${selected.length})` : 'selected'}</button></div>
    </section>
    {notice && <p className="results-notice" role="status">{notice}</p>}
    {isDemo ? <><div className="results-rule"><span>Strong matches</span><span>Showing 9 preview frames · demo collection</span></div><section className="photo-gallery" aria-label="Your matched photographs">{MOCK_PHOTOS.map((photo, index) => <PhotoCard key={photo.id} photo={photo} index={index} selected={selected.includes(photo.id)} onSelect={toggleSelected} onOpen={onOpen} />)}</section><div className="possible-matches"><span className="possible-mark">+</span><div><strong>6 possible matches</strong><span>A few frames might be you. We’ll make these confirmable when matching is connected.</span></div><button type="button" onClick={() => setNotice('Possible matches will be available in the matching phase.')}>Review later <ArrowIcon /></button></div></> : hasMatches ? <><div className="results-rule"><span>Similarity ranked</span><span>{possibleMatches ? `${possibleMatches} possible match${possibleMatches === 1 ? '' : 'es'}` : 'Strong matches only'}</span></div><section className="photo-gallery" aria-label="Your matched photographs">{matches.map((photo, index) => <PhotoCard key={photo.id} photo={photo} index={index} selected={selected.includes(photo.id)} onSelect={toggleSelected} onOpen={onOpen} />)}</section></> : <div className="index-ready-empty"><span className="empty-orbit" aria-hidden="true" /><h2>We looked carefully.<br /><em>Nothing confident.</em></h2><p>{errorMessage || 'We couldn’t find a face in this collection that crossed the development threshold. Try another reference photo or collection.'}</p></div>}
    <footer className="results-footer"><button className="text-action" type="button" onClick={onStartOver}>Start a new search</button><PrivacyNote /></footer>
  </main>
}

export function Viewer({ photo, onClose, onPrevious, onNext }) {
  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === 'Escape') onClose(); if (event.key === 'ArrowLeft') onPrevious(); if (event.key === 'ArrowRight') onNext() }
    document.addEventListener('keydown', onKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', onKeyDown); document.body.style.overflow = previousOverflow }
  }, [onClose, onNext, onPrevious])

  return <div className="viewer-backdrop" role="dialog" aria-modal="true" aria-label={`${photo.label} photograph`}>
    <button className="viewer-close" type="button" onClick={onClose} aria-label="Close photograph viewer"><CloseIcon /></button>
    <button className="viewer-nav viewer-nav-prev" type="button" onClick={onPrevious} aria-label="Previous photograph"><BackIcon /></button>
    <figure className="viewer-figure"><ImageWithFallback src={photo.src} alt={photo.alt} /><figcaption><span>{photo.label}</span><span>FindMyFrame · {photo.match_type ? `${photo.match_type} match · ${photo.similarity_score.toFixed(2)}` : 'strong match'}</span></figcaption></figure>
    <button className="viewer-nav viewer-nav-next" type="button" onClick={onNext} aria-label="Next photograph"><ArrowIcon /></button>
    <a className="viewer-download" href={photo.src} download={`findmyframe-${photo.id}.jpg`} target="_blank" rel="noreferrer"><DownloadIcon /> Download</a>
  </div>
}
