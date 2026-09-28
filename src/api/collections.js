import { request } from './client'

export function createCollection() {
  return request('/api/collections', { method: 'POST' })
}

export function uploadCollectionPhotos(collectionId, files) {
  const body = new FormData()
  files.forEach((file) => body.append('files', file, file.name))
  return request(`/api/collections/${collectionId}/photos`, { method: 'POST', body })
}

export function uploadCollectionSelfie(collectionId, file) {
  const body = new FormData()
  body.append('file', file, file.name)
  return request(`/api/collections/${collectionId}/selfie`, { method: 'POST', body })
}

export function processCollectionSelfie(collectionId) {
  return request(`/api/collections/${collectionId}/process-selfie`, { method: 'POST' })
}

export function processCollectionFaces(collectionId) {
  return request(`/api/collections/${collectionId}/process-faces`, { method: 'POST' })
}

export function getCollectionStatus(collectionId) {
  return request(`/api/collections/${collectionId}`)
}
