/**
 * Dashboard analytics and chart rendering
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
    statAverageScore.innerHTML = `${stats.average_score}<span class="fs-6 text-muted">/100</span>`;
    statCriticalIssues.textContent = stats.critical_issues;
    statSecurityIssues.textContent = stats.security_issues;

    // 2. Render Score Trend Chart (Chart.js)
    const trendCtx = document.getElementById('scoreTrendChart').getContext('2d');
    const trendLabels = score_trend.map(item => item.date || `Review #${item.id}`);
    const trendScores = score_trend.map(item => item.score);

    trendChartInstance = new Chart(trendCtx, {
      type: 'line',
      data: {
        labels: trendLabels.length ? trendLabels : ['No data yet'],
        datasets: [{
          label: 'Code Quality Score',
          data: trendScores.length ? trendScores : [0],
          borderColor: '#6B7A3A',
          backgroundColor: 'rgba(107, 122, 58, 0.12)',
          borderWidth: 2.5,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: '#4F5D2A',
          pointRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            grid: { color: '#E8EDD8' }
          },
          x: {
            grid: { display: false }
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
            '#C87D2B', // Security
            '#B94A48', // Bugs
            '#6B7A3A', // Performance
            '#4F5D2A', // Code Quality
            '#8A9A5B', // Best Practices
            '#B0BE96'  // Maintainability
          ],
          borderWidth: 2,
          borderColor: '#FFFFFF'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 12, font: { size: 11 } }
          }
        }
      }
    });

    // 4. Render Recent Reviews Table
    if (!recent_reviews || recent_reviews.length === 0) {
      recentTableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center py-5 text-muted">
            <div class="mb-2" style="font-size: 2rem;">🚀</div>
            <div class="fw-bold mb-1">No reviews yet</div>
            <p class="small text-muted mb-3">Submit your first code snippet to see AI insights here.</p>
            <a href="review.html" class="btn-olive btn-sm text-decoration-none">+ Start Your First Review</a>
          </td>
        </tr>
      `;
    } else {
      recentTableBody.innerHTML = recent_reviews.map(r => {
        let badgeColor = 'bg-secondary';
        if (r.score >= 80) badgeColor = 'bg-success';
        else if (r.score >= 60) badgeColor = 'bg-warning text-dark';
        else badgeColor = 'bg-danger';

        return `
          <tr>
            <td>
              <span class="fw-semibold">${escapeHtml(r.language)}</span>
              <div class="small text-muted text-truncate" style="max-width: 280px;">${escapeHtml(r.summary)}</div>
            </td>
            <td>
              <span class="badge ${badgeColor} px-2 py-1">${r.score}/100</span>
            </td>
            <td>
              <span class="badge bg-light text-dark border">${r.issues_count} issues</span>
            </td>
            <td class="small text-muted">${r.created_at}</td>
            <td class="text-end">
              <a href="result.html?id=${r.id}" class="btn btn-sm btn-olive-subtle text-decoration-none">View Report →</a>
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
