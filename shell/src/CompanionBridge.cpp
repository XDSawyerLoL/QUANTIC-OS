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
#include <memory>

namespace {
struct VadState {
    int ticks=0;
    int loudTicks=0;
    int silentTicks=0;
    double noiseFloor=180.0;
    bool heardSpeech=false;
};

double pcm16MeanAbsTail(const QString &wavPath) {
    QFile f(wavPath);
    if(!f.open(QIODevice::ReadOnly))return -1.0;
    const qint64 size=f.size();
    if(size<=44)return -1.0;
    qint64 start=qMax<qint64>(44,size-3200);
    if(((start-44)&1)!=0)++start;
    if(!f.seek(start))return -1.0;
    const QByteArray pcm=f.read(3200);
    if(pcm.size()<2)return -1.0;
    const auto *data=reinterpret_cast<const unsigned char *>(pcm.constData());
    qint64 sum=0;int samples=0;
    for(int i=0;i+1<pcm.size();i+=2){
        const quint16 raw=quint16(data[i])|(quint16(data[i+1])<<8);
        const qint16 sample=static_cast<qint16>(raw);
        sum+=qAbs(int(sample));++samples;
    }
    return samples?double(sum)/double(samples):-1.0;
}
}

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
    const QString python=findExecutable({"python3"});
    const bool neuralCandidate=!python.isEmpty()&&!neuralVoiceAdapter().isEmpty();
    const bool piper=!findExecutable({"piper","piper-tts"}).isEmpty();
    const bool voice=!findVoiceModel().isEmpty();
    const bool whisper=!findExecutable({"whisper-cli","whisper-cpp","main"}).isEmpty();
    const bool sttModel=!findWhisperModel().isEmpty();
    m_neuralVoiceReady=neuralCandidate;
    if(neuralCandidate){
        m_voiceEngine=m_voiceWorkerReady?m_voiceEngine:"Neural adaptatif · préchauffage";
        m_voiceStatus=(whisper&&sttModel)?"Voix premium : préchauffage local":"Voix premium : sortie en préchauffage · écoute indisponible";
        ensureNeuralWorker();
    }else if(piper&&voice){
        m_voiceEngine="Piper · secours";
        m_voiceStatus=(whisper&&sttModel)?"Voix locale : mode secours":"Voix locale : sortie prête · écoute indisponible";
    }else{
        m_voiceEngine="indisponible";
        m_voiceStatus="Voix locale : composants à installer";
    }
    emit changed();
}

bool CompanionBridge::ensureNeuralWorker(){
    if(!m_neuralVoiceReady)return false;
    if(m_voiceWorker&&m_voiceWorker->state()!=QProcess::NotRunning)return true;
    const QString python=findExecutable({"python3"});const QString adapter=neuralVoiceAdapter();
    if(python.isEmpty()||adapter.isEmpty())return false;
    QProcess *worker=new QProcess(this);m_voiceWorker=worker;m_voiceWorkerReady=false;
    connect(worker,&QProcess::readyReadStandardOutput,this,[this,worker](){if(worker==m_voiceWorker)handleNeuralWorkerOutput();});
    connect(worker,&QProcess::finished,this,[this,worker](int,QProcess::ExitStatus){
        if(worker!=m_voiceWorker){worker->deleteLater();return;}
        handleNeuralWorkerOutput();
        const bool hadPending=m_voicePendingId>0;
        const QString pendingChunk=m_voicePendingChunk;
        const QString pendingWav=m_voicePendingWav;
        m_voiceWorker=nullptr;m_voiceWorkerReady=false;m_voicePendingId=0;m_voicePendingChunk.clear();m_voicePendingWav.clear();
        if(!pendingWav.isEmpty())QFile::remove(pendingWav);
        if(!m_stopRequested&&hadPending&&!pendingChunk.isEmpty()){
            if(speakPiper(pendingChunk)){worker->deleteLater();return;}
            if(synthesizeNextChunk()){worker->deleteLater();return;}
            if(!m_audioPlaying&&m_readyAudioQueue.isEmpty()){m_speaking=false;setState("prêt");emit changed();}
        }
        worker->deleteLater();
    });
    worker->start(python,{adapter,"--server","--engine","auto","--voice","ff_siwis","--speed","1.03"});
    if(!worker->waitForStarted(220)){
        m_voiceWorker=nullptr;worker->deleteLater();return false;
    }
    return true;
}

void CompanionBridge::handleNeuralWorkerOutput(){
    if(!m_voiceWorker)return;
    while(m_voiceWorker->canReadLine()){
        const QByteArray line=m_voiceWorker->readLine().trimmed();if(line.isEmpty())continue;
        QJsonParseError err;const auto doc=QJsonDocument::fromJson(line,&err);if(err.error!=QJsonParseError::NoError||!doc.isObject())continue;
        const auto o=doc.object();const QString type=o.value("type").toString();
        if(type=="ready"){
            const bool ok=o.value("ok").toBool();m_voiceWorkerReady=ok;
            if(!ok){m_neuralVoiceReady=false;m_voiceEngine="Piper · secours";m_voiceStatus="Voix neuronale indisponible · secours local";emit changed();continue;}
            const QString selected=o.value("selected").toString();
            if(selected=="chatterbox")m_voiceEngine="Chatterbox Multilingual · chaud";
            else if(selected=="kokoro")m_voiceEngine="Kokoro 82M · chaud";
            else m_voiceEngine="Neural adaptatif · chaud";
            m_voiceStatus="Voix premium fluide : prête";emit changed();continue;
        }
        if(type!="result")continue;
        const int id=o.value("id").toInt();if(id<=0||id!=m_voicePendingId)continue;
        const QString chunk=m_voicePendingChunk;const QString wavPath=m_voicePendingWav;
        m_voicePendingId=0;m_voicePendingChunk.clear();m_voicePendingWav.clear();
        if(o.value("ok").toBool()&&QFileInfo(wavPath).size()>1024){
            const QString engine=o.value("engine").toString();
            if(engine.contains("chatterbox"))m_voiceEngine="Chatterbox Multilingual · français";
            else if(engine.contains("kokoro"))m_voiceEngine="Kokoro 82M · français";
            emit changed();
            playWave(wavPath);
            if(!m_stopRequested&&m_readyAudioQueue.size()<4&&!m_speechQueue.isEmpty())synthesizeNextChunk();
            return;
        }
        QFile::remove(wavPath);
        if(!m_stopRequested&&speakPiper(chunk))return;
        if(!m_stopRequested&&synthesizeNextChunk())return;
        if(!m_audioPlaying&&m_readyAudioQueue.isEmpty()){m_speaking=false;setState("prêt");emit changed();}
    }
}

void CompanionBridge::playWave(const QString &wavPath, QObject *cleanupOwner){
    if(cleanupOwner)cleanupOwner->deleteLater();
    if(wavPath.isEmpty()||!QFile::exists(wavPath)){
        if(!m_stopRequested&&m_voicePendingId==0&&!m_speechQueue.isEmpty())synthesizeNextChunk();
        return;
    }
    m_readyAudioQueue.append(wavPath);
    while(m_readyAudioQueue.size()>6){const QString dropped=m_readyAudioQueue.takeLast();QFile::remove(dropped);}
    playNextReadyAudio();
}

void CompanionBridge::playNextReadyAudio(){
    if(m_stopRequested||m_audioPlaying)return;
    if(m_readyAudioQueue.isEmpty()){
        if(m_voicePendingId==0&&!m_speechQueue.isEmpty()){synthesizeNextChunk();return;}
        if(m_voicePendingId==0&&!m_speech){m_speaking=false;setState("prêt");emit changed();}
        return;
    }
    const QString wavPath=m_readyAudioQueue.takeFirst();
    const QString player=findExecutable({"pw-play","aplay"});
    if(player.isEmpty()){
        QFile::remove(wavPath);
        playNextReadyAudio();
        return;
    }
    QProcess *play=new QProcess(this);m_player=play;m_audioPlaying=true;m_speaking=true;setState("parle");emit changed();
    connect(play,&QProcess::finished,this,[this,play,wavPath](int,QProcess::ExitStatus){
        play->deleteLater();QFile::remove(wavPath);
        if(m_player==play)m_player=nullptr;
        m_audioPlaying=false;
        if(m_stopRequested)return;
        playNextReadyAudio();
        if(m_voicePendingId==0&&m_readyAudioQueue.size()<4&&!m_speechQueue.isEmpty())synthesizeNextChunk();
    });
    play->start(player,{wavPath});
    if(!play->waitForStarted(120)){
        play->deleteLater();m_player=nullptr;m_audioPlaying=false;QFile::remove(wavPath);playNextReadyAudio();
    }
}

bool CompanionBridge::speakPiper(const QString &clean){
    const QString piper=findExecutable({"piper","piper-tts"}); const QString model=findVoiceModel();
    if(piper.isEmpty()||model.isEmpty()) return false;
    QTemporaryFile *wav=new QTemporaryFile(QDir::tempPath()+"/quantic-piper-XXXXXX.wav",this); wav->setAutoRemove(false);
    if(!wav->open()){wav->deleteLater();return false;} const QString wavPath=wav->fileName(); wav->close();
    QProcess *synth=new QProcess(this); m_speech=synth; m_speaking=true; m_voiceEngine="Piper · secours"; setState("parle"); emit changed();
    connect(synth,&QProcess::finished,this,[this,synth,wav,wavPath](int code,QProcess::ExitStatus){
        synth->deleteLater();if(m_speech==synth)m_speech=nullptr;
        if(code!=0){ QFile::remove(wavPath); wav->deleteLater(); if(!m_stopRequested&&synthesizeNextChunk())return; if(!m_audioPlaying&&m_readyAudioQueue.isEmpty()){m_speaking=false;setState("prêt");emit changed();} return; }
        playWave(wavPath,wav);
    });
    synth->start(piper,{"--model",model,"--output_file",wavPath,"--length_scale","0.94","--noise_scale","0.62","--noise_w","0.82","--sentence_silence","0.10"});
    if(!synth->waitForStarted(180)){ synth->deleteLater(); QFile::remove(wavPath); wav->deleteLater(); m_speech=nullptr; return false; }
    synth->write(clean.toUtf8()); synth->write("\n"); synth->closeWriteChannel();
    return true;
}

bool CompanionBridge::synthesizeNextChunk(){
    if(m_stopRequested)return false;
    if(m_voicePendingId>0)return true;
    if(m_speechQueue.isEmpty())return false;
    const QString chunk=m_speechQueue.takeFirst();
    if(m_neuralVoiceReady&&ensureNeuralWorker()){
        QTemporaryFile wav(QDir::tempPath()+"/quantic-neural-XXXXXX.wav");wav.setAutoRemove(false);
        if(wav.open()){
            const QString wavPath=wav.fileName();wav.close();
            m_voicePendingId=++m_voiceRequestId;m_voicePendingWav=wavPath;m_voicePendingChunk=chunk;
            QJsonObject request;request.insert("id",m_voicePendingId);request.insert("text",chunk);request.insert("output",wavPath);request.insert("voice","ff_siwis");request.insert("speed",1.03);
            QByteArray payload=QJsonDocument(request).toJson(QJsonDocument::Compact);payload.append('\n');
            if(m_voiceWorker&&m_voiceWorker->write(payload)>=0){m_speaking=true;setState("parle");emit changed();return true;}
            m_voicePendingId=0;m_voicePendingWav.clear();m_voicePendingChunk.clear();QFile::remove(wavPath);
        }
    }
    return speakPiper(chunk);
}

bool CompanionBridge::enqueueSpeech(const QString &text){
    if(m_listening)return false;
    const QStringList chunks=speechChunks(text);if(chunks.isEmpty())return false;
    m_stopRequested=false;m_speechQueue.append(chunks);while(m_speechQueue.size()>18)m_speechQueue.removeLast();
    if(m_speaking){
        if(m_voicePendingId==0&&!m_speech&&m_readyAudioQueue.size()<4)synthesizeNextChunk();
        emit changed();return true;
    }
    m_speaking=true;setState("parle");emit changed();
    if(synthesizeNextChunk())return true;
    m_speaking=false;setState("prêt");emit changed();return false;
}

void CompanionBridge::beginStreamingSpeech(){
    m_streamSpeechBuffer.clear();
    if(m_speaking)stopSpeaking();
    m_stopRequested=false;
}

void CompanionBridge::pushStreamingText(const QString &delta){
    if(delta.isEmpty()||!m_autoSpeak)return;
    m_streamSpeechBuffer+=delta;
    for(;;){
        int cut=-1;const int maxScan=qMin(m_streamSpeechBuffer.size(),260);
        for(int i=0;i<maxScan;++i){
            const QChar c=m_streamSpeechBuffer.at(i);
            const bool terminal=c=='.'||c=='!'||c=='?'||c==QChar(0x2026)||c=='\n';
            const bool boundary=(i+1<m_streamSpeechBuffer.size())&&m_streamSpeechBuffer.at(i+1).isSpace();
            if(terminal&&boundary&&i>=28){cut=i+1;break;}
        }
        if(cut<0&&m_streamSpeechBuffer.size()>190){
            const int clause=qMax(m_streamSpeechBuffer.lastIndexOf(','),qMax(m_streamSpeechBuffer.lastIndexOf(';'),m_streamSpeechBuffer.lastIndexOf(':')));
            if(clause>=80&&clause<=220)cut=clause+1;
        }
        if(cut<0&&m_streamSpeechBuffer.size()>240){
            const int space=m_streamSpeechBuffer.lastIndexOf(' ',220);if(space>=100)cut=space;
        }
        if(cut<0)break;
        const QString phrase=m_streamSpeechBuffer.left(cut).trimmed();m_streamSpeechBuffer=m_streamSpeechBuffer.mid(cut).trimmed();
        if(!phrase.isEmpty())enqueueSpeech(phrase);
    }
}

void CompanionBridge::finishStreamingSpeech(){
    const QString tail=m_streamSpeechBuffer.trimmed();m_streamSpeechBuffer.clear();
    if(m_autoSpeak&&!tail.isEmpty())enqueueSpeech(tail);
}

bool CompanionBridge::speak(const QString &text){
    if(m_speaking||m_listening)return false;
    m_speechQueue.clear();
    return enqueueSpeech(text);
}
void CompanionBridge::stopSpeaking(){
    m_stopRequested=true;m_streamSpeechBuffer.clear();m_speechQueue.clear();
    if(m_speech){QProcess *speech=m_speech;m_speech=nullptr;speech->kill();}
    if(m_player){QProcess *player=m_player;m_player=nullptr;player->kill();}
    m_audioPlaying=false;
    for(const QString &path:m_readyAudioQueue)QFile::remove(path);m_readyAudioQueue.clear();
    if(m_voicePendingId>0){
        m_voicePendingId=0;m_voicePendingChunk.clear();if(!m_voicePendingWav.isEmpty())QFile::remove(m_voicePendingWav);m_voicePendingWav.clear();
        if(m_voiceWorker){QProcess *worker=m_voiceWorker;m_voiceWorker=nullptr;m_voiceWorkerReady=false;worker->kill();worker->deleteLater();}
    }
    m_speaking=false;setState("prêt");emit changed();
}
bool CompanionBridge::listenOnce(){
    if(m_listening)return false;
    const QString recorder=findExecutable({"arecord","pw-record"});
    const QString whisper=findExecutable({"whisper-cli","whisper-cpp","main"}); const QString model=findWhisperModel();
    if(recorder.isEmpty()||whisper.isEmpty()||model.isEmpty()){refresh();return false;}
    QTemporaryFile *wav=new QTemporaryFile(QDir::tempPath()+"/quantic-listen-XXXXXX.wav",this); wav->setAutoRemove(false);
    if(!wav->open()){wav->deleteLater();return false;} const QString wavPath=wav->fileName(); wav->close();
    if(m_speaking) stopSpeaking();
    QProcess *rec=new QProcess(this); m_listener=rec; m_listening=true; setState("écoute"); emit changed();
    const bool adaptiveVad=recorder.endsWith("arecord");
    const auto vadState=std::make_shared<VadState>();
    QStringList args;
    if(adaptiveVad) args={"-q","-f","S16_LE","-r","16000","-c","1","-t","wav",wavPath};
    else args={"--rate","16000","--channels","1",wavPath};
    rec->start(recorder,args);
    if(!rec->waitForStarted(200)){rec->deleteLater();QFile::remove(wavPath);wav->deleteLater();m_listening=false;setState("prêt");emit changed();return false;}

    QTimer *endpointTimer=new QTimer(rec);endpointTimer->setInterval(100);
    connect(rec,&QProcess::finished,this,[this,rec,endpointTimer,wav,wavPath,whisper,model,vadState,adaptiveVad](int,QProcess::ExitStatus){
        endpointTimer->stop();rec->deleteLater();
        if(adaptiveVad&&!vadState->heardSpeech){
            QFile::remove(wavPath);wav->deleteLater();m_lastTranscript.clear();m_listening=false;m_listener=nullptr;setState("prêt");emit changed();return;
        }
        QProcess *stt=new QProcess(this);m_listener=stt;setState("comprend");emit changed();
        connect(stt,&QProcess::finished,this,[this,stt,wav,wavPath](int code,QProcess::ExitStatus){
            QString out=QString::fromUtf8(stt->readAllStandardOutput());if(out.isEmpty())out=QString::fromUtf8(stt->readAllStandardError());
            stt->deleteLater();QFile::remove(wavPath);wav->deleteLater();
            QStringList lines=out.split('\n',Qt::SkipEmptyParts);QString text;
            for(auto line:lines){line=line.trimmed();if(line.startsWith('[')&&line.contains(']'))line=line.section(']',1).trimmed();if(line.size()>1&&!line.startsWith("whisper_"))text+=(text.isEmpty()?"":" ")+line;}
            m_lastTranscript=text.left(1200).trimmed();m_listening=false;m_listener=nullptr;setState("prêt");emit changed();if(code==0&&!m_lastTranscript.isEmpty())emit transcriptReady(m_lastTranscript);
        });
        stt->start(whisper,{"-m",model,"-f",wavPath,"-l","fr","-nt"});
    });

    if(adaptiveVad){
        connect(endpointTimer,&QTimer::timeout,this,[rec,endpointTimer,wavPath,vadState](){
            if(rec->state()==QProcess::NotRunning){endpointTimer->stop();return;}
            ++vadState->ticks;
            const double level=pcm16MeanAbsTail(wavPath);
            if(level>=0.0){
                if(vadState->ticks<=2){
                    vadState->noiseFloor=(vadState->noiseFloor+level)*0.5;
                }else{
                    const double startThreshold=qMax(380.0,vadState->noiseFloor*2.4+120.0);
                    const bool loud=level>startThreshold;
                    if(!vadState->heardSpeech){
                        if(loud)++vadState->loudTicks;else{vadState->loudTicks=0;vadState->noiseFloor=vadState->noiseFloor*0.86+level*0.14;}
                        if(vadState->loudTicks>=2){vadState->heardSpeech=true;vadState->silentTicks=0;}
                    }else{
                        const double silenceThreshold=qMax(300.0,vadState->noiseFloor*1.65+80.0);
                        if(level<silenceThreshold)++vadState->silentTicks;else vadState->silentTicks=0;
                    }
                }
            }
            const bool speechEnded=vadState->heardSpeech&&vadState->silentTicks>=7&&vadState->ticks>=10;
            const bool hardLimit=vadState->ticks>=60;
            if(speechEnded||hardLimit){
                endpointTimer->stop();rec->terminate();
                QTimer::singleShot(260,rec,[rec](){if(rec->state()!=QProcess::NotRunning)rec->kill();});
            }
        });
        endpointTimer->start();
    }else{
        QTimer::singleShot(6000,rec,[rec](){if(rec->state()!=QProcess::NotRunning)rec->terminate();});
    }
    return true;
}
