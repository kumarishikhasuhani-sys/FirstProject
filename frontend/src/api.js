const BASE = '/api'

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  // Tenants
  getTenants: () => req('/tenants/'),
  createTenant: (name) => req('/tenants/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  }),

  // Ingestion
  ingest: (tenantId, sourceType, file, createdBy = 'analyst') => {
    const fd = new FormData()
    fd.append('tenant_id', tenantId)
    fd.append('source_type', sourceType)
    fd.append('file', file)
    fd.append('created_by', createdBy)
    return req('/ingestions/', { method: 'POST', body: fd })
  },
  getJob: (id) => req(`/ingestions/${id}/`),
  getJobs: (tenantId) => req(`/ingestions/${tenantId ? `?tenant_id=${tenantId}` : ''}`),

  // Activities
  getActivities: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))
    ).toString()
    return req(`/activities/${qs ? `?${qs}` : ''}`)
  },
  getActivity: (id) => req(`/activities/${id}/`),
  patchActivity: (id, data) => req(`/activities/${id}/`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),
  approveActivity: (id, approvedBy = 'analyst') => req(`/activities/${id}/approve/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approved_by: approvedBy }),
  }),
  rejectActivity: (id) => req(`/activities/${id}/reject/`, { method: 'POST' }),

  // Dashboard
  getSummary: (tenantId) => req(`/dashboard/summary/${tenantId ? `?tenant_id=${tenantId}` : ''}`),
}
