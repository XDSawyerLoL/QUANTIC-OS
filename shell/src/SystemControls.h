#pragma once

#include <QObject>
#include <QString>

class SystemControls final : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool wifiEnabled READ wifiEnabled NOTIFY stateChanged)
    Q_PROPERTY(bool bluetoothEnabled READ bluetoothEnabled NOTIFY stateChanged)
    Q_PROPERTY(bool muted READ muted NOTIFY stateChanged)
    Q_PROPERTY(int volumePercent READ volumePercent NOTIFY stateChanged)
    Q_PROPERTY(int brightnessPercent READ brightnessPercent NOTIFY stateChanged)
    Q_PROPERTY(QString powerProfile READ powerProfile NOTIFY stateChanged)
    Q_PROPERTY(QString statusText READ statusText NOTIFY stateChanged)

public:
    explicit SystemControls(QObject *parent=nullptr);

    bool wifiEnabled() const { return m_wifiEnabled; }
    bool bluetoothEnabled() const { return m_bluetoothEnabled; }
    bool muted() const { return m_muted; }
    int volumePercent() const { return m_volumePercent; }
    int brightnessPercent() const { return m_brightnessPercent; }
    QString powerProfile() const { return m_powerProfile; }
    QString statusText() const { return m_statusText; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void setWifiEnabled(bool enabled);
    Q_INVOKABLE void setBluetoothEnabled(bool enabled);
    Q_INVOKABLE void setMuted(bool muted);
    Q_INVOKABLE void setVolumePercent(int percent);
    Q_INVOKABLE void setBrightnessPercent(int percent);
    Q_INVOKABLE void cyclePowerProfile();

signals:
    void stateChanged();

private:
    bool runControl(const QString &program, const QStringList &args, const QString &successText);
    QString runRead(const QString &program, const QStringList &args, int timeoutMs=500) const;
    void probeWifi();
    void probeBluetooth();
    void probeAudio();
    void probeBrightness();
    void probePowerProfile();

    bool m_wifiEnabled=false;
    bool m_bluetoothEnabled=false;
    bool m_muted=false;
    int m_volumePercent=0;
    int m_brightnessPercent=-1;
    QString m_powerProfile="indisponible";
    QString m_statusText="Réglages système prêts";
};
