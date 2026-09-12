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
  }

  // Update line and character stats
  function updateStats() {
    const text = codeEditor.value;
    const lines = text ? text.split('\n').length : 0;
    const chars = text.length;
    editorStats.textContent = `${lines} line${lines === 1 ? '' : 's'} | ${chars} characters`;
  }

  codeEditor.addEventListener('input', updateStats);

  // Allow pressing Tab inside textarea to insert 4 spaces instead of losing focus
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
    if (codeEditor.value.trim() && !confirm('Are you sure you want to clear the editor?')) {
      return;
    }
    codeEditor.value = '';
    updateStats();
  });

  // Sample code loader
  sampleCodeBtn.addEventListener('click', () => {
    languageSelect.value = 'Python';
    codeEditor.value = `import os
import sqlite3

# Sample Python backend service
DATABASE_PATH = "production_data.db"
API_SECRET_KEY = "AIzaSyB391-fake-super-secret-key"

def fetch_user_profile(user_id):
    """Fetch user profile details from database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Potential SQL injection risk
    query = "SELECT id, username, email FROM users WHERE id = " + str(user_id)
    
    try:
        cursor.execute(query)
        user = cursor.fetchone()
        return user
    except:
        # Bare except clause masks critical runtime exceptions
        print("Database query failed!")
        return None
    finally:
        conn.close()

def compute_analytics(data_list):
    """Redundant nested computation causing performance degradation."""
    results = []
    for item in data_list:
        if item in [x for x in data_list if x > 0]:
            results.append(item * 2)
    return results
`;
    updateStats();
    showToast('Loaded sample code containing security & performance findings!', 'info');
  });

  // Animated loading step runner
  let loadingInterval = null;
  const stages = [
    { title: 'Analyzing Code Structure...', subtitle: 'Parsing abstract syntax tree and logic flow', progress: 25 },
    { title: 'Checking Security Vulnerabilities...', subtitle: 'Scanning for secrets, SQL injections, and OWASP risks', progress: 50 },
    { title: 'Evaluating Performance & Efficiency...', subtitle: 'Detecting complexity bottlenecks and resource leaks', progress: 75 },
    { title: 'Generating AI Recommendations...', subtitle: 'Synthesizing refactored code and final quality score', progress: 92 }
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
      bsGithubModal.show();
    });
  }

  // GitHub Import & Review
  if (fetchGithubBtn) {
    fetchGithubBtn.addEventListener('click', async () => {
      const repoUrl = document.getElementById('githubRepoUrl').value.trim();
      const filePath = document.getElementById('githubFilePath').value.trim();
      const branch = document.getElementById('githubBranch').value.trim() || 'main';

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
