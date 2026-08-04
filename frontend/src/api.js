const API_BASE = 'http://localhost:8000/api'

function buildQuery(params) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') {
      query.set(key, value)
    }
  }
  return query.toString()
}

export async function fetchComplaints(filters, limit, offset) {
  const query = buildQuery({ ...filters, limit, offset })
  const response = await fetch(`${API_BASE}/complaints?${query}`)
  if (!response.ok) {
    throw new Error(`fetchComplaints failed: ${response.status}`)
  }
  return response.json()
}

export async function fetchSummary(filters, limit) {
  const { complaint_type, ...summaryFilters } = filters
  const query = buildQuery({ ...summaryFilters, limit })
  const response = await fetch(`${API_BASE}/complaints/summary?${query}`)
  if (!response.ok) {
    throw new Error(`fetchSummary failed: ${response.status}`)
  }
  return response.json()
}
