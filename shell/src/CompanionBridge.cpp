#include "CompanionBridge.h"
#include <QDir>
#include <QFile>
#include <QStandardPaths>
#include <QTemporaryFile>

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
void CompanionBridge::setState(const QString &state){ if(m_state==state)return; m_state=state; emit changed(); }
void CompanionBridge::refresh(){
    const bool piper=!findExecutable({"piper","piper-tts"}).isEmpty();
    const bool voice=!findVoiceModel().isEmpty();
    const bool whisper=!findExecutable({"whisper-cli","whisper-cpp","main"}).isEmpty();
    const bool sttModel=!findWhisperModel().isEmpty();
    if(piper&&voice&&whisper&&sttModel) m_voiceStatus="Voix locale : prête";
    else if(piper&&voice) m_voiceStatus="Voix locale : sortie prête · écoute indisponible";
    else m_voiceStatus="Voix locale : composants à installer";
    emit changed();
}
bool CompanionBridge::speak(const QString &text){
    const QString clean=text.trimmed().left(1600);
    if(clean.isEmpty()||m_speaking)return false;
    const QString piper=findExecutable({"piper","piper-tts"}); const QString model=findVoiceModel();
    const QString player=findExecutable({"pw-play","aplay"});
    if(piper.isEmpty()||model.isEmpty()||player.isEmpty()){ refresh(); return false; }
    QTemporaryFile *wav=new QTemporaryFile(QDir::tempPath()+"/quantic-voice-XXXXXX.wav",this); wav->setAutoRemove(false);
    if(!wav->open()){wav->deleteLater();return false;} const QString wavPath=wav->fileName(); wav->close();
    QProcess *synth=new QProcess(this); m_speech=synth; m_speaking=true; setState("parle"); emit changed();
    connect(synth,&QProcess::finished,this,[this,synth,wav,wavPath,player](int code,QProcess::ExitStatus){
        synth->deleteLater();
        if(code!=0){ QFile::remove(wavPath); wav->deleteLater(); m_speaking=false; m_speech=nullptr; setState("prêt"); emit changed(); return; }
        QProcess *play=new QProcess(this); m_speech=play;
        connect(play,&QProcess::finished,this,[this,play,wav,wavPath](int,QProcess::ExitStatus){ play->deleteLater(); QFile::remove(wavPath); wav->deleteLater(); m_speaking=false; m_speech=nullptr; setState("prêt"); emit changed(); });
        play->start(player,{wavPath});
    });
    synth->start(piper,{"--model",model,"--output_file",wavPath});
    if(!synth->waitForStarted(180)){ synth->deleteLater(); QFile::remove(wavPath); wav->deleteLater(); m_speaking=false; m_speech=nullptr; setState("prêt"); emit changed(); return false; }
    synth->write(clean.toUtf8()); synth->write("\n"); synth->closeWriteChannel();
    return true;
}
void CompanionBridge::stopSpeaking(){ if(m_speech){m_speech->kill();} m_speaking=false; m_speech=nullptr; setState("prêt"); emit changed(); }
bool CompanionBridge::listenOnce(){
    if(m_listening)return false;
    const QString recorder=findExecutable({"pw-record","arecord"});
    const QString whisper=findExecutable({"whisper-cli","whisper-cpp","main"}); const QString model=findWhisperModel();
    if(recorder.isEmpty()||whisper.isEmpty()||model.isEmpty()){refresh();return false;}
    QTemporaryFile *wav=new QTemporaryFile(QDir::tempPath()+"/quantic-listen-XXXXXX.wav",this); wav->setAutoRemove(false);
    if(!wav->open()){wav->deleteLater();return false;} const QString wavPath=wav->fileName(); wav->close();
    QProcess *rec=new QProcess(this); m_listener=rec; m_listening=true; setState("écoute"); emit changed();
    QStringList args;
    if(recorder.endsWith("pw-record")) args={"--rate","16000","--channels","1",wavPath}; else args={"-f","S16_LE","-r","16000","-c","1","-d","6",wavPath};
    rec->start(recorder,args);
    if(!rec->waitForStarted(200)){rec->deleteLater();QFile::remove(wavPath);wav->deleteLater();m_listening=false;setState("prêt");emit changed();return false;}
    QTimer::singleShot(6200,this,[this,rec,wav,wavPath,whisper,model](){
        if(rec->state()!=QProcess::NotRunning) rec->terminate(); rec->waitForFinished(500); rec->deleteLater();
        QProcess *stt=new QProcess(this); m_listener=stt;
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
