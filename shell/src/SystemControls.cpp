#include "SystemControls.h"

#include <QProcess>
#include <QRegularExpression>
#include <QStandardPaths>
#include <algorithm>

SystemControls::SystemControls(QObject *parent): QObject(parent) {
    refresh();
}

QString SystemControls::runRead(const QString &program, const QStringList &args, int timeoutMs) const {
    const QString exe=QStandardPaths::findExecutable(program);
    if(exe.isEmpty()) return {};
    QProcess p;
    p.start(exe,args);
    if(!p.waitForStarted(120)) return {};
    if(!p.waitForFinished(timeoutMs)) { p.kill(); p.waitForFinished(80); return {}; }
    return QString::fromUtf8(p.readAllStandardOutput()).trimmed();
}

bool SystemControls::runControl(const QString &program, const QStringList &args, const QString &successText) {
    const QString exe=QStandardPaths::findExecutable(program);
    if(exe.isEmpty()) {
        m_statusText=program+" indisponible";
        emit stateChanged();
        return false;
    }
    QProcess p;
    p.start(exe,args);
    if(!p.waitForStarted(160) || !p.waitForFinished(1500) || p.exitCode()!=0) {
        QString err=QString::fromUtf8(p.readAllStandardError()).trimmed();
        m_statusText=err.isEmpty()?"Action système refusée":err.left(160);
        emit stateChanged();
        return false;
    }
    m_statusText=successText;
    refresh();
    return true;
}

void SystemControls::probeWifi() {
    const QString out=runRead("nmcli",{"radio","wifi"});
    m_wifiEnabled=out.compare("enabled",Qt::CaseInsensitive)==0 || out.compare("activé",Qt::CaseInsensitive)==0;
}

void SystemControls::probeBluetooth() {
    const QString out=runRead("bluetoothctl",{"show"});
    m_bluetoothEnabled=out.contains("Powered: yes",Qt::CaseInsensitive);
}

void SystemControls::probeAudio() {
    const QString out=runRead("wpctl",{"get-volume","@DEFAULT_AUDIO_SINK@"});
    QRegularExpression re("([0-9]+(?:\\.[0-9]+)?)");
    const auto m=re.match(out);
    if(m.hasMatch()) m_volumePercent=std::clamp(qRound(m.captured(1).toDouble()*100.0),0,150);
    m_muted=out.contains("MUTED",Qt::CaseInsensitive);
}

void SystemControls::probeBrightness() {
    const QString out=runRead("brightnessctl",{"-m"});
    const auto parts=out.split(',');
    if(parts.size()>=4) {
        QString pct=parts[3].trimmed();
        pct.remove('%');
        bool ok=false;
        const int value=pct.toInt(&ok);
        if(ok) { m_brightnessPercent=std::clamp(value,0,100); return; }
    }
    m_brightnessPercent=-1;
}

void SystemControls::probePowerProfile() {
    const QString out=runRead("powerprofilesctl",{"get"});
    m_powerProfile=out.isEmpty()?"indisponible":out;
}

void SystemControls::refresh() {
    probeWifi();
    probeBluetooth();
    probeAudio();
    probeBrightness();
    probePowerProfile();
    emit stateChanged();
}

void SystemControls::setWifiEnabled(bool enabled) {
    runControl("nmcli",{"radio","wifi",enabled?"on":"off"},enabled?"Wi‑Fi activé":"Wi‑Fi désactivé");
}

void SystemControls::setBluetoothEnabled(bool enabled) {
    runControl("bluetoothctl",{"power",enabled?"on":"off"},enabled?"Bluetooth activé":"Bluetooth désactivé");
}

void SystemControls::setMuted(bool muted) {
    runControl("wpctl",{"set-mute","@DEFAULT_AUDIO_SINK@",muted?"1":"0"},muted?"Son coupé":"Son rétabli");
}

void SystemControls::setVolumePercent(int percent) {
    percent=std::clamp(percent,0,150);
    runControl("wpctl",{"set-volume","@DEFAULT_AUDIO_SINK@",QString::number(percent)+"%"},QString("Volume · %1 %").arg(percent));
}

void SystemControls::setBrightnessPercent(int percent) {
    percent=std::clamp(percent,1,100);
    runControl("brightnessctl",{"set",QString::number(percent)+"%"},QString("Luminosité · %1 %").arg(percent));
}

void SystemControls::cyclePowerProfile() {
    static const QStringList profiles={"power-saver","balanced","performance"};
    int idx=profiles.indexOf(m_powerProfile.trimmed());
    idx=(idx<0)?1:(idx+1)%profiles.size();
    const QString next=profiles[idx];
    runControl("powerprofilesctl",{"set",next},"Profil énergie · "+next);
}
