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
            const c=getContext("2d"); c.reset(); const cx=width*0.50, cy=height*0.46, r=Math.min(width,height)*0.285;
            const g=c.createLinearGradient(cx-r,cy-r,cx+r,cy+r); g.addColorStop(0,"#00D9FF"); g.addColorStop(.48,"#14B8A6"); g.addColorStop(1,"#E8FFFF");
            c.lineWidth=Math.max(12,width*0.023); c.strokeStyle=g; c.shadowColor="#00D9FF"; c.shadowBlur=42; c.beginPath(); c.arc(cx,cy,r,0,Math.PI*1.94); c.stroke();
            c.lineWidth=Math.max(10,width*0.018); c.beginPath(); c.moveTo(cx+r*0.56,cy+r*0.55); c.quadraticCurveTo(cx+r*0.95,cy+r*0.91,cx+r*1.34,cy+r*0.78); c.stroke();
            c.lineWidth=Math.max(5,width*0.010); c.strokeStyle="#F5FDFF"; c.globalAlpha=.72; c.beginPath(); c.moveTo(cx-r*.82,cy+r*.62); c.quadraticCurveTo(cx-r*.1,cy+r*.25,cx+r*.62,cy+r*.63); c.quadraticCurveTo(cx+r*.94,cy+r*.78,cx+r*1.29,cy+r*.62); c.stroke(); c.shadowBlur=0;
            for(let i=0;i<430;i++){ const angle=(i/430)*Math.PI*2+Math.sin(i*0.71)*0.035; const wobble=Math.sin(i*12.73+root.phase*1.8)*0.5+Math.sin(i*2.91-root.phase)*0.28; const rr=r+wobble*(24+Math.min(width,height)*0.015)+Math.sin(i*1.37)*9; const x=cx+Math.cos(angle)*rr,y=cy+Math.sin(angle)*rr; const s=1.2+(i%5)*0.42; c.globalAlpha=0.26+((i*17)%67)/100; c.fillStyle=i%7===0?"#E8FFFF":i%3===0?"#14B8A6":"#00D9FF"; c.fillRect(x,y,s,s); }
            c.globalAlpha=1;
        }
    }
}
