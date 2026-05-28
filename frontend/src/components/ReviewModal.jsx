import { useEffect, useState } from 'react'
import { api } from '../api'

const FLAG_COLORS = {
  MISSING_SCOPE: 'bg-red-100 text-red-700',
  MISSING_QUANTITY: 'bg-orange-100 text-orange-700',
  NEGATIVE_QUANTITY: 'bg-red-100 text-red-700',
  UNKNOWN_PLANT: 'bg-yellow-100 text-yellow-700',
  LONG_BILLING_PERIOD: 'bg-yellow-100 text-yellow-700',
  ABSURD_FUEL_QUANTITY: 'bg-red-100 text-red-700',
  MISSING_CURRENCY: 'bg-orange-100 text-orange-700',
  MISSING_DISTANCE: 'bg-orange-100 text-orange-700',
  MISSING_ROUTE: 'bg-orange-100 text-orange-700',
}

function Field({ label, value, editable, onChange, type = 'text' }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      {editable ? (
        <input
          type={type}
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-500"
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <div className="text-sm text-gray-800 py-1">{value ?? <span className="text-gray-400 italic">—</span>}</div>
      )}
    </div>
  )
}

export default function ReviewModal({ activityId, onClose, onUpdated }) {
  const [record, setRecord] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [approving, setApproving] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [error, setError] = useState('')
  const [edits, setEdits] = useState({})
  const [showRaw, setShowRaw] = useState(false)
  const [showLog, setShowLog] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.getActivity(activityId)
      .then((r) => { setRecord(r); setEdits({}) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [activityId])

  const isLocked = record?.status === 'APPROVED'
  const isDirty = Object.keys(edits).length > 0

  function edit(field, value) {
    setEdits((prev) => ({ ...prev, [field]: value }))
  }

  function val(field) {
    return field in edits ? edits[field] : record?.[field]
  }

  async function handleSave() {
    if (!isDirty) return
    setSaving(true)
    setError('')
    try {
      const updated = await api.patchActivity(activityId, { ...edits, edited_by: 'analyst' })
      setRecord(updated)
      setEdits({})
      onUpdated?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleApprove() {
    setApproving(true)
    setError('')
    try {
      const updated = await api.approveActivity(activityId, 'analyst')
      setRecord(updated)
      onUpdated?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setApproving(false)
    }
  }

  async function handleReject() {
    setRejecting(true)
    setError('')
    try {
      const updated = await api.rejectActivity(activityId)
      setRecord(updated)
      onUpdated?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setRejecting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="flex-1 bg-black/40" onClick={onClose} />

      {/* Drawer */}
      <div className="w-[640px] bg-white shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="font-semibold text-gray-900">Review Record</h2>
            {record && (
              <p className="text-xs text-gray-400 font-mono mt-0.5">{record.id}</p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {record && <StatusChip status={record.status} />}
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
          </div>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">Loading…</div>
        ) : !record ? (
          <div className="flex-1 flex items-center justify-center text-red-500">{error}</div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
              {/* Flags */}
              {record.flags?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Flags</p>
                  <div className="flex flex-wrap gap-1.5">
                    {record.flags.map((f) => (
                      <span key={f} className={`badge ${FLAG_COLORS[f] || 'bg-gray-100 text-gray-700'}`}>
                        ⚠ {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Classification */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Classification</p>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Scope" value={val('scope')} editable={!isLocked} onChange={(v) => edit('scope', v)} />
                  <Field label="Category" value={val('category')} editable={!isLocked} onChange={(v) => edit('category', v)} />
                </div>
              </div>

              {/* Quantities */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Quantity</p>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Original Qty" value={val('quantity')} editable={!isLocked} type="number" onChange={(v) => edit('quantity', v)} />
                  <Field label="Original Unit" value={val('unit_original')} editable={!isLocked} onChange={(v) => edit('unit_original', v)} />
                  <Field label="Normalized Qty" value={val('quantity_normalized')} editable={!isLocked} type="number" onChange={(v) => edit('quantity_normalized', v)} />
                  <Field label="Normalized Unit" value={val('unit_normalized')} editable={!isLocked} onChange={(v) => edit('unit_normalized', v)} />
                </div>
              </div>

              {/* Dates */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Dates</p>
                <div className="grid grid-cols-3 gap-3">
                  <Field label="Activity Date" value={val('activity_date')} editable={!isLocked} type="date" onChange={(v) => edit('activity_date', v)} />
                  <Field label="Period Start" value={val('period_start')} editable={!isLocked} type="date" onChange={(v) => edit('period_start', v)} />
                  <Field label="Period End" value={val('period_end')} editable={!isLocked} type="date" onChange={(v) => edit('period_end', v)} />
                </div>
              </div>

              {/* Attribution */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Attribution</p>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Facility ID" value={val('facility_id')} editable={!isLocked} onChange={(v) => edit('facility_id', v)} />
                  <Field label="Facility Name" value={val('facility_name')} editable={!isLocked} onChange={(v) => edit('facility_name', v)} />
                  <Field label="Meter ID" value={val('meter_id')} editable={!isLocked} onChange={(v) => edit('meter_id', v)} />
                  <Field label="Vendor" value={val('vendor')} editable={!isLocked} onChange={(v) => edit('vendor', v)} />
                  <Field label="Cost Amount" value={val('cost_amount')} editable={!isLocked} type="number" onChange={(v) => edit('cost_amount', v)} />
                  <Field label="Currency" value={val('cost_currency')} editable={!isLocked} onChange={(v) => edit('cost_currency', v)} />
                </div>
              </div>

              {/* Travel fields (shown if relevant) */}
              {(record.travel_mode || record.category === 'FLIGHT' || record.category === 'HOTEL' || record.category === 'GROUND') && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Travel</p>
                  <div className="grid grid-cols-3 gap-3">
                    <Field label="Mode" value={val('travel_mode')} editable={!isLocked} onChange={(v) => edit('travel_mode', v)} />
                    <Field label="Origin" value={val('origin')} editable={!isLocked} onChange={(v) => edit('origin', v)} />
                    <Field label="Destination" value={val('destination')} editable={!isLocked} onChange={(v) => edit('destination', v)} />
                    <Field label="Distance (km)" value={val('distance_km')} editable={!isLocked} type="number" onChange={(v) => edit('distance_km', v)} />
                    <Field label="Cabin Class" value={val('cabin_class')} editable={!isLocked} onChange={(v) => edit('cabin_class', v)} />
                    <Field label="Nights" value={val('nights')} editable={!isLocked} type="number" onChange={(v) => edit('nights', v)} />
                  </div>
                </div>
              )}

              {/* Procurement fields */}
              {record.category === 'PROCUREMENT' && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Procurement</p>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Material Group" value={val('material_group')} editable={!isLocked} onChange={(v) => edit('material_group', v)} />
                    <Field label="Item Description" value={val('item_description')} editable={!isLocked} onChange={(v) => edit('item_description', v)} />
                    <Field label="Spend Amount" value={val('spend_amount')} editable={!isLocked} type="number" onChange={(v) => edit('spend_amount', v)} />
                    <Field label="Spend Currency" value={val('spend_currency')} editable={!isLocked} onChange={(v) => edit('spend_currency', v)} />
                  </div>
                </div>
              )}

              {/* Lock info */}
              {isLocked && (
                <div className="px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
                  ✓ Approved by <strong>{record.locked_by}</strong> on {new Date(record.locked_at).toLocaleString()}
                </div>
              )}

              {/* Raw JSON */}
              <div>
                <button
                  className="text-xs text-brand-600 hover:underline font-medium"
                  onClick={() => setShowRaw((v) => !v)}
                >
                  {showRaw ? '▲ Hide' : '▼ Show'} raw payload
                </button>
                {showRaw && (
                  <pre className="mt-2 p-3 bg-gray-900 text-green-400 text-xs rounded-lg overflow-auto max-h-48 font-mono">
                    {JSON.stringify(record.raw_record?.raw_payload, null, 2)}
                  </pre>
                )}
              </div>

              {/* Edit log */}
              {record.edit_logs?.length > 0 && (
                <div>
                  <button
                    className="text-xs text-brand-600 hover:underline font-medium"
                    onClick={() => setShowLog((v) => !v)}
                  >
                    {showLog ? '▲ Hide' : '▼ Show'} edit log ({record.edit_logs.length})
                  </button>
                  {showLog && (
                    <div className="mt-2 space-y-2">
                      {record.edit_logs.map((log) => (
                        <div key={log.id} className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-xs">
                          <div className="flex justify-between text-gray-500 mb-1">
                            <span>By <strong>{log.edited_by}</strong></span>
                            <span>{new Date(log.edited_at).toLocaleString()}</span>
                          </div>
                          {Object.keys(log.after).map((k) => (
                            <div key={k}>
                              <span className="text-gray-400">{k}:</span>{' '}
                              <span className="line-through text-red-400">{String(log.before[k])}</span>{' → '}
                              <span className="text-green-600">{String(log.after[k])}</span>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer actions */}
            {error && (
              <div className="px-6 py-2 bg-red-50 border-t border-red-100 text-sm text-red-600">{error}</div>
            )}
            {!isLocked && (
              <div className="px-6 py-4 border-t border-gray-200 flex items-center gap-3">
                <button
                  onClick={handleSave}
                  disabled={saving || !isDirty}
                  className="btn-secondary"
                >
                  {saving ? 'Saving…' : 'Save Edits'}
                </button>
                <button
                  onClick={handleApprove}
                  disabled={approving || isDirty}
                  className="btn-primary"
                  title={isDirty ? 'Save edits first before approving' : ''}
                >
                  {approving ? 'Approving…' : '✓ Approve'}
                </button>
                <button
                  onClick={handleReject}
                  disabled={rejecting}
                  className="btn-danger ml-auto"
                >
                  {rejecting ? 'Rejecting…' : 'Reject'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function StatusChip({ status }) {
  const map = {
    PENDING_REVIEW: 'bg-yellow-100 text-yellow-800',
    APPROVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800',
  }
  return <span className={`badge text-xs ${map[status] || 'bg-gray-100 text-gray-600'}`}>{status}</span>
}
