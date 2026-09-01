#pragma once
#include <QObject>
#include <QProcess>
#include <QString>
#include <QStringList>

class CompanionBridge final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString state READ state NOTIFY changed)
    Q_PROPERTY(bool speaking READ speaking NOTIFY changed)
    Q_PROPERTY(bool listening READ listening NOTIFY changed)
    Q_PROPERTY(QString lastTranscript READ lastTranscript NOTIFY changed)
    Q_PROPERTY(QString voiceStatus READ voiceStatus NOTIFY changed)
    Q_PROPERTY(QString voiceEngine READ voiceEngine NOTIFY changed)
    Q_PROPERTY(bool autoSpeak READ autoSpeak WRITE setAutoSpeak NOTIFY changed)
public:
    explicit CompanionBridge(QObject *parent=nullptr);
    QString state() const { return m_state; }
    bool speaking() const { return m_speaking; }
    bool listening() const { return m_listening; }
    QString lastTranscript() const { return m_lastTranscript; }
    QString voiceStatus() const { return m_voiceStatus; }
    QString voiceEngine() const { return m_voiceEngine; }
    bool autoSpeak() const { return m_autoSpeak; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE bool speak(const QString &text);
    Q_INVOKABLE void stopSpeaking();
    Q_INVOKABLE bool listenOnce();
    Q_INVOKABLE void setAutoSpeak(bool enabled);
    Q_INVOKABLE QString speechPreview(const QString &text) const;

signals:
    void changed();
    void transcriptReady(const QString &text);

private:
    QString findExecutable(const QStringList &names) const;
    QString findVoiceModel() const;
    QString findWhisperModel() const;
    QString neuralVoiceAdapter() const;
    bool neuralVoiceAvailable() const;
    QString naturalSpeechText(const QString &text) const;
    QStringList speechChunks(const QString &text) const;
    bool synthesizeNextChunk();
    bool speakPiper(const QString &text);
    void playWave(const QString &wavPath, QObject *cleanupOwner=nullptr);
    void setState(const QString &state);

    QString m_state="prêt";
    QString m_lastTranscript;
    QString m_voiceStatus="Voix locale : détection…";
    QString m_voiceEngine="détection";
    bool m_speaking=false;
    bool m_listening=false;
    bool m_autoSpeak=true;
    bool m_stopRequested=false;
    QStringList m_speechQueue;
    QProcess *m_speech=nullptr;
    QProcess *m_listener=nullptr;
};
