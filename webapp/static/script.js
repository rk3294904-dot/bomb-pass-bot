// Game state
let currentWord = '';
let currentEmoji = '';
let correctCount = 0;
let coinCount = 0;
let timer = 30;
let timerInterval = null;
let isPlaying = false;

// DOM elements
const emojiDisplay = document.getElementById('emojiDisplay');
const guessInput = document.getElementById('guessInput');
const guessBtn = document.getElementById('guessBtn');
const message = document.getElementById('message');
const timerFill = document.getElementById('timerFill');
const timerText = document.getElementById('timerText');
const correctCountEl = document.getElementById('correctCount');
const coinCountEl = document.getElementById('coinCount');
const startBtn = document.getElementById('startBtn');
const newWordBtn = document.getElementById('newWordBtn');
const leaderboardList = document.getElementById('leaderboardList');

// Fetch new word from API
async function fetchWord() {
    try {
        const res = await fetch('/api/word');
        const data = await res.json();
        currentWord = data.word;
        currentEmoji = data.emoji;
        emojiDisplay.textContent = currentEmoji;
    } catch (err) {
        emojiDisplay.textContent = '❌ Error loading word';
    }
}

// Check guess
async function checkGuess() {
    const guess = guessInput.value.trim();
    if (!guess) return;
    
    try {
        const res = await fetch('/api/check_guess', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guess: guess, answer: currentWord })
        });
        const data = await res.json();
        
        if (data.correct) {
            showMessage('✅ Correct! +10 coins', 'correct');
            correctCount++;
            coinCount += 10;
            correctCountEl.textContent = correctCount;
            coinCountEl.textContent = coinCount;
            resetTimer();
            await fetchWord();
        } else {
            showMessage('❌ Wrong! Try again!', 'wrong');
        }
    } catch (err) {
        showMessage('Error checking guess', 'wrong');
    }
    
    guessInput.value = '';
    guessInput.focus();
}

// Show message
function showMessage(msg, type) {
    message.textContent = msg;
    message.className = 'message ' + type;
    setTimeout(() => {
        message.textContent = '';
        message.className = 'message';
    }, 2000);
}

// Timer functions
function startTimer() {
    timer = 30;
    updateTimerDisplay();
    timerInterval = setInterval(() => {
        timer--;
        updateTimerDisplay();
        if (timer <= 0) {
            clearInterval(timerInterval);
            showMessage('💥 Time up! New word...', 'wrong');
            fetchWord();
            resetTimer();
        }
    }, 1000);
}

function resetTimer() {
    clearInterval(timerInterval);
    timer = 30;
    updateTimerDisplay();
    if (isPlaying) startTimer();
}

function updateTimerDisplay() {
    timerText.textContent = timer + 's';
    const percent = (timer / 30) * 100;
    timerFill.style.width = percent + '%';
    
    if (timer <= 5) {
        timerFill.style.background = '#ff6b6b';
        timerText.style.color = '#ff6b6b';
    } else if (timer <= 10) {
        timerFill.style.background = 'linear-gradient(90deg, #ffaa00, #ff6b6b)';
        timerText.style.color = '#ffaa00';
    } else {
        timerFill.style.background = 'linear-gradient(90deg, #00ff88, #ffaa00)';
        timerText.style.color = '#00ff88';
    }
}

// Start game
function startGame() {
    isPlaying = true;
    correctCount = 0;
    coinCount = 0;
    correctCountEl.textContent = '0';
    coinCountEl.textContent = '0';
    fetchWord();
    resetTimer();
    guessInput.focus();
    showMessage('🎮 Game Started!', 'correct');
}

// Load leaderboard
async function loadLeaderboard() {
    try {
        const res = await fetch('/api/leaderboard');
        const data = await res.json();
        
        if (data.length === 0) {
            leaderboardList.innerHTML = '<p style="text-align:center;color:#aaa;">No players yet!</p>';
            return;
        }
        
        const medals = ['🥇', '🥈', '🥉'];
        leaderboardList.innerHTML = data.map((p, i) => `
            <div class="leader-item">
                <span><span class="medal">${medals[i] || '👤'}</span> ${p.name}</span>
                <span>💰 ${p.coins}</span>
            </div>
        `).join('');
    } catch (err) {
        leaderboardList.innerHTML = '<p style="text-align:center;color:#aaa;">Could not load</p>';
    }
}

// Event listeners
guessBtn.addEventListener('click', checkGuess);
guessInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') checkGuess();
});
startBtn.addEventListener('click', startGame);
newWordBtn.addEventListener('click', () => {
    fetchWord();
    resetTimer();
    showMessage('🔄 New word!', 'correct');
});

// Initial load
loadLeaderboard();
fetchWord();
updateTimerDisplay();