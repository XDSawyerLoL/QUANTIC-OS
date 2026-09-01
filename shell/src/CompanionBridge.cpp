#include "CompanionBridge.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QTemporaryFile>
#include <QTimer>

CompanionBridge::CompanionBridge(QObject *parent): QObject(parent) { refresh(); }

QString CompanionBridge::findExecutable(const QStringList &names) const {
    for(const auto &name:names){ const QString exe=QStandardPaths::findExecutable(name); if(!exe.isEmpty()) return exe; }
    return {};
}
QString CompanionBridge::findVoiceModel() const {
    const QStringList candidates={
        "/var/lib/quantic/models/voices/fr_FR-siwis-medium.onnx",
        "/usr/share/quantic/models/fr_FR-siwis-medium.onnx",
        "/opt/quantic/models/fr_FR-siwis-medium.onnx"
    };
    for(const auto &path:candidates) if(QFile::exists(path)) return path;
    return {};
}
QString CompanionBridge::findWhisperModel() const {
    const QStringList candidates={
        "/var/lib/quantic/models/stt/ggml-base.bin",
        "/usr/share/quantic/models/ggml-base.bin",
        "/opt/quantic/models/ggml-base.bin"
    };
    for(const auto &path:candidates) if(QFile::exists(path)) return path;
    return {};
}
QString CompanionBridge::neuralVoiceAdapter() const {
    const QStringList candidates={
        "/usr/lib/quantic/services/qvoice_neural.py",
        QDir(QCoreApplication::applicationDirPath()).filePath("../../services/qvoice_neural.py")
    };
    for(const auto &path:candidates){ const QString clean=QDir::cleanPath(path); if(QFile::exists(clean)) return clean; }
    return {};
}
bool CompanionBridge::neuralVoiceAvailable() const {
    const QString python=findExecutable({"python3"}); const QString adapter=neuralVoiceAdapter();
    if(python.isEmpty()||adapter.isEmpty()) return false;
    QProcess p; p.start(python,{"-c","import kokoro, soundfile, numpy"});
    return p.waitForStarted(180)&&p.waitForFinished(1800)&&p.exitCode()==0;
}
void CompanionBridge::setState(const QString &state){ if(m_state==state)return; m_state=state; emit changed(); }
void CompanionBridge::setAutoSpeak(bool enabled){ if(m_autoSpeak==enabled)return; m_autoSpeak=enabled; emit changed(); }

QString CompanionBridge::naturalSpeechText(const QString &text) const {
    QString out=text;
    out.remove(QRegularExpression("```[\\s\\S]*?```"));
    out.replace(QRegularExpression("`([^`]+)`"), "\\1");
    out.replace(QRegularExpression("\\[([^\\]]+)\\]\\([^\\)]+\\)"), "\\1");
    out.replace(QRegularExpression("https?://\\S+"), "ce lien");
    out.replace(QRegularExpression("[\\x{1F000}-\\x{1FAFF}\\x{2600}-\\x{27BF}]"), "");
    out.replace(QRegularExpression("(?m)^\\s*[-*•]+\\s*"), "");
    out.replace(QRegularExpression("(?m)^\\s*#{1,6}\\s*"), "");
    out.replace(QRegularExpression("[*_~>]"), "");
    out.replace(QRegularExpression("\\bIA\\b"), "intelligence artificielle");
    out.replace(QRegularExpression("\\bOS\\b"), "système");
    out.replace(QRegularExpression("\\bCPU\\b"), "processeur");
    out.replace(QRegularExpression("\\bGPU\\b"), "carte graphique");
    out.replace(QRegularExpression("\\bRAM\\b"), "mémoire vive");
    out.replace(QRegularExpression("\\bAPI\\b"), "A P I");
    out.replace(QRegularExpression("\\bURL\\b"), "adresse web");
    out.replace('\n', ". ");
    out.replace(QRegularExpression("\\s+"), " ");
    out.replace(QRegularExpression("([.!?])\\1+"), "\\1");
    out=out.trimmed();
    if(out.size()>1100){
        out=out.left(1100);
        const int lastStop=qMax(out.lastIndexOf('.'), qMax(out.lastIndexOf('!'), out.lastIndexOf('?')));
        if(lastStop>520) out=out.left(lastStop+1);
        else { const int space=out.lastIndexOf(' '); if(space>0) out=out.left(space)+"."; }
    }
    return out;
}
QString CompanionBridge::speechPreview(const QString &text) const { return naturalSpeechText(text); }

void CompanionBridge::refresh(){
    const bool neural=neuralVoiceAvailable();
    const bool piper=!findExecutable({"piper","piper-tts"}).isEmpty();
    const bool voice=!findVoiceModel().isEmpty();
    const bool whisper=!findExecutable({"whisper-cli","whisper-cpp","main"}).isEmpty();
    const bool sttModel=!findWhisperModel().isEmpty();
    if(neural){ m_voiceEngine="Kokoro 82M · français"; m_voiceStatus=(whisper&&sttModel)?"Voix premium locale : prête":"Voix premium locale : sortie prête · écoute indisponible"; }
    else if(piper&&voice){ m_voiceEngine="Piper · secours"; m_voiceStatus=(whisper&&sttModel)?"Voix locale : mode secours":"Voix locale : sortie prête · écoute indisponible"; }
    else { m_voiceEngine="indisponible"; m_voiceStatus="Voix locale : composants à installer"; }
    emit changed();
}

void CompanionBridge::playWave(const QString &wavPath, QObject *cleanupOwner){
    const QString player=findExecutable({"pw-play","aplay"});
    if(player.isEmpty()){ QFile::remove(wavPath); if(cleanupOwner)cleanupOwner->deleteLater(); m_speaking=false; m_speech=nullptr; setState("prêt"); emit changed(); return; }
    QProcess *play=new QProcess(this); m_speech=play;
    connect(play,&QProcess::finished,this,[this,play,wavPath,cleanupOwner](int,QProcess::ExitStatus){
        play->deleteLater(); QFile::remove(wavPath); if(cleanupOwner)cleanupOwner->deleteLater(); m_speaking=false; m_speech=nullptr; setState("prêt"); emit changed();
    });
    play->start(player,{wavPath});
}

bool CompanionBridge::speakPiper(const QString &clean){
    const QString piper=findExecutable({"piper","piper-tts"}); const QString model=findVoiceModel();
    if(piper.isEmpty()||model.isEmpty()) return false;
    QTemporaryFile *wav=new QTemporaryFile(QDir::tempPath()+"/quantic-piper-XXXXXX.wav",this); wav->setAutoRemove(false);
    if(!wav->open()){wav->deleteLater();return false;} const QString wavPath=wav->fileName(); wav->close();
    QProcess *synth=new QProcess(this); m_speech=synth; m_speaking=true; m_voiceEngine="Piper · secours"; setState("parle"); emit changed();
    connect(synth,&QProcess::finished,this,[this,synth,wav,wavPath](int code,QProcess::ExitStatus){
        synth->deleteLater();
        if(code!=0){ QFile::remove(wavPath); wav->deleteLater(); m_speaking=false; m_speech=nullptr; setState("prêt"); emit changed(); return; }
        playWave(wavPath,wav);
    });
    synth->start(piper,{"--model",model,"--output_file",wavPath,"--length_scale","0.94","--noise_scale","0.62","--noise_w","0.82","--sentence_silence","0.14"});
    if(!synth->waitForStarted(180)){ synth->deleteLater(); QFile::remove(wavPath); wav->deleteLater(); m_speaking=false; m_speech=nullptr; setState("prêt"); emit changed(); return false; }
    synth->write(clean.toUtf8()); synth->write("\n"); synth->closeWriteChannel();
    return true;
}

bool CompanionBridge::speak(const QString &text){
    const QString clean=naturalSpeechText(text);
    if(clean.isEmpty()||m_speaking)return false;
    const QString python=findExecutable({"python3"}); const QString adapter=neuralVoiceAdapter();
    if(!python.isEmpty()&&!adapter.isEmpty()&&neuralVoiceAvailable()){
        QTemporaryFile *wav=new QTemporaryFile(QDir::tempPath()+"/quantic-kokoro-XXXXXX.wav",this); wav->setAutoRemove(false);
        if(!wav->open()){wav->deleteLater();return speakPiper(clean);} const QString wavPath=wav->fileName(); wav->close();
        QProcess *synth=new QProcess(this); m_speech=synth; m_speaking=true; m_voiceEngine="Kokoro 82M · français"; setState("parle"); emit changed();
        connect(synth,&QProcess::finished,this,[this,synth,wav,wavPath,clean](int code,QProcess::ExitStatus){
            synth->deleteLater();
            if(code==0&&QFileInfo(wavPath).size()>1024){ playWave(wavPath,wav); return; }
            QFile::remove(wavPath); wav->deleteLater(); m_speaking=false; m_speech=nullptr; setState("prêt"); emit changed();
            speakPiper(clean);
        });
        synth->start(python,{adapter,"--output",wavPath,"--voice","ff_siwis","--speed","1.03",clean});
        if(synth->waitForStarted(220)) return true;
        synth->deleteLater(); QFile::remove(wavPath); wav->deleteLater(); m_speaking=false; m_speech=nullptr;
    }
    return speakPiper(clean);
}
void CompanionBridge::stopSpeaking(){ if(m_speech){m_speech->kill();} m_speaking=false; m_speech=nullptr; setState("prêt"); emit changed(); }
bool CompanionBridge::listenOnce(){
    if(m_listening)return false;
    const QString recorder=findExecutable({"pw-record","arecord"});
    const QString whisper=findExecutable({"whisper-cli","whisper-cpp","main"}); const QString model=findWhisperModel();
    if(recorder.isEmpty()||whisper.isEmpty()||model.isEmpty()){refresh();return false;}
    QTemporaryFile *wav=new QTemporaryFile(QDir::tempPath()+"/quantic-listen-XXXXXX.wav",this); wav->setAutoRemove(false);
    if(!wav->open()){wav->deleteLater();return false;} const QString wavPath=wav->fileName(); wav->close();
    if(m_speaking) stopSpeaking();
    QProcess *rec=new QProcess(this); m_listener=rec; m_listening=true; setState("écoute"); emit changed();
    QStringList args;
    if(recorder.endsWith("pw-record")) args={"--rate","16000","--channels","1",wavPath}; else args={"-f","S16_LE","-r","16000","-c","1","-d","6",wavPath};
    rec->start(recorder,args);
    if(!rec->waitForStarted(200)){rec->deleteLater();QFile::remove(wavPath);wav->deleteLater();m_listening=false;setState("prêt");emit changed();return false;}
    QTimer::singleShot(6200,this,[this,rec,wav,wavPath,whisper,model](){
        if(rec->state()!=QProcess::NotRunning) rec->terminate(); rec->waitForFinished(500); rec->deleteLater();
        QProcess *stt=new QProcess(this); m_listener=stt; setState("comprend"); emit changed();
        connect(stt,&QProcess::finished,this,[this,stt,wav,wavPath](int code,QProcess::ExitStatus){
            QString out=QString::fromUtf8(stt->readAllStandardOutput()); if(out.isEmpty()) out=QString::fromUtf8(stt->readAllStandardError());
            stt->deleteLater(); QFile::remove(wavPath); wav->deleteLater();
            QStringList lines=out.split('\n',Qt::SkipEmptyParts); QString text;
            for(auto line:lines){ line=line.trimmed(); if(line.startsWith('[')&&line.contains(']')) line=line.section(']',1).trimmed(); if(line.size()>1&&!line.startsWith("whisper_")) text += (text.isEmpty()?"":" ")+line; }
            m_lastTranscript=text.left(1200).trimmed(); m_listening=false; m_listener=nullptr; setState("prêt"); emit changed(); if(code==0&&!m_lastTranscript.isEmpty())emit transcriptReady(m_lastTranscript);
        });
        stt->start(whisper,{"-m",model,"-f",wavPath,"-l","fr","-nt"});
    });
    return true;
}
