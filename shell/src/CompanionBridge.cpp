#include "CompanionBridge.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
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
    QProcess p; p.start(python,{adapter,"--output","/tmp/quantic-voice-probe.wav","--probe"});
    if(!p.waitForStarted(180)||!p.waitForFinished(2200)) return false;
    QJsonParseError err; const auto doc=QJsonDocument::fromJson(p.readAllStandardOutput(),&err);
    return p.exitCode()==0&&err.error==QJsonParseError::NoError&&doc.isObject()&&doc.object().value("selected").toString()!="none";
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
    if(out.size()>1400){
        out=out.left(1400);
        const int lastStop=qMax(out.lastIndexOf('.'), qMax(out.lastIndexOf('!'), out.lastIndexOf('?')));
        if(lastStop>650) out=out.left(lastStop+1);
        else { const int space=out.lastIndexOf(' '); if(space>0) out=out.left(space)+"."; }
    }
    return out;
}
QString CompanionBridge::speechPreview(const QString &text) const { return naturalSpeechText(text); }

QStringList CompanionBridge::speechChunks(const QString &text) const {
    QStringList out;
    const QString clean=naturalSpeechText(text);
    if(clean.isEmpty()) return out;
    const auto parts=clean.split(QRegularExpression("(?<=[.!?…])\\s+"),Qt::SkipEmptyParts);
    QString current;
    for(QString part:parts){
        part=part.trimmed(); if(part.isEmpty())continue;
        if(part.size()>260){
            const auto clauses=part.split(QRegularExpression("(?<=[,;:])\\s+"),Qt::SkipEmptyParts);
            for(QString clause:clauses){
                clause=clause.trimmed();
                if(!current.isEmpty()&&current.size()+clause.size()+1>220){out.append(current.trimmed());current.clear();}
                current += (current.isEmpty()?"":" ")+clause;
            }
        }else{
            if(!current.isEmpty()&&current.size()+part.size()+1>220){out.append(current.trimmed());current.clear();}
            current += (current.isEmpty()?"":" ")+part;
        }
    }
    if(!current.trimmed().isEmpty())out.append(current.trimmed());
    return out.mid(0,12);
}

void CompanionBridge::refresh(){
    const bool neural=neuralVoiceAvailable();
    const bool piper=!findExecutable({"piper","piper-tts"}).isEmpty();
    const bool voice=!findVoiceModel().isEmpty();
    const bool whisper=!findExecutable({"whisper-cli","whisper-cpp","main"}).isEmpty();
    const bool sttModel=!findWhisperModel().isEmpty();
    if(neural){ m_voiceEngine="Neural adaptatif · Chatterbox/Kokoro"; m_voiceStatus=(whisper&&sttModel)?"Voix premium fluide : prête":"Voix premium : sortie prête · écoute indisponible"; }
    else if(piper&&voice){ m_voiceEngine="Piper · secours"; m_voiceStatus=(whisper&&sttModel)?"Voix locale : mode secours":"Voix locale : sortie prête · écoute indisponible"; }
    else { m_voiceEngine="indisponible"; m_voiceStatus="Voix locale : composants à installer"; }
    emit changed();
}

void CompanionBridge::playWave(const QString &wavPath, QObject *cleanupOwner){
    const QString player=findExecutable({"pw-play","aplay"});
    if(player.isEmpty()){
        QFile::remove(wavPath); if(cleanupOwner)cleanupOwner->deleteLater(); m_speech=nullptr;
        if(!m_stopRequested&&synthesizeNextChunk())return;
        m_speaking=false; setState("prêt"); emit changed(); return;
    }
    QProcess *play=new QProcess(this); m_speech=play;
    connect(play,&QProcess::finished,this,[this,play,wavPath,cleanupOwner](int,QProcess::ExitStatus){
        play->deleteLater(); QFile::remove(wavPath); if(cleanupOwner)cleanupOwner->deleteLater(); m_speech=nullptr;
        if(!m_stopRequested&&synthesizeNextChunk())return;
        m_speaking=false; m_speechQueue.clear(); setState("prêt"); emit changed();
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
        synth->deleteLater(); m_speech=nullptr;
        if(code!=0){ QFile::remove(wavPath); wav->deleteLater(); if(!m_stopRequested&&synthesizeNextChunk())return; m_speaking=false; setState("prêt"); emit changed(); return; }
        playWave(wavPath,wav);
    });
    synth->start(piper,{"--model",model,"--output_file",wavPath,"--length_scale","0.94","--noise_scale","0.62","--noise_w","0.82","--sentence_silence","0.10"});
    if(!synth->waitForStarted(180)){ synth->deleteLater(); QFile::remove(wavPath); wav->deleteLater(); m_speech=nullptr; return false; }
    synth->write(clean.toUtf8()); synth->write("\n"); synth->closeWriteChannel();
    return true;
}

bool CompanionBridge::synthesizeNextChunk(){
    if(m_stopRequested||m_speechQueue.isEmpty()) return false;
    const QString chunk=m_speechQueue.takeFirst();
    const QString python=findExecutable({"python3"}); const QString adapter=neuralVoiceAdapter();
    if(!python.isEmpty()&&!adapter.isEmpty()&&neuralVoiceAvailable()){
        QTemporaryFile *wav=new QTemporaryFile(QDir::tempPath()+"/quantic-neural-XXXXXX.wav",this); wav->setAutoRemove(false);
        if(!wav->open()){wav->deleteLater();return speakPiper(chunk);} const QString wavPath=wav->fileName(); wav->close();
        QProcess *synth=new QProcess(this); m_speech=synth; m_speaking=true; setState("parle"); emit changed();
        connect(synth,&QProcess::finished,this,[this,synth,wav,wavPath,chunk](int code,QProcess::ExitStatus){
            const QByteArray stdoutData=synth->readAllStandardOutput(); synth->deleteLater(); m_speech=nullptr;
            if(code==0&&QFileInfo(wavPath).size()>1024){
                QJsonParseError err;const auto doc=QJsonDocument::fromJson(stdoutData,&err);
                if(err.error==QJsonParseError::NoError&&doc.isObject()){
                    const QString engine=doc.object().value("engine").toString();
                    if(engine.contains("chatterbox"))m_voiceEngine="Chatterbox Multilingual · français";
                    else if(engine.contains("kokoro"))m_voiceEngine="Kokoro 82M · français";
                }
                emit changed(); playWave(wavPath,wav); return;
            }
            QFile::remove(wavPath); wav->deleteLater();
            if(!m_stopRequested&&speakPiper(chunk))return;
            if(!m_stopRequested&&synthesizeNextChunk())return;
            m_speaking=false;setState("prêt");emit changed();
        });
        synth->start(python,{adapter,"--output",wavPath,"--engine","auto","--voice","ff_siwis","--speed","1.03",chunk});
        if(synth->waitForStarted(220)) return true;
        synth->deleteLater(); QFile::remove(wavPath); wav->deleteLater(); m_speech=nullptr;
    }
    return speakPiper(chunk);
}

bool CompanionBridge::speak(const QString &text){
    if(m_speaking||m_listening)return false;
    m_speechQueue=speechChunks(text);
    if(m_speechQueue.isEmpty())return false;
    m_stopRequested=false; m_speaking=true; setState("parle"); emit changed();
    if(synthesizeNextChunk())return true;
    m_speaking=false;setState("prêt");emit changed();return false;
}
void CompanionBridge::stopSpeaking(){
    m_stopRequested=true;m_speechQueue.clear();if(m_speech){m_speech->kill();m_speech=nullptr;}m_speaking=false;setState("prêt");emit changed();
}
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
