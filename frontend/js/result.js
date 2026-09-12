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
      scoreValue.style.color = '#4F5D2A';
    } else if (reviewData.score >= 60) {
      scoreCircle.style.borderColor = '#A66420';
      scoreValue.style.color = '#A66420';
    } else {
      scoreCircle.style.borderColor = '#9E3836';
      scoreValue.style.color = '#9E3836';
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

    // Display original code exactly as submitted (preserved permanently)
    originalCodeBlock.textContent = reviewData.code || '// No source code provided';
    const lines = (reviewData.code || '').split('\n').length;
    origLineCount.textContent = `${lines} line${lines === 1 ? '' : 's'}`;

    // Aggregate practical suggested refactorings
    const suggestedSnippets = allIssues
      .filter(i => i.suggested_code && i.suggested_code.trim())
      .map(i => {
        const lineInfo = i.line_number ? `Line ${i.line_number}` : 'Global';
        return `// [${lineInfo} - ${i.category}] ${i.message}\n${i.suggested_code}`;
      });

    if (suggestedSnippets.length > 0) {
      combinedSuggestedCode = suggestedSnippets.join('\n\n// ----------------------------------------\n\n');
      suggestedCodeBlock.textContent = combinedSuggestedCode;
    } else {
      combinedSuggestedCode = reviewData.code;
      suggestedCodeBlock.textContent = '// No code refactoring recommendations required for this snippet.';
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
      <div class="card-clean text-center py-4 text-danger">
        <h6 class="fw-bold">Error Loading Review Report</h6>
        <p class="small mb-2">${escapeHtml(err.message)}</p>
        <a href="dashboard.html" class="btn btn-sm btn-subtle mt-1">Return to Dashboard</a>
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
          <h6 class="fw-bold text-dark mb-1">No ${categoryFilter === 'ALL' ? '' : escapeHtml(categoryFilter)} Findings</h6>
          <p class="small text-muted mb-0">The code adheres to established standards in this category.</p>
        </div>
      `;
      return;
    }

    issuesContainer.innerHTML = filtered.map((issue, idx) => {
      const sev = issue.severity || 'Medium';
      const cat = issue.category || 'Code Quality';
      const lineNum = issue.line_number ? `Line ${issue.line_number}` : 'Global';

      return `
        <div class="issue-card severity-${escapeHtml(sev)}">
          <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
            <div class="d-flex align-items-center gap-2">
              <span class="badge-category">${escapeHtml(cat)}</span>
              <span class="badge-severity ${escapeHtml(sev)}">${escapeHtml(sev)}</span>
              <span class="badge-line">${escapeHtml(lineNum)}</span>
            </div>
          </div>

          <h6 class="fw-bold mb-2 text-dark">${escapeHtml(issue.message)}</h6>
          
          <div class="mb-2">
            <div class="small fw-bold text-muted text-uppercase" style="letter-spacing: 0.05em; font-size: 0.7rem;">Explanation</div>
            <p class="small text-dark mb-1">${escapeHtml(issue.explanation)}</p>
          </div>

          <div class="mb-3">
            <div class="small fw-bold text-uppercase" style="color: var(--dark-olive); letter-spacing: 0.05em; font-size: 0.7rem;">Recommendation</div>
            <p class="small text-dark mb-0">${escapeHtml(issue.recommendation)}</p>
          </div>

          ${issue.suggested_code ? `
            <div class="mt-3">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="small fw-semibold text-muted text-uppercase" style="font-size: 0.68rem; letter-spacing: 0.05em;">Suggested Refactoring</span>
                <button type="button" class="btn btn-sm btn-subtle copy-single-snippet-btn" data-index="${idx}" style="padding: 0.15rem 0.5rem; font-size: 0.72rem;">
                  Copy Snippet
                </button>
              </div>
              <div class="code-snippet-box">
                <code>${escapeHtml(issue.suggested_code)}</code>
              </div>
            </div>
          ` : ''}
        </div>
      `;
    }).join('');

    // Attach listeners to per-issue copy buttons
    document.querySelectorAll('.copy-single-snippet-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const issueIdx = parseInt(btn.getAttribute('data-index'), 10);
        const issue = filtered[issueIdx];
        if (issue && issue.suggested_code) {
          try {
            await copyTextToClipboard(issue.suggested_code);
            const originalText = btn.textContent;
            btn.textContent = 'Copied!';
            setTimeout(() => { btn.textContent = originalText; }, 1800);
            showToast('Code snippet copied to clipboard.', 'info');
          } catch {
            showToast('Unable to copy to clipboard.', 'error');
          }
        }
      });
    });
  }

  // Master copy suggested code button
  if (copySuggestedCodeBtn) {
    copySuggestedCodeBtn.addEventListener('click', async () => {
      if (!combinedSuggestedCode) {
        showToast('No suggested code to copy.', 'info');
        return;
      }

      try {
        await copyTextToClipboard(combinedSuggestedCode);
        const originalHtml = copySuggestedCodeBtn.innerHTML;
        copySuggestedCodeBtn.innerHTML = `
          <svg style="width: 14px; height: 14px; stroke: currentColor; stroke-width: 2; fill: none;" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>
          <span>Copied!</span>
        `;
        setTimeout(() => {
          copySuggestedCodeBtn.innerHTML = originalHtml;
        }, 2000);
        showToast('Full suggested code copied to clipboard.', 'info');
      } catch {
        showToast('Unable to copy code to clipboard.', 'error');
      }
    });
  }
});

async function copyTextToClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text);
  }
  // Fallback
  const textarea = document.createElement('textarea');
  textarea.value = text;
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  textarea.remove();
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
