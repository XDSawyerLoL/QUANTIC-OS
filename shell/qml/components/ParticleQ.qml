import QtQuick
Item {
    id: root
    property real phase: 0
    property bool animate: true
    NumberAnimation on phase { from: 0; to: Math.PI * 2; duration: 16000; loops: Animation.Infinite; running: root.animate }
    Canvas {
        id: canvas; anchors.fill: parent
        onWidthChanged: requestPaint(); onHeightChanged: requestPaint()
        Connections { target: root; function onPhaseChanged(){ canvas.requestPaint() } }
        onPaint: {
            const c=getContext("2d"); c.reset(); const cx=width*0.50, cy=height*0.48, r=Math.min(width,height)*0.285;
            const g=c.createLinearGradient(cx-r,cy-r,cx+r,cy+r); g.addColorStop(0,"#2988FF"); g.addColorStop(.48,"#5C71FF"); g.addColorStop(1,"#A05EFF");
            c.lineWidth=Math.max(12,width*0.023); c.strokeStyle=g; c.shadowColor="#5E6DFF"; c.shadowBlur=42; c.beginPath(); c.arc(cx,cy,r,0,Math.PI*1.94); c.stroke();
            c.lineWidth=Math.max(10,width*0.018); c.beginPath(); c.moveTo(cx+r*0.56,cy+r*0.55); c.lineTo(cx+r*1.13,cy+r*1.12); c.stroke(); c.shadowBlur=0;
            for(let i=0;i<430;i++){ const angle=(i/430)*Math.PI*2+Math.sin(i*0.71)*0.035; const wobble=Math.sin(i*12.73+root.phase*1.8)*0.5+Math.sin(i*2.91-root.phase)*0.28; const rr=r+wobble*(24+Math.min(width,height)*0.015)+Math.sin(i*1.37)*9; const x=cx+Math.cos(angle)*rr,y=cy+Math.sin(angle)*rr; const s=1.2+(i%5)*0.42; c.globalAlpha=0.32+((i*17)%67)/100; c.fillStyle=i%7===0?"#B271FF":i%3===0?"#65C8FF":"#4B83FF"; c.fillRect(x,y,s,s); }
            c.globalAlpha=1;
        }
    }
}
