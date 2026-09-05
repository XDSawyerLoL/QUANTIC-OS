#include "AuthorizationBridge.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>

static QString pythonExe(){return QFile::exists("/usr/bin/python3")?"/usr/bin/python3":"python3";}

AuthorizationBridge::AuthorizationBridge(QObject *parent):QObject(parent){
    connect(&m_timer,&QTimer::timeout,this,&AuthorizationBridge::refresh);
    m_timer.start(1800);
    refresh();
}
QString AuthorizationBridge::servicePath() const{
    const QString installed="/usr/lib/quantic/services/qapproval_bridge.py";
    if(QFile::exists(installed))return installed;
    return QDir::cleanPath(QDir(QCoreApplication::applicationDirPath()).filePath("../../services/qapproval_bridge.py"));
}
void AuthorizationBridge::refresh(){
    if(m_busy)return;
    QProcess *p=new QProcess(this);
    connect(p,&QProcess::finished,this,[this,p](int code,QProcess::ExitStatus){
        QJsonParseError err;const auto doc=QJsonDocument::fromJson(p->readAllStandardOutput(),&err);
        if(code==0&&err.error==QJsonParseError::NoError&&doc.isObject()){
            const auto o=doc.object();m_pending=o.value("pending").toBool(false);m_request=o.toVariantMap();
            m_status=m_pending?"Autorisation requise":"Aucune autorisation en attente";
        }else{m_status="Service d’autorisation indisponible";}
        emit changed();p->deleteLater();
    });
    p->start(pythonExe(),{servicePath(),"pending"});
}
void AuthorizationBridge::decide(const QString &verb){
    if(m_busy||!m_pending)return;
    const QString plan=m_request.value("plan_id").toString();const QString action=m_request.value("action_id").toString();
    if(plan.isEmpty()||action.isEmpty())return;
    m_busy=true;m_status=verb=="approve"?"Autorisation en cours…":"Refus en cours…";emit changed();
    QProcess *p=new QProcess(this);
    connect(p,&QProcess::finished,this,[this,p,verb](int code,QProcess::ExitStatus){
        QJsonParseError err;const auto doc=QJsonDocument::fromJson(p->readAllStandardOutput(),&err);
        if(code==0&&err.error==QJsonParseError::NoError&&doc.isObject()&&doc.object().value("ok").toBool())
            m_status=verb=="approve"?"Action autorisée":"Action refusée";
        else m_status="Décision non appliquée";
        m_busy=false;emit changed();p->deleteLater();QTimer::singleShot(300,this,&AuthorizationBridge::refresh);
    });
    p->start(pythonExe(),{servicePath(),verb,plan,action});
}
void AuthorizationBridge::approve(){decide("approve");}
void AuthorizationBridge::reject(){decide("reject");}
