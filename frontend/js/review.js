/**
 * Review page logic: Editor interaction, multi-stage loading, and API submission
 */

document.addEventListener('DOMContentLoaded', () => {
  Auth.requireAuth();

  const codeEditor = document.getElementById('codeEditor');
  const languageSelect = document.getElementById('languageSelect');
  const editorStats = document.getElementById('editorStats');
  const clearBtn = document.getElementById('clearBtn');
  const submitReviewBtn = document.getElementById('submitReviewBtn');
  const sampleCodeBtn = document.getElementById('sampleCodeBtn');
  const loadingOverlay = document.getElementById('loadingOverlay');
  const loadingStepTitle = document.getElementById('loadingStepTitle');
  const loadingStepSubtitle = document.getElementById('loadingStepSubtitle');
  const loadingProgressBar = document.getElementById('loadingProgressBar');

  // GitHub Modal elements
  const githubModalBtn = document.getElementById('githubModalBtn');
  const githubModalEl = document.getElementById('githubModal');
  const fetchGithubBtn = document.getElementById('fetchGithubBtn');
  let bsGithubModal = null;
  if (githubModalEl && window.bootstrap) {
    bsGithubModal = new bootstrap.Modal(githubModalEl);
    githubModalEl.addEventListener('show.bs.modal', () => {
      githubModalEl.removeAttribute('aria-hidden');
    });
    githubModalEl.addEventListener('hide.bs.modal', () => {
      if (githubModalEl.contains(document.activeElement)) {
        document.activeElement.blur();
      }
    });
    githubModalEl.addEventListener('hidden.bs.modal', () => {
      if (githubModalBtn) {
        githubModalBtn.focus();
      }
    });
  }

  // Update line and character stats
  function updateStats() {
    const text = codeEditor.value;
    const lines = text ? text.split('\n').length : 0;
    const chars = text.length;
    editorStats.textContent = `${lines} line${lines === 1 ? '' : 's'} | ${chars} chars`;
  }

  codeEditor.addEventListener('input', updateStats);

  // Tab key indentation support (4 spaces)
  codeEditor.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = codeEditor.selectionStart;
      const end = codeEditor.selectionEnd;
      codeEditor.value = codeEditor.value.substring(0, start) + '    ' + codeEditor.value.substring(end);
      codeEditor.selectionStart = codeEditor.selectionEnd = start + 4;
      updateStats();
    }
  });

  // Clear button
  clearBtn.addEventListener('click', () => {
    if (codeEditor.value.trim() && !confirm('Clear current code in editor?')) {
      return;
    }
    codeEditor.value = '';
    updateStats();
  });

  // Sample code snippets (cycling between JavaScript and Python security test cases)
  let sampleIndex = 0;
  const sampleSnippets = [
    {
      language: 'JavaScript',
      code: `function getUser(username) {
    // Dynamic SQL query construction without parameterization
    const query = "SELECT * FROM users WHERE name = '" + username + "'";
    console.log(query);
    return query;
}

getUser("admin");`
    },
    {
      language: 'Python',
      code: `import os
import sqlite3

# Backend user lookup service
API_KEY = "sk_live_9948172648194719"

def fetch_user_data(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # SQL query construction via string concatenation
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    try:
        cursor.execute(query)
        return cursor.fetchone()
    except:
        print("Database query failed")
        return None
    finally:
        conn.close()`
    }
  ];

  sampleCodeBtn.addEventListener('click', () => {
    const sample = sampleSnippets[sampleIndex % sampleSnippets.length];
    languageSelect.value = sample.language;
    codeEditor.value = sample.code;
    sampleIndex++;
    updateStats();
    showToast(`Loaded ${sample.language} sample containing security findings.`, 'info');
  });

  // Multi-stage loading progress
  let loadingInterval = null;
  const stages = [
    { title: 'Analyzing Code Structure...', subtitle: 'Evaluating AST, control flow, and taint propagation', progress: 25 },
    { title: 'Security & Injection Audit...', subtitle: 'Scanning for SQL injection, credentials, and OWASP risks', progress: 50 },
    { title: 'Performance & Resource Analysis...', subtitle: 'Checking computational complexity and memory allocations', progress: 75 },
    { title: 'Synthesizing Recommendations...', subtitle: 'Generating refactored code implementations and scoring', progress: 92 }
  ];

  function startLoadingStages() {
    let currentStage = 0;
    loadingOverlay.style.display = 'flex';
    
    const updateStage = () => {
      const stage = stages[currentStage];
      loadingStepTitle.textContent = stage.title;
      loadingStepSubtitle.textContent = stage.subtitle;
      loadingProgressBar.style.width = `${stage.progress}%`;
      currentStage = (currentStage + 1) % stages.length;
    };

    updateStage();
    loadingInterval = setInterval(updateStage, 1400);
  }

  function stopLoadingStages() {
    if (loadingInterval) {
      clearInterval(loadingInterval);
      loadingInterval = null;
    }
    loadingProgressBar.style.width = '100%';
    loadingOverlay.style.display = 'none';
  }

  // Submit Code Review
  submitReviewBtn.addEventListener('click', async () => {
    const code = codeEditor.value.trim();
    const language = languageSelect.value;

    if (!code) {
      showToast('Please enter some code before starting the review.', 'error');
      codeEditor.focus();
      return;
    }

    startLoadingStages();

    try {
      const res = await apiClient.post('/api/reviews', {
        language,
        code
      });

      if (res.success && res.review) {
        stopLoadingStages();
        window.location.href = `result.html?id=${res.review.id}`;
      } else {
        throw new Error(res.error || 'Failed to complete code review');
      }
    } catch (err) {
      stopLoadingStages();
      showToast(err.message || 'Unable to complete code review. Please try again.', 'error');
    }
  });

  // GitHub Modal launcher
  if (githubModalBtn && bsGithubModal) {
    githubModalBtn.addEventListener('click', () => {
      bsGithubModal.show(githubModalBtn);
    });
  }

  // GitHub Import & Review
  if (fetchGithubBtn) {
    fetchGithubBtn.addEventListener('click', async () => {
      const repoUrl = document.getElementById('githubRepoUrl').value.trim();
      const filePath = document.getElementById('githubFilePath').value.trim();
      const branch = document.getElementById('githubBranch').value.trim() || 'master';

      if (!repoUrl || !filePath) {
        showToast('Please enter both repository URL and file path.', 'error');
        return;
      }

      if (bsGithubModal) bsGithubModal.hide();
      startLoadingStages();

      try {
        const res = await apiClient.post('/api/reviews/github', {
          repo_url: repoUrl,
          file_path: filePath,
          branch
        });

        if (res.success && res.review) {
          stopLoadingStages();
          window.location.href = `result.html?id=${res.review.id}`;
        } else {
          throw new Error(res.error || 'Failed to analyze GitHub file');
        }
      } catch (err) {
        stopLoadingStages();
        showToast(err.message || 'Error fetching GitHub file.', 'error');
      }
    });
  }

  updateStats();
});
