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

// 适配 MkDocs Instant Loading
document.addEventListener("DOMContentLoaded", initDynamicBackground);
if (typeof app !== 'undefined') {
    app.document$.subscribe(initDynamicBackground);
}