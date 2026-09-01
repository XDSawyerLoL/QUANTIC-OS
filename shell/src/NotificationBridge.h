#pragma once
#include <QObject>
#include <QVariantList>
#include <QString>
#include <QTimer>

class NotificationBridge final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QVariantList items READ items NOTIFY changed)
    Q_PROPERTY(int count READ count NOTIFY changed)
    Q_PROPERTY(QString status READ status NOTIFY changed)
public:
    explicit NotificationBridge(QObject *parent=nullptr);
    QVariantList items() const { return m_items; }
    int count() const { return m_items.size(); }
    QString status() const { return m_status; }
    Q_INVOKABLE void refresh();
    Q_INVOKABLE void clearAll();
signals:
    void changed();
private:
    QString bridgePath() const;
    void consume(const QByteArray &json, bool clearing=false);
    QVariantList m_items;
    QString m_status="Notifications prêtes";
    QTimer m_timer;
};
