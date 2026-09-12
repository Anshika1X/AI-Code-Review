/**
 * Review Results page logic: Renders score, breakdown, category tabs, and diff
 */

document.addEventListener('DOMContentLoaded', async () => {
  Auth.requireAuth();

  const urlParams = new URLSearchParams(window.location.search);
  const reviewId = urlParams.get('id');

  if (!reviewId) {
    window.location.href = 'history.html';
    return;
  }

  const breadcrumbReviewId = document.getElementById('breadcrumbReviewId');
  const scoreValue = document.getElementById('scoreValue');
  const scoreCircle = document.getElementById('scoreCircle');
  const languageBadge = document.getElementById('languageBadge');
  const timestampBadge = document.getElementById('timestampBadge');
  const totalIssuesBadge = document.getElementById('totalIssuesBadge');
  const summaryText = document.getElementById('summaryText');

  const countCritical = document.getElementById('countCritical');
  const countHigh = document.getElementById('countHigh');
  const countMedium = document.getElementById('countMedium');
  const countLow = document.getElementById('countLow');

  const issuesContainer = document.getElementById('issuesContainer');
  const originalCodeBlock = document.getElementById('originalCodeBlock');
  const suggestedCodeBlock = document.getElementById('suggestedCodeBlock');
  const origLineCount = document.getElementById('origLineCount');
  const copySuggestedCodeBtn = document.getElementById('copySuggestedCodeBtn');
  const filterTabs = document.querySelectorAll('#categoryFilterTabs .filter-btn');

  let reviewData = null;
  let allIssues = [];
  let combinedSuggestedCode = '';

  try {
    const res = await apiClient.get(`/api/reviews/${reviewId}`);
    if (!res.success || !res.review) {
      throw new Error(res.error || 'Failed to retrieve code review details.');
    }

    reviewData = res.review;
    allIssues = reviewData.issues || [];

    breadcrumbReviewId.textContent = `Review #${reviewData.id}`;
    scoreValue.textContent = reviewData.score;
    languageBadge.textContent = reviewData.language;
    timestampBadge.textContent = reviewData.created_at ? new Date(reviewData.created_at).toLocaleString() : '';
    totalIssuesBadge.textContent = `${allIssues.length} Finding${allIssues.length === 1 ? '' : 's'}`;
    summaryText.textContent = reviewData.summary;

    // Set score circle color
    if (reviewData.score >= 80) {
      scoreCircle.style.borderColor = '#4F5D2A';
    } else if (reviewData.score >= 60) {
      scoreCircle.style.borderColor = '#C87D2B';
    } else {
      scoreCircle.style.borderColor = '#B94A48';
    }

    // Calculate severity counts
    let critical = 0, high = 0, medium = 0, low = 0;
    allIssues.forEach(i => {
      const sev = (i.severity || '').toLowerCase();
      if (sev === 'critical') critical++;
      else if (sev === 'high') high++;
      else if (sev === 'medium') medium++;
      else low++;
    });

    countCritical.textContent = critical;
    countHigh.textContent = high;
    countMedium.textContent = medium;
    countLow.textContent = low;

    // Display original code
    originalCodeBlock.textContent = reviewData.code || '// No source code provided';
    const lines = (reviewData.code || '').split('\n').length;
    origLineCount.textContent = `${lines} lines`;

    // Aggregate suggested code
    const suggestedSnippets = allIssues
      .filter(i => i.suggested_code && i.suggested_code.trim())
      .map(i => `// Finding (Line ${i.line_number || 'General'}): ${i.message}\n${i.suggested_code}`);

    if (suggestedSnippets.length > 0) {
      combinedSuggestedCode = suggestedSnippets.join('\n\n// ----------------------------------------\n\n');
      suggestedCodeBlock.textContent = combinedSuggestedCode;
    } else {
      combinedSuggestedCode = reviewData.code;
      suggestedCodeBlock.textContent = '// No refactoring needed or suggested for this snippet.';
    }

    // Render Issue Cards
    renderIssues('ALL');

    // Setup Category Filter Tabs
    filterTabs.forEach(btn => {
      btn.addEventListener('click', () => {
        filterTabs.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const category = btn.getAttribute('data-category');
        renderIssues(category);
      });
    });

  } catch (err) {
    showToast(err.message, 'error');
    issuesContainer.innerHTML = `
      <div class="alert alert-danger py-4 text-center">
        <h5>Error Loading Review</h5>
        <p class="mb-2">${escapeHtml(err.message)}</p>
        <a href="dashboard.html" class="btn btn-sm btn-olive mt-2">Return to Dashboard</a>
      </div>
    `;
  }

  function renderIssues(categoryFilter) {
    const filtered = categoryFilter === 'ALL'
      ? allIssues
      : allIssues.filter(i => (i.category || '').toLowerCase() === categoryFilter.toLowerCase());

    if (filtered.length === 0) {
      issuesContainer.innerHTML = `
        <div class="card-clean text-center py-5 text-muted">
          <div class="mb-2" style="font-size: 2.2rem;">🎉</div>
          <h5 class="fw-bold text-dark mb-1">No ${categoryFilter === 'ALL' ? '' : categoryFilter} Issues Found</h5>
          <p class="small text-muted mb-0">The code demonstrates good practices in this area.</p>
        </div>
      `;
      return;
    }

    issuesContainer.innerHTML = filtered.map(issue => {
      const sev = issue.severity || 'Medium';
      const cat = issue.category || 'Code Quality';
      const lineNum = issue.line_number ? `Line ${issue.line_number}` : 'Global Scope';

      return `
        <div class="issue-card severity-${escapeHtml(sev)}">
          <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
            <div class="d-flex align-items-center gap-2">
              <span class="badge-category">${escapeHtml(cat)}</span>
              <span class="badge-severity ${escapeHtml(sev)}">${escapeHtml(sev)}</span>
              <span class="badge-line">${escapeHtml(lineNum)}</span>
            </div>
          </div>

          <h5 class="fw-bold mb-2 text-dark">${escapeHtml(issue.message)}</h5>
          
          <div class="mb-2">
            <div class="small fw-bold text-muted text-uppercase" style="letter-spacing: 0.05em; font-size: 0.75rem;">Explanation</div>
            <p class="small text-dark mb-1">${escapeHtml(issue.explanation)}</p>
          </div>

          <div class="mb-3">
            <div class="small fw-bold text-success text-uppercase" style="letter-spacing: 0.05em; font-size: 0.75rem;">Recommendation</div>
            <p class="small text-dark mb-0">${escapeHtml(issue.recommendation)}</p>
          </div>

          ${issue.suggested_code ? `
            <div class="mt-3">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="small fw-semibold text-muted">SUGGESTED IMPLEMENTATION</span>
              </div>
              <div class="code-snippet-box">
                <code>${escapeHtml(issue.suggested_code)}</code>
              </div>
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  }

  // Copy suggested code handler
  copySuggestedCodeBtn.addEventListener('click', async () => {
    if (!combinedSuggestedCode) {
      showToast('No suggested code to copy.', 'info');
      return;
    }

    try {
      await navigator.clipboard.writeText(combinedSuggestedCode);
      showToast('Suggested code copied to clipboard!', 'info');
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = combinedSuggestedCode;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      textarea.remove();
      showToast('Suggested code copied to clipboard!', 'info');
    }
  });
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
