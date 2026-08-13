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

export async function fetchBoroughSummary(filters) {
  const { complaint_type, ...summaryFilters } = filters
  const query = buildQuery({ ...summaryFilters, group_by: 'borough' })
  const response = await fetch(`${API_BASE}/complaints/summary?${query}`)
  if (!response.ok) {
    throw new Error(`fetchBoroughSummary failed: ${response.status}`)
  }
  return response.json()
}

export async function fetchComplaintPoints(filters, limit) {
  const query = buildQuery({ ...filters, limit })
  const response = await fetch(`${API_BASE}/complaints/points?${query}`)
  if (!response.ok) {
    throw new Error(`fetchComplaintPoints failed: ${response.status}`)
  }
  return response.json()
}

export async function askQuestion(question) {
  const response = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.error || `askQuestion failed: ${response.status}`)
  }
  return data
}
