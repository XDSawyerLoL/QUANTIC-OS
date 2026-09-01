#pragma once
#include <QObject>
#include <QProcess>
#include <QString>

class CompanionBridge final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString state READ state NOTIFY changed)
    Q_PROPERTY(bool speaking READ speaking NOTIFY changed)
    Q_PROPERTY(bool listening READ listening NOTIFY changed)
    Q_PROPERTY(QString lastTranscript READ lastTranscript NOTIFY changed)
    Q_PROPERTY(QString voiceStatus READ voiceStatus NOTIFY changed)
public:
    explicit CompanionBridge(QObject *parent=nullptr);
    QString state() const { return m_state; }
    bool speaking() const { return m_speaking; }
    bool listening() const { return m_listening; }
    QString lastTranscript() const { return m_lastTranscript; }
    QString voiceStatus() const { return m_voiceStatus; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE bool speak(const QString &text);
    Q_INVOKABLE void stopSpeaking();
    Q_INVOKABLE bool listenOnce();

signals:
    void changed();
    void transcriptReady(const QString &text);

private:
    QString findExecutable(const QStringList &names) const;
    QString findVoiceModel() const;
    QString findWhisperModel() const;
    void setState(const QString &state);

    QString m_state="prêt";
    QString m_lastTranscript;
    QString m_voiceStatus="Voix locale : détection…";
    bool m_speaking=false;
    bool m_listening=false;
    QProcess *m_speech=nullptr;
    QProcess *m_listener=nullptr;
};
