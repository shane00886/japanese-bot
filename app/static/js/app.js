/* ── 小新的日语教室 H5 App ── */

// ═══════════════════════════════════════════
// TTS 语音朗读（浏览器 Web Speech API）
// ═══════════════════════════════════════════

// 音色模式: 'normal' | 'shinchan' | 'misae'
let voiceMode = 'normal';

function setVoiceMode(mode) {
    voiceMode = mode;
    document.querySelectorAll('.voice-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.mode === mode);
    });
    try { localStorage.setItem('jp-voice-mode', mode); } catch(e) {}

    // 切换音色后立即朗读一句，让孩子听到变化
    setTimeout(() => {
        const demos = {
            'shinchan': 'オラはしんのすけ！',
            'misae': 'しんのすけ！ご飯の時間よ！',
            'normal': 'こんにちは。日本語を勉強しましょう。',
        };
        speak(demos[mode] || demos.normal);
    }, 200);
}

// 恢复上次选择的音色
try {
    const saved = localStorage.getItem('jp-voice-mode');
    if (saved) voiceMode = saved;
} catch(e) {}

function getVoiceParams(text) {
    switch (voiceMode) {
        case 'shinchan':
            return { pitch: 2.0, rate: 1.3, desc: '小新音色 🦸', preferFemale: false };
        case 'misae':
            return { pitch: 0.7, rate: 0.75, desc: '美冴音色 👩', preferFemale: true };
        default:
            return { pitch: 1.2, rate: 0.85, desc: '标准音色 📖', preferFemale: true };
    }
}

function speak(text, rate = 0.9) {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    if (!text || !window.speechSynthesis) return;

    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'ja-JP';
    u.rate = rate;
    u.volume = 1.0;

    // 只加音高（不影响播放，只改变音色）
    if (voiceMode === 'shinchan') u.pitch = 2.0;
    else if (voiceMode === 'misae') u.pitch = 0.7;
    else u.pitch = 1.0;

    // 尝试找日语语音（找不到用默认也不影响播放）
    const voices = window.speechSynthesis.getVoices();
    const jpVoice = voices.find(v => v.lang.startsWith('ja'));
    if (jpVoice) u.voice = jpVoice;

    window.speechSynthesis.speak(u);
}

function speakText(element) {
    const text = element.getAttribute('data-speak') || element.textContent;
    speak(text);
}

// 点击播放按钮朗读
document.addEventListener('click', function(e) {
    const btn = e.target.closest('.speak-btn, .voice-btn');
    if (btn) {
        e.preventDefault();
        if (btn.classList.contains('voice-btn')) {
            setVoiceMode(btn.dataset.mode);
        } else {
            const text = btn.getAttribute('data-speak');
            if (text) speak(text);
        }
    }
});

// 预加载语音列表
if (window.speechSynthesis) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}

// === 课程数据（学习内容保留日语） ===
const LESSONS = [
    { id: 'n5_01', no: 1, title: '冒险开始', chapter: '开学季', desc: '自我介绍、数字、颜色', emoji: '🌸',
      jp_title: '冒険の始まり',
      vocab: [
        { jp: '私', kana: 'わたし', cn: '我' },
        { jp: '名前', kana: 'なまえ', cn: '名字' },
        { jp: '学校', kana: 'がっこう', cn: '学校' },
        { jp: '先生', kana: 'せんせい', cn: '老师' },
        { jp: '友達', kana: 'ともだち', cn: '朋友' },
        { jp: '一年生', kana: 'いちねんせい', cn: '一年级' },
    ]},
    { id: 'n5_02', no: 2, title: '小新的一天', chapter: '蜡笔小新', desc: '起床、上学、睡觉', emoji: '🌞',
      jp_title: 'しんちゃんの一日',
      vocab: [
        { jp: '朝', kana: 'あさ', cn: '早上' },
        { jp: '昼', kana: 'ひる', cn: '中午' },
        { jp: '夜', kana: 'よる', cn: '晚上' },
        { jp: '起きる', kana: 'おきる', cn: '起床' },
        { jp: '寝る', kana: 'ねる', cn: '睡觉' },
        { jp: '学校', kana: 'がっこう', cn: '学校' },
    ]},
    { id: 'n5_03', no: 3, title: '生日派对', chapter: '生日', desc: '日期、礼物、食物', emoji: '🎂',
      jp_title: 'お誕生日パーティー',
      vocab: [
        { jp: '誕生日', kana: 'たんじょうび', cn: '生日' },
        { jp: 'プレゼント', kana: 'ぷれぜんと', cn: '礼物' },
        { jp: 'ケーキ', kana: 'けーき', cn: '蛋糕' },
        { jp: '楽しい', kana: 'たのしい', cn: '快乐' },
        { jp: '嬉しい', kana: 'うれしい', cn: '开心' },
        { jp: '欲しい', kana: 'ほしい', cn: '想要' },
    ]},
    { id: 'n5_04', no: 4, title: '校园生活', chapter: '学校', desc: '教室、科目、活动', emoji: '📚',
      jp_title: '学校の一日',
      vocab: [
        { jp: '教室', kana: 'きょうしつ', cn: '教室' },
        { jp: '本', kana: 'ほん', cn: '书' },
        { jp: '勉強', kana: 'べんきょう', cn: '学习' },
        { jp: '絵', kana: 'え', cn: '画' },
        { jp: '歌', kana: 'うた', cn: '歌' },
        { jp: '遊ぶ', kana: 'あそぶ', cn: '玩' },
    ]},
    { id: 'n5_05', no: 5, title: '拉面馆', chapter: '美食', desc: '点餐、味道、价格', emoji: '🍜',
      jp_title: 'ラーメン屋さんへ',
      vocab: [
        { jp: 'ラーメン', kana: 'らーめん', cn: '拉面' },
        { jp: '美味しい', kana: 'おいしい', cn: '好吃' },
        { jp: '値段', kana: 'ねだん', cn: '价格' },
        { jp: '水', kana: 'みず', cn: '水' },
        { jp: 'メニュー', kana: 'めにゅー', cn: '菜单' },
        { jp: 'お箸', kana: 'おはし', cn: '筷子' },
    ]},
];

const SHINCHAN_QUOTES = [
    { jp: '「オラはしんのすけ！よろしく頼むゾ！」', cn: '「我是新之助！请多多关照！」' },
    { jp: '「おはよう！朝だゾ！」', cn: '「早安！是早上了哦！」' },
    { jp: '「楽しいことが一番だゾ！」', cn: '「开心的事最重要！」' },
    { jp: '「ご飯まだ？お腹すいたゾ〜」', cn: '「饭还没好吗？肚子饿了～」' },
    { jp: '「今日はいい天気だね〜」', cn: '「今天天气真好呢～」' },
    { jp: '「オラ、ケーキが食べたいゾ！」', cn: '「我想吃蛋糕！」' },
    { jp: '「オラ、もう待てないゾ！」', cn: '「我已经等不及了！」' },
];

const ACHIEVEMENTS = [
    { id: 'a1', icon: '🔥', name: '第一步', desc: '第一次打卡' },
    { id: 'a2', icon: '🔥', name: '坚持3天', desc: '连续学习3天' },
    { id: 'a3', icon: '⭐', name: '一周达人', desc: '连续学习7天' },
    { id: 'a4', icon: '🏆', name: '半月勇士', desc: '连续学习14天' },
    { id: 'a5', icon: '👑', name: '月度传奇', desc: '连续学习30天' },
    { id: 'a6', icon: '⚡', name: '单词大师', desc: '单词闯关全对' },
    { id: 'a7', icon: '👂', name: '顺风耳', desc: '听力全对3次' },
];

// === 用户状态 ===
let userState = {
    name: '小忍者',
    level: 'N5',
    levelName: '见习忍者',
    xp: 340,
    xpNext: 600,
    streak: 5,
    maxStreak: 12,
    currentLesson: 2,
    completedLessons: [],
    achievements: ['a1', 'a2'],
};

// === 页面切换 ===
function navigate(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`).classList.add('active');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');

    if (page === 'home') refreshHome();
    if (page === 'map') renderMap();
    if (page === 'profile') renderProfile();
    if (page === 'game') startGame();
    if (page === 'speak') startSpeak();
    if (page === 'listen') startListen();
}

// === 首页 ===
function refreshHome() {
    document.getElementById('stat-level').textContent = userState.level;
    document.getElementById('stat-xp').textContent = userState.xp;
    document.getElementById('stat-streak').textContent = userState.streak;
    document.getElementById('level-name').textContent = userState.levelName;
    document.getElementById('xp-text').textContent = `${userState.xp} / ${userState.xpNext}`;
    const pct = Math.min(100, (userState.xp / userState.xpNext) * 100);
    document.getElementById('xp-bar').style.width = `${pct}%`;

    const lesson = LESSONS[userState.currentLesson - 1] || LESSONS[0];
    document.getElementById('today-lesson').textContent = lesson.title;
    document.getElementById('today-chapter').textContent = `${lesson.chapter} · ${lesson.desc}`;
    document.getElementById('today-duration').textContent = '12';

    const q = SHINCHAN_QUOTES[Math.floor(Math.random() * SHINCHAN_QUOTES.length)];
    document.getElementById('shinchan-quote').innerHTML = `${q.jp}<br><span style="font-size:13px;color:#795548;">→ ${q.cn}</span>`;
    const speakBtn = document.querySelector('.speak-btn.mini');
    if (speakBtn) speakBtn.setAttribute('data-speak', q.jp);
}

// === 学习地图 ===
function renderMap() {
    const container = document.getElementById('lesson-list');
    let html = '';
    let completed = 0;

    LESSONS.forEach((l, i) => {
        const isCompleted = userState.completedLessons.includes(l.id);
        const isCurrent = (i + 1) === userState.currentLesson;
        const isLocked = (i + 1) > Math.max(userState.currentLesson, 1);
        if (isCompleted) completed++;

        let cls = 'map-chapter';
        if (isCompleted) cls += ' completed';
        if (isCurrent) cls += ' current';
        if (isLocked && !isCurrent && !isCompleted) cls += ' locked';

        // 解锁逻辑：当前课程和之前的都已解锁
        const isAccessible = (i + 1) <= userState.currentLesson || isCompleted;
        const badge = isCompleted ? '✅' : isCurrent ? '⚔️' : (isAccessible ? '📖' : '🔒');

        html += `
            <div class="${cls}">
                <div class="ch-number">${l.no}</div>
                <div class="ch-info">
                    <div class="ch-title">${l.emoji} ${l.title}</div>
                    <div class="ch-desc">${l.jp_title} · ${l.desc}</div>
                </div>
                <div class="ch-badge">${badge}</div>
            </div>
        `;
    });

    container.innerHTML = html;
    const pct = Math.round((completed / LESSONS.length) * 100);
    document.getElementById('map-progress').textContent = `${pct}%（${completed}/${LESSONS.length} 章完成）`;
}

// === 单词大作战 ===
let gameState = { words: [], current: 0, score: 0, timer: null, timeLeft: 180, finished: false };

function startGame() {
    const allWords = [];
    LESSONS.forEach(l => l.vocab.forEach(v => allWords.push({ ...v, lessonId: l.id })));
    const shuffled = allWords.sort(() => Math.random() - 0.5).slice(0, 8);

    gameState = {
        words: shuffled,
        current: 0, score: 0, timer: null,
        timeLeft: shuffled.length * 20, finished: false,
    };

    document.getElementById('game-result').style.display = 'none';
    document.getElementById('game-area').style.display = 'block';
    document.getElementById('game-score').textContent = '0';
    updateTimer();

    if (gameState.timer) clearInterval(gameState.timer);
    gameState.timer = setInterval(() => {
        gameState.timeLeft--;
        updateTimer();
        if (gameState.timeLeft <= 0) endGame();
    }, 1000);

    showNextWord();
}

function updateTimer() {
    const m = Math.floor(gameState.timeLeft / 60);
    const s = gameState.timeLeft % 60;
    document.getElementById('game-timer').textContent = `${m}:${s.toString().padStart(2, '0')}`;
}

function showNextWord() {
    if (gameState.current >= gameState.words.length) { endGame(); return; }

    const word = gameState.words[gameState.current];
    document.getElementById('game-jp').textContent = word.jp;
    document.getElementById('game-kana').textContent = word.kana;
    const speakBtn = document.getElementById('game-speak-btn');
    speakBtn.setAttribute('data-speak', word.jp);

    // 自动朗读
    setTimeout(() => speak(word.jp, 0.85), 300);

    const allMeanings = [];
    LESSONS.forEach(l => l.vocab.forEach(v => allMeanings.push(v.cn)));
    const wrongs = allMeanings.filter(m => m !== word.cn).sort(() => Math.random() - 0.5).slice(0, 3);
    const options = [word.cn, ...wrongs].sort(() => Math.random() - 0.5);

    document.getElementById('game-options').innerHTML = options.map(opt =>
        `<button class="option-btn" onclick="answerWord('${opt.replace(/'/g, "\\'")}', '${word.cn.replace(/'/g, "\\'")}')">${opt}</button>`
    ).join('');
}

function answerWord(selected, correct) {
    if (gameState.finished) return;
    const buttons = document.querySelectorAll('#game-options .option-btn');
    buttons.forEach(b => {
        b.disabled = true;
        if (b.textContent === correct) b.classList.add('correct');
        if (b.textContent === selected && selected !== correct) b.classList.add('wrong');
    });

    if (selected === correct) gameState.score++;

    setTimeout(() => {
        gameState.current++;
        document.getElementById('game-score').textContent = gameState.score;
        if (gameState.current < gameState.words.length) showNextWord();
        else endGame();
    }, 600);
}

function endGame() {
    gameState.finished = true;
    if (gameState.timer) clearInterval(gameState.timer);

    document.getElementById('game-area').style.display = 'none';
    document.getElementById('game-result').style.display = 'block';

    const total = gameState.words.length;
    const pct = Math.round((gameState.score / total) * 100);

    let title, emoji;
    if (pct === 100) { title = '满分过关！太厉害了！🎉🎉🎉'; emoji = '🏆'; }
    else if (pct >= 80) { title = '很棒！继续加油！⭐'; emoji = '⭐'; }
    else if (pct >= 60) { title = '还不错！再来一次会更好！👍'; emoji = '👍'; }
    else { title = '加油！多练几次就熟悉了！💪'; emoji = '💪'; }

    document.getElementById('result-title').textContent = `${emoji} ${title}`;
    document.getElementById('result-text').textContent = `${gameState.score}/${total} 题正确（${pct}%）`;

    document.getElementById('result-details').innerHTML = `
        <div style="margin-top:12px;padding:12px;background:#F9F9F9;border-radius:10px;text-align:left;font-size:13px;">
            ${gameState.words.map(w =>
                `<div style="padding:4px 0;border-bottom:1px solid #eee;display:flex;justify-content:space-between;">
                    <span>${w.jp}（${w.kana}）</span>
                    <span style="color:var(--primary);font-weight:600;">${w.cn}</span>
                </div>`
            ).join('')}
        </div>
    `;
}

// === 听力挑战 ===
let listenState = { questions: [], current: 0, score: 0 };

function startListen() {
    const allWords = [];
    LESSONS.forEach(l => l.vocab.forEach(v => allWords.push(v)));
    const qs = allWords.sort(() => Math.random() - 0.5).slice(0, 5);

    listenState = { questions: qs, current: 0, score: 0 };
    document.getElementById('listen-result').style.display = 'none';
    document.getElementById('listen-area').style.display = 'block';
    showNextListen();
}

function showNextListen() {
    if (listenState.current >= listenState.questions.length) { endListen(); return; }

    const q = listenState.questions[listenState.current];
    document.getElementById('listen-num').textContent = listenState.current + 1;
    document.getElementById('listen-total').textContent = listenState.questions.length;

    // 设置播放按钮
    const playBtn = document.getElementById('listen-play-btn');
    playBtn.setAttribute('data-speak', q.jp);
    playBtn.textContent = '🔊';

    // 自动播放
    setTimeout(() => {
        speak(q.jp, 0.85);
        playBtn.classList.add('playing');
        setTimeout(() => playBtn.classList.remove('playing'), 1200);
    }, 500);

    const allMeanings = [];
    LESSONS.forEach(l => l.vocab.forEach(v => allMeanings.push(v.cn)));
    const wrongs = allMeanings.filter(m => m !== q.cn).sort(() => Math.random() - 0.5).slice(0, 3);
    const options = [q.cn, ...wrongs].sort(() => Math.random() - 0.5);

    document.getElementById('listen-options').innerHTML = options.map(opt =>
        `<button class="option-btn" onclick="answerListen('${opt.replace(/'/g, "\\'")}', '${q.cn.replace(/'/g, "\\'")}')">${opt}</button>`
    ).join('');
}

function answerListen(selected, correct) {
    const buttons = document.querySelectorAll('#listen-options .option-btn');
    buttons.forEach(b => {
        b.disabled = true;
        if (b.textContent === correct) b.classList.add('correct');
        if (b.textContent === selected && selected !== correct) b.classList.add('wrong');
    });

    if (selected === correct) listenState.score++;

    setTimeout(() => {
        listenState.current++;
        showNextListen();
    }, 600);
}

function endListen() {
    document.getElementById('listen-area').style.display = 'none';
    document.getElementById('listen-result').style.display = 'block';

    const total = listenState.questions.length;
    const pct = Math.round((listenState.score / total) * 100);

    document.getElementById('listen-result-title').textContent =
        pct === 100 ? '👂 全部答对了！耳朵真灵！' : `👂 答对 ${listenState.score}/${total} 题！`;
    document.getElementById('listen-result-text').textContent =
        pct === 100 ? '太棒了！🎉' : '继续加油，下次会更好！💪';
}

// === 个人主页 ===
function renderProfile() {
    document.getElementById('profile-name').textContent = userState.name;
    document.getElementById('profile-level').textContent = `${userState.level} · ${userState.levelName}`;

    const container = document.getElementById('achievements');
    container.innerHTML = ACHIEVEMENTS.map(a => {
        const unlocked = userState.achievements.includes(a.id);
        return `
            <div class="achievement ${unlocked ? '' : 'locked'}">
                <div class="icon">${unlocked ? a.icon : '🔒'}</div>
                <div class="name">${unlocked ? a.name : '???'}</div>
                <div style="font-size:10px;color:var(--text-light);">${unlocked ? a.desc : ''}</div>
            </div>
        `;
    }).join('');

    document.getElementById('learning-stats').innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div><strong>🔥 当前连续</strong><br>${userState.streak} 天</div>
            <div><strong>🏆 最长连续</strong><br>${userState.maxStreak} 天</div>
            <div><strong>💎 总经验值</strong><br>${userState.xp}</div>
            <div><strong>📖 完成课程</strong><br>${userState.completedLessons.length}/${LESSONS.length}</div>
        </div>
    `;
}

// ═══════════════════════════════════════════
// 🎤 声优训练营
// ═══════════════════════════════════════════
// 🎤 声优训练营 - 带语音识别自动评分
// ═══════════════════════════════════════════

const SPEAK_SENTENCES = (() => {
    const s = [];
    LESSONS.forEach(l => l.vocab.forEach(v => s.push({ jp: v.jp, kana: v.kana, cn: v.cn, type: 'word' })));
    SHINCHAN_QUOTES.forEach(q => s.push({ jp: q.jp.replace(/[「」]/g, ''), kana: '', cn: q.cn, type: 'shinchan' }));
    return s;
})();

function speakScore(similarity) {
    if (similarity >= 0.9) return { stars: 3, str: '⭐⭐⭐', label: '🎉 完美！太棒了！', color: '#00B894', pass: true };
    if (similarity >= 0.7) return { stars: 2, str: '⭐⭐', label: '👍 不错哦！继续加油！', color: '#FDCB6E', pass: true };
    if (similarity >= 0.5) return { stars: 1, str: '⭐', label: '🤔 再练一遍吧！', color: '#E17055', pass: false };
    return { stars: 0, str: '☆', label: '😅 没听清，再试一次！', color: '#D63031', pass: false };
}

function speakSimilarity(a, b) {
    a = a.replace(/[　 .,!?。、！？]/g, '').toLowerCase();
    b = b.replace(/[　 .,!?。、！？]/g, '').toLowerCase();
    if (a === b) return 1.0;
    if (!a || !b) return 0;
    let matches = 0;
    for (const ch of a) { if (b.includes(ch)) matches++; }
    return matches / Math.max(a.length, b.length);
}

let speakState = { sentences: [], current: 0, completed: 0, totalScore: 0, recording: false, mediaRecorder: null, audioChunks: [], audioUrl: null, recognizer: null };

function startSpeak() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const shuffled = [...SPEAK_SENTENCES].sort(() => Math.random() - 0.5).slice(0, 6);
    let recog = null;
    if (SR) { recog = new SR(); recog.lang = 'ja-JP'; recog.continuous = false; recog.interimResults = false; recog.maxAlternatives = 3; }
    speakState = { sentences: shuffled, current: 0, completed: 0, totalScore: 0, recording: false, mediaRecorder: null, audioChunks: [], audioUrl: null, recognizer: recog };
    document.getElementById('speak-result').style.display = 'none';
    document.getElementById('speak-area').style.display = 'block';
    document.getElementById('speak-total').textContent = shuffled.length;
    document.getElementById('speak-mode-label').textContent = shuffled.some(s => s.type === 'shinchan') ? '🎭 声优挑战' : '🗣️ 跟读模仿';
    showSpeakSentence();
}

function showSpeakSentence() {
    if (speakState.current >= speakState.sentences.length) { endSpeak(); return; }
    const s = speakState.sentences[speakState.current];
    document.getElementById('speak-num').textContent = speakState.current + 1;
    document.getElementById('speak-jp').textContent = s.jp;
    document.getElementById('speak-kana').textContent = s.kana || s.jp;

    if (s.type === 'shinchan') {
        document.getElementById('speak-role-icon').textContent = '🦸';
        document.getElementById('speak-role-name').textContent = '🎭 声优挑战！';
        document.getElementById('speak-role-desc').textContent = '像小新一样大声说出来！';
    } else {
        document.getElementById('speak-role-icon').textContent = '🗣️';
        document.getElementById('speak-role-name').textContent = '跟读模仿';
        document.getElementById('speak-role-desc').textContent = '听原声，跟着读';
    }

    // 重置评分区
    document.getElementById('speak-score-area').style.display = 'none';
    document.getElementById('speak-score-detail').innerHTML = '';
    document.getElementById('speak-record-area').style.display = 'flex';
    document.getElementById('speak-score-actions').style.display = 'none';
    document.getElementById('speak-status').textContent = '👆 先听原声！';
    document.getElementById('speak-status').className = 'speak-status';
    document.getElementById('speak-listen-btn').disabled = false;
    document.getElementById('speak-record-btn').disabled = false;
    document.getElementById('speak-playback-btn').disabled = true;

    speakState.audioUrl = null; speakState.recording = false;
    document.getElementById('speak-record-icon').textContent = '🎤';
    document.getElementById('speak-record-label').textContent = '点我说话';
    document.getElementById('speak-record-btn').className = 'speak-action-btn speak-record-btn';

    setTimeout(() => speak(s.jp, 0.85), 300);
}

function speakListenPlay() {
    const s = speakState.sentences[speakState.current];
    speak(s.jp, 0.85);
    document.getElementById('speak-status').textContent = '🔊 听清楚了吗？点 🎤 读一遍！';
}

function speakToggleRecord() {
    if (speakState.recording) { speakStopRecord(); } else { speakStartRecord(); }
}

function speakStartRecord() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        document.getElementById('speak-status').textContent = '⚠️ 浏览器不支持录音，请用手机 Chrome 打开！';
        return;
    }
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        speakState.recording = true; speakState.audioChunks = [];
        document.getElementById('speak-record-icon').textContent = '⏹️';
        document.getElementById('speak-record-label').textContent = '松手停止';
        document.getElementById('speak-record-btn').classList.add('active');
        document.getElementById('speak-status').textContent = '🎤 在说话！大声读出来！';

        const recorder = new MediaRecorder(stream);
        speakState.mediaRecorder = recorder;
        recorder.ondataavailable = e => speakState.audioChunks.push(e.data);
        recorder.onstop = () => {
            stream.getTracks().forEach(t => t.stop());
            const blob = new Blob(speakState.audioChunks, { type: 'audio/webm' });
            speakState.audioUrl = URL.createObjectURL(blob);
            document.getElementById('speak-playback-btn').disabled = false;
            // 录音结束 → 自动评分
            speakAutoScore();
        };
        recorder.start();
    }).catch(() => {
        document.getElementById('speak-status').textContent = '⚠️ 无法访问麦克风，请允许录音权限！';
    });
}

function speakStopRecord() {
    if (speakState.mediaRecorder && speakState.mediaRecorder.state === 'recording') speakState.mediaRecorder.stop();
    speakState.recording = false;
}

function speakPlayback() {
    if (speakState.audioUrl) { const a = new Audio(speakState.audioUrl); a.play(); }
}

/** ⭐ 自动评分 */
function speakAutoScore() {
    const s = speakState.sentences[speakState.current];
    const expected = s.kana || s.jp;

    document.getElementById('speak-record-area').style.display = 'none';
    document.getElementById('speak-score-area').style.display = 'block';
    document.getElementById('speak-score-actions').style.display = 'flex';
    document.getElementById('speak-score-detail').innerHTML = `
        <div style="text-align:center;padding:20px;">
            <div style="font-size:24px;margin-bottom:8px;">⏳</div>
            <div style="font-size:16px;color:var(--text-light);">正在识别你的发音……</div>
        </div>`;

    // 尝试语音识别
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
        const recog = new SR();
        recog.lang = 'ja-JP';
        recog.continuous = false;
        recog.interimResults = false;
        recog.maxAlternatives = 3;

        let done = false;

        recog.onresult = (event) => {
            if (done) return; done = true;
            let heard = '';
            for (let i = 0; i < event.results.length; i++) {
                if (event.results[i].isFinal) { heard = event.results[i][0].transcript; break; }
            }
            const similarity = speakSimilarity(heard, expected);
            const score = speakScore(similarity);
            speakState.totalScore += score.stars;
            document.getElementById('speak-score-detail').innerHTML = showScoreUI(score, heard);
            if (!score.pass) {
                document.getElementById('speak-score-actions').innerHTML =
                    `<button class="btn btn-outline btn-small" onclick="speakRetry()">🔄 再练一遍</button>` +
                    `<button class="btn btn-primary btn-small" onclick="speakAdvance()">✅ 我觉得可以了，继续</button>`;
            } else {
                document.getElementById('speak-score-actions').innerHTML =
                    `<button class="btn btn-primary btn-small" onclick="speakAdvance()">✅ 继续下一句</button>`;
            }
        };

        recog.onerror = () => {
            if (done) return; done = true;
            speakState.totalScore += 2;
            showManualScore();
        };

        recog.onend = () => {
            if (!done) {
                done = true;
                speakState.totalScore += 2;
                showManualScore();
            }
        };

        try { recog.start(); } catch(e) { showManualScore(); }
        // 8秒超时降级
        setTimeout(() => { if (!done) { done = true; speakState.totalScore += 2; showManualScore(); } }, 8000);
    } else {
        speakState.totalScore += 2;
        showManualScore();
    }
}

function showManualScore() {
    document.getElementById('speak-score-detail').innerHTML = `
        <div style="text-align:center;padding:16px;">
            <div style="font-size:32px;margin-bottom:4px;">⭐⭐ 听听自己的录音</div>
            <div style="font-size:14px;color:var(--text-light);margin:8px 0;">
                点 ▶️ 听听自己说的，跟原声比较一下
            </div>
            <div style="display:flex;gap:8px;justify-content:center;margin-top:8px;">
                <button class="btn btn-outline btn-small" onclick="speakListenPlay()">🔊 听原声</button>
                <button class="btn btn-outline btn-small" onclick="speakPlayback()">▶️ 听自己</button>
            </div>
        </div>`;
    document.getElementById('speak-score-actions').innerHTML =
        `<button class="btn btn-outline btn-small" onclick="speakRetry()">🔄 再练一遍</button>` +
        `<button class="btn btn-primary btn-small" onclick="speakAdvance()">✅ 我觉得可以，继续</button>`;
}

function speakAdvance() {
    const s = speakState.sentences[speakState.current];
    speakState.completed++;
    speakState.current++;
    if (speakState.current < speakState.sentences.length) { showSpeakSentence(); } else { endSpeak(); }
}

function speakRetry() {
    // 不计数，原地重练
    showSpeakSentence();
}

function showScoreUI(score, heard) {
    return `
        <div style="text-align:center;padding:12px;">
            <div style="font-size:32px;margin-bottom:4px;">${score.str}</div>
            <div style="font-size:18px;font-weight:700;color:${score.color};">${score.label}</div>
            <div style="font-size:13px;color:var(--text-light);margin-top:8px;">
                你说的是：<span style="color:var(--primary);font-weight:600;">${heard || '（没识别到）'}</span>
            </div>
            <div style="font-size:13px;color:var(--text-light);">
                原句是：<span style="font-weight:600;">${speakState.sentences[speakState.current].jp}</span>
            </div>
        </div>`;
}

function endSpeak() {
    document.getElementById('speak-area').style.display = 'none';
    document.getElementById('speak-result').style.display = 'block';
    const total = speakState.sentences.length;
    const avg = total > 0 ? (speakState.totalScore / total) : 0;
    let title, sub;
    if (avg >= 2.5) { title = '🏆 太棒了！金牌声优！'; sub = `平均 ${avg.toFixed(1)} 星！`; }
    else if (avg >= 1.5) { title = '⭐ 不错！继续加油！'; sub = `平均 ${avg.toFixed(1)} 星`; }
    else { title = '💪 多练几次会更好！'; sub = `平均 ${avg.toFixed(1)} 星`; }
    document.getElementById('speak-result-title').textContent = title;
    document.getElementById('speak-result-text').textContent = `今天学了 ${total} 句 · ${sub}`;
}

// === 启动 ===
document.addEventListener('DOMContentLoaded', () => {
    // 恢复上次选择的音色
    try {
        const saved = localStorage.getItem('jp-voice-mode');
        if (saved) setVoiceMode(saved);
    } catch(e) {}
    refreshHome();
});
