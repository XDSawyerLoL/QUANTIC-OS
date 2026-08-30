#pragma once
#include <QObject>
#include <QTimer>
#include <QString>
#include <QVariantList>

class Backend final : public QObject {
    Q_OBJECT
    Q_PROPERTY(double cpu READ cpu NOTIFY metricsChanged)
    Q_PROPERTY(double ramPercent READ ramPercent NOTIFY metricsChanged)
    Q_PROPERTY(double ramUsedGb READ ramUsedGb NOTIFY metricsChanged)
    Q_PROPERTY(double ramTotalGb READ ramTotalGb NOTIFY metricsChanged)
    Q_PROPERTY(int gpu READ gpu NOTIFY metricsChanged)
    Q_PROPERTY(QString gpuText READ gpuText NOTIFY metricsChanged)
    Q_PROPERTY(QString workload READ workload NOTIFY metricsChanged)
    Q_PROPERTY(QVariantList cpuHistory READ cpuHistory NOTIFY metricsChanged)
    Q_PROPERTY(QVariantList gpuHistory READ gpuHistory NOTIFY metricsChanged)
    Q_PROPERTY(QVariantList ramHistory READ ramHistory NOTIFY metricsChanged)
    Q_PROPERTY(QString cpuTempText READ cpuTempText NOTIFY metricsChanged)
    Q_PROPERTY(QString diskFreeText READ diskFreeText NOTIFY metricsChanged)
    Q_PROPERTY(QString networkText READ networkText NOTIFY metricsChanged)
    Q_PROPERTY(QString volumeText READ volumeText NOTIFY metricsChanged)
    Q_PROPERTY(bool safeMode READ safeMode NOTIFY metricsChanged)
    Q_PROPERTY(QString localAiStatus READ localAiStatus NOTIFY metricsChanged)
    Q_PROPERTY(QString healthText READ healthText NOTIFY metricsChanged)
    Q_PROPERTY(QString activityTitle READ activityTitle NOTIFY metricsChanged)
    Q_PROPERTY(QString activityDetail READ activityDetail NOTIFY metricsChanged)
    Q_PROPERTY(QString companionMessage READ companionMessage NOTIFY companionChanged)
    Q_PROPERTY(bool companionBusy READ companionBusy NOTIFY companionChanged)
    Q_PROPERTY(QString labOutput READ labOutput NOTIFY labChanged)
public:
    explicit Backend(QObject *parent=nullptr);
    double cpu() const { return m_cpu; }
    double ramPercent() const { return m_ramPercent; }
    double ramUsedGb() const { return m_ramUsedGb; }
    double ramTotalGb() const { return m_ramTotalGb; }
    int gpu() const { return m_gpu; }
    QString gpuText() const { return m_gpu >= 0 ? QString::number(m_gpu)+" %" : "N/D"; }
    QString workload() const { return m_workload; }
    QVariantList cpuHistory() const { return m_cpuHistory; }
    QVariantList gpuHistory() const { return m_gpuHistory; }
    QVariantList ramHistory() const { return m_ramHistory; }
    QString cpuTempText() const { return m_cpuTempC > 0 ? QString::number(m_cpuTempC, 'f', 0)+" °C" : "N/D"; }
    QString diskFreeText() const { return m_diskFreeText; }
    QString networkText() const { return m_networkText; }
    QString volumeText() const { return m_volumeText; }
    bool safeMode() const { return m_safeMode; }
    QString localAiStatus() const { return m_localAiStatus; }
    QString healthText() const { return m_healthText; }
    QString activityTitle() const { return m_activityTitle; }
    QString activityDetail() const { return m_activityDetail; }
    QString companionMessage() const { return m_companion; }
    bool companionBusy() const { return m_companionBusy; }
    QString labOutput() const { return m_labOutput; }
    Q_INVOKABLE void optimize();
    Q_INVOKABLE void openDestination(const QString &name);
    Q_INVOKABLE void askCompanion(const QString &prompt);
    Q_INVOKABLE void runLab(const QString &experiment);
signals:
    void metricsChanged();
    void companionChanged();
    void labChanged();
private slots:
    void refresh();
private:
    static void appendHistory(QVariantList &list, double value, int maxPoints=48);
    int probeGpu();
    double probeCpuTemperature();
    QString probeNetwork();
    QString probeVolume();
    bool probeOllama();
    void updateWorkload();
    double m_cpu=0, m_ramPercent=0, m_ramUsedGb=0, m_ramTotalGb=0, m_cpuTempC=0;
    int m_gpu=-1;
    QString m_workload="Équilibré";
    QVariantList m_cpuHistory, m_gpuHistory, m_ramHistory;
    QString m_diskFreeText="N/D", m_networkText="N/D", m_volumeText="N/D", m_localAiStatus="IA locale : aucun modèle détecté";
    QString m_healthText="Tout fonctionne normalement";
    QString m_activityTitle="Quantic observe la machine en continu";
    QString m_activityDetail="CPU, GPU, mémoire, stockage et pression système sont mesurés avant toute optimisation.";
    bool m_safeMode=false;
    QString m_companion="Quantic est prêt. Je surveille le système sans effectuer d’action sensible sans autorisation.";
    bool m_companionBusy=false;
    QString m_labOutput="Sélectionne une expérience. Les calculs seront exécutés localement par Q-Core.";
    quint64 m_prevTotal=0, m_prevIdle=0;
    QTimer m_timer;
};
