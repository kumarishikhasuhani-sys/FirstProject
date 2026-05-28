import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import ReviewModal from './ReviewModal'

const SOURCE_TYPES = ['', 'SAP', 'UTILITY', 'TRAVEL']
const STATUSES = ['', 'PENDING_REVIEW', 'APPROVED', 'REJECTED']

const STATUS_BADGE = {
  PENDING_REVIEW: 'bg-yellow-100 text-yellow-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
}

const SCOPE_BADGE = {
  SCOPE_1: 'bg-red-50 text-red-700',
  SCOPE_2: 'bg-blue-50 text-blue-700',
  SCOPE_3: 'bg-purple-50 text-purple-700',
}

function MetricCard({ label, value, sub, accent = false, color }) {
  const accentMap = {
    green: 'bg-green-50 border-green-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    red: 'bg-red-50 border-red-200',
    orange: 'bg-orange-50 border-orange-200',
    purple: 'bg-purple-50 border-purple-200',
    default: 'bg-white border-gray-200',
  }
  return (
    <div className={`card p-5 border ${accentMap[color] || accentMap.default}`}>
      <div className="text-3xl font-bold text-gray-900">{value ?? '—'}</div>
      <div className="text-sm font-medium text-gray-600 mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const [tenants, setTenants] = useState([])
  const [tenantId, setTenantId] = useState('')
  const [summary, setSummary] = useState(null)
  const [activities, setActivities] = useState([])
  const [filters, setFilters] = useState({ status: '', source_type: '', suspicious: '' })
  const [loadingData, setLoadingData] = useState(false)
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => {
    api.getTenants().then(setTenants).catch(() => {})
  }, [])

  const load = useCallback(async () => {
    setLoadingData(true)
    try {
      const params = { ...filters }
      if (tenantId) params.tenant_id = tenantId
      const [acts, sum] = await Promise.all([
        api.getActivities(params),
        api.getSummary(tenantId || undefined),
      ])
      setActivities(acts)
      setSummary(sum)
    } catch {
      // silently fail; user can retry
    } finally {
      setLoadingData(false)
    }
  }, [tenantId, filters])

  useEffect(() => { load() }, [load])

  function setFilter(key, val) {
    setFilters((prev) => ({ ...prev, [key]: val }))
  }

  return (
    <div className="p-8">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Review and approve ESG activity records</p>
        </div>
        <div className="flex items-center gap-3">
          <select className="input w-48" value={tenantId} onChange={(e) => setTenantId(e.target.value)}>
            <option value="">All tenants</option>
            {tenants.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <button onClick={load} className="btn-secondary" disabled={loadingData}>
            {loadingData ? 'Loading…' : '↺ Refresh'}
          </button>
        </div>
      </div>

      {/* Metric cards */}
      {summary && (
        <div className="grid grid-cols-6 gap-4 mb-8">
          <MetricCard label="Total Records" value={summary.total} />
          <MetricCard label="Pending Review" value={summary.pending} color="yellow" />
          <MetricCard label="Approved" value={summary.approved} color="green" />
          <MetricCard label="Rejected" value={summary.rejected} color="red" />
          <MetricCard label="Suspicious" value={summary.suspicious} color="orange" sub="have flags" />
          <MetricCard label="Parse Failures" value={summary.failed} color="red" sub="raw record errors" />
        </div>
      )}

      {/* Filters */}
      <div className="card p-4 mb-5 flex items-center gap-4">
        <span className="text-sm font-medium text-gray-600 shrink-0">Filter:</span>
        <select className="input w-40" value={filters.status} onChange={(e) => setFilter('status', e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.filter(Boolean).map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
        <select className="input w-36" value={filters.source_type} onChange={(e) => setFilter('source_type', e.target.value)}>
          <option value="">All sources</option>
          {SOURCE_TYPES.filter(Boolean).map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.suspicious === 'true'}
            onChange={(e) => setFilter('suspicious', e.target.checked ? 'true' : '')}
            className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
          />
          Flagged only
        </label>
        <span className="ml-auto text-xs text-gray-400">{activities.length} record{activities.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                {['Source', 'Scope', 'Category', 'Date', 'Quantity', 'Unit', 'Flags', 'Status', ''].map((h) => (
                  <th key={h} className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {activities.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-12 text-center text-gray-400 text-sm">
                    {loadingData ? 'Loading…' : 'No records found. Upload data on the Ingest page.'}
                  </td>
                </tr>
              ) : (
                activities.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => setSelectedId(a.id)}
                  >
                    <td className="px-4 py-3 font-medium text-gray-700">{a.source_type}</td>
                    <td className="px-4 py-3">
                      {a.scope ? (
                        <span className={`badge ${SCOPE_BADGE[a.scope] || 'bg-gray-100 text-gray-600'}`}>
                          {a.scope}
                        </span>
                      ) : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{a.category || <span className="text-gray-300">—</span>}</td>
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">{a.activity_date || '—'}</td>
                    <td className="px-4 py-3 text-gray-700 font-mono text-right">
                      {a.quantity_normalized != null
                        ? Number(a.quantity_normalized).toLocaleString(undefined, { maximumFractionDigits: 2 })
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{a.unit_normalized || '—'}</td>
                    <td className="px-4 py-3">
                      {a.flags?.length > 0 ? (
                        <span className="badge bg-orange-100 text-orange-700">⚠ {a.flags.length}</span>
                      ) : (
                        <span className="text-gray-300 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`badge ${STATUS_BADGE[a.status] || 'bg-gray-100 text-gray-600'}`}>
                        {a.status?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        className="text-xs text-brand-600 hover:underline font-medium"
                        onClick={(e) => { e.stopPropagation(); setSelectedId(a.id) }}
                      >
                        Review →
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Review modal */}
      {selectedId && (
        <ReviewModal
          activityId={selectedId}
          onClose={() => setSelectedId(null)}
          onUpdated={() => { load(); }}
        />
      )}
    </div>
  )
}
