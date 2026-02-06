const tg = window.Telegram.WebApp;
const WEB_APP_URL = window.location.origin; // Dynamically get current origin

// State
let state = {
    currentView: 'home',
    tickets: [
        { id: 'cam1', name: 'Cam 1', color: '#e67e22' },
        { id: 'cam2', name: 'Cam 2', color: '#d35400' },
        { id: 'do1', name: 'Đỏ 1', color: '#e74c3c' },
        { id: 'do2', name: 'Đỏ 2', color: '#c0392b' },
        { id: 'duong1', name: 'Dương 1', color: '#3498db' },
        { id: 'duong2', name: 'Dương 2', color: '#2980b9' },
        { id: 'hong1', name: 'Hồng 1', color: '#fd79a8' },
        { id: 'hong2', name: 'Hồng 2', color: '#e84393' },
        { id: 'luc1', name: 'Lục 1', color: '#2ecc71' },
        { id: 'luc2', name: 'Lục 2', color: '#27ae60' },
        { id: 'tim1', name: 'Tím 1', color: '#9b59b6' },
        { id: 'tim2', name: 'Tím 2', color: '#8e44ad' },
        { id: 'vang1', name: 'Vàng 1', color: '#f1c40f' },
        { id: 'vang2', name: 'Vàng 2', color: '#f39c12' },
        { id: 'xanh1', name: 'Xanh 1', color: '#1abc9c' },
        { id: 'xanh2', name: 'Xanh 2', color: '#16a085' }
    ]
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    tg.expand();
    
    // Check URL params for direct routing
    const urlParams = new URLSearchParams(window.location.search);
    const view = urlParams.get('view');
    const target = urlParams.get('target');
    
    if (target) {
        // Mode animation quay số
        initWheelMode(urlParams);
        switchView('wheel');
    } else if (view) {
        switchView(view);
    } else {
        switchView('home');
    }

    setupNavigation();
    renderTickets();
});

// Navigation
function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const viewId = item.getAttribute('href').substring(1); // remove #
            switchView(viewId);
        });
    });
}

function switchView(viewId) {
    // Hide all views
    document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
    
    // Show target view
    const target = document.getElementById(viewId + '-view');
    if (target) target.classList.remove('hidden');
    
    // Update nav
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    const activeNav = document.querySelector(`.nav-item[href="#${viewId}"]`);
    if (activeNav) activeNav.classList.add('active');

    state.currentView = viewId;
    tg.MainButton.hide(); // Hide main button by default

    if (viewId === 'tickets') {
        tg.MainButton.setText("CHỌN VÉ");
        tg.MainButton.color = "#2ed573";
    }
}

// Logic: Tickets
function renderTickets() {
    const grid = document.getElementById('ticket-grid');
    if (!grid) return;

    grid.innerHTML = state.tickets.map(ticket => `
        <div class="ticket-item" onclick="selectTicket('${ticket.id}')">
            <div class="ticket-color-preview" style="background-color: ${ticket.color}"></div>
            <div class="ticket-name">${ticket.name}</div>
        </div>
    `).join('');
}

function selectTicket(ticketId) {
    // Highlight UI
    document.querySelectorAll('.ticket-item').forEach(el => el.classList.remove('selected'));
    // event.currentTarget.classList.add('selected'); // Need reliable way to target this

    // Send data to Bot
    tg.sendData(JSON.stringify({
        action: 'lay_ve',
        ticket_id: ticketId
    }));
}

// Logic: Wheel (Simplified port from previous index.html)
let isSpinning = false;
function initWheelMode(params) {
    // Hide nav bar in spin mode
    document.querySelector('.bottom-nav').classList.add('hidden');
    
    const startNum = parseInt(params.get('start')) || 1;
    const endNum = parseInt(params.get('end')) || 90;
    const targetNum = parseInt(params.get('target'));

    const canvas = document.getElementById('wheelCanvas');
    const ctx = canvas.getContext('2d');
    const btn = document.getElementById('spinBtn');
    
    // init wheel logic here ... (Reuse drawing logic)
    drawWheel(ctx, canvas.width, canvas.height); // Define this function similar to before

    btn.addEventListener('click', () => {
        if(isSpinning) return;
        isSpinning = true;
        
        // Spin logic...
        // For brevity, using simple logic placeholder
        const resultNumber = targetNum || Math.floor(Math.random()*(endNum-startNum+1)+startNum);
        
        // Finalize
        setTimeout(() => {
            document.getElementById('resultNumber').innerText = resultNumber;
            document.getElementById('resultPanel').classList.add('winning');
            tg.HapticFeedback.notificationOccurred('success');
            
            tg.MainButton.setText("ĐÓNG");
            tg.MainButton.show();
            tg.MainButton.onClick(() => tg.close());
        }, 3000);
    });
}

function drawWheel(ctx, width, height) {
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = width / 2 - 10;
    const sections = 8;
    const colors = ['#ff4757', '#2f3542', '#ffa502', '#2ed573', '#1e90ff', '#747d8c', '#a29bfe', '#ff6b81'];

    ctx.clearRect(0, 0, width, height);
    for (let i = 0; i < sections; i++) {
        const startAngle = (i * 2 * Math.PI) / sections;
        const endAngle = ((i + 1) * 2 * Math.PI) / sections;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, startAngle, endAngle);
        ctx.fillStyle = colors[i];
        ctx.fill();
        ctx.stroke();
    }
}
