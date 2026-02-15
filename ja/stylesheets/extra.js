function initDynamicBackground() {
    const hour = new Date().getHours();
    const body = document.body;
    
    // 1. 定义时间段和对应的图片路径
    const timeConfigs = {
        morning:   { range: [6, 12],  path: "../assets/illustration/Telysta&Losalind_Library_day_01.webp" },
        afternoon: { range: [12, 18], path: "../assets/illustration/Telysta&Losalind_Library_day_02.webp" },
        evening:   { range: [18, 22], path: "../assets/illustration/Telysta&Losalind_Library_night_01.webp" },
        night:     { range: [22, 6],  path: "../assets/illustration/Telysta&Losalind_Library_night_02.webp" }
    };

    // 2. 立即应用当前时间段的 Class (保证首屏背景立刻显示)
    let currentPeriod = 'night';
    for (const [period, config] of Object.entries(timeConfigs)) {
        const [start, end] = config.range;
        if (start < end ? (hour >= start && hour < end) : (hour >= start || hour < end)) {
            currentPeriod = period;
            break;
        }
    }
    body.classList.add(`time-${currentPeriod}`);

    // 3. 异步预加载：等页面闲置时再下载其余图片
    window.addEventListener('load', () => {
        // 延迟 2 秒执行，确保不竞争首屏资源
        setTimeout(() => {
            Object.entries(timeConfigs).forEach(([period, config]) => {
                if (period !== currentPeriod) {
                    const img = new Image();
                    img.src = config.path;
                    console.log(`后台静默预加载: ${period} 壁纸`);
                }
            });
        }, 2000);
    });
}

function checkBackgroundLoaded() {
    const hour = new Date().getHours();
    const body = document.body;
    
    // 1. 路径映射 (确保路径相对于 HTML 页面是正确的)
    const bgMap = {
        morning:   "/assets/illustration/Telysta&Losalind_Library_day_01.webp",
        afternoon: "/assets/illustration/Telysta&Losalind_Library_day_02.webp",
        evening:   "/assets/illustration/Telysta&Losalind_Library_night_01.webp",
        night:     "/assets/illustration/Telysta&Losalind_Library_night_02.webp"
    };

    let key = 'night';
    if (hour >= 6 && hour < 12) key = 'morning';
    else if (hour >= 12 && hour < 18) key = 'afternoon';
    else if (hour >= 18 && hour < 22) key = 'evening';

    // 立即加上时间类名，否则背景也出不来
    body.classList.add(`time-${key}`);

    // 2. 预加载当前背景
    const img = new Image();
    img.src = bgMap[key];
    
    img.onload = () => {
        body.classList.add('content-ready');
        console.log("仪式感启动：背景已就绪");
    };

    // 3. 兜底逻辑：如果图片加载太慢，3秒后强制显示，防止页面永久空白
    setTimeout(() => {
        if (!body.classList.contains('content-ready')) {
            body.classList.add('content-ready');
            console.log("超时兜底：强制显示内容");
        }
    }, 3000);
}

// 绑定初始化
document.addEventListener("DOMContentLoaded", checkBackgroundLoaded);

// 适配 MkDocs Instant Loading (修正这里的函数名)
if (typeof app !== 'undefined') {
    app.document$.subscribe(() => {
        checkBackgroundLoaded();
    });
}