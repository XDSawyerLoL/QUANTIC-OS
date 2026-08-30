import QtQuick
Canvas {
    id: root
    property var values: []
    property color lineColor: "#6282FF"
    property real lineWidth: 2
    onValuesChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        const ctx = getContext("2d"); ctx.reset();
        if (!values || values.length < 2) return;
        const n = values.length;
        ctx.lineWidth = lineWidth; ctx.lineCap = "round"; ctx.lineJoin = "round";
        ctx.strokeStyle = lineColor; ctx.shadowColor = lineColor; ctx.shadowBlur = 8; ctx.beginPath();
        for (let i = 0; i < n; ++i) {
            const x = (i / (n - 1)) * width;
            const normalized = Math.max(0, Math.min(1, Number(values[i]) / 100.0));
            const y = height - 2 - normalized * (height - 4);
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }
}
