/**
 * Review History page logic: List, search, score filter, and delete
 */

document.addEventListener('DOMContentLoaded', async () => {
  Auth.requireAuth();

  const historyTableBody = document.getElementById('historyTableBody');
  const searchInput = document.getElementById('searchInput');
  const scoreFilterSelect = document.getElementById('scoreFilterSelect');
  const totalHistoryCounter = document.getElementById('totalHistoryCounter');
  const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
  const deleteModalEl = document.getElementById('deleteConfirmModal');

  let bsDeleteModal = null;
  if (deleteModalEl && window.bootstrap) {
    bsDeleteModal = new bootstrap.Modal(deleteModalEl);
  }

  let allReviews = [];
  let pendingDeleteId = null;

  async function loadHistory() {
    try {
      const res = await apiClient.get('/api/reviews');
      if (!res.success) {
        throw new Error(res.error || 'Failed to fetch review history');
      }

      allReviews = res.reviews || [];
      renderTable();
    } catch (err) {
      showToast(err.message, 'error');
      historyTableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-5 text-danger">
            Error loading history: ${escapeHtml(err.message)}
          </td>
        </tr>
      `;
    }
  }

  function renderTable() {
    const searchTerm = searchInput.value.toLowerCase().trim();
    const scoreFilter = scoreFilterSelect.value;

    const filtered = allReviews.filter(r => {
      // 1. Search term matching
      const matchesSearch = !searchTerm ||
        (r.language && r.language.toLowerCase().includes(searchTerm)) ||
        (r.summary && r.summary.toLowerCase().includes(searchTerm));

      if (!matchesSearch) return false;

      // 2. Score filtering
      if (scoreFilter === 'HIGH') return r.score >= 80;
      if (scoreFilter === 'MEDIUM') return r.score >= 60 && r.score < 80;
      if (scoreFilter === 'LOW') return r.score < 60;

      return true;
    });

    totalHistoryCounter.textContent = `Showing ${filtered.length} of ${allReviews.length} review${allReviews.length === 1 ? '' : 's'}`;

    if (filtered.length === 0) {
      historyTableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-5 text-muted">
            <div class="mb-2" style="font-size: 2rem;">🔍</div>
            <h6 class="fw-bold text-dark">No reviews found</h6>
            <p class="small text-muted mb-0">Try adjusting your search query or score filter.</p>
          </td>
        </tr>
      `;
      return;
    }

    historyTableBody.innerHTML = filtered.map(r => {
      let badgeClass = 'bg-secondary';
      if (r.score >= 80) badgeClass = 'bg-success';
      else if (r.score >= 60) badgeClass = 'bg-warning text-dark';
      else badgeClass = 'bg-danger';

      const dateStr = r.created_at ? new Date(r.created_at).toLocaleString() : 'Recent';

      return `
        <tr>
          <td>
            <div class="fw-bold">${escapeHtml(r.language)}</div>
            <div class="small text-muted text-truncate" style="max-width: 320px;">${escapeHtml(r.summary)}</div>
          </td>
          <td>
            <span class="badge ${badgeClass} px-2 py-1">${r.score} / 100</span>
          </td>
          <td>
            <span class="badge bg-light text-dark border">${r.issues_count} finding${r.issues_count === 1 ? '' : 's'}</span>
          </td>
          <td class="small text-muted">${dateStr}</td>
          <td class="text-end">
            <div class="d-inline-flex gap-2">
              <a href="result.html?id=${r.id}" class="btn btn-sm btn-olive-subtle text-decoration-none">View Report</a>
              <button type="button" class="btn btn-sm btn-outline-danger delete-review-btn" data-id="${r.id}" title="Delete Review">🗑️</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Attach delete listeners
    document.querySelectorAll('.delete-review-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        pendingDeleteId = btn.getAttribute('data-id');
        if (bsDeleteModal) {
          bsDeleteModal.show();
        } else if (confirm('Are you sure you want to delete this review?')) {
          executeDelete(pendingDeleteId);
        }
      });
    });
  }

  async function executeDelete(id) {
    try {
      const res = await apiClient.delete(`/api/reviews/${id}`);
      if (res.success) {
        showToast('Review deleted successfully.', 'info');
        allReviews = allReviews.filter(r => r.id != id);
        renderTable();
      } else {
        throw new Error(res.error || 'Failed to delete review');
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener('click', async () => {
      if (pendingDeleteId) {
        if (bsDeleteModal) bsDeleteModal.hide();
        await executeDelete(pendingDeleteId);
        pendingDeleteId = null;
      }
    });
  }

  searchInput.addEventListener('input', renderTable);
  scoreFilterSelect.addEventListener('change', renderTable);

  // Initial load
  loadHistory();
});

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
