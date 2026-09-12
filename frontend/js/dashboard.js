/**
 * Dashboard analytics and chart rendering with restrained, cohesive theme
 */

document.addEventListener('DOMContentLoaded', async () => {
  Auth.requireAuth();

  const statTotalReviews = document.getElementById('statTotalReviews');
  const statAverageScore = document.getElementById('statAverageScore');
  const statCriticalIssues = document.getElementById('statCriticalIssues');
  const statSecurityIssues = document.getElementById('statSecurityIssues');
  const recentTableBody = document.getElementById('recentReviewsTableBody');

  let trendChartInstance = null;
  let categoryChartInstance = null;

  try {
    const res = await apiClient.get('/api/dashboard');
    if (!res.success) {
      throw new Error(res.error || 'Failed to fetch dashboard data');
    }

    const { stats, score_trend, category_distribution, recent_reviews } = res;

    // 1. Update Metrics Cards
    statTotalReviews.textContent = stats.total_reviews;
    statAverageScore.innerHTML = `${stats.average_score}<span class="fs-6 text-muted fw-normal">/100</span>`;
    statCriticalIssues.textContent = stats.critical_issues;
    statSecurityIssues.textContent = stats.security_issues;

    // 2. Render Score Trend Chart (Chart.js)
    const trendCtx = document.getElementById('scoreTrendChart').getContext('2d');
    const trendLabels = score_trend.map(item => item.date || `#${item.id}`);
    const trendScores = score_trend.map(item => item.score);

    trendChartInstance = new Chart(trendCtx, {
      type: 'line',
      data: {
        labels: trendLabels.length ? trendLabels : ['No reviews yet'],
        datasets: [{
          label: 'Quality Score',
          data: trendScores.length ? trendScores : [0],
          borderColor: '#4F5D2A',
          backgroundColor: 'rgba(107, 122, 58, 0.08)',
          borderWidth: 2,
          fill: true,
          tension: 0.25,
          pointBackgroundColor: '#4F5D2A',
          pointBorderColor: '#FFFFFF',
          pointBorderWidth: 1.5,
          pointRadius: 3.5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1F2418',
            titleFont: { size: 12 },
            bodyFont: { size: 12 },
            padding: 10,
            cornerRadius: 6
          }
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            grid: { color: '#E8EDD8' },
            ticks: { font: { size: 11 } }
          },
          x: {
            grid: { display: false },
            ticks: { font: { size: 11 } }
          }
        }
      }
    });

    // 3. Render Issues by Category Chart
    const catCtx = document.getElementById('categoryChart').getContext('2d');
    const catLabels = Object.keys(category_distribution);
    const catValues = Object.values(category_distribution);

    categoryChartInstance = new Chart(catCtx, {
      type: 'doughnut',
      data: {
        labels: catLabels,
        datasets: [{
          data: catValues,
          backgroundColor: [
            '#A66420', // Security (refined amber)
            '#9E3836', // Bugs (refined crimson)
            '#4F5D2A', // Performance (dark olive)
            '#6B7A3A', // Code Quality (primary olive)
            '#8F9C66', // Best Practices (medium olive)
            '#68705B'  // Maintainability (slate olive)
          ],
          borderWidth: 1.5,
          borderColor: '#FFFFFF'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 10, font: { size: 11 }, padding: 12 }
          }
        },
        cutout: '68%'
      }
    });

    // 4. Render Recent Reviews Table
    if (!recent_reviews || recent_reviews.length === 0) {
      recentTableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-5 text-muted">
            <div class="fw-bold mb-1 text-dark">No reviews recorded</div>
            <p class="small text-muted mb-3">Submit a code snippet to run automated quality analysis.</p>
            <a href="review.html" class="btn-olive text-decoration-none">+ Start Code Review</a>
          </td>
        </tr>
      `;
    } else {
      recentTableBody.innerHTML = recent_reviews.map(r => {
        let scoreBadgeStyle = 'background-color: var(--sev-medium-bg); color: var(--sev-medium-text); border: 1px solid var(--sev-medium-border);';
        if (r.score < 60) {
          scoreBadgeStyle = 'background-color: var(--sev-critical-bg); color: var(--sev-critical-text); border: 1px solid var(--sev-critical-border);';
        } else if (r.score < 80) {
          scoreBadgeStyle = 'background-color: var(--sev-high-bg); color: var(--sev-high-text); border: 1px solid var(--sev-high-border);';
        }

        return `
          <tr>
            <td>
              <div class="fw-semibold text-dark">${escapeHtml(r.language)}</div>
              <div class="small text-muted text-truncate" style="max-width: 320px;">${escapeHtml(r.summary)}</div>
            </td>
            <td>
              <span class="badge px-2 py-1" style="${scoreBadgeStyle}">${r.score} / 100</span>
            </td>
            <td>
              <span class="badge bg-white text-dark border">${r.issues_count} finding${r.issues_count === 1 ? '' : 's'}</span>
            </td>
            <td class="small text-muted">${r.created_at}</td>
            <td class="text-end">
              <a href="result.html?id=${r.id}" class="btn btn-sm btn-subtle text-decoration-none">Inspect &rarr;</a>
            </td>
          </tr>
        `;
      }).join('');
    }

  } catch (err) {
    showToast(err.message, 'error');
    recentTableBody.innerHTML = `
      <tr>
        <td colspan="5" class="text-center text-danger py-4">
          Error loading dashboard data: ${escapeHtml(err.message)}
        </td>
      </tr>
    `;
  }
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
