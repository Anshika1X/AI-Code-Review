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
  let lastActiveTrigger = null;

  if (deleteModalEl && window.bootstrap) {
    bsDeleteModal = new bootstrap.Modal(deleteModalEl);

    // Ensure aria-hidden is not present when showing or active
    deleteModalEl.addEventListener('show.bs.modal', () => {
      deleteModalEl.removeAttribute('aria-hidden');
    });

    // Move focus inside the modal when opened (Cancel button for safety)
    deleteModalEl.addEventListener('shown.bs.modal', () => {
      deleteModalEl.removeAttribute('aria-hidden');
      const cancelBtn = document.getElementById('cancelDeleteBtn') || deleteModalEl.querySelector('[data-bs-dismiss="modal"]');
      if (cancelBtn) {
        cancelBtn.focus();
      }
    });

    // Release focus from modal descendants before hide sets aria-hidden
    deleteModalEl.addEventListener('hide.bs.modal', () => {
      if (deleteModalEl.contains(document.activeElement)) {
        document.activeElement.blur();
      }
    });

    // Return focus to the triggering element after closing (or fallback if deleted)
    deleteModalEl.addEventListener('hidden.bs.modal', () => {
      if (lastActiveTrigger && document.body.contains(lastActiveTrigger)) {
        lastActiveTrigger.focus();
      } else {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) searchInput.focus();
      }
      lastActiveTrigger = null;
    });
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
            <h6 class="fw-bold text-dark">No reviews matching criteria</h6>
            <p class="small text-muted mb-0">Try clearing the search query or changing the filter.</p>
          </td>
        </tr>
      `;
      return;
    }

    historyTableBody.innerHTML = filtered.map(r => {
      let scoreBadgeStyle = 'background-color: var(--sev-medium-bg); color: var(--sev-medium-text); border: 1px solid var(--sev-medium-border);';
      if (r.score < 60) {
        scoreBadgeStyle = 'background-color: var(--sev-critical-bg); color: var(--sev-critical-text); border: 1px solid var(--sev-critical-border);';
      } else if (r.score < 80) {
        scoreBadgeStyle = 'background-color: var(--sev-high-bg); color: var(--sev-high-text); border: 1px solid var(--sev-high-border);';
      }

      const dateStr = r.created_at ? new Date(r.created_at).toLocaleString() : 'Recent';

      return `
        <tr>
          <td>
            <div class="fw-bold text-dark">${escapeHtml(r.language)}</div>
            <div class="small text-muted text-truncate" style="max-width: 340px;">${escapeHtml(r.summary)}</div>
          </td>
          <td>
            <span class="badge px-2 py-1" style="${scoreBadgeStyle}">${r.score} / 100</span>
          </td>
          <td>
            <span class="badge bg-white text-muted border">${r.issues_count} finding${r.issues_count === 1 ? '' : 's'}</span>
          </td>
          <td class="small text-muted">${dateStr}</td>
          <td class="text-end">
            <div class="d-inline-flex gap-1">
              <a href="result.html?id=${r.id}" class="btn btn-sm btn-subtle text-decoration-none" style="padding: 0.25rem 0.65rem; font-size: 0.8rem;">Inspect</a>
              <button type="button" class="btn btn-sm btn-subtle text-danger delete-review-btn" data-id="${r.id}" title="Delete Review" style="padding: 0.25rem 0.5rem;">
                <svg style="width: 14px; height: 14px; stroke: currentColor; stroke-width: 2; fill: none;" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Attach delete listeners
    document.querySelectorAll('.delete-review-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        lastActiveTrigger = btn;
        pendingDeleteId = btn.getAttribute('data-id');
        if (bsDeleteModal) {
          bsDeleteModal.show(btn);
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
        const idToDelete = pendingDeleteId;
        pendingDeleteId = null;
        if (bsDeleteModal) {
          bsDeleteModal.hide();
        }
        await executeDelete(idToDelete);
      }
    });
  }

  searchInput.addEventListener('input', renderTable);
  scoreFilterSelect.addEventListener('change', renderTable);

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
