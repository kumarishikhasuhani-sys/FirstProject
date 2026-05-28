import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const SOURCE_TYPES = ['SAP', 'UTILITY', 'TRAVEL']
const ACCEPT = { SAP: '.csv', UTILITY: '.csv', TRAVEL: '.json' }
const SOURCE_DESC = {
  SAP: 'Fuel & procurement CSV export',
  UTILITY: 'Electricity meter billing CSV',
  TRAVEL: 'Flight/Hotel/Ground JSON export',
}

function StatusBadge({ status }) {
  const map = {
    UPLOADED: 'bg-gray-100 text-gray-700',
    PARSING: 'bg-yellow-100 text-yellow-800',
    PARSED: 'bg-green-100 text-green-800',
    FAILED: 'bg-red-100 text-red-800',
    PARTIALLY_PARSED: 'bg-orange-100 text-orange-800',
  }
  return (
    <span className={`badge ${map[status] || 'bg-gray-100 text-gray-600'}`}>{status}</span>
  )
}

function MetricPill({ label, value, color = 'gray' }) {
  const colors = {
    gray: 'bg-gray-50 border-gray-200',
    green: 'bg-green-50 border-green-200',
    red: 'bg-red-50 border-red-200',
    orange: 'bg-orange-50 border-orange-200',
  }
  return (
    <div className={`flex flex-col items-center px-4 py-3 rounded-lg border ${colors[color]}`}>
      <span className="text-2xl font-bold">{value}</span>
      <span className="text-xs text-gray-500 mt-0.5">{label}</span>
    </div>
  )
}

export default function IngestPage() {
  const navigate = useNavigate()
  const [tenants, setTenants] = useState([])
  const [tenantId, setTenantId] = useState('')
  const [newTenantName, setNewTenantName] = useState('')
  const [creatingTenant, setCreatingTenant] = useState(false)
  const [sourceType, setSourceType] = useState('SAP')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')
  const fileRef = useRef()

  useEffect(() => {
    api.getTenants().then(setTenants).catch(() => {})
  }, [])

  async function handleCreateTenant(e) {
    e.preventDefault()
    if (!newTenantName.trim()) return
    setCreatingTenant(true)
    try {
      const t = await api.createTenant(newTenantName.trim())
      setTenants((prev) => [...prev, t])
      setTenantId(String(t.id))
      setNewTenantName('')
    } catch (err) {
      setError(err.message)
    } finally {
      setCreatingTenant(false)
    }
  }

  async function handleIngest(e) {
    e.preventDefault()
    if (!tenantId || !file) return
    setLoading(true)
    setError('')
    setJob(null)
    try {
      const result = await api.ingest(tenantId, sourceType, file)
      setJob(result)
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Ingest Data</h1>
      <p className="text-sm text-gray-500 mb-8">
        Upload source files to create an ingestion job and generate activity records for review.
      </p>

      {/* Tenant section */}
      <div className="card p-5 mb-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">1. Select Tenant</h2>
        <select
          className="input mb-3"
          value={tenantId}
          onChange={(e) => setTenantId(e.target.value)}
        >
          <option value="">— choose a tenant —</option>
          {tenants.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <form onSubmit={handleCreateTenant} className="flex gap-2">
          <input
            className="input"
            placeholder="Or create new tenant…"
            value={newTenantName}
            onChange={(e) => setNewTenantName(e.target.value)}
          />
          <button
            type="submit"
            className="btn-secondary whitespace-nowrap"
            disabled={creatingTenant || !newTenantName.trim()}
          >
            {creatingTenant ? 'Creating…' : '+ Create'}
          </button>
        </form>
      </div>

      {/* Source type */}
      <div className="card p-5 mb-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">2. Select Source Type</h2>
        <div className="grid grid-cols-3 gap-3">
          {SOURCE_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => { setSourceType(t); setFile(null); if (fileRef.current) fileRef.current.value = '' }}
              className={`p-3 rounded-lg border-2 text-left transition-colors ${
                sourceType === t
                  ? 'border-brand-500 bg-brand-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="font-semibold text-sm">{t}</div>
              <div className="text-xs text-gray-500 mt-0.5">{SOURCE_DESC[t]}</div>
            </button>
          ))}
        </div>
      </div>

      {/* File upload */}
      <div className="card p-5 mb-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">3. Upload File</h2>
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT[sourceType]}
          onChange={(e) => setFile(e.target.files[0] || null)}
          className="block w-full text-sm text-gray-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100 cursor-pointer"
        />
        {file && (
          <p className="text-xs text-gray-500 mt-2">
            Selected: <span className="font-medium">{file.name}</span> ({(file.size / 1024).toFixed(1)} KB)
          </p>
        )}
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      <button
        onClick={handleIngest}
        disabled={loading || !tenantId || !file}
        className="btn-primary w-full justify-center py-3 text-base"
      >
        {loading ? 'Ingesting…' : '↑ Upload & Ingest'}
      </button>

      {/* Job result */}
      {job && (
        <div className="card p-5 mt-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Ingestion Complete</h3>
            <StatusBadge status={job.status} />
          </div>
          <div className="grid grid-cols-4 gap-3 mb-4">
            <MetricPill label="Total" value={job.total_rows} />
            <MetricPill label="Parsed" value={job.parsed_rows} color="green" />
            <MetricPill label="Failed" value={job.failed_rows} color="red" />
            <MetricPill label="Suspicious" value={job.suspicious_rows} color="orange" />
          </div>
          <div className="text-xs text-gray-400 font-mono">Job ID: {job.id}</div>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-3 text-sm text-brand-600 hover:underline text-left"
          >
            → Go to Dashboard to review records
          </button>
        </div>
      )}
    </div>
  )
}
