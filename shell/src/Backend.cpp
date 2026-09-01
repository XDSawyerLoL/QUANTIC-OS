#include "Backend.h"
#include <QFile>
#include <QProcess>
#include <QRegularExpression>
#include <QStorageInfo>
#include <QTcpSocket>
#include <QDir>
#include <QStandardPaths>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QHash>
#include <algorithm>

static bool readCpu(quint64 &total, quint64 &idle) {
    QFile f("/proc/stat"); if (!f.open(QIODevice::ReadOnly|QIODevice::Text)) return false;
    const auto parts = QString::fromUtf8(f.readLine()).simplified().split(' ');
    if (parts.size() < 8 || parts[0] != "cpu") return false;
    total=0; for (int i=1;i<parts.size();++i) total += parts[i].toULongLong();
    idle = parts[4].toULongLong() + (parts.size()>5 ? parts[5].toULongLong() : 0);
    return true;
}
static QString runText(const QString &program, const QStringList &args, int timeoutMs=220) {
    QProcess p; p.start(program,args); if (!p.waitForStarted(80)) return {};
    if (!p.waitForFinished(timeoutMs)) { p.kill(); p.waitForFinished(40); return {}; }
    return QString::fromUtf8(p.readAllStandardOutput()).trimmed();
}
static QString desktopStatePath() {
    const QString base=QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
    QDir().mkpath(base);
    return QDir(base).filePath("desktop-state.json");
}
static const QHash<QString,QStringList> &appCandidates() {
    static const QHash<QString,QStringList> apps={
        {"browser", {"firefox","chromium","google-chrome","brave-browser"}},
        {"files", {"dolphin","nautilus","thunar"}},
        {"terminal", {"konsole","gnome-terminal","xterm"}},
        {"editor", {"code","codium","kate","gedit"}},
        {"settings", {"systemsettings","gnome-control-center"}},
        {"discover", {"plasma-discover","gnome-software"}}
    };
    return apps;
}
Backend::Backend(QObject *parent): QObject(parent) {
    QFile cmd("/proc/cmdline");
    if (cmd.open(QIODevice::ReadOnly)) { const auto text=QString::fromUtf8(cmd.readAll()); m_safeMode=text.contains("rd.live.image") || text.contains("quantic.live=1"); }
    loadDesktopState();
    connect(&m_timer,&QTimer::timeout,this,&Backend::refresh); m_timer.start(1000); refresh();
}
void Backend::appendHistory(QVariantList &list, double value, int maxPoints) { list.append(value); while (list.size()>maxPoints) list.removeFirst(); }
int Backend::probeGpu() {
    QString out=runText("nvidia-smi", {"--query-gpu=utilization.gpu","--format=csv,noheader,nounits"},250); bool ok=false; int v=out.section('\n',0,0).trimmed().toInt(&ok); if(ok) return std::clamp(v,0,100);
    QDir drm("/sys/class/drm"); for(const QString &card:drm.entryList({"card*"},QDir::Dirs|QDir::NoDotAndDotDot)){ QFile f(drm.filePath(card+"/device/gpu_busy_percent")); if(f.open(QIODevice::ReadOnly)){int x=QString::fromUtf8(f.readAll()).trimmed().toInt(&ok);if(ok)return std::clamp(x,0,100);}}
    return -1;
}
double Backend::probeCpuTemperature() {
    QDir thermal("/sys/class/thermal"); double best=0;
    for(const QString &zone:thermal.entryList({"thermal_zone*"},QDir::Dirs|QDir::NoDotAndDotDot)){ QFile type(thermal.filePath(zone+"/type")),temp(thermal.filePath(zone+"/temp")); if(!temp.open(QIODevice::ReadOnly))continue; double t=QString::fromUtf8(temp.readAll()).trimmed().toDouble()/1000.0; if(type.open(QIODevice::ReadOnly)){const QString s=QString::fromUtf8(type.readAll()).toLower();if(s.contains("x86_pkg")||s.contains("cpu")||s.contains("package"))return t;} if(t>best&&t<130)best=t; }
    return best;
}
QString Backend::probeNetwork(){QString out=runText("nmcli",{"-t","-f","NAME,TYPE","connection","show","--active"},180);if(out.isEmpty())return "Hors ligne";const auto first=out.section('\n',0,0);return first.section(':',0,0).isEmpty()?"Connecté":first.section(':',0,0);}
QString Backend::probeVolume(){QString out=runText("wpctl",{"get-volume","@DEFAULT_AUDIO_SINK@"},180);QRegularExpression re("([0-9]+(?:\\.[0-9]+)?)");auto m=re.match(out);if(!m.hasMatch())return "N/D";const int pct=qRound(m.captured(1).toDouble()*100.0);return QString::number(std::clamp(pct,0,150))+" %";}
bool Backend::probeOllama(){QTcpSocket socket;socket.connectToHost("127.0.0.1",11434);bool ok=socket.waitForConnected(45);if(ok)socket.disconnectFromHost();return ok;}
void Backend::updateWorkload(){const QString processes=runText("bash",{"-lc","ps -eo comm= | tr '[:upper:]' '[:lower:]' | head -n 400"},180).toLower();if(processes.contains("obs")||processes.contains("ffmpeg"))m_workload="Streaming";else if(processes.contains("steam")||processes.contains("gamescope")||processes.contains("proton"))m_workload="Gaming";else if(processes.contains("ollama")&&(m_cpu>25||m_gpu>25))m_workload="IA locale";else if(processes.contains("ninja")||processes.contains("cargo")||processes.contains("make"))m_workload="Compilation";else if(m_cpu<8&&m_ramPercent<45)m_workload="Repos";else m_workload="Équilibré";}
void Backend::refresh(){
    quint64 total=0,idle=0;if(readCpu(total,idle)){if(m_prevTotal&&total>m_prevTotal){const auto dt=total-m_prevTotal,di=idle-m_prevIdle;m_cpu=dt?100.0*double(dt-di)/double(dt):0.0;}m_prevTotal=total;m_prevIdle=idle;}
    QFile mf("/proc/meminfo");if(mf.open(QIODevice::ReadOnly|QIODevice::Text)){quint64 totalKb=0,availKb=0;while(!mf.atEnd()){const QString l=QString::fromUtf8(mf.readLine());const auto p=l.split(QRegularExpression("\\s+"));if(l.startsWith("MemTotal:")&&p.size()>1)totalKb=p[1].toULongLong();if(l.startsWith("MemAvailable:")&&p.size()>1)availKb=p[1].toULongLong();}if(totalKb){m_ramTotalGb=totalKb/1048576.0;m_ramUsedGb=(totalKb-availKb)/1048576.0;m_ramPercent=100.0*(totalKb-availKb)/double(totalKb);}}
    m_gpu=probeGpu();m_cpuTempC=probeCpuTemperature();QStorageInfo storage(QDir::homePath());if(storage.isValid()&&storage.bytesTotal()>0)m_diskFreeText=QString::number(storage.bytesAvailable()/1073741824.0,'f',1)+" GB";
    static int slow=0;if((slow++%5)==0){m_networkText=probeNetwork();m_volumeText=probeVolume();m_localAiStatus=probeOllama()?"IA locale : Ollama prêt":"IA locale : modèle à installer";}
    updateWorkload();appendHistory(m_cpuHistory,m_cpu);appendHistory(m_ramHistory,m_ramPercent);appendHistory(m_gpuHistory,m_gpu<0?0:m_gpu);m_healthText=(m_ramPercent>92||m_cpuTempC>95)?"Attention requise":"Tout fonctionne normalement";emit metricsChanged();
}
void Backend::loadDesktopState(){
    QFile f(desktopStatePath()); if(!f.open(QIODevice::ReadOnly)) return;
    QJsonParseError err; const auto doc=QJsonDocument::fromJson(f.readAll(),&err); if(err.error!=QJsonParseError::NoError||!doc.isObject()) return;
    const auto o=doc.object(); const QString mission=o.value("activeMission").toString(); if(!mission.isEmpty())m_activeMission=mission;
    const auto apps=o.value("recentApps").toArray(); for(const auto &v:apps){const QString id=v.toString();if(appCandidates().contains(id)&&!m_recentApps.contains(id))m_recentApps.append(id);if(m_recentApps.size()>=8)break;}
}
void Backend::saveDesktopState() const{
    QJsonObject o; o.insert("version",1);o.insert("activeMission",m_activeMission);QJsonArray apps;for(const auto &v:m_recentApps)apps.append(v.toString());o.insert("recentApps",apps);
    QSaveFile f(desktopStatePath());if(f.open(QIODevice::WriteOnly)){f.write(QJsonDocument(o).toJson(QJsonDocument::Compact));f.commit();}
}
void Backend::noteRecentApp(const QString &appId){m_recentApps.removeAll(appId);m_recentApps.prepend(appId);while(m_recentApps.size()>8)m_recentApps.removeLast();saveDesktopState();emit desktopChanged();}
bool Backend::launchApp(const QString &appId){
    const auto it=appCandidates().find(appId);if(it==appCandidates().end()){m_lastLaunchStatus="Application non autorisée";emit desktopChanged();return false;}
    for(const QString &candidate:it.value()){
        const QString exe=QStandardPaths::findExecutable(candidate);if(exe.isEmpty())continue;
        const bool ok=QProcess::startDetached(exe,{});m_lastLaunchStatus=ok?("Ouvert : "+candidate):("Échec : "+candidate);if(ok)noteRecentApp(appId);else emit desktopChanged();return ok;
    }
    m_lastLaunchStatus="Aucune application compatible installée";emit desktopChanged();return false;
}
void Backend::setActiveMission(const QString &mission){
    static const QStringList allowed={"Quantic OS","Personnel","Création"};if(!allowed.contains(mission))return;if(m_activeMission==mission)return;m_activeMission=mission;saveDesktopState();emit desktopChanged();
}
void Backend::rememberDesktopState(){saveDesktopState();m_lastLaunchStatus="Mission enregistrée";emit desktopChanged();}
void Backend::optimize(){QProcess *p=new QProcess(this);connect(p,&QProcess::finished,this,[this,p](int,QProcess::ExitStatus){const QString out=QString::fromUtf8(p->readAllStandardOutput()).trimmed();m_activityTitle="Analyse Q-Resource terminée";m_activityDetail=out.isEmpty()?"Aucune modification risquée n’a été appliquée. Les décisions restent réversibles et mesurables.":out.left(420);m_companion="J’ai analysé les ressources. Les modifications critiques restent hors de portée du modèle IA.";emit metricsChanged();emit companionChanged();p->deleteLater();});p->start("/usr/bin/python3",{"/usr/lib/quantic/services/qresource.py"});}
void Backend::openDestination(const QString &name){if(name=="Fichiers")launchApp("files");else if(name=="Apps"||name=="AppsNative")launchApp("discover");else if(name=="Paramètres")launchApp("settings");else if(name=="Terminal")launchApp("terminal");else if(name=="Bridge")QProcess::startDetached("konsole",{"-e","python3","/usr/lib/quantic/services/qbridge.py","--help"});else if(name=="Lab")runLab("chsh");}
void Backend::askCompanion(const QString &prompt){if(prompt.trimmed().isEmpty()||m_companionBusy)return;m_companionBusy=true;m_companion="Je réfléchis localement…";emit companionChanged();QProcess *p=new QProcess(this);connect(p,&QProcess::finished,this,[this,p](int code,QProcess::ExitStatus){QString out=QString::fromUtf8(p->readAllStandardOutput()).trimmed();if(out.isEmpty())out=QString::fromUtf8(p->readAllStandardError()).trimmed();if(code!=0&&out.isEmpty())out="Le moteur IA local n’est pas encore configuré. Installe un modèle depuis Q-Model Hub.";m_companion=out.left(4000);m_companionBusy=false;emit companionChanged();p->deleteLater();});p->start("/usr/bin/python3",{"/usr/lib/quantic/services/qagent.py",prompt});}
void Backend::runLab(const QString &experiment){const QString exp=(experiment=="bell")?"bell":"chsh";m_labOutput="Exécution de Q-Core…";emit labChanged();QProcess *p=new QProcess(this);connect(p,&QProcess::finished,this,[this,p](int,QProcess::ExitStatus){QString out=QString::fromUtf8(p->readAllStandardOutput()).trimmed();if(out.isEmpty())out=QString::fromUtf8(p->readAllStandardError()).trimmed();m_labOutput=out;emit labChanged();p->deleteLater();});p->start("/usr/bin/python3",{"/usr/lib/quantic/services/qcore.py",exp});}
