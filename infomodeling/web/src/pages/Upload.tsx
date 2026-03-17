import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ModelSchema, ValidationResult } from '../api'

export default function Upload() {
  const [file, setFile] = useState<File | null>(null)
  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const handleFile = async (f: File) => {
    setFile(f)
    setError(null)
    setValidation(null)
    try {
      const result = await api.validateModel(f)
      setValidation(result)
    } catch {
      setError('Failed to validate file')
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    try {
      await api.uploadModel(file)
      navigate('/explorer')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 600 }}>
      <h1>Upload Conceptual Model</h1>
      <p style={{ color: 'var(--color-muted)', marginBottom: '1.5rem' }}>
        Upload a YAML file defining your organization's conceptual information model.
      </p>

      <div
        className="card"
        style={{
          border: '2px dashed var(--color-border)',
          textAlign: 'center',
          cursor: 'pointer',
          padding: '2.5rem',
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          const f = e.dataTransfer.files[0]
          if (f) handleFile(f)
        }}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".yaml,.yml"
          style={{ display: 'none' }}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
        />
        {file ? (
          <div>
            <div style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>{file.name}</div>
            <div style={{ color: 'var(--color-muted)', fontSize: '0.85rem' }}>
              {(file.size / 1024).toFixed(1)} KB
            </div>
          </div>
        ) : (
          <div style={{ color: 'var(--color-muted)' }}>
            Drag & drop a YAML file here, or click to browse
          </div>
        )}
      </div>

      {validation && (
        <div className="card" style={{
          borderColor: validation.valid ? '#22c55e33' : '#ef444433',
          color: validation.valid ? 'var(--color-success)' : '#f87171',
        }}>
          <strong>{validation.valid ? '✓ Valid' : '✗ Invalid'}</strong>{' '}
          {validation.message}
          {validation.errors.length > 0 && (
            <ul style={{ marginTop: '0.5rem', paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
              {validation.errors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
        </div>
      )}

      {error && (
        <div className="card" style={{ color: '#f87171', borderColor: '#ef444433' }}>{error}</div>
      )}

      <button
        onClick={handleUpload}
        disabled={!file || !validation?.valid || loading}
        style={{ marginTop: '1rem' }}
      >
        {loading ? 'Loading...' : 'Load Model →'}
      </button>
    </div>
  )
}
