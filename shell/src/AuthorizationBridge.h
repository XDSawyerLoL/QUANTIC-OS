#pragma once
#include <QObject>
#include <QTimer>
#include <QVariantMap>

class AuthorizationBridge final : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool pending READ pending NOTIFY changed)
    Q_PROPERTY(QVariantMap request READ request NOTIFY changed)
    Q_PROPERTY(bool busy READ busy NOTIFY changed)
    Q_PROPERTY(QString status READ status NOTIFY changed)
public:
    explicit AuthorizationBridge(QObject *parent=nullptr);
    bool pending() const { return m_pending; }
    QVariantMap request() const { return m_request; }
    bool busy() const { return m_busy; }
    QString status() const { return m_status; }
    Q_INVOKABLE void refresh();
    Q_INVOKABLE void approve();
    Q_INVOKABLE void reject();
signals:
    void changed();
private:
    QString servicePath() const;
    void decide(const QString &verb);
    QTimer m_timer;
    bool m_pending=false;
    bool m_busy=false;
    QVariantMap m_request;
    QString m_status="Aucune autorisation en attente";
};
