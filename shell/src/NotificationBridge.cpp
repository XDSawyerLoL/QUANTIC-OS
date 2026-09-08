#include "NotificationBridge.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>

NotificationBridge::NotificationBridge(QObject *parent): QObject(parent) {
    connect(&m_timer,&QTimer::timeout,this,&NotificationBridge::refresh);
    m_timer.start(2500);
    refresh();
}

QString NotificationBridge::bridgePath() const {
    const QString installed="/usr/lib/quantic/services/qnotification_bridge.py";
    if(QFile::exists(installed)) return installed;
    return QDir::cleanPath(QDir(QCoreApplication::applicationDirPath()).filePath("../../services/qnotification_bridge.py"));
}

void NotificationBridge::consume(const QByteArray &json, bool clearing) {
    QJsonParseError err;
    const auto doc=QJsonDocument::fromJson(json,&err);
    if(err.error!=QJsonParseError::NoError||!doc.isObject()){
        m_status="Notifications indisponibles";
        emit changed();
        return;
    }
    const auto o=doc.object();
    if(!o.value("ok").toBool()){
        m_status="Notifications indisponibles";
        emit changed();
        return;
    }
    if(clearing){
        m_items.clear();
        m_status="Notifications effacées";
        emit changed();
        return;
    }
    QVariantList next;
    for(const auto &value:o.value("items").toArray()){
        if(!value.isObject())continue;
        const auto item=value.toObject();
        QVariantMap row;
        row.insert("id",item.value("id").toString());
        row.insert("title",item.value("title").toString());
        row.insert("message",item.value("message").toString());
        row.insert("topic",item.value("topic").toString());
        row.insert("source",item.value("source").toString());
        row.insert("severity",item.value("severity").toString("info"));
        row.insert("ts",item.value("ts").toDouble());
        next.append(row);
    }
    m_items=next;
    m_status=m_items.isEmpty()?"Aucune nouvelle notification":QString("%1 notification(s)").arg(m_items.size());
    emit changed();
}

void NotificationBridge::refresh() {
    QProcess *p=new QProcess(this);
    connect(p,&QProcess::finished,this,[this,p](int,QProcess::ExitStatus){
        consume(p->readAllStandardOutput());
        p->deleteLater();
    });
    p->start("/usr/bin/python3",{bridgePath(),"recent","--limit","20"});
}

void NotificationBridge::clearAll() {
    QProcess *p=new QProcess(this);
    connect(p,&QProcess::finished,this,[this,p](int,QProcess::ExitStatus){
        consume(p->readAllStandardOutput(),true);
        p->deleteLater();
    });
    p->start("/usr/bin/python3",{bridgePath(),"clear"});
}
